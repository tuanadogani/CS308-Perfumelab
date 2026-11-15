import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import PerfumeBottle from '../components/PerfumeBottle';
import { formatPrice } from '../utils/format';

export default function CartPage() {
  const { items, total, setQuantity, removeItem, clear } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleCheckout = () => {
    // Requirement 4: login is required to order; the cart is kept (localStorage)
    if (!isAuthenticated) return navigate('/login', { state: { from: '/cart' } });
    alert('Checkout will be added in Sprint 2.');
  };

  if (!items.length) {
    return (
      <div className="container section empty">
        <h2>Your cart is empty</h2>
        <p className="muted">Explore the collection to find your scent.</p>
        <Link to="/shop" className="btn btn-dark">Go to collection</Link>
      </div>
    );
  }

  return (
    <div className="container section cart">
      <h1>My Cart</h1>
      <div className="cart__layout">
        <ul className="cart__list">
          {items.map((i) => (
            <li key={i.productId} className="cart-item">
              <PerfumeBottle color={i.color} variant={i.productId} size={90} alt={i.name} imageUrl={i.imageUrl} />
              <div className="cart-item__info">
                <p className="eyebrow">{i.brand}</p>
                <Link to={`/shop/${i.productId}`}><strong>{i.name}</strong></Link>
                <p className="muted small">{i.volumeMl} ml · {formatPrice(i.price)}</p>
              </div>
              <div className="qty">
                <button onClick={() => setQuantity(i.productId, i.quantity - 1)} aria-label="Decrease">−</button>
                <span>{i.quantity}</span>
                <button onClick={() => setQuantity(i.productId, i.quantity + 1)} disabled={i.quantity >= i.stock} aria-label="Increase">+</button>
              </div>
              <strong className="cart-item__total">{formatPrice(i.price * i.quantity)}</strong>
              <button className="link-btn" onClick={() => removeItem(i.productId)}>Remove</button>
            </li>
          ))}
        </ul>

        <aside className="summary">
          <h3>Order Summary</h3>
          <div className="summary__row"><span>Subtotal</span><span>{formatPrice(total)}</span></div>
          <div className="summary__row"><span>Shipping</span><span>Free</span></div>
          <div className="summary__row summary__total"><span>Total</span><span>{formatPrice(total)}</span></div>
          <button className="btn btn-gold btn-block" onClick={handleCheckout}>
            {isAuthenticated ? 'Proceed to checkout' : 'Log in to continue'}
          </button>
          <button className="link-btn" onClick={clear}>Empty cart</button>
        </aside>
      </div>
    </div>
  );
}
