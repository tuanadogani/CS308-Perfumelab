import { useState } from 'react';
import { useWishlist } from '../context/WishlistContext';

export default function WishlistButton({ product, large = false }) {
  const { isWishlisted, isPending, loading, error: loadError, toggle, reload } = useWishlist();
  const [error, setError] = useState('');
  const selected = isWishlisted(product.id);
  const label = selected ? 'Remove from wishlist' : 'Add to wishlist';
  const handleClick = async () => {
    setError('');
    if (loadError) { reload(); return; }
    try { await toggle(product); } catch (err) { setError(err.message); }
  };

  return <>
    <button type="button"
      className={`wishlist-btn ${large ? 'wishlist-btn--large' : ''} ${selected ? 'is-wishlisted' : ''}`}
      onClick={handleClick} disabled={loading || isPending(product.id)}
      aria-label={loadError ? 'Retry loading wishlist' : label} aria-pressed={selected}
      title={loadError || label}>
      <svg width={large ? 24 : 20} height={large ? 24 : 20} viewBox="0 0 24 24"
        fill={selected ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    </button>
    {(error || loadError) && <span className="wishlist-error form-error" role="alert">{error || loadError}</span>}
  </>;
}
