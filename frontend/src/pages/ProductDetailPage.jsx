import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import PerfumeBottle from '../components/PerfumeBottle';
import StockBadge from '../components/StockBadge';
import { getProduct } from '../api/productApi';
import { useCart } from '../context/CartContext';
import { formatPrice } from '../utils/format';

export default function ProductDetailPage() {
  const { id } = useParams();
  const { addItem, items } = useCart();
  const [product, setProduct] = useState(null);
  const [error, setError] = useState('');
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);
  const [isWishlisted, setIsWishlisted] = useState(false);

  useEffect(() => {
    setProduct(null); setError('');
    getProduct(id).then(setProduct).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="container section"><p className="form-error">{error}</p><Link to="/shop">← Back to collection</Link></div>;
  if (!product) return <div className="container section muted">Loading…</div>;

  const inCart = items.find((i) => i.productId === product.id)?.quantity ?? 0;
  const maxAddable = Math.max(product.stock - inCart, 0);
  const outOfStock = product.stock <= 0;

  const handleAdd = () => {
    addItem(product, qty);
    setAdded(true);
    setTimeout(() => setAdded(false), 1800);
  };

  return (
    <div className="container detail">
      <Link to="/shop" className="link-arrow">← Collection</Link>
      <div className="detail__grid">
        <div className="detail__media">
          <PerfumeBottle color={product.color} variant={product.id} size={380} alt={product.name} imageUrl={product.imageUrl} />
        </div>

        <div className="detail__info">
          <p className="eyebrow">{product.brand}</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <h1 style={{ margin: 0 }}>{product.name}</h1>
            <button
              className={`wishlist-btn wishlist-btn--large ${isWishlisted ? 'is-wishlisted' : ''}`}
              onClick={() => setIsWishlisted(!isWishlisted)}
              aria-label={isWishlisted ? 'Remove from wishlist' : 'Add to wishlist'}
              title={isWishlisted ? 'Remove from wishlist' : 'Add to wishlist'}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill={isWishlisted ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
              </svg>
            </button>
          </div>
          <p className="muted">{product.gender} · {product.volumeMl} ml · ★ {product.rating}</p>
          <p className="price price--lg">{formatPrice(product.price)}</p>
          <StockBadge stock={product.stock} />
          <p className="lead">{product.description}</p>

          <div className="notes">
            {[['Top Notes', product.notes.top], ['Heart Notes', product.notes.heart], ['Base Notes', product.notes.base]].map(([label, list]) => (
              <div key={label}><h4>{label}</h4><p>{list.join(', ')}</p></div>
            ))}
          </div>

          <div className="buy-row">
            <input type="number" min="1" max={maxAddable || 1} value={qty} disabled={outOfStock || !maxAddable}
              onChange={(e) => setQty(Math.min(Math.max(1, Number(e.target.value) || 1), maxAddable || 1))}
              aria-label="Quantity" />
            <button className="btn btn-dark" disabled={outOfStock || !maxAddable} onClick={handleAdd}>
              {outOfStock ? 'Out of stock' : !maxAddable ? 'All stock is in your cart' : added ? 'Added ✓' : 'Add to cart'}
            </button>
          </div>

          {/* Requirement 9: required product fields */}
          <table className="specs">
            <tbody>
              <tr><th>Product ID</th><td>{product.id}</td></tr>
              <tr><th>Model</th><td>{product.model}</td></tr>
              <tr><th>Serial No.</th><td>{product.serialNumber}</td></tr>
              <tr><th>Stock</th><td>{product.stock}</td></tr>
              <tr><th>Warranty</th><td>{product.warrantyStatus}</td></tr>
              <tr><th>Distributor</th><td>{product.distributor}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
