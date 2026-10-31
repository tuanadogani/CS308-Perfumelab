import { Link } from 'react-router-dom';

// "Get Started" → sign up / log in / continue as guest
export default function StartPage() {
  return (
    <section className="auth-page">
      <div className="auth-card auth-card--center">
        <p className="eyebrow">Welcome</p>
        <h1>How would you like to continue?</h1>
        <div className="start-options">
          <Link to="/login" className="btn btn-dark btn-block">I have an account — Log in</Link>
          <Link to="/register" className="btn btn-gold btn-block">Create a new account</Link>
          <Link to="/shop" className="link-arrow">Browse as a guest →</Link>
        </div>
        <p className="muted small">You can add products to your cart as a guest; you need to log in to place an order.</p>
      </div>
    </section>
  );
}
