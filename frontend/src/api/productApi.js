import { USE_MOCK, request, delay } from './client';
import { products as mockProducts, CATEGORIES } from '../mocks/products';

/**
 * Backend contract (share with the team):
 *   GET /products?q=&category=&brand=&family=&sort=price_asc|price_desc|popularity
 *   GET /products/:id
 *   GET /categories
 */

export function filterAndSort(list, { q = '', category = '', brand = '', family = '', sort = 'popularity' } = {}) {
  const term = q.trim().toLowerCase();
  const out = list.filter((p) => {
    // Requirement 7: search by name OR description. Out-of-stock products are still listed.
    const matchesQ = !term ||
      p.name.toLowerCase().includes(term) ||
      p.description.toLowerCase().includes(term) ||
      p.brand.toLowerCase().includes(term);
    return matchesQ &&
      (!category || p.category === category) &&
      (!brand || p.brand === brand) &&
      (!family || p.families?.includes(family));
  });
  const sorters = {
    price_asc: (a, b) => a.price - b.price,
    price_desc: (a, b) => b.price - a.price,
    popularity: (a, b) => b.popularity - a.popularity,
  };
  return [...out].sort(sorters[sort] ?? sorters.popularity);
}

export async function getProducts(params = {}) {
  if (USE_MOCK) { await delay(); return filterAndSort(mockProducts, params); }
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  return request(`/products${qs ? `?${qs}` : ''}`);
}

export async function getProduct(id) {
  if (USE_MOCK) {
    await delay();
    const p = mockProducts.find((x) => x.id === Number(id));
    if (!p) throw new Error('Product not found');
    return p;
  }
  return request(`/products/${encodeURIComponent(id)}`);
}

export async function getCategories() {
  if (USE_MOCK) return CATEGORIES;
  return request('/categories');
}

export const getBrands = (list) => [...new Set(list.map((p) => p.brand))].sort();
