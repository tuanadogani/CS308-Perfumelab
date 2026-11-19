import { request } from './client';

/**
 * Product manager endpoints (backend/catalog/manager.py), all under /product-manager/:
 *   GET    /products/                 every product, inactive ones included
 *   POST   /products/                 { name, model, serial_number, description, stock, warranty_status,
 *                                       distributor, brand, category(slug), gender, volume_ml, families[], notes{top,heart,base} }
 *   PATCH  /products/:id/             any subset of the fields above, plus `active`
 *   DELETE /products/:id/             soft delete (active = false)
 *   GET    /categories/               [{ id, slug, name }]
 *   POST   /categories/               { slug, name }
 *   PATCH  /categories/:id/           { name }
 *   DELETE /categories/:id/           400 while the category still has products
 *   GET    /deliveries/               one row per order line
 *   PATCH  /orders/:id/status/        { status: 'in_transit' | 'delivered' } (one step at a time)
 *   GET    /comments/
 *   PATCH  /comments/:id/             { approve: true | false }
 * Prices are not set here: they belong to the sales manager.
 */
const BASE = '/product-manager';
const id = (v) => encodeURIComponent(v);

export const getManagedProducts = () => request(`${BASE}/products/`);
export const createProduct = (body) => request(`${BASE}/products/`, { method: 'POST', body });
export const updateProduct = (pk, body) => request(`${BASE}/products/${id(pk)}/`, { method: 'PATCH', body });
export const deactivateProduct = (pk) => request(`${BASE}/products/${id(pk)}/`, { method: 'DELETE' });

export const getManagedCategories = () => request(`${BASE}/categories/`);
export const createCategory = (body) => request(`${BASE}/categories/`, { method: 'POST', body });
export const updateCategory = (pk, body) => request(`${BASE}/categories/${id(pk)}/`, { method: 'PATCH', body });
export const deleteCategory = (pk) => request(`${BASE}/categories/${id(pk)}/`, { method: 'DELETE' });

export const getDeliveries = () => request(`${BASE}/deliveries/`);
export const advanceOrderStatus = (orderId, status) =>
  request(`${BASE}/orders/${id(orderId)}/status/`, { method: 'PATCH', body: { status } });

export const getComments = () => request(`${BASE}/comments/`);
export const moderateComment = (pk, approve) =>
  request(`${BASE}/comments/${id(pk)}/`, { method: 'PATCH', body: { approve } });
