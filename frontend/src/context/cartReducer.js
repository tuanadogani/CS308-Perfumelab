// Pure cart logic — independent of React, so it is easy to unit test.

export const initialCart = { items: [] };

export function cartReducer(state, action) {
  switch (action.type) {
    case 'ADD': {
      const { product, quantity = 1 } = action;
      if (!product || product.stock <= 0) return state; // Requirement 7: out-of-stock items cannot be added
      const existing = state.items.find((i) => i.productId === product.id);
      const currentQty = existing?.quantity ?? 0;
      const newQty = Math.min(currentQty + quantity, product.stock); // never more than the stock
      if (existing) {
        return { ...state, items: state.items.map((i) =>
          i.productId === product.id ? { ...i, quantity: newQty, stock: product.stock } : i) };
      }
      return { ...state, items: [...state.items, {
        productId: product.id, name: product.name, brand: product.brand, price: product.price,
        volumeMl: product.volumeMl, color: product.color, stock: product.stock, quantity: newQty,
      }] };
    }
    case 'SET_QTY': {
      const qty = Math.floor(Number(action.quantity));
      if (!Number.isFinite(qty)) return state;
      if (qty <= 0) return { ...state, items: state.items.filter((i) => i.productId !== action.productId) };
      return { ...state, items: state.items.map((i) =>
        i.productId === action.productId ? { ...i, quantity: Math.min(qty, i.stock) } : i) };
    }
    case 'REMOVE':
      return { ...state, items: state.items.filter((i) => i.productId !== action.productId) };
    case 'CLEAR':
      return initialCart;
    case 'HYDRATE':
      return Array.isArray(action.items) ? { items: action.items } : state;
    default:
      return state;
  }
}

export const cartCount = (items) => items.reduce((s, i) => s + i.quantity, 0);
export const cartTotal = (items) => items.reduce((s, i) => s + i.price * i.quantity, 0);
