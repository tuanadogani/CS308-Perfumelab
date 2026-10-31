import { Link } from 'react-router-dom';
import { useState } from 'react';
import PerfumeBottle from './PerfumeBottle';
import StockBadge from './StockBadge';
import { useCart } from '../context/CartContext';
import { formatPrice } from '../utils/format';

export default function ProductCard({ product }) {
  const { addItem } = useCart();
  const [isWishlisted, setIsWishlisted] = useState(false);
  const outOfStock = product.stock <= 0;

  const toggleWishlist = (e) => {
    e.preventDefault();
    setIsWishlisted(!isWishlisted);
  };

  return (
    <article className={`product-card ${outOfStock ? 'is-out' : ''}`}>
      <Link to={`/shop/${product.id}`} className="product-card__media">
        <PerfumeBottle color={product.color} variant={product.id} size={190} alt={product.name} imageUrl={product.imageUrl} />
        <button
          className={`wishlist-btn ${isWishlisted ? 'is-wishlisted' : ''}`}
          onClick={toggleWishlist}
          aria-label={isWishlisted ? 'Remove from wishlist' : 'Add to wishlist'}
          title={isWishlisted ? 'Remove from wishlist' : 'Add to wishlist'}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill={isWishlisted ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
        </button>
      </Link>
      <div className="product-card__body">
        <p className="eyebrow">{product.brand}</p>
        <h3><Link to={`/shop/${product.id}`}>{product.name}</Link></h3>
        <p className="muted small">{product.notes.heart.join(' · ')} — {product.volumeMl} ml</p>
        <div className="product-card__row">
          <span className="price">{formatPrice(product.price)}</span>
          <StockBadge stock={product.stock} />
        </div>
        <button
          className="btn btn-dark btn-block"
          disabled={outOfStock}
          onClick={() => addItem(product)}
          title={outOfStock ? 'This product is currently out of stock' : 'Add to cart'}
        >
          {outOfStock ? 'Out of stock' : 'Add to cart'}
        </button>
      </div>
    </article>
  );
}
