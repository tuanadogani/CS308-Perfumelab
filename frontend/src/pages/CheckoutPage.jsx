import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { checkout, syncCart } from '../api/checkoutApi';
import { formatPrice } from '../utils/format';
import {
  cartDifferences, formatCardNumber, formatExpiry, toCheckoutBody, validateCheckout,
} from '../utils/checkout';
import '../styles/checkout.css';

// Requirement 4 + 15: the customer enters card details, the (mock) bank confirms,
// then the invoice is shown and emailed. Card number and CVV are only sent, never stored here.
export default function CheckoutPage() {
  const { items, total, setQuantity, clear } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    holderName: user?.name ?? '', cardNumber: '', expiry: '', cvv: '',
    shippingAddress: user?.homeAddress ?? '',
  });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [paying, setPaying] = useState(false);

  if (!items.length && !paying) return <Navigate to="/cart" replace />;

  const onChange = (e) => {
    const { name, value } = e.target;
    const formatted = name === 'cardNumber' ? formatCardNumber(value)
      : name === 'expiry' ? formatExpiry(value)
        : name === 'cvv' ? value.replace(/\D/g, '').slice(0, 4)
          : value;
    setForm({ ...form, [name]: formatted });
    if (errors[name]) setErrors({ ...errors, [name]: undefined });
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (paying) return; // no double charge from a double click (the backend also guards this)
    setMessage('');
    const found = validateCheckout(form);
    setErrors(found);
    if (Object.keys(found).length) return;

    setPaying(true);
    try {
      // 1) Copy the browser cart to the server; stop if stock changed meanwhile.
      const serverCart = await syncCart(items);
      const changed = cartDifferences(items, serverCart);
      if (changed.length) {
        changed.forEach((line) => setQuantity(line.productId, line.quantity));
        setMessage(`Stock changed for ${changed.map((l) => l.name).join(', ')}. `
          + 'We updated your cart — please check it and pay again.');
        setPaying(false);
        return;
      }
      // 2) Pay. On success the order exists, stock is reduced and the invoice is emailed.
      const result = await checkout(toCheckoutBody(form));
      clear();
      navigate(`/orders/${result.order.id}/invoice`, { replace: true, state: { justPaid: true } });
    } catch (err) {
      setMessage(err.status === 402
        ? 'Your card was declined by the bank. Nothing was charged — try another card.'
        : err.message);
      setPaying(false);
    }
  };

  const field = (name) => ({
    name, value: form[name], onChange, 'aria-invalid': errors[name] ? 'true' : undefined,
  });

  return (
    <div className="container section checkout">
      <p className="muted small"><Link to="/cart">← Back to cart</Link></p>
      <h1>Checkout</h1>
      <div className="cart__layout">
        <form className="auth-card checkout-card" onSubmit={onSubmit} noValidate>
          <h3>Delivery address</h3>
          <label>Address
            <textarea rows={2} autoComplete="street-address" {...field('shippingAddress')} />
            {errors.shippingAddress && <span className="field-error">{errors.shippingAddress}</span>}
          </label>

          <h3>Payment</h3>
          <label>Name on card
            <input autoComplete="cc-name" {...field('holderName')} />
            {errors.holderName && <span className="field-error">{errors.holderName}</span>}
          </label>
          <label>Card number
            <input inputMode="numeric" autoComplete="cc-number" placeholder="1234 5678 9012 3456" {...field('cardNumber')} />
            {errors.cardNumber && <span className="field-error">{errors.cardNumber}</span>}
          </label>
          <div className="checkout-card__row">
            <label>Expiry
              <input inputMode="numeric" autoComplete="cc-exp" placeholder="MM/YY" {...field('expiry')} />
              {errors.expiry && <span className="field-error">{errors.expiry}</span>}
            </label>
            <label>CVV
              <input inputMode="numeric" autoComplete="cc-csc" type="password" placeholder="123" {...field('cvv')} />
              {errors.cvv && <span className="field-error">{errors.cvv}</span>}
            </label>
          </div>

          {message && <p className="form-error" role="alert">{message}</p>}

          <button className="btn btn-dark btn-block" disabled={paying}>
            {paying ? 'Processing payment…' : `Pay ${formatPrice(total)}`}
          </button>
          <p className="muted small center">Your card number and CVV are never stored.</p>
        </form>

        <aside className="summary">
          <h3>Order Summary</h3>
          {items.map((i) => (
            <div key={i.productId} className="summary__row">
              <span>{i.quantity} × {i.brand} {i.name}</span>
              <span>{formatPrice(i.price * i.quantity)}</span>
            </div>
          ))}
          <div className="summary__row"><span>Shipping</span><span>Free</span></div>
          <div className="summary__row summary__total"><span>Total</span><span>{formatPrice(total)}</span></div>
        </aside>
      </div>
    </div>
  );
}
