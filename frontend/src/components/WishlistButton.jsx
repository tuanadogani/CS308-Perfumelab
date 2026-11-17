import { useState } from 'react';
import { useWishlist } from '../context/WishlistContext';
import { useAuth } from '../context/AuthContext';
import Toast from './Toast';

export default function WishlistButton({ product, large = false }) {
  const { user } = useAuth();
  const { isWishlisted, isPending, loading, error: loadError, toggle, reload } = useWishlist();
  const [error, setError] = useState('');
  const [showToast, setShowToast] = useState(false);
  const selected = isWishlisted(product.id);
  const label = selected ? 'Remove from wishlist' : 'Add to wishlist';

  const handleClick = async () => {
    setError('');
    setShowToast(false);
    if (loadError) { reload(); return; }
    try {
      await toggle(product);
    } catch (err) {
      setError(err.message);
      setShowToast(true);
    }
  };

  const errorMessage = error || loadError;
  const showLoginLink = !user && errorMessage && errorMessage.includes('log in');

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
    {showToast && errorMessage && (
      <Toast
        message={showLoginLink ? 'to add items to your wishlist' : errorMessage}
        type="error"
        link={showLoginLink ? { to: '/login', text: 'Log in' } : null}
        onClose={() => {
          setShowToast(false);
          setError('');
        }}
      />
    )}
  </>;
}
