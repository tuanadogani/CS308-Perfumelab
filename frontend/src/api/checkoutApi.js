import { request, requestBlob } from './client';

// Checkout (Requirement 4). Backend contract: docs/CHECKOUT_API.md.
//
// The cart itself stays in localStorage (CartContext), so guests keep it after login.
// Right before paying we copy it to the server cart: the server re-checks stock and
// prices, then POST /checkout/ pays for exactly that cart.

/** Replace the server cart with the browser cart. Returns the server cart (capped at stock). */
export async function syncCart(items) {
  await request('/cart/', { method: 'DELETE' });
  return request('/cart/merge/', {
    method: 'POST',
    body: { items: items.map((i) => ({ productId: i.productId, quantity: i.quantity })) },
  });
}

export const getSavedCards = () => request('/cards/');

/** Pay. Throws ApiError with status 402 (card declined) or 400 (cart/stock/card problem). */
export const checkout = (payment) => request('/checkout/', { method: 'POST', body: payment });

export const getInvoice = (orderId) => request(`/orders/${encodeURIComponent(orderId)}/invoice/`);
export const getInvoicePdf = (orderId) => requestBlob(`/orders/${encodeURIComponent(orderId)}/invoice/pdf/`);
