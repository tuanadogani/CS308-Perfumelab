import { useAuth } from '../../context/AuthContext';
import { ROLES, ROLE_LABELS } from '../../constants/roles';

// Role foundation (Requirement 10): each staff role only sees its own modules.
// Skeleton in Sprint 1; contents are filled in during the relevant sprints.
const MODULES = {
  [ROLES.PRODUCT_MANAGER]: [
    ['Products & Categories', 'Add / remove products, manage categories', 'Sprint 3'],
    ['Stock Management', 'Update stock quantities', 'Sprint 3'],
    ['Delivery List', 'Pending deliveries and addresses', 'Sprint 3'],
    ['Comment Approval', 'Approve / reject comments', 'Sprint 3'],
  ],
  [ROLES.SALES_MANAGER]: [
    ['Pricing & Discounts', 'Set prices, apply discounts', 'Sprint 4'],
    ['Invoices', 'View invoices in a date range / export PDF', 'Sprint 4'],
    ['Revenue Report', 'Profit / loss chart', 'Sprint 4'],
    ['Refund Requests', 'Evaluate refund requests', 'Sprint 5'],
  ],
  [ROLES.SUPPORT_AGENT]: [
    ['Live Chat Queue', 'View and claim active conversations', 'Sprint 4'],
  ],
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const modules = MODULES[user.role] ?? [];
  return (
    <div className="container section">
      <p className="eyebrow">Admin Panel · {ROLE_LABELS[user.role]}</p>
      <h1>Hello, {user.name.split(' ')[0]}</h1>
      <div className="admin-grid">
        {modules.map(([title, desc, sprint]) => (
          <div key={title} className="admin-card">
            <h3>{title}</h3>
            <p className="muted">{desc}</p>
            <span className="badge badge-low">{sprint}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
