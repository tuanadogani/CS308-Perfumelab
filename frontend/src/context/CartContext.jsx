import { createContext, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import { cartReducer, initialCart, cartCount, cartTotal } from './cartReducer';
import { Link } from 'react-router-dom';
import AddedToCartModal from '../components/AddedToCartModal';
import { useAuth } from './AuthContext';
import { USE_MOCK } from '../api/client';
import { ROLES } from '../constants/roles';
import * as cartApi from '../api/cartApi';
import { syncCart } from '../api/checkoutApi';

const CartContext = createContext(null);
const STORAGE_KEY = 'ml_cart';

function cartWithFeedback(state, action) {
  if (action.type === 'DISMISS_NOTICE') {
    return state.notice?.id === action.id ? { ...state, notice: null } : state;
  }
  if (action.type === 'SYNC_ERROR') {
    const id = (state.noticeSequence ?? 0) + 1;
    return { ...state, notice: { id, message: action.message, success: false }, noticeSequence: id };
  }
  const next = cartReducer(state, action);
  if (action.type !== 'ADD' || !action.product) return next;
  const before = state.items.find((item) => item.productId === action.product.id)?.quantity ?? 0;
  const after = next.items.find((item) => item.productId === action.product.id)?.quantity ?? 0;
  const added = after - before;
  return {
    ...next,
    notice: {
      id: (state.noticeSequence ?? 0) + 1,
      message: added > 0
        ? `${action.product.name} added to your cart${added > 1 ? ` (${added})` : ''}.`
        : action.product.stock <= 0 ? 'This product is out of stock.' : 'All available stock is already in your cart.',
      success: added > 0,
      product: action.product,
      quantity: added,
    },
    noticeSequence: (state.noticeSequence ?? 0) + 1,
  };
}

function loadCart() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const items = raw ? JSON.parse(raw) : [];
    return { items: Array.isArray(items) ? items : [] };
  } catch {
    return initialCart;
  }
}

function saveGuestCart(items) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); } catch { /* ignore */ }
}

