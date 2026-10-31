import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { STAFF_ROLES, ROLE_LABELS } from '../constants/roles';

export default function Navbar() {
  const { user, isAuthenticated, hasRole, logout } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();

  const handleLogout = async () => { await logout(); navigate('/'); };

  return (
    <header className="navbar">
      <div className="container navbar__inner">
        <Link to="/" className="logo">Maison <em>Lumière</em></Link>
        <nav className="navbar__links">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/shop">Collection</NavLink>
          {hasRole(...STAFF_ROLES) && <NavLink to="/admin">Admin</NavLink>}
        </nav>
        <div className="navbar__actions">
          {isAuthenticated ? (
            <>
              <NavLink to="/profile" className="navbar__user" title={ROLE_LABELS[user.role]}>
                {user.name.split(' ')[0]}
              </NavLink>
              <button className="link-btn" onClick={handleLogout}>Log out</button>
            </>
          ) : (
            <NavLink to="/login">Log in</NavLink>
          )}
          <NavLink to="/wishlist" aria-label="Wishlist">Wishlist</NavLink>
          <NavLink to="/cart" className="cart-link" aria-label="Cart">
            Cart <span className="cart-count">{count}</span>
          </NavLink>
        </div>
      </div>
    </header>
  );
}
