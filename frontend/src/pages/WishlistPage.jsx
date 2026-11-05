import { Link } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { useWishlist } from '../context/WishlistContext';

export default function WishlistPage() {
  const { items, loading, error, reload } = useWishlist();
  return (
    <section className="container section">
      <h1>My Wishlist</h1>
      <p className="lead muted">Save your favorite fragrances for later.</p>
      {loading ? <p role="status">Loading wishlist…</p> : error ? (
        <div role="alert"><p className="form-error">{error}</p><button className="btn btn-dark" onClick={reload}>Try again</button></div>
      ) : items.length ? (
        <div className="grid">{items.map((product) => <ProductCard key={product.id} product={product} />)}</div>
      ) : (
        <div className="empty" style={{ padding: '5rem 1rem' }}>
          <p>Your wishlist is empty</p>
          <p className="muted">Explore our collection and save fragrances you love.</p>
          <Link to="/shop" className="btn btn-dark">Explore collection</Link>
        </div>
      )}
    </section>
  );
}
