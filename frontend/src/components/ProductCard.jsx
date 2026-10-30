import { Link } from 'react-router-dom';
import PerfumeBottle from './PerfumeBottle';
import StockBadge from './StockBadge';
import { useCart } from '../context/CartContext';
import { formatPrice } from '../utils/format';

export default function ProductCard({ product }) {
  const { addItem } = useCart();
  const outOfStock = product.stock <= 0;

  return (
    <article className={`product-card ${outOfStock ? 'is-out' : ''}`}>
      <Link to={`/shop/${product.id}`} className="product-card__media">
        <PerfumeBottle color={product.color} variant={product.id} size={190} alt={product.name} imageUrl={product.imageUrl} />
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
