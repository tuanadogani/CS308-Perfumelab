import { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import '../../styles/admin.css';

export default function StockManagement() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editingStock, setEditingStock] = useState(null);
  const [newStock, setNewStock] = useState('');
  const [filter, setFilter] = useState('all'); // all, low, out

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const data = await apiClient('/api/products/');
      setProducts(data);
    } catch (err) {
      setError('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStock = async (productId) => {
    setError('');
    setSuccess('');

    try {
      const stockValue = parseInt(newStock);
      if (isNaN(stockValue) || stockValue < 0) {
        setError('Please enter a valid stock number');
        return;
      }

      await apiClient(`/api/products/${productId}/update-stock/`, {
        method: 'PATCH',
        body: JSON.stringify({ stock: stockValue })
      });

      setSuccess('Stock updated successfully');
      setEditingStock(null);
      setNewStock('');
      fetchProducts();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to update stock');
    }
  };

  const getStockStatus = (stock) => {
    if (stock === 0) return { label: 'Out of Stock', class: 'badge-danger' };
    if (stock <= 5) return { label: 'Low Stock', class: 'badge-warning' };
    if (stock <= 20) return { label: 'Medium', class: 'badge-pending' };
    return { label: 'In Stock', class: 'badge-success' };
  };

  const filteredProducts = products.filter(p => {
    if (filter === 'low') return p.stock > 0 && p.stock <= 10;
    if (filter === 'out') return p.stock === 0;
    return true;
  });

  const stats = {
    total: products.length,
    inStock: products.filter(p => p.stock > 10).length,
    lowStock: products.filter(p => p.stock > 0 && p.stock <= 10).length,
    outOfStock: products.filter(p => p.stock === 0).length
  };

  if (loading) return <div className="container section loading">Loading...</div>;

  return (
    <div className="container section">
      <h1>Stock Management</h1>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <h4>Total Products</h4>
          <p>{stats.total}</p>
        </div>
        <div className="stat-card">
          <h4>In Stock</h4>
          <p style={{ color: '#059669' }}>{stats.inStock}</p>
        </div>
        <div className="stat-card">
          <h4>Low Stock</h4>
          <p style={{ color: '#d97706' }}>{stats.lowStock}</p>
        </div>
        <div className="stat-card">
          <h4>Out of Stock</h4>
          <p style={{ color: '#dc2626' }}>{stats.outOfStock}</p>
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Filter by Status</label>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All Products</option>
            <option value="low">Low Stock (≤10)</option>
            <option value="out">Out of Stock</option>
          </select>
        </div>
      </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>Product Name</th>
              <th>Model</th>
              <th>Category</th>
              <th>Current Stock</th>
              <th>Status</th>
              <th>Price</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredProducts.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                  No products found with the selected filter.
                </td>
              </tr>
            ) : (
              filteredProducts.map((product) => {
                const status = getStockStatus(product.stock);
                return (
                  <tr key={product.id}>
                    <td><strong>{product.name}</strong></td>
                    <td>{product.model}</td>
                    <td>{product.category_name || '-'}</td>
                    <td>
                      {editingStock === product.id ? (
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <input
                            type="number"
                            value={newStock}
                            onChange={(e) => setNewStock(e.target.value)}
                            min="0"
                            style={{ width: '80px', padding: '0.25rem' }}
                            autoFocus
                          />
                          <button
                            className="btn-sm btn-success"
                            onClick={() => handleUpdateStock(product.id)}
                          >
                            Save
                          </button>
                          <button
                            className="btn-sm btn-secondary"
                            onClick={() => {
                              setEditingStock(null);
                              setNewStock('');
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <span className={
                          product.stock > 20 ? 'stock-high' :
                          product.stock > 5 ? 'stock-medium' : 'stock-low'
                        }>
                          {product.stock}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${status.class}`}>{status.label}</span>
                    </td>
                    <td>${product.price}</td>
                    <td>
                      {editingStock !== product.id && (
                        <button
                          className="btn-sm btn-edit"
                          onClick={() => {
                            setEditingStock(product.id);
                            setNewStock(product.stock.toString());
                          }}
                        >
                          Update Stock
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
