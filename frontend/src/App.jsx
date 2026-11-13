import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './routes/ProtectedRoute';
import { STAFF_ROLES, ROLES } from './constants/roles';

import HomePage from './pages/HomePage';
import StartPage from './pages/StartPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ShopPage from './pages/ShopPage';
import ProductDetailPage from './pages/ProductDetailPage';
import CartPage from './pages/CartPage';
import WishlistPage from './pages/WishlistPage';
import ProfilePage from './pages/ProfilePage';
import AdminDashboard from './pages/admin/AdminDashboard';
import ProductsManagement from './pages/admin/ProductsManagement';
import CategoriesManagement from './pages/admin/CategoriesManagement';
import StockManagement from './pages/admin/StockManagement';
import DeliveryList from './pages/admin/DeliveryList';
import CommentApproval from './pages/admin/CommentApproval';
import { NotFoundPage, UnauthorizedPage } from './pages/StatusPages';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Public (Requirement 4: guests can browse and add to cart) */}
        <Route path="/" element={<HomePage />} />
        <Route path="/start" element={<StartPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/shop" element={<ShopPage />} />
        <Route path="/shop/:id" element={<ProductDetailPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/wishlist" element={<WishlistPage />} />

        {/* Login required */}
        <Route element={<ProtectedRoute />}>
          <Route path="/profile" element={<ProfilePage />} />
        </Route>

        {/* Staff roles only */}
        <Route element={<ProtectedRoute roles={STAFF_ROLES} />}>
          <Route path="/admin" element={<AdminDashboard />} />
        </Route>

        {/* Product Manager only */}
        <Route element={<ProtectedRoute roles={[ROLES.PRODUCT_MANAGER]} />}>
          <Route path="/admin/products" element={<ProductsManagement />} />
          <Route path="/admin/categories" element={<CategoriesManagement />} />
          <Route path="/admin/stock" element={<StockManagement />} />
          <Route path="/admin/deliveries" element={<DeliveryList />} />
          <Route path="/admin/comments" element={<CommentApproval />} />
        </Route>

        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
