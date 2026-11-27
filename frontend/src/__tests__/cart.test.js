import { afterEach, describe, expect, it, vi } from 'vitest';
import { setAccessToken } from '../api/client';
import {
  addCartItem, clearCart, fromServerItem, getCart, mergeCart, removeCartItem, setCartItemQuantity,
} from '../api/cartApi';
import { cartReducer } from '../context/cartReducer';

const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
const emptyCart = { items: [], itemCount: 0, total: '0.00' };
afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

describe('cart API contract', () => {
  it('calls the backend cart endpoints with the right method and body', async () => {
    const fetch = vi.fn().mockResolvedValue(response(emptyCart));
    vi.stubGlobal('fetch', fetch);
    setAccessToken('token');

    await getCart();
    await addCartItem(7, 2);
    await setCartItemQuantity(7, 3);
    await removeCartItem(7);
    await clearCart();
    await mergeCart([{ productId: 7, quantity: 2, name: 'X', price: 10 }]);

    expect(fetch.mock.calls.map(([url, opts]) => [url, opts.method ?? 'GET', opts.body && JSON.parse(opts.body)])).toEqual([
      ['/api/cart/', 'GET', undefined],
      ['/api/cart/items/', 'POST', { productId: 7, quantity: 2 }],
      ['/api/cart/items/7/', 'PATCH', { quantity: 3 }],
      ['/api/cart/items/7/', 'DELETE', undefined],
      ['/api/cart/', 'DELETE', undefined],
      ['/api/cart/merge/', 'POST', { items: [{ productId: 7, quantity: 2 }] }],
    ]);
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer token');
  });

  it('surfaces a stock error from the server', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ message: 'This product is out of stock.' }, 400)));
    await expect(addCartItem(7)).rejects.toMatchObject({ status: 400, message: 'This product is out of stock.' });
  });

  it('maps a server cart line to the shape the cart pages use', () => {
    expect(fromServerItem({
      productId: 7, name: 'Oud', brand: 'Maison', volumeMl: 50, unitPrice: '129.90',
      quantity: 2, stock: 5, lineTotal: '259.80', imageUrl: null,
    })).toEqual({
      productId: 7, name: 'Oud', brand: 'Maison', price: 129.9, volumeMl: 50, stock: 5, quantity: 2, imageUrl: null,
    });
  });
});

describe('cartReducer HYDRATE', () => {
  it('replaces the items with the server cart but keeps the known bottle colour', () => {
    const state = { items: [{ productId: 7, quantity: 5, color: '#123456', price: 10, stock: 9 }] };
    const next = cartReducer(state, { type: 'HYDRATE', items: [
      { productId: 7, quantity: 3, price: 12, stock: 3 },
      { productId: 8, quantity: 1, price: 5, stock: 1 },
    ] });
    expect(next.items).toEqual([
      { productId: 7, quantity: 3, price: 12, stock: 3, color: '#123456' },
      { productId: 8, quantity: 1, price: 5, stock: 1 },
    ]);
  });
});
