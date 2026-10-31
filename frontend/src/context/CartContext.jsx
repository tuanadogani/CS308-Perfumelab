import { createContext, useContext, useEffect, useMemo, useReducer } from 'react';
import { cartReducer, initialCart, cartCount, cartTotal } from './cartReducer';

const CartContext = createContext(null);
const STORAGE_KEY = 'ml_cart';

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
  const [state, dispatch] = useReducer(cartReducer, undefined, loadCart);

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

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export const useCart = () => useContext(CartContext);
