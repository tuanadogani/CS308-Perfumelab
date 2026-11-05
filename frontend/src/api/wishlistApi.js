import { request } from './client';

export const getWishlist = () => request('/wishlist/');
export const addToWishlist = (id) => request(`/wishlist/${encodeURIComponent(id)}/`, { method: 'PUT' });
export const removeFromWishlist = (id) => request(`/wishlist/${encodeURIComponent(id)}/`, { method: 'DELETE' });
