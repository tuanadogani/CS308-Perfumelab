import { USE_MOCK, request, delay } from './client';

// Customer order history (Requirement 3, 14). Backend: backend/orders/customer_views.py.
//   GET  /orders/              newest first: [{ id, status, total, shippingAddress, createdAt, deliveredAt, items }]
//   GET  /orders/:id/          one order of the signed-in customer (404 for someone else's)
//   POST /orders/:id/cancel/   only while 'processing'; the stock goes back on the shelf
// Item shape: { id, productId, productName, quantity, unitPrice, lineTotal, refund }.
// Money comes as decimal strings ("1250.00").

export async function getOrders() {
  if (USE_MOCK) { await delay(); return []; }
  return request('/orders/');
}

export const getOrder = (orderId) => request(`/orders/${encodeURIComponent(orderId)}/`);

export const cancelOrder = (orderId) =>
  request(`/orders/${encodeURIComponent(orderId)}/cancel/`, { method: 'POST' });

/**
 * Ask to return one delivered order line (Requirement 16). Optional reason (max 2000 chars).
 * The amount is the price paid at purchase, discount included — never the current price.
 * Returns the refund: { id, orderItemId, reason, status: 'requested', amount, requestedAt, ... }
 */
export const requestRefund = (orderId, itemId, reason = '') =>
  request(`/orders/${encodeURIComponent(orderId)}/items/${encodeURIComponent(itemId)}/refund/`, {
    method: 'POST', body: { reason },
  });
