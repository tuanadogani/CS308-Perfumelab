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
