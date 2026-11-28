import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS, ROLES } from '../constants/roles';

// Requirement 14: the customer can view their name, email and home address on a profile page.
export default function ProfilePage() {
  const { user } = useAuth();
  return (
    <div className="container section">
      <div className="auth-card profile">
        <p className="eyebrow">{ROLE_LABELS[user.role]}</p>
        <h1>{user.name}</h1>
        <dl>
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>Home Address</dt><dd>{user.homeAddress || '—'}</dd>
        </dl>
        {user.role === ROLES.CUSTOMER && (
          <Link to="/orders" className="btn btn-dark">View my orders</Link>
        )}
      </div>
    </div>
  );
}
