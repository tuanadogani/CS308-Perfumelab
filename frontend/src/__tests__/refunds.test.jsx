// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { requestRefund } from '../api/ordersApi';
import { decideRefund, getRefunds, receiveRefund } from '../api/salesApi';
import OrdersPage from '../pages/OrdersPage';
import { RefundsTab, refundStage } from '../pages/admin/SalesDashboard';
import { canRequestRefund, refundDeadline } from '../utils/orders';

// Requirements 14 & 16: a delivered item can be returned within 30 days; the sales manager
// receives it, then approves (card refund at the purchase price, restock, email) or rejects.

vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { id: 2, name: 'Monica Sales', role: 'sales_manager' } }) }));

const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const NOW = new Date('2026-11-28T12:00:00+03:00');
const daysBefore = (n) => new Date(NOW.getTime() - n * 86400000).toISOString();
const deliveredOrder = (extra = {}) => ({
  id: 12, status: 'delivered', total: '900.00', shippingAddress: 'Moda', createdAt: daysBefore(5), deliveredAt: daysBefore(2),
  items: [{ id: 120, productId: 7, productName: 'Sauvage', quantity: 2, unitPrice: '450.00', lineTotal: '900.00', refund: null }],
  ...extra,
});

describe('refund eligibility', () => {
  it('allows a delivered item without a request inside 30 days', () => {
    const order = deliveredOrder();
    expect(canRequestRefund(order, order.items[0], NOW)).toBe(true);
  });

  it('refuses orders that are not delivered', () => {
    ['processing', 'in_transit', 'cancelled', 'refunded'].forEach((status) => {
      const order = deliveredOrder({ status });
      expect(canRequestRefund(order, order.items[0], NOW)).toBe(false);
    });
  });

  it('counts 30 days from purchase, not delivery', () => {
    const order = deliveredOrder({ createdAt: daysBefore(31), deliveredAt: daysBefore(1) });
    expect(canRequestRefund(order, order.items[0], NOW)).toBe(false);
    expect(refundDeadline(deliveredOrder({ createdAt: '2026-11-01T00:00:00Z' })).toISOString()).toBe('2026-12-01T00:00:00.000Z');
  });

  it('refuses a line that already has a request', () => {
    const order = deliveredOrder();
    expect(canRequestRefund(order, { ...order.items[0], refund: { status: 'rejected' } }, NOW)).toBe(false);
  });
});

describe('refund API calls', () => {
  it('uses the documented endpoints', async () => {
    const fetchMock = vi.fn(async () => json({}));
    vi.stubGlobal('fetch', fetchMock);
    await requestRefund(12, 120, 'Too sweet');
    await getRefunds('requested');
    await receiveRefund(3);
    await decideRefund(3, true);
    const calls = fetchMock.mock.calls.map(([url, init]) => [init.method ?? 'GET', url, init.body && JSON.parse(init.body)]);
    expect(calls).toEqual([
      ['POST', '/api/orders/12/items/120/refund/', { reason: 'Too sweet' }],
      ['GET', '/api/sales/refunds/?status=requested', undefined],
      ['POST', '/api/sales/refunds/3/receive/', undefined],
      ['POST', '/api/sales/refunds/3/decision/', { approve: true }],
    ]);
  });
});

describe('customer return request (My Orders)', () => {
  function renderOrders(order, onRefund) {
    const calls = [];
    vi.stubGlobal('fetch', vi.fn(async (url, init = {}) => {
      calls.push({ url, method: init.method ?? 'GET', body: init.body && JSON.parse(init.body) });
      if (url === '/api/orders/') return json([order]);
      if (url.endsWith('/refund/')) return onRefund();
      return json({}, 404);
    }));
    render(<MemoryRouter><OrdersPage /></MemoryRouter>);
    return calls;
  }

  it('asks for an optional reason, shows the amount and sends the request', async () => {
    const calls = renderOrders(deliveredOrder({ createdAt: new Date().toISOString() }), () => json({
      id: 3, orderItemId: 120, status: 'requested', amount: '900.00', receivedAt: null, paymentRefund: null,
    }, 201));
    fireEvent.click(await screen.findByRole('button', { name: 'Return' }));
    expect(screen.getByText(/the price you paid/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: '  Too sweet ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Request return' }));
    expect(await screen.findByText('Return requested')).toBeTruthy();
    expect(screen.getByText(/Please send the product back/)).toBeTruthy();
    expect(calls.find((c) => c.method === 'POST')).toEqual({ url: '/api/orders/12/items/120/refund/', method: 'POST', body: { reason: 'Too sweet' } });
    expect(screen.queryByRole('button', { name: 'Return' })).toBeNull();
  });

  it('shows the backend message when the request is refused', async () => {
    renderOrders(deliveredOrder({ createdAt: new Date().toISOString() }),
      () => json({ message: 'The 30-day refund window has passed.' }, 400));
    fireEvent.click(await screen.findByRole('button', { name: 'Return' }));
    fireEvent.click(screen.getByRole('button', { name: 'Request return' }));
    expect(await screen.findByText('The 30-day refund window has passed.')).toBeTruthy();
  });

  it('offers no return after 30 days', async () => {
    renderOrders(deliveredOrder({ createdAt: '2026-01-01T00:00:00Z' }));
    await screen.findByText('Order #12');
    expect(screen.queryByRole('button', { name: 'Return' })).toBeNull();
  });

  it('shows the refunded amount once approved', async () => {
    const order = deliveredOrder({ status: 'refunded' });
    order.items[0].refund = {
      id: 3, status: 'approved', amount: '900.00', decidedAt: daysBefore(1),
      paymentRefund: { amount: '900.00', transactionId: 'RFND-1', refundedAt: daysBefore(1) },
    };
    renderOrders(order);
    expect(await screen.findByText(/was refunded to your card/)).toBeTruthy();
    expect(screen.getByText('Refunded', { selector: '.order-card__refund' })).toBeTruthy();
  });
});

