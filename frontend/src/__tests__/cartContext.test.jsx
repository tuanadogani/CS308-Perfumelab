// @vitest-environment jsdom
import { StrictMode } from 'react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { CartProvider, useCart } from '../context/CartContext';
import CheckoutPage from '../pages/CheckoutPage';

// CartContext with a fake backend: guests use localStorage, customers use /api/cart/.

const auth = vi.hoisted(() => ({ user: null }));
const flags = vi.hoisted(() => ({ mock: false }));

vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: auth.user }) }));
vi.mock('../api/client', async (importOriginal) => {
  const real = await importOriginal();
  return { ...real, get USE_MOCK() { return flags.mock; } };
});

const CUSTOMER = { id: 1, name: 'Ada Lovelace', role: 'customer', homeAddress: 'Kadıköy, Istanbul' };
const STORAGE_KEY = 'ml_cart';

const product = (id, extra = {}) => ({
  id, name: `Perfume ${id}`, brand: 'Maison', price: 100, volumeMl: 50, color: '#123456', stock: 10, imageUrl: null, ...extra,
});
const guestLine = (id, quantity, extra = {}) => ({
  productId: id, name: `Perfume ${id}`, brand: 'Maison', price: 100, volumeMl: 50, color: '#123456', stock: 10, quantity, imageUrl: null, ...extra,
});

// ---- fake backend ---------------------------------------------------------------

const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

function fakeServer({ stock = {}, cart = {} } = {}) {
  const lines = new Map(Object.entries(cart).map(([id, q]) => [Number(id), q]));
  const server = {
    stock: { 7: 10, 8: 10, ...stock },
    calls: [],
    fail: null, // (method, path) => response | undefined, to force an error
    hold: false, // when true, cart responses wait until release()
    waiting: [],
    release() { server.waiting.shift()?.(); },
  };
  const payload = (extra = {}) => {
    const items = [...lines].map(([id, quantity]) => ({
      productId: id, name: `Perfume ${id}`, brand: 'Maison', volumeMl: 50, unitPrice: '100.00',
      quantity, stock: server.stock[id] ?? 0, lineTotal: `${100 * quantity}.00`, imageUrl: null,
    }));
    return { items, itemCount: items.reduce((s, i) => s + i.quantity, 0), total: '0.00', ...extra };
  };
  const add = (id, q) => {
    const max = server.stock[id] ?? 0;
    if (max <= 0) return false;
    lines.set(id, Math.min((lines.get(id) ?? 0) + q, max));
    return true;
  };

  const handle = (method, path, body) => {
    const forced = server.fail?.(method, path);
    if (forced) return forced;
    const item = /^\/api\/cart\/items\/(\d+)\/$/.exec(path);
    if (path === '/api/cart/' && method === 'GET') return json(payload());
    if (path === '/api/cart/' && method === 'DELETE') { lines.clear(); return json(payload()); }
    if (path === '/api/cart/items/' && method === 'POST') {
      return add(body.productId, body.quantity) ? json(payload(), 201) : json({ message: 'This product is out of stock.' }, 400);
    }
    if (item && method === 'PATCH') {
      const id = Number(item[1]);
      if (body.quantity === 0) lines.delete(id); else lines.set(id, Math.min(body.quantity, server.stock[id] ?? 0));
      return json(payload());
    }
    if (item && method === 'DELETE') { lines.delete(Number(item[1])); return json(payload()); }
    if (path === '/api/cart/merge/' && method === 'POST') {
      const skipped = body.items.filter((l) => !add(l.productId, l.quantity)).map((l) => l.productId);
      return json(payload({ skipped }));
    }
    if (path === '/api/checkout/' && method === 'POST') { lines.clear(); return json({ order: { id: 42 } }, 201); }
    return json([]); // e.g. the product list the "added to cart" dialog loads
  };

  vi.stubGlobal('fetch', vi.fn(async (url, opts = {}) => {
    const method = opts.method ?? 'GET';
    const body = opts.body ? JSON.parse(opts.body) : undefined;
    server.calls.push({ method, path: url, body });
    if (server.hold && url.startsWith('/api/cart')) await new Promise((resolve) => server.waiting.push(resolve));
    return handle(method, url, body);
  }));
  server.cartCalls = () => server.calls.filter((c) => c.path.startsWith('/api/cart'));
  server.lines = lines;
  return server;
}

