// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { setAccessToken } from '../api/client';
import { cancelOrder, getOrder, getOrders } from '../api/ordersApi';
import OrdersPage from '../pages/OrdersPage';
import {
  canCancel, deliveryStep, filterOrders, isOpen, itemCount, statusLabel,
} from '../utils/orders';

// Requirement 3: order history with processing / in-transit / delivered status.

const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

const order = (id, status, extra = {}) => ({
  id,
  status,
  total: '300.00',
  shippingAddress: 'Kadıköy, Istanbul',
  createdAt: '2026-11-20T10:00:00+03:00',
  deliveredAt: status === 'delivered' ? '2026-11-24T10:00:00+03:00' : null,
  items: [
    { id: id * 10, productId: 7, productName: 'Sauvage', quantity: 2, unitPrice: '100.00', lineTotal: '200.00', refund: null },
    { id: id * 10 + 1, productId: 8, productName: 'Bleu', quantity: 1, unitPrice: '100.00', lineTotal: '100.00', refund: null },
  ],
  ...extra,
});

afterEach(() => { cleanup(); setAccessToken(null); vi.unstubAllGlobals(); });

describe('order status helpers', () => {
  it('labels every backend status', () => {
    expect(statusLabel('processing')).toBe('Processing');
    expect(statusLabel('in_transit')).toBe('In transit');
    expect(statusLabel('delivered')).toBe('Delivered');
    expect(statusLabel('cancelled')).toBe('Cancelled');
    expect(statusLabel('refunded')).toBe('Refunded');
  });

  it('falls back to the raw value for an unknown status', () => {
    expect(statusLabel('lost')).toBe('lost');
  });

  it('maps statuses to delivery steps', () => {
    expect(deliveryStep('processing')).toBe(0);
    expect(deliveryStep('in_transit')).toBe(1);
    expect(deliveryStep('delivered')).toBe(2);
    expect(deliveryStep('refunded')).toBe(2); // a refunded order was delivered first
    expect(deliveryStep('cancelled')).toBe(-1);
  });

  it('allows cancelling only processing orders', () => {
    expect(canCancel(order(1, 'processing'))).toBe(true);
    ['in_transit', 'delivered', 'cancelled', 'refunded'].forEach((s) => expect(canCancel(order(1, s))).toBe(false));
    expect(canCancel(null)).toBe(false);
  });

  it('treats processing and in-transit orders as open', () => {
    expect(isOpen(order(1, 'processing'))).toBe(true);
    expect(isOpen(order(1, 'in_transit'))).toBe(true);
    expect(isOpen(order(1, 'delivered'))).toBe(false);
  });

  it('filters the list by tab', () => {
    const list = ['processing', 'in_transit', 'delivered', 'cancelled', 'refunded'].map((s, i) => order(i + 1, s));
    expect(filterOrders(list, 'all')).toHaveLength(5);
    expect(filterOrders(list, 'open').map((o) => o.status)).toEqual(['processing', 'in_transit']);
    expect(filterOrders(list, 'delivered').map((o) => o.status)).toEqual(['delivered']);
    expect(filterOrders(list, 'closed').map((o) => o.status)).toEqual(['cancelled', 'refunded']);
  });

  it('counts units, not lines', () => {
    expect(itemCount(order(1, 'processing'))).toBe(3);
    expect(itemCount({ items: [] })).toBe(0);
  });
});

describe('orders API', () => {
  it('lists, reads and cancels orders with the access token', async () => {
    const fetchMock = vi.fn(async () => json([]));
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('abc');

    await getOrders();
    await getOrder(5);
    await cancelOrder(5);

    const [[listUrl, listInit], [detailUrl], [cancelUrl, cancelInit]] = fetchMock.mock.calls;
    expect(listUrl).toBe('/api/orders/');
    expect(listInit.headers.Authorization).toBe('Bearer abc');
    expect(detailUrl).toBe('/api/orders/5/');
    expect(cancelUrl).toBe('/api/orders/5/cancel/');
    expect(cancelInit.method).toBe('POST');
  });

  it('passes the backend message on a refused cancel', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ message: "Only orders in 'processing' status can be cancelled." }, 400)));
    await expect(cancelOrder(5)).rejects.toMatchObject({ status: 400, message: expect.stringContaining('processing') });
  });
});

