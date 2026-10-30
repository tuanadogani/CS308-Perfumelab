import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../constants/roles';

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
        <p className="muted small">Order history and wish list will be added in later sprints.</p>
      </div>
    </div>
  );
}
