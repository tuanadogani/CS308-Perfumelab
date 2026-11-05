import { describe, it, expect } from 'vitest';
import { cartReducer, initialCart } from '../context/cartReducer';

const product = { id: 7, name: 'Black Opium', brand: 'YSL', price: 100, volumeMl: 90, stock: 5,
  imageUrl: 'http://localhost:8000/api/products/7/image/' };

describe('cart keeps the product photo', () => {
  it('stores imageUrl on a new cart row', () => {
    const s = cartReducer(initialCart, { type: 'ADD', product });
    expect(s.items[0].imageUrl).toBe(product.imageUrl);
  });

  it('fills in a missing photo when an older cart row is added again', () => {
    const old = { ...initialCart, items: [{ productId: 7, name: 'Black Opium', quantity: 1, stock: 5 }] };
    const s = cartReducer(old, { type: 'ADD', product });
    expect(s.items[0].imageUrl).toBe(product.imageUrl);
    expect(s.items[0].quantity).toBe(2);
  });
});

describe('shop filter options', () => {
  it('loads brands and families from GET /api/filters/', async () => {
    const { vi } = await import('vitest');
    const { getFilters } = await import('../api/productApi');
    const data = { brands: [{ name: 'Dior', count: 3 }], families: [{ name: 'Woody', count: 5 }], categories: [] };
    const fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => data });
    vi.stubGlobal('fetch', fetch);
    expect(await getFilters()).toEqual(data);
    expect(fetch.mock.calls[0][0]).toBe('/api/filters/');
    vi.unstubAllGlobals();
  });
});
