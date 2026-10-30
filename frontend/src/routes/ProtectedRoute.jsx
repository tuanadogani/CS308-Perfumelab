import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Role-based access (Requirements 10 & 17).
 * <ProtectedRoute />                          → logged-in users only
 * <ProtectedRoute roles={['sales_manager']} /> → only these role(s)
 *
 * NOTE: this only protects the UI. The backend must check authorization on every request.
 */
export default function ProtectedRoute({ roles }) {
  const { isAuthenticated, hasRole } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (roles && !hasRole(...roles)) {
    return <Navigate to="/unauthorized" replace />;
  }
  return <Outlet />;
}
