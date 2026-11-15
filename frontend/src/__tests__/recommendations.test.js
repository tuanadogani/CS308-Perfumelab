import { describe, expect, it } from 'vitest';
import { recommendProducts } from '../utils/recommendations';

const product = { id: 1, price: 100, stock: 5, families: ['Woody'], notes: { base: ['Cedar'] } };

describe('cart recommendations', () => {
  it('excludes the added product, cart items and unavailable products', () => {
    const available = { ...product, id: 4 };
    expect(recommendProducts(product, [product, { ...product, id: 2, stock: 0 }, { ...product, id: 3 }, available], [3])).toEqual([available]);
  });

  it('prioritizes scent similarity, then price proximity and limits results', () => {
    const candidates = [
      { id: 2, stock: 3, price: 100, families: ['Floral'] },
      { id: 3, stock: 3, price: 110, families: ['Woody'] },
      { id: 4, stock: 3, price: 100, families: ['Woody'] },
      { id: 5, stock: 3, price: 200, families: ['Woody'], notes: { base: ['cedar'] } },
    ];
    expect(recommendProducts(product, candidates, [], 3).map((p) => p.id)).toEqual([5, 4, 3]);
    expect(candidates.map((p) => p.id)).toEqual([2, 3, 4, 5]);
  });
});
