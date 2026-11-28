import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { cancelOrder, getOrders, requestRefund } from '../api/ordersApi';
import { formatPrice } from '../utils/format';
import {
  DELIVERY_STEPS, ORDER_FILTERS, REFUND_STATUS_LABELS, canCancel, canRequestRefund, deliveryStep,
  filterOrders, itemCount, refundDeadline, statusLabel,
} from '../utils/orders';
import '../styles/orders.css';

const formatDate = (value) => (value ? new Date(value).toLocaleDateString(undefined, {
  year: 'numeric', month: 'short', day: 'numeric',
}) : '');

// Requirement 3: the customer follows each order as processing → in transit → delivered.
// Requirement 14: an order can be cancelled while it is still processing.
export default function OrdersPage() {
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState('');
  const [params, setParams] = useSearchParams();
  const filter = ORDER_FILTERS.some(([key]) => key === params.get('filter')) ? params.get('filter') : 'all';

  const load = () => {
    setError('');
    return getOrders().then(setOrders).catch((err) => setError(err.message || 'Could not load your orders.'));
  };
  useEffect(() => { load(); }, []);

  const shown = useMemo(() => (orders ? filterOrders(orders, filter) : []), [orders, filter]);
  const replaceOrder = (updated) => setOrders((list) => list.map((o) => (o.id === updated.id ? updated : o)));

  if (error && !orders) {
    return (
      <div className="container section empty">
        <h2>{error}</h2>
        <button className="btn btn-dark" onClick={load}>Try again</button>
      </div>
    );
  }
  if (!orders) return <div className="container section muted">Loading your orders…</div>;

  if (!orders.length) {
    return (
      <div className="container section empty">
        <h2>No orders yet</h2>
        <p className="muted">When you place an order, you can follow its delivery here.</p>
        <Link to="/shop" className="btn btn-dark">Go to collection</Link>
      </div>
    );
  }

  return (
    <div className="container section orders">
      <header className="orders__head">
        <div>
          <p className="eyebrow">My account</p>
          <h1>My Orders</h1>
        </div>
        <button className="link-btn" onClick={load}>Refresh status</button>
      </header>

      <div className="orders__filters" role="tablist" aria-label="Filter orders">
        {ORDER_FILTERS.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={filter === key}
            className={`chip ${filter === key ? 'active' : ''}`}
            onClick={() => setParams(key === 'all' ? {} : { filter: key }, { replace: true })}>
            {label} <span className="muted">({filterOrders(orders, key).length})</span>
          </button>
        ))}
      </div>

      {shown.length === 0
        ? <div className="empty">No orders in this list.</div>
        : <ul className="orders__list">{shown.map((o) => <OrderCard key={o.id} order={o} onUpdate={replaceOrder} />)}</ul>}
    </div>
  );
}

function OrderCard({ order, onUpdate }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  const handleCancel = async () => {
    setBusy(true); setMessage(null);
    try {
      onUpdate(await cancelOrder(order.id));
      setMessage({ ok: true, text: 'Your order was cancelled. Nothing will be shipped.' });
    } catch (err) {
      setMessage({ ok: false, text: err.message || 'Could not cancel the order.' });
    } finally {
      setBusy(false); setConfirming(false);
    }
  };

  return (
    <li className="order-card">
      <div className="order-card__head">
        <div>
          <h3>Order #{order.id}</h3>
          <p className="muted small">
            Placed {formatDate(order.createdAt)} · {itemCount(order)} item{itemCount(order) === 1 ? '' : 's'}
          </p>
        </div>
        <div className="order-card__total">
          <span className={`status status--${order.status}`}>{statusLabel(order.status)}</span>
          <strong>{formatPrice(order.total)}</strong>
        </div>
      </div>

      <StatusTracker order={order} />

      <ul className="order-card__items">
        {order.items.map((item) => (
          <OrderLine
            key={item.id}
            order={order}
            item={item}
            onRefund={(refund) => onUpdate({
              ...order,
              items: order.items.map((i) => (i.id === item.id ? { ...i, refund } : i)),
            })}
          />
        ))}
      </ul>

      {order.status === 'delivered' && order.items.some((i) => canRequestRefund(order, i)) && (
        <p className="muted small order-card__address">
          Returns accepted until {formatDate(refundDeadline(order))} (30 days after purchase).
        </p>
      )}

      <p className="muted small order-card__address"><strong>Delivery address:</strong> {order.shippingAddress}</p>

      {message && <p className={message.ok ? 'form-success' : 'form-error'} role="status">{message.text}</p>}

      <div className="order-card__actions">
        <Link className="btn btn-ghost" to={`/orders/${order.id}/invoice`}>View invoice</Link>
        {canCancel(order) && !confirming && (
          <button className="link-btn" onClick={() => setConfirming(true)}>Cancel order</button>
        )}
        {canCancel(order) && confirming && (
          <span className="order-card__confirm">
            <span className="small">Cancel this order?</span>
            <button className="btn btn-dark" disabled={busy} onClick={handleCancel}>
              {busy ? 'Cancelling…' : 'Yes, cancel'}
            </button>
            <button className="link-btn" disabled={busy} onClick={() => setConfirming(false)}>Keep order</button>
          </span>
        )}
      </div>
    </li>
  );
}

