import { request } from './client';

/**
 * Get the current user's rating for a product
 * Returns: { score: number | null }
 */
export async function getUserRating(productId) {
  return request(`/products/${productId}/rating/`);
}

/**
 * Submit or update a rating (1-5 stars)
 * Returns: { score: number }
 */
export async function submitRating(productId, score) {
  return request(`/products/${productId}/rating/`, {
    method: 'PUT',
    body: { score },
  });
}

/**
 * Get approved comments for a product
 * Returns: Array of { id, customerName, text, approved, createdAt }
 */
export async function getProductComments(productId) {
  return request(`/products/${productId}/comments/`);
}

/**
 * Submit a comment on a product
 * Returns: { id, customerName, text, approved, createdAt }
 */
export async function submitComment(productId, text) {
  return request(`/products/${productId}/comments/`, {
    method: 'POST',
    body: { text },
  });
}