function renderPage(orders, onCancel) {
  vi.stubGlobal('fetch', vi.fn(async (url, init = {}) => {
    if (url === '/api/orders/') return json(orders);
    if (init.method === 'POST' && url.endsWith('/cancel/')) return onCancel(url);
    return json({}, 404);
  }));
  return render(<MemoryRouter initialEntries={['/orders']}><OrdersPage /></MemoryRouter>);
}

describe('OrdersPage', () => {
  it('shows an empty state with a link to the shop', async () => {
    renderPage([]);
    expect(await screen.findByText('No orders yet')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Go to collection' }).getAttribute('href')).toBe('/shop');
  });

  it('shows each order with its status, items and invoice link', async () => {
    renderPage([order(2, 'in_transit'), order(1, 'delivered')]);
    expect(await screen.findByText('Order #2')).toBeTruthy();
    expect(screen.getByText('Order #1')).toBeTruthy();
    expect(screen.getByLabelText('Delivery status: In transit')).toBeTruthy();
    expect(screen.getByLabelText('Delivery status: Delivered')).toBeTruthy();
    const invoiceLinks = screen.getAllByRole('link', { name: 'View invoice' }).map((a) => a.getAttribute('href'));
    expect(invoiceLinks).toEqual(['/orders/2/invoice', '/orders/1/invoice']);
  });

  it('offers review links only for delivered orders', async () => {
    renderPage([order(2, 'in_transit'), order(1, 'delivered')]);
    await screen.findByText('Order #1');
    expect(screen.getAllByRole('link', { name: 'Rate & review' })).toHaveLength(2); // two lines of order #1
  });

  it('offers cancel only for processing orders', async () => {
    renderPage([order(3, 'processing'), order(2, 'in_transit')]);
    await screen.findByText('Order #3');
    expect(screen.getAllByRole('button', { name: 'Cancel order' })).toHaveLength(1);
  });

  it('cancels after confirmation and shows the new status', async () => {
    const onCancel = vi.fn(() => json(order(3, 'cancelled')));
    renderPage([order(3, 'processing')], onCancel);
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel order' }));
    expect(onCancel).not.toHaveBeenCalled(); // first click only asks
    fireEvent.click(screen.getByRole('button', { name: 'Yes, cancel' }));
    await screen.findByText(/Your order was cancelled/);
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: 'Cancel order' })).toBeNull();
    expect(screen.getByText(/returned to stock/)).toBeTruthy();
  });

  it('keeps the order and shows the error when cancelling fails', async () => {
    renderPage([order(3, 'processing')], () => json({ message: 'Order already shipped.' }, 400));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel order' }));
    fireEvent.click(screen.getByRole('button', { name: 'Yes, cancel' }));
    expect(await screen.findByText('Order already shipped.')).toBeTruthy();
    expect(screen.getByLabelText('Delivery status: Processing')).toBeTruthy();
  });

  it('filters orders with the tabs', async () => {
    renderPage([order(3, 'processing'), order(2, 'delivered'), order(1, 'cancelled')]);
    await screen.findByText('Order #3');
    fireEvent.click(screen.getByRole('tab', { name: /Delivered/ }));
    await waitFor(() => expect(screen.queryByText('Order #3')).toBeNull());
    expect(screen.getByText('Order #2')).toBeTruthy();
    expect(screen.queryByText('Order #1')).toBeNull();
  });

  it('shows the return status of a refunded line', async () => {
    const refunded = order(4, 'delivered');
    refunded.items[0].refund = { id: 1, status: 'requested' };
    renderPage([refunded]);
    const card = (await screen.findByText('Order #4')).closest('li');
    expect(within(card).getByText('Return requested')).toBeTruthy();
    expect(within(card).getAllByRole('link', { name: 'Rate & review' })).toHaveLength(1);
  });

  it('shows an error with a retry button when loading fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ message: 'Server down' }, 500)));
    render(<MemoryRouter><OrdersPage /></MemoryRouter>);
    expect(await screen.findByText('Server down')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy();
  });
});