function StatusTracker({ order }) {
  if (order.status === 'cancelled') {
    return <p className="order-track__note">This order was cancelled and its items were returned to stock.</p>;
  }
  const reached = deliveryStep(order.status);
  return (
    <ol className="order-track" aria-label={`Delivery status: ${statusLabel(order.status)}`}>
      {DELIVERY_STEPS.map((step, i) => (
        <li key={step} className={`order-track__step${i <= reached ? ' is-done' : ''}${i === reached ? ' is-current' : ''}`}
          aria-current={i === reached ? 'step' : undefined}>
          <span className="order-track__dot" aria-hidden="true">{i < reached || (i === reached && step === 'delivered') ? '✓' : i + 1}</span>
          <span className="order-track__label">{statusLabel(step)}</span>
          {step === 'delivered' && order.deliveredAt && (
            <span className="muted small">{formatDate(order.deliveredAt)}</span>
          )}
        </li>
      ))}
    </ol>
  );
}

// Requirement 16: return one purchased product of a delivered order within 30 days.
function OrderLine({ order, item, onRefund }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const refund = item.refund;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      onRefund(await requestRefund(order.id, item.id, reason.trim()));
      setOpen(false);
    } catch (err) {
      setError(err.message || 'Could not request the return.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="order-line">
      <div className="order-line__row">
        <span>
          <Link to={`/shop/${item.productId}`}>{item.productName}</Link>
          <span className="muted"> × {item.quantity}</span>
          {order.status === 'delivered' && !refund && (
            <Link className="order-card__review small" to={`/shop/${item.productId}`}>Rate &amp; review</Link>
          )}
          {canRequestRefund(order, item) && !open && (
            <button type="button" className="link-btn order-card__review" onClick={() => setOpen(true)}>Return</button>
          )}
          {refund && (
            <span className={`status status--${refund.status === 'approved' ? 'refunded' : refund.status === 'rejected' ? 'cancelled' : 'processing'} order-card__refund`}>
              {REFUND_STATUS_LABELS[refund.status] ?? refund.status}
            </span>
          )}
        </span>
        <span>{formatPrice(item.lineTotal)}</span>
      </div>

      {refund && <RefundNote refund={refund} />}

      {open && (
        <form className="return-form" onSubmit={submit}>
          <p className="small">
            Return <strong>{item.quantity} × {item.productName}</strong>. If approved, you get back{' '}
            <strong>{formatPrice(item.lineTotal)}</strong>, the price you paid, to your card.
          </p>
          <label className="small" htmlFor={`reason-${item.id}`}>Reason <span className="muted">(optional)</span></label>
          <textarea id={`reason-${item.id}`} rows={2} maxLength={2000} value={reason}
            onChange={(e) => setReason(e.target.value)} placeholder="e.g. Not the scent I expected" />
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="return-form__actions">
            <button type="submit" className="btn btn-dark" disabled={busy}>{busy ? 'Sending…' : 'Request return'}</button>
            <button type="button" className="link-btn" disabled={busy} onClick={() => { setOpen(false); setError(''); }}>Cancel</button>
          </div>
        </form>
      )}
    </li>
  );
}

function RefundNote({ refund }) {
  if (refund.status === 'approved') {
    const paid = refund.paymentRefund?.amount ?? refund.amount;
    return (
      <p className="muted small order-line__note">
        {formatPrice(paid)} was refunded to your card on {formatDate(refund.paymentRefund?.refundedAt ?? refund.decidedAt)}.
      </p>
    );
  }
  if (refund.status === 'rejected') {
    return <p className="muted small order-line__note">Your return request was not accepted.</p>;
  }
  return (
    <p className="muted small order-line__note">
      {refund.receivedAt
        ? 'We received the product and are reviewing your refund.'
        : 'Please send the product back to us. We will refund it once it arrives.'}
      {' '}Refund amount: {formatPrice(refund.amount)}.
    </p>
  );
}