// ---- harness ---------------------------------------------------------------------

let cart;
let quantityHistory;
function Probe() {
  cart = useCart();
  quantityHistory.push(cart.items.find((i) => i.productId === 7)?.quantity);
  return null;
}

const tree = (strict) => {
  const app = <MemoryRouter><CartProvider><Probe /></CartProvider></MemoryRouter>;
  return strict ? <StrictMode>{app}</StrictMode> : app;
};
function renderCart({ strict = false } = {}) {
  const view = render(tree(strict));
  return { ...view, setUser: (user) => { auth.user = user; view.rerender(tree(strict)); } };
}

const quantities = () => Object.fromEntries(cart.items.map((i) => [i.productId, i.quantity]));
const storedGuestCart = () => JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)));

beforeAll(() => {
  // jsdom has no <dialog> methods; the "added to cart" dialog needs them.
  HTMLDialogElement.prototype.showModal ??= function showModal() { this.open = true; };
  HTMLDialogElement.prototype.close ??= function close() { this.open = false; };
});
beforeEach(() => {
  auth.user = null;
  flags.mock = false;
  quantityHistory = [];
  localStorage.clear();
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

// ---- the 8 core tests ------------------------------------------------------------

describe('CartContext — guest and customer carts', () => {
  it('1. keeps a guest cart in localStorage and restores it after a reload', async () => {
    const server = fakeServer();
    const first = renderCart();
    act(() => cart.addItem(product(7), 2));
    expect(storedGuestCart()).toEqual([expect.objectContaining({ productId: 7, quantity: 2 })]);

    first.unmount();
    renderCart();
    expect(quantities()).toEqual({ 7: 2 });
    await flush();
    expect(server.cartCalls()).toEqual([]); // guests never call the cart API
  });

  it('2. merges the guest cart into the account cart exactly once after login (StrictMode)', async () => {
    const server = fakeServer({ cart: { 8: 1 } });
    localStorage.setItem(STORAGE_KEY, JSON.stringify([guestLine(7, 2)]));
    const view = renderCart({ strict: true });

    view.setUser(CUSTOMER);
    await waitFor(() => expect(quantities()).toEqual({ 7: 2, 8: 1 }));
    await flush();

    const merges = server.cartCalls().filter((c) => c.path === '/api/cart/merge/');
    expect(merges).toEqual([{ method: 'POST', path: '/api/cart/merge/', body: { items: [{ productId: 7, quantity: 2 }] } }]);
    expect(storedGuestCart()).toBeNull(); // the guest copy is gone from the browser
  });

  it('3. loads the account cart with GET when the guest cart is empty', async () => {
    const server = fakeServer({ cart: { 8: 3 } });
    auth.user = CUSTOMER;
    renderCart();

    await waitFor(() => expect(quantities()).toEqual({ 8: 3 }));
    expect(server.cartCalls().map((c) => `${c.method} ${c.path}`)).toEqual(['GET /api/cart/']);
  });

  it('4. puts the guest cart back into localStorage when the merge fails', async () => {
    const server = fakeServer();
    server.fail = (method, path) => (path === '/api/cart/merge/' ? json({ message: 'boom' }, 500) : undefined);
    localStorage.setItem(STORAGE_KEY, JSON.stringify([guestLine(7, 2)]));
    const view = renderCart();

    view.setUser(CUSTOMER);
    expect(await screen.findByText('Could not load your cart. Please refresh the page.')).toBeTruthy();
    expect(storedGuestCart()).toEqual([expect.objectContaining({ productId: 7, quantity: 2 })]);
  });

  it('5. on logout shows an empty cart and never copies the account cart into localStorage', async () => {
    fakeServer({ cart: { 7: 4 } });
    auth.user = CUSTOMER;
    const view = renderCart();
    await waitFor(() => expect(quantities()).toEqual({ 7: 4 }));

    view.setUser(null);
    await flush();
    expect(cart.items).toEqual([]);
    expect(storedGuestCart() ?? []).toEqual([]);
  });

  it('6. corrects the quantity to what the server allows (stock changed meanwhile)', async () => {
    fakeServer({ stock: { 7: 2 } });
    auth.user = CUSTOMER;
    renderCart();
    await flush();

    act(() => cart.addItem(product(7, { stock: 10 }), 5)); // the page still thinks 10 are left
    expect(quantities()).toEqual({ 7: 5 }); // shown at once…
    await waitFor(() => expect(quantities()).toEqual({ 7: 2 })); // …then fixed by the server reply
    expect(cart.items[0].stock).toBe(2);
  });

  it('7. fast +/+/+ clicks: requests go in order and an older reply never overwrites the screen', async () => {
    const server = fakeServer({ cart: { 7: 1 } });
    auth.user = CUSTOMER;
    renderCart();
    await waitFor(() => expect(quantities()).toEqual({ 7: 1 }));

    server.hold = true;
    act(() => { cart.setQuantity(7, 2); cart.setQuantity(7, 3); cart.setQuantity(7, 4); });
    expect(quantities()).toEqual({ 7: 4 });

    quantityHistory = [];
    await act(async () => { server.release(); });
    await flush();
    expect(quantities()).toEqual({ 7: 4 }); // the reply for "2" is not applied

    await act(async () => { server.release(); });
    await flush();
    await act(async () => { server.release(); });
    await flush();
    expect(quantities()).toEqual({ 7: 4 });
    expect(quantityHistory).not.toContain(2);
    expect(quantityHistory).not.toContain(3);
    expect(server.calls.filter((c) => c.method === 'PATCH').map((c) => c.body.quantity)).toEqual([2, 3, 4]);
  });

  it('8. shows the error and reloads the real cart from the server when an update fails', async () => {
    const server = fakeServer({ cart: { 7: 1 } });
    auth.user = CUSTOMER;
    renderCart();
    await waitFor(() => expect(quantities()).toEqual({ 7: 1 }));

    server.fail = (method) => (method === 'PATCH' ? json({ message: 'This product is out of stock.' }, 400) : undefined);
    act(() => cart.setQuantity(7, 3));
    expect(quantities()).toEqual({ 7: 3 });

    expect(await screen.findByText('This product is out of stock.')).toBeTruthy();
    await waitFor(() => expect(quantities()).toEqual({ 7: 1 }));
    expect(server.cartCalls().map((c) => `${c.method} ${c.path}`).slice(-2)).toEqual(['PATCH /api/cart/items/7/', 'GET /api/cart/']);
  });
});

// ---- extra cases -----------------------------------------------------------------

describe('CartContext — extra cases', () => {
  it('staff roles keep a browser cart and never call the cart API', async () => {
    const server = fakeServer();
    auth.user = { id: 2, role: 'sales_manager' };
    renderCart();
    act(() => cart.addItem(product(7), 1));
    await flush();

    expect(server.cartCalls()).toEqual([]);
    expect(storedGuestCart()).toEqual([expect.objectContaining({ productId: 7, quantity: 1 })]);
  });

  it('mock mode keeps a browser cart even for customers', async () => {
    flags.mock = true;
    const server = fakeServer();
    auth.user = CUSTOMER;
    renderCart();
    act(() => cart.addItem(product(7), 1));
    await flush();

    expect(server.cartCalls()).toEqual([]);
    expect(storedGuestCart()).toEqual([expect.objectContaining({ productId: 7, quantity: 1 })]);
  });

  it('tells the customer when merged items were sold out', async () => {
    fakeServer({ stock: { 8: 0 } });
    localStorage.setItem(STORAGE_KEY, JSON.stringify([guestLine(7, 1), guestLine(8, 1)]));
    auth.user = CUSTOMER;
    renderCart();

    expect(await screen.findByText('Some items from your cart are no longer available and were removed.')).toBeTruthy();
    expect(quantities()).toEqual({ 7: 1 });
  });

  it('remove and empty-cart are sent to the server', async () => {
    const server = fakeServer({ cart: { 7: 1, 8: 2 } });
    auth.user = CUSTOMER;
    renderCart();
    await waitFor(() => expect(quantities()).toEqual({ 7: 1, 8: 2 }));

    act(() => cart.removeItem(7));
    await waitFor(() => expect(server.lines.has(7)).toBe(false));
    act(() => cart.clear());
    await waitFor(() => expect(server.lines.size).toBe(0));
    expect(server.cartCalls().map((c) => `${c.method} ${c.path}`).slice(-2)).toEqual(['DELETE /api/cart/items/7/', 'DELETE /api/cart/']);
    expect(cart.items).toEqual([]);
  });

  it('clear({ local: true }) empties the screen without a DELETE request', async () => {
    const server = fakeServer({ cart: { 7: 1 } });
    auth.user = CUSTOMER;
    renderCart();
    await waitFor(() => expect(quantities()).toEqual({ 7: 1 }));

    act(() => cart.clear({ local: true }));
    await flush();
    expect(cart.items).toEqual([]);
    expect(server.cartCalls().some((c) => c.method === 'DELETE')).toBe(false);
  });
});

// ---- checkout page with the server cart ------------------------------------------

describe('CheckoutPage with the server cart', () => {
  const renderCheckout = () => render(
    <MemoryRouter initialEntries={['/checkout']}>
      <CartProvider>
        <Probe />
        <Routes>
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/cart" element={<p>cart page</p>} />
          <Route path="/orders/:id/invoice" element={<p>invoice page</p>} />
        </Routes>
      </CartProvider>
    </MemoryRouter>,
  );
  const fillAndPay = () => {
    fireEvent.change(screen.getByLabelText('Name on card'), { target: { name: 'holderName', value: 'Ada Lovelace' } });
    fireEvent.change(screen.getByLabelText('Card number'), { target: { name: 'cardNumber', value: '4242424242424242' } });
    fireEvent.change(screen.getByLabelText('Expiry'), { target: { name: 'expiry', value: '1230' } });
    fireEvent.change(screen.getByLabelText('CVV'), { target: { name: 'cvv', value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: /^Pay/ }));
  };

  it('stops before paying when the server cart changed, and shows the updated cart', async () => {
    const server = fakeServer({ cart: { 7: 3 } });
    auth.user = CUSTOMER;
    renderCheckout();
    await screen.findByRole('button', { name: /^Pay/ });

    server.lines.set(7, 1); // someone bought the rest meanwhile
    fillAndPay();

    expect(await screen.findByText(/Stock changed for Perfume 7/)).toBeTruthy();
    expect(quantities()).toEqual({ 7: 1 });
    expect(server.calls.some((c) => c.path === '/api/checkout/')).toBe(false);
  });

  it('pays for the server cart, then clears only the screen (no DELETE /cart/)', async () => {
    const server = fakeServer({ cart: { 7: 2 } });
    auth.user = CUSTOMER;
    renderCheckout();
    await screen.findByRole('button', { name: /^Pay/ });

    fillAndPay();

    expect(await screen.findByText('invoice page')).toBeTruthy();
    expect(cart.items).toEqual([]);
    expect(server.calls.filter((c) => c.path === '/api/checkout/')).toHaveLength(1);
    expect(server.calls.some((c) => c.path.startsWith('/api/cart') && c.method === 'DELETE')).toBe(false);
  });
});
