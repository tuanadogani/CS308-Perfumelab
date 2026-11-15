import { formatPrice } from '../utils/format';

export const isDiscounted = (p) => Number(p?.discountRate) > 0 && Number(p?.originalPrice) > Number(p?.price);
export const formatRate = (rate) => `${Number(rate).toLocaleString('en-US', { maximumFractionDigits: 1 })}%`;

// Shows the current price; when the product is discounted, the old price is struck through next to it.
export default function PriceTag({ product, large = false }) {
  const sale = isDiscounted(product);
  return (
    <span className={`price-tag${large ? ' price-tag--lg' : ''}`}>
      {sale && (
        <s className="price-tag__old">
          <span className="sr-only">Original price: </span>{formatPrice(product.originalPrice)}
        </s>
      )}
      <span className={`price${large ? ' price--lg' : ''}`}>
        {sale && <span className="sr-only">Sale price: </span>}{formatPrice(product.price)}
      </span>
    </span>
  );
}

export function SaleBadge({ product, className = '' }) {
  if (!isDiscounted(product)) return null;
  return <span className={`sale-badge ${className}`}>{formatRate(product.discountRate)} off</span>;
}
