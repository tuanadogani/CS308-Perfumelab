import { afterEach, describe, expect, it, vi } from 'vitest';
import { setAccessToken } from '../api/client';
import { checkout, getInvoice, syncCart } from '../api/checkoutApi';
import {
  cartDifferences, formatCardNumber, formatExpiry, parseExpiry, toCheckoutBody, validateCheckout,
} from '../utils/checkout';

const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

const validForm = {
  holderName: 'Ada Lovelace', cardNumber: '4242 4242 4242 4242', expiry: '12/30', cvv: '123',
  shippingAddress: 'Kadıköy, Istanbul',
};
const NOV_2026 = new Date(2026, 10, 20);

describe('checkout form helpers', () => {
  it('formats card number and expiry while typing', () => {
    expect(formatCardNumber('4242424242424242')).toBe('4242 4242 4242 4242');
    expect(formatCardNumber('4242-42ab42')).toBe('4242 4242');
    expect(formatExpiry('1230')).toBe('12/30');
    expect(formatExpiry('1')).toBe('1');
  });

  it('parses expiry and rejects month 13', () => {
    expect(parseExpiry('07/29')).toEqual({ month: 7, year: 2029 });
    expect(parseExpiry('13/29')).toBeNull();
    expect(parseExpiry('7/29')).toBeNull();
  });

  it('accepts a valid form', () => {
    expect(validateCheckout(validForm, NOV_2026)).toEqual({});
  });

  it('flags every invalid field', () => {
    const errors = validateCheckout(
      { holderName: ' ', cardNumber: '1234', expiry: '10/26', cvv: '12', shippingAddress: '' }, NOV_2026,
    );
    expect(Object.keys(errors).sort()).toEqual(['cardNumber', 'cvv', 'expiry', 'holderName', 'shippingAddress']);
    expect(errors.expiry).toMatch(/expired/);
  });

  it('a card expiring this month is still valid', () => {
    expect(validateCheckout({ ...validForm, expiry: '11/26' }, NOV_2026)).toEqual({});
  });

  it('builds the backend body with digits only', () => {
    expect(toCheckoutBody(validForm)).toEqual({
      cardNumber: '4242424242424242', holderName: 'Ada Lovelace', expiryMonth: 12, expiryYear: 2030,
      cvv: '123', shippingAddress: 'Kadıköy, Istanbul',
    });
  });

  it('detects lines the server reduced or dropped', () => {
    const local = [{ productId: 1, name: 'A', quantity: 3 }, { productId: 2, name: 'B', quantity: 1 },
      { productId: 3, name: 'C', quantity: 2 }];
    const server = { items: [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }] };
    expect(cartDifferences(local, server)).toEqual([
      { productId: 1, name: 'A', quantity: 2 }, { productId: 3, name: 'C', quantity: 0 },
    ]);
  });
});

describe('checkout API contract', () => {
  it('replaces the server cart with the browser cart', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response({ items: [] }))
      .mockResolvedValueOnce(response({ items: [{ productId: 7, quantity: 2 }] }));
    vi.stubGlobal('fetch', fetch);
    await syncCart([{ productId: 7, quantity: 2, name: 'X', price: 10 }]);
    expect(fetch.mock.calls.map(([url, opts]) => [url, opts.method])).toEqual([
      ['/api/cart/', 'DELETE'], ['/api/cart/merge/', 'POST'],
    ]);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ items: [{ productId: 7, quantity: 2 }] });
  });

  it('surfaces a declined card as status 402', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ message: 'The bank declined this card.' }, 402)));
    await expect(checkout({})).rejects.toMatchObject({ status: 402, message: 'The bank declined this card.' });
  });

  it('loads the invoice of an order', async () => {
    const fetch = vi.fn().mockResolvedValue(response({ number: 'INV-0000001' }));
    vi.stubGlobal('fetch', fetch);
    expect((await getInvoice(12)).number).toBe('INV-0000001');
    expect(fetch.mock.calls[0][0]).toBe('/api/orders/12/invoice/');
  });
});
