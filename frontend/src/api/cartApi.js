import { request } from './client';

// Server cart for logged-in customers (Requirement 4, 7). Backend: backend/cart/views.py.
// Every call returns the whole cart: { items: [...], itemCount, total }.
// Guests keep their cart in localStorage; it is sent once to /cart/merge/ right after login.

export const getCart = () => request('/cart/');
export const clearCart = () => request('/cart/', { method: 'DELETE' });

export const addCartItem = (productId, quantity = 1) =>
  request('/cart/items/', { method: 'POST', body: { productId, quantity } });

/** Set an exact quantity (0 removes the line). Capped at stock on the server. */
export const setCartItemQuantity = (productId, quantity) =>
  request(`/cart/items/${encodeURIComponent(productId)}/`, { method: 'PATCH', body: { quantity } });

export const removeCartItem = (productId) =>
  request(`/cart/items/${encodeURIComponent(productId)}/`, { method: 'DELETE' });

/** Add the guest cart's quantities to the account's cart. Sold-out products come back in `skipped`. */
export const mergeCart = (items) => request('/cart/merge/', {
  method: 'POST',
  body: { items: items.map((i) => ({ productId: i.productId, quantity: i.quantity })) },
});

/** A server cart line -> the shape the cart pages use. */
export const fromServerItem = (line) => ({
  productId: line.productId,
  name: line.name,
  brand: line.brand,
  price: Number(line.unitPrice),
  volumeMl: line.volumeMl,
  stock: line.stock,
  quantity: line.quantity,
  imageUrl: line.imageUrl,
});
