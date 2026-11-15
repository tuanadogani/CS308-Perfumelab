import { createContext, useContext, useEffect, useMemo, useReducer } from 'react';
import { cartReducer, initialCart, cartCount, cartTotal } from './cartReducer';
import { Link } from 'react-router-dom';

const CartContext = createContext(null);
const STORAGE_KEY = 'ml_cart';

function cartWithFeedback(state, action) {
  if (action.type === 'DISMISS_NOTICE') {
    return state.notice?.id === action.id ? { ...state, notice: null } : state;
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

export function CartProvider({ children }) {
  // A guest's cart lives in localStorage → it is kept after logging in (Requirement 4).
  // Sprint 2+: on login, merge this cart with the user's cart on the backend (POST /cart/merge).
  const [state, dispatch] = useReducer(cartWithFeedback, undefined, loadCart);

  useEffect(() => {
    if (!state.notice) return;
    const id = state.notice.id;
    const timer = setTimeout(() => dispatch({ type: 'DISMISS_NOTICE', id }), 5000);
    return () => clearTimeout(timer);
  }, [state.notice]);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.items)); } catch { /* ignore */ }
  }, [state.items]);

  const value = useMemo(() => ({
    items: state.items,
    count: cartCount(state.items),
    total: cartTotal(state.items),
    addItem: (product, quantity = 1) => dispatch({ type: 'ADD', product, quantity }),
    setQuantity: (productId, quantity) => dispatch({ type: 'SET_QTY', productId, quantity }),
    removeItem: (productId) => dispatch({ type: 'REMOVE', productId }),
    clear: () => dispatch({ type: 'CLEAR' }),
  }), [state.items]);

  return (
    <CartContext.Provider value={value}>
      {children}
      <div className="cart-notice-region" role="status" aria-live="polite" aria-atomic="true">
        {state.notice && (
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
