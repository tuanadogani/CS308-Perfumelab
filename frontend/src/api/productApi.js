import { USE_MOCK, request, delay } from './client';
import { products as mockProducts, CATEGORIES, NOTE_FAMILIES } from '../mocks/products';

/**
 * Backend contract (share with the team):
 *   GET /products?q=&category=&brand=&family=&family=&sort=price_asc|price_desc|popularity
 *       (repeat `family` to require every selected scent family)
 *   GET /products/:id
 *   GET /categories
 *   GET /filters  -> { brands: [{name, count}], families: [{name, count}], categories: [...] }
 */

const toList = (value) => (Array.isArray(value) ? value : [value]).filter(Boolean);

export function filterAndSort(list, { q = '', category = '', brand = '', family = [], sort = 'popularity' } = {}) {
  const term = q.trim().toLowerCase();
  const families = toList(family);
  const out = list.filter((p) => {
    // Requirement 7: search by name OR description. Out-of-stock products are still listed.
    const matchesQ = !term ||
      p.name.toLowerCase().includes(term) ||
      p.description.toLowerCase().includes(term) ||
      p.brand.toLowerCase().includes(term);
    return matchesQ &&
      (!category || p.category === category) &&
      (!brand || p.brand === brand) &&
      families.every((f) => p.families?.includes(f));
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
  // Arrays become repeated keys: { family: ['Woody', 'Spicy'] } -> ?family=Woody&family=Spicy
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => toList(value).forEach((v) => search.append(key, v)));
  const qs = search.toString();
  return request(`/products/${qs ? `?${qs}` : ''}`);
}

export async function getProduct(id) {
  if (USE_MOCK) {
    await delay();
    const p = mockProducts.find((x) => x.id === Number(id));
    if (!p) throw new Error('Product not found');
    return p;
  }
  return request(`/products/${encodeURIComponent(id)}/`);
}

export async function getCategories() {
  if (USE_MOCK) return CATEGORIES;
  return request('/categories/');
}

export const getBrands = (list) => [...new Set(list.map((p) => p.brand))].sort();

// Sidebar filter options. Real mode reads them from the database, so newly added
// brands and scent families show up without touching the frontend.
export async function getFilters() {
  if (USE_MOCK) {
    return {
      brands: getBrands(mockProducts).map((name) => ({ name })),
      families: NOTE_FAMILIES.map((name) => ({ name })),
      categories: CATEGORIES,
    };
  }
  return request('/filters/');
}
