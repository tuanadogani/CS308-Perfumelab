import { request, requestBlob } from './client';

/**
 * Sales manager endpoints (backend/orders + backend/wishlist):
 *   GET  /sales/revenue/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
 *   GET  /sales/invoices/?start_date=&end_date=
 *   GET  /sales/invoices/:id/
 *   GET  /sales/invoices/:id/pdf/?download=true
 *   POST /sales/discounts/  { productIds: [..], discountRate: 0-100 }
 */
const range = ({ startDate, endDate } = {}) => {
  const qs = new URLSearchParams();
  if (startDate) qs.set('start_date', startDate);
  if (endDate) qs.set('end_date', endDate);
  const s = qs.toString();
  return s ? `?${s}` : '';
};

export const getRevenueReport = (params) => request(`/sales/revenue/${range(params)}`);
export const getInvoices = (params) => request(`/sales/invoices/${range(params)}`);
export const getInvoice = (id) => request(`/sales/invoices/${encodeURIComponent(id)}/`);
export const getInvoicePdf = (id, download = false) =>
  requestBlob(`/sales/invoices/${encodeURIComponent(id)}/pdf/${download ? '?download=true' : ''}`);
export const setDiscount = ({ productIds, discountRate }) =>
  request('/sales/discounts/', { method: 'POST', body: { productIds, discountRate } });

/**
 * Return / refund requests (Requirement 16), backend/refunds/views.py:
 *   GET  /sales/refunds/?status=requested|approved|rejected
 *   POST /sales/refunds/:id/receive/                 the returned product arrived at the store
 *   POST /sales/refunds/:id/decision/ { approve }    approve needs the receipt; refunds the card,
 *                                                    restocks and emails the customer. 502 = bank error.
 */
export const getRefunds = (status) => request(`/sales/refunds/${status ? `?status=${encodeURIComponent(status)}` : ''}`);
export const receiveRefund = (id) => request(`/sales/refunds/${encodeURIComponent(id)}/receive/`, { method: 'POST' });
export const decideRefund = (id, approve) =>
  request(`/sales/refunds/${encodeURIComponent(id)}/decision/`, { method: 'POST', body: { approve } });
