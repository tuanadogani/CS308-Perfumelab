export default function WishlistPage() {
  return (
    <section className="cart">
      <div className="container">
        <h1>My Wishlist</h1>
        <p className="lead muted">Save your favorite fragrances for later.</p>

        <div className="empty" style={{ padding: '5rem 1rem' }}>
          <p style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Your wishlist is empty</p>
          <p className="muted">Explore our collection and save fragrances you love.</p>
        </div>
      </div>
    </section>
  );
}