export function CartProvider({ children }) {
  // Guests: the cart lives in localStorage, so it is kept after logging in (Requirement 4).
  // Logged-in customers: the backend cart (/api/cart/) is the source of truth. On login the
  // guest cart is merged into it once (POST /cart/merge/) and removed from the browser.
  const { user } = useAuth();
  const remote = !USE_MOCK && user?.role === ROLES.CUSTOMER;
  const owner = remote ? `user:${user.id}` : 'guest';
  const [state, dispatch] = useReducer(cartWithFeedback, undefined, loadCart);

  // Whose items are in `state` right now. Stops a logged-in cart from being saved as the guest cart.
  const itemsOwner = useRef(remote ? null : 'guest');
  const ownerRef = useRef(owner);
  ownerRef.current = owner;
  // Server calls run one after another; only the newest response is shown (fast +/+/+ clicks).
  const queue = useRef(Promise.resolve());
  const latest = useRef(0);

  const enqueue = (call) => {
    const id = ++latest.current;
    const callOwner = ownerRef.current;
    const run = queue.current.catch(() => {}).then(call).then((cart) => {
      if (ownerRef.current === callOwner && id === latest.current) {
        itemsOwner.current = callOwner;
        dispatch({ type: 'HYDRATE', items: cart.items.map(cartApi.fromServerItem) });
      }
      return cart;
    });
    queue.current = run;
    return run;
  };

  // A write failed: say why, then show what the server really holds.
  const write = (call) => enqueue(call).catch((err) => {
    if (err.status === 401) return; // session expired → the logout path resets the cart
    dispatch({ type: 'SYNC_ERROR', message: err.message || 'Could not update your cart.' });
    return enqueue(cartApi.getCart).catch(() => {});
  });

  useEffect(() => {
    if (!state.notice || state.notice.success) return;
    const id = state.notice.id;
    const timer = setTimeout(() => dispatch({ type: 'DISMISS_NOTICE', id }), 5000);
    return () => clearTimeout(timer);
  }, [state.notice]);

  // Declared before the owner switch below, so it never sees an account's items as the guest's.
  useEffect(() => {
    if (!remote && itemsOwner.current === 'guest') saveGuestCart(state.items);
  }, [state.items, remote]);

  // Logging in / out switches between the browser cart and the account cart.
  useEffect(() => {
    if (!remote) {
      if (itemsOwner.current !== 'guest') {
        itemsOwner.current = 'guest';
        dispatch({ type: 'HYDRATE', items: loadCart().items });
      }
      return;
    }
    // Take the guest cart out of storage first, so it is merged only once (StrictMode runs this twice).
    const guest = loadCart().items;
    if (guest.length) try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    enqueue(() => (guest.length ? cartApi.mergeCart(guest) : cartApi.getCart())).then((cart) => {
      if (cart.skipped?.length) {
        dispatch({ type: 'SYNC_ERROR', message: 'Some items from your cart are no longer available and were removed.' });
      }
    }).catch((err) => {
      if (ownerRef.current === owner) itemsOwner.current = owner; // stop showing "loading"
      if (guest.length) saveGuestCart(guest); // keep it for the next try
      if (err.status !== 401) dispatch({ type: 'SYNC_ERROR', message: 'Could not load your cart. Please refresh the page.' });
    });
  }, [owner]);

  // True until the account cart has arrived (pages should not treat it as "empty" yet).
  const loading = remote && itemsOwner.current !== owner;

  const value = useMemo(() => ({
    items: state.items,
    loading,
    count: cartCount(state.items),
    total: cartTotal(state.items),
    addItem: (product, quantity = 1) => {
      dispatch({ type: 'ADD', product, quantity }); // show it at once; the server reply corrects it
      if (remote && product && product.stock > 0) write(() => cartApi.addCartItem(product.id, quantity));
    },
    setQuantity: (productId, quantity) => {
      dispatch({ type: 'SET_QTY', productId, quantity });
      const qty = Math.floor(Number(quantity));
      if (remote && Number.isFinite(qty)) write(() => cartApi.setCartItemQuantity(productId, Math.max(qty, 0)));
    },
    removeItem: (productId) => {
      dispatch({ type: 'REMOVE', productId });
      if (remote) write(() => cartApi.removeCartItem(productId));
    },
    /** `{ local: true }` after checkout: the server has already emptied the cart. */
    clear: ({ local = false } = {}) => {
      dispatch({ type: 'CLEAR' });
      if (remote && !local) write(cartApi.clearCart);
    },
    /**
     * Fresh cart from the server (waits for pending updates) — checkout compares it with
     * what the customer saw. Without a server cart (mock mode) the browser cart is copied up.
     */
    refresh: () => (remote ? enqueue(cartApi.getCart) : syncCart(state.items)),
  }), [state.items, remote, loading]);

  return (
    <CartContext.Provider value={value}>
      {children}
      {state.notice?.success && (
        <AddedToCartModal
          product={state.notice.product}
          quantity={state.notice.quantity}
          items={state.items}
          onClose={() => dispatch({ type: 'DISMISS_NOTICE', id: state.notice.id })}
        />
      )}
      <div className="cart-notice-region" role="status" aria-live="polite" aria-atomic="true">
        {state.notice && !state.notice.success && (
          <div className="cart-notice" key={state.notice.id}>
            <span className="cart-notice__icon" aria-hidden="true">{state.notice.success ? '✓' : '!'}</span>
            <div className="cart-notice__body">
              <p>{state.notice.message}</p>
              <Link to="/cart" onClick={() => dispatch({ type: 'DISMISS_NOTICE', id: state.notice.id })}>View cart →</Link>
            </div>
            <button type="button" className="cart-notice__close" aria-label="Dismiss notification" onClick={() => dispatch({ type: 'DISMISS_NOTICE', id: state.notice.id })}>×</button>
          </div>
        )}
      </div>
    </CartContext.Provider>
  );
}

export const useCart = () => useContext(CartContext);
