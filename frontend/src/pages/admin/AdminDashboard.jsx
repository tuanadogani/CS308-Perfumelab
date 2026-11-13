import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ROLES, ROLE_LABELS } from '../../constants/roles';
import '../../styles/admin.css';

// Role foundation (Requirement 10): each staff role only sees its own modules.
const MODULES = {
  [ROLES.PRODUCT_MANAGER]: [
    { title: 'Products', desc: 'Add / remove products, manage categories', path: '/admin/products' },
    { title: 'Stock Management', desc: 'Update stock quantities', path: '/admin/stock' },
    { title: 'Delivery List', desc: 'View deliveries and update order status', path: '/admin/deliveries' },
    { title: 'Comment Approval', desc: 'Approve / reject customer comments', path: '/admin/comments' },
  ],
  [ROLES.SALES_MANAGER]: [
    { title: 'Pricing & Discounts', desc: 'Set prices, apply discounts', path: '#', badge: 'Sprint 4' },
    { title: 'Invoices', desc: 'View invoices in a date range / export PDF', path: '#', badge: 'Sprint 4' },
    { title: 'Revenue Report', desc: 'Profit / loss chart', path: '#', badge: 'Sprint 4' },
    { title: 'Refund Requests', desc: 'Evaluate refund requests', path: '#', badge: 'Sprint 5' },
  ],
  [ROLES.SUPPORT_AGENT]: [
    { title: 'Live Chat Queue', desc: 'View and claim active conversations', path: '#', badge: 'Sprint 4' },
  ],
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const modules = MODULES[user.role] ?? [];

  return (
    <div className="container section">
      <p className="eyebrow">Admin Panel · {ROLE_LABELS[user.role]}</p>
      <h1>Hello, {user.name.split(' ')[0]}</h1>
      <div className="admin-grid">
        {modules.map((module) => (
          <div
            key={module.title}
            className="admin-card"
            onClick={() => module.path !== '#' && navigate(module.path)}
            style={{ cursor: module.path !== '#' ? 'pointer' : 'default' }}
          >
            <h3>{module.title}</h3>
            <p className="muted">{module.desc}</p>
            {module.badge && <span className="badge badge-low">{module.badge}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
