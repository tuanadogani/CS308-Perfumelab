import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ROLES, ROLE_LABELS } from '../../constants/roles';

// Role foundation (Requirement 10): each staff role only sees its own modules.
// [title, description, link?] — modules without a link are not built yet.
const MODULES = {
  [ROLES.PRODUCT_MANAGER]: [
    ['Products & Categories', 'Add / remove products, manage categories'],
    ['Stock Management', 'Update stock quantities'],
    ['Delivery List', 'Pending deliveries and addresses'],
    ['Comment Approval', 'Approve / reject comments'],
  ],
  [ROLES.SUPPORT_AGENT]: [
    ['Live Chat Queue', 'View and claim active conversations'],
  ],
};

export default function AdminDashboard() {
  const { user } = useAuth();
  // Sales managers land straight on their dashboard: all their tools live there.
  if (user.role === ROLES.SALES_MANAGER) return <Navigate to="/admin/sales" replace />;
  const modules = MODULES[user.role] ?? [];
  return (
    <div className="container section">
      <p className="eyebrow">Admin Panel · {ROLE_LABELS[user.role]}</p>
      <h1>Hello, {user.name.split(' ')[0]}</h1>
      <div className="admin-grid">
        {modules.map(([title, desc, to]) => (to ? (
          <Link key={title} to={to} className="admin-card admin-card--link">
            <h3>{title}</h3>
            <p className="muted">{desc}</p>
            <span className="link-arrow">Open →</span>
          </Link>
        ) : (
          <div key={title} className="admin-card admin-card--soon">
            <h3>{title}</h3>
            <p className="muted">{desc}</p>
            <span className="badge badge-low">Coming soon</span>
          </div>
        )))}
      </div>
    </div>
  );
}