const refund = (extra = {}) => ({
  id: 3, orderId: 12, orderItemId: 120, customerName: 'Ross Customer', customerEmail: 'customer@demo.com',
  productId: 7, productName: 'Sauvage', quantity: 2, unitPrice: '450.00', amount: '900.00', reason: 'Too sweet',
  status: 'requested', requestedAt: daysBefore(1), receivedAt: null, decidedAt: null, paymentRefund: null, ...extra,
});

describe('sales manager refund tab', () => {
  function renderTab(list, handlers = {}) {
    const calls = [];
    vi.stubGlobal('fetch', vi.fn(async (url, init = {}) => {
      const method = init.method ?? 'GET';
      calls.push({ url, method, body: init.body && JSON.parse(init.body) });
      if (url === '/api/sales/refunds/') return json(list);
      if (url.endsWith('/receive/')) return handlers.receive?.() ?? json(refund({ receivedAt: NOW.toISOString() }));
      if (url.endsWith('/decision/')) return handlers.decide?.(JSON.parse(init.body)) ?? json({});
      return json({}, 404);
    }));
    render(<MemoryRouter><RefundsTab /></MemoryRouter>);
    return calls;
  }

  it('names each stage', () => {
    expect(refundStage(refund())).toBe('Waiting for product');
    expect(refundStage(refund({ receivedAt: 'x' }))).toBe('Product received');
    expect(refundStage(refund({ status: 'approved' }))).toBe('Refunded');
    expect(refundStage(refund({ status: 'rejected' }))).toBe('Rejected');
  });

  it('lists pending requests with customer, product, reason and the paid amount', async () => {
    renderTab([refund(), refund({ id: 4, status: 'approved', productName: 'Libre' })]);
    const row = (await screen.findByText('Sauvage')).closest('tr');
    expect(within(row).getByText('Ross Customer')).toBeTruthy();
    expect(within(row).getByText('“Too sweet”')).toBeTruthy();
    expect(within(row).getByText('Waiting for product')).toBeTruthy();
    expect(screen.queryByText('Libre')).toBeNull(); // the Pending filter hides decided requests
  });

  it('cannot approve before the product is received', async () => {
    renderTab([refund()]);
    await screen.findByText('Sauvage');
    expect(screen.queryByRole('button', { name: 'Approve refund' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Mark received' })).toBeTruthy();
  });

  it('marks received, then approves after confirmation', async () => {
    const calls = renderTab([refund()], {
      decide: () => json(refund({
        status: 'approved', receivedAt: NOW.toISOString(), decidedAt: NOW.toISOString(),
        paymentRefund: { amount: '900.00', transactionId: 'RFND-ABC', refundedAt: NOW.toISOString() },
      })),
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Mark received' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Approve refund' }));
    expect(calls.some((c) => c.url.endsWith('/decision/'))).toBe(false); // asks first
    fireEvent.click(screen.getByRole('button', { name: 'Yes, refund' }));
    fireEvent.click(await screen.findByRole('tab', { name: /Refunded/ }));
    expect(await screen.findByText('Ref RFND-ABC')).toBeTruthy();
    expect(calls.find((c) => c.url.endsWith('/decision/')).body).toEqual({ approve: true });
  });

  it('rejects without needing the product', async () => {
    const calls = renderTab([refund()], { decide: () => json(refund({ status: 'rejected', decidedAt: NOW.toISOString() })) });
    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }));
    fireEvent.click(screen.getByRole('button', { name: 'Yes, reject' }));
    fireEvent.click(await screen.findByRole('tab', { name: /Rejected/ }));
    expect(await screen.findByText('Rejected', { selector: '.status' })).toBeTruthy();
    expect(calls.find((c) => c.url.endsWith('/decision/')).body).toEqual({ approve: false });
  });

  it('keeps the request pending and shows the bank error', async () => {
    renderTab([refund({ receivedAt: NOW.toISOString() })], {
      decide: () => json({ message: 'The bank could not process the refund. Please retry.' }, 502),
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Approve refund' }));
    fireEvent.click(screen.getByRole('button', { name: 'Yes, refund' }));
    expect(await screen.findByText(/bank could not process/)).toBeTruthy();
    expect(screen.getByText('Product received')).toBeTruthy();
  });
});
