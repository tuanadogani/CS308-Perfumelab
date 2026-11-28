// Order status helpers for the order history page (Requirement 3).

export const ORDER_STATUS_LABELS = {
  processing: 'Processing',
  in_transit: 'In transit',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
  refunded: 'Refunded',
};

// The delivery steps a customer can follow, in order.
export const DELIVERY_STEPS = ['processing', 'in_transit', 'delivered'];

export const statusLabel = (status) => ORDER_STATUS_LABELS[status] ?? status;

/** Index of the reached delivery step, or -1 when the order left the delivery flow (cancelled). */
export function deliveryStep(status) {
  if (status === 'refunded') return DELIVERY_STEPS.length - 1; // only delivered orders can be refunded
  return DELIVERY_STEPS.indexOf(status);
}

/** Only orders still being prepared can be cancelled (Requirement 14). */
export const canCancel = (order) => order?.status === 'processing';

/** Orders still on their way to the customer. */
export const isOpen = (order) => order?.status === 'processing' || order?.status === 'in_transit';

export const ORDER_FILTERS = [
  ['all', 'All'],
  ['open', 'Active'],
  ['delivered', 'Delivered'],
  ['closed', 'Cancelled / refunded'],
];

export function filterOrders(orders, filter) {
  switch (filter) {
    case 'open': return orders.filter(isOpen);
    case 'delivered': return orders.filter((o) => o.status === 'delivered');
    case 'closed': return orders.filter((o) => o.status === 'cancelled' || o.status === 'refunded');
    default: return orders;
  }
}

export const itemCount = (order) => (order?.items ?? []).reduce((sum, item) => sum + item.quantity, 0);

// Requirement 16: a delivered item can be returned within 30 days of purchase (not of delivery).
export const REFUND_WINDOW_DAYS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Last moment a return can be requested for this order. */
export const refundDeadline = (order) => new Date(new Date(order.createdAt).getTime() + REFUND_WINDOW_DAYS * DAY_MS);

/** The backend has the final word; this only decides whether to offer the button. */
export function canRequestRefund(order, item, now = new Date()) {
  return order?.status === 'delivered' && !item?.refund && now <= refundDeadline(order);
}

export const REFUND_STATUS_LABELS = {
  requested: 'Return requested',
  approved: 'Refunded',
  rejected: 'Return rejected',
};
