import { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import '../../styles/admin.css';

export default function ProductsManagement() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    model: '',
    serial_number: '',
    description: '',
    stock: 0,
    price: '',
    warranty_status: '',
    distributor: '',
    category: '',
    brand: '',
    scent_family: '',
    top_notes: '',
    heart_notes: '',
    base_notes: '',
    size_ml: '',
    image_url: '',
    cost_price: '',
    discount_rate: 0
  });

  useEffect(() => {
    fetchProducts();
    fetchCategories();
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

  const fetchCategories = async () => {
    try {
      const data = await apiClient('/api/categories/');
      setCategories(data);
    } catch (err) {
      console.error('Failed to load categories', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const payload = { ...formData };
      // Convert empty strings to null for numeric fields
      if (!payload.size_ml) payload.size_ml = null;
      if (!payload.cost_price) payload.cost_price = null;
      if (!payload.category) payload.category = null;

      if (editingProduct) {
        await apiClient(`/api/products/${editingProduct.id}/`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiClient('/api/products/', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }

      setShowForm(false);
      setEditingProduct(null);
      resetForm();
      fetchProducts();
    } catch (err) {
      setError(err.message || 'Failed to save product');
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      model: product.model,
      serial_number: product.serial_number,
      description: product.description,
      stock: product.stock,
      price: product.price,
      warranty_status: product.warranty_status,
      distributor: product.distributor,
      category: product.category || '',
      brand: product.brand || '',
      scent_family: product.scent_family || '',
      top_notes: product.top_notes || '',
      heart_notes: product.heart_notes || '',
      base_notes: product.base_notes || '',
      size_ml: product.size_ml || '',
      image_url: product.image_url || '',
      cost_price: product.cost_price || '',
      discount_rate: product.discount_rate || 0
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this product?')) return;

    try {
      await apiClient(`/api/products/${id}/`, { method: 'DELETE' });
      fetchProducts();
    } catch (err) {
      setError('Failed to delete product');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      model: '',
      serial_number: '',
      description: '',
      stock: 0,
      price: '',
      warranty_status: '',
      distributor: '',
      category: '',
      brand: '',
      scent_family: '',
      top_notes: '',
      heart_notes: '',
      base_notes: '',
      size_ml: '',
      image_url: '',
      cost_price: '',
      discount_rate: 0
    });
  };

  if (loading) return <div className="container section loading">Loading...</div>;

  return (
    <div className="container section">
      <div className="admin-header">
        <h1>Product Management</h1>
        <button
          className="btn btn-primary"
          onClick={() => {
            setShowForm(true);
            setEditingProduct(null);
            resetForm();
          }}
        >
          + Add Product
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{editingProduct ? 'Edit Product' : 'Add New Product'}</h2>
            <form onSubmit={handleSubmit} className="product-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Model *</label>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Serial Number *</label>
                  <input
                    type="text"
                    value={formData.serial_number}
                    onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  >
                    <option value="">Select category</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Brand</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Stock *</label>
                  <input
                    type="number"
                    value={formData.stock}
                    onChange={(e) => setFormData({ ...formData, stock: parseInt(e.target.value) || 0 })}
                    min="0"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Price *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Cost Price</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.cost_price}
                    onChange={(e) => setFormData({ ...formData, cost_price: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Discount Rate (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.discount_rate}
                    onChange={(e) => setFormData({ ...formData, discount_rate: parseFloat(e.target.value) || 0 })}
                    min="0"
                    max="100"
                  />
                </div>

                <div className="form-group">
                  <label>Warranty Status *</label>
                  <input
                    type="text"
                    value={formData.warranty_status}
                    onChange={(e) => setFormData({ ...formData, warranty_status: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Distributor *</label>
                  <input
                    type="text"
                    value={formData.distributor}
                    onChange={(e) => setFormData({ ...formData, distributor: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Size (ml)</label>
                  <input
                    type="number"
                    value={formData.size_ml}
                    onChange={(e) => setFormData({ ...formData, size_ml: e.target.value })}
                  />
                </div>

                <div className="form-group full-width">
                  <label>Description *</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows="3"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Scent Family</label>
                  <input
                    type="text"
                    value={formData.scent_family}
                    onChange={(e) => setFormData({ ...formData, scent_family: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Top Notes</label>
                  <input
                    type="text"
                    value={formData.top_notes}
                    onChange={(e) => setFormData({ ...formData, top_notes: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Heart Notes</label>
                  <input
                    type="text"
                    value={formData.heart_notes}
                    onChange={(e) => setFormData({ ...formData, heart_notes: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Base Notes</label>
                  <input
                    type="text"
                    value={formData.base_notes}
                    onChange={(e) => setFormData({ ...formData, base_notes: e.target.value })}
                  />
                </div>

                <div className="form-group full-width">
                  <label>Image URL</label>
                  <input
                    type="url"
                    value={formData.image_url}
                    onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingProduct ? 'Update' : 'Create'} Product
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="products-table">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Model</th>
              <th>Serial #</th>
              <th>Category</th>
              <th>Stock</th>
              <th>Price</th>
              <th>Discount</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                  No products found. Add your first product!
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr key={product.id}>
                  <td>{product.name}</td>
                  <td>{product.model}</td>
                  <td>{product.serial_number}</td>
                  <td>{product.category_name || '-'}</td>
                  <td>
                    <span className={
                      product.stock > 20 ? 'stock-high' :
                      product.stock > 5 ? 'stock-medium' : 'stock-low'
                    }>
                      {product.stock}
                    </span>
                  </td>
                  <td>${product.price}</td>
                  <td>{product.discount_rate}%</td>
                  <td>
                    <button className="btn-sm btn-edit" onClick={() => handleEdit(product)}>
                      Edit
                    </button>
                    <button className="btn-sm btn-delete" onClick={() => handleDelete(product.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
