import { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import '../../styles/admin.css';

export default function DeliveryList() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedOrder, setExpandedOrder] = useState(null);

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const fetchOrders = async () => {
    try {
      const url = statusFilter
        ? `/api/deliveries/?status=${statusFilter}`
        : '/api/deliveries/';
      const data = await apiClient(url);
      setOrders(data);
    } catch (err) {
      setError('Failed to load delivery list');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (orderId, newStatus) => {
    setError('');
    setSuccess('');

    try {
      await apiClient(`/api/orders/${orderId}/update-status/`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });

      setSuccess(`Order #${orderId} status updated to ${newStatus}`);
      fetchOrders();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to update order status');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      processing: 'badge-processing',
      in_transit: 'badge-in-transit',
      delivered: 'badge-delivered',
      cancelled: 'badge-danger'
    };
    return badges[status] || 'badge-pending';
  };

  const getStatusLabel = (status) => {
    const labels = {
      processing: 'Processing',
      in_transit: 'In Transit',
      delivered: 'Delivered',
      cancelled: 'Cancelled'
    };
    return labels[status] || status;
  };

  const stats = {
    processing: orders.filter(o => o.status === 'processing').length,
    inTransit: orders.filter(o => o.status === 'in_transit').length,
    delivered: orders.filter(o => o.status === 'delivered').length
  };

  if (loading) return <div className="container section loading">Loading...</div>;

  return (
    <div className="container section">
      <h1>Delivery Management</h1>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <h4>Processing</h4>
          <p style={{ color: '#3b82f6' }}>{stats.processing}</p>
        </div>
        <div className="stat-card">
          <h4>In Transit</h4>
          <p style={{ color: '#8b5cf6' }}>{stats.inTransit}</p>
        </div>
        <div className="stat-card">
          <h4>Delivered</h4>
          <p style={{ color: '#059669' }}>{stats.delivered}</p>
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Filter by Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Orders</option>
            <option value="processing">Processing</option>
            <option value="in_transit">In Transit</option>
            <option value="delivered">Delivered</option>
          </select>
        </div>
      </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>Order ID</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Total</th>
              <th>Order Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                  No orders found.
                </td>
              </tr>
            ) : (
              orders.map((order) => (
                <>
                  <tr key={order.id} style={{ cursor: 'pointer' }} onClick={() => setExpandedOrder(expandedOrder === order.id ? null : order.id)}>
                    <td><strong>#{order.id}</strong></td>
                    <td>
                      {order.customer_name}<br />
                      <small style={{ color: '#6b7280' }}>{order.customer_email}</small>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadge(order.status)}`}>
                        {getStatusLabel(order.status)}
                      </span>
                    </td>
                    <td>${order.total_price}</td>
                    <td>{new Date(order.created_at).toLocaleDateString()}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      {order.status === 'processing' && (
                        <button
                          className="btn-sm btn-success"
                          onClick={() => handleStatusUpdate(order.id, 'in_transit')}
                        >
                          Ship
                        </button>
                      )}
                      {order.status === 'in_transit' && (
                        <button
                          className="btn-sm btn-success"
                          onClick={() => handleStatusUpdate(order.id, 'delivered')}
                        >
                          Mark Delivered
                        </button>
                      )}
                      {order.status === 'delivered' && (
                        <span style={{ color: '#059669', fontSize: '0.875rem' }}>✓ Complete</span>
                      )}
                    </td>
                  </tr>
                  {expandedOrder === order.id && (
                    <tr>
                      <td colSpan="6" style={{ background: '#f9fafb', padding: '1.5rem' }}>
                        <div style={{ marginBottom: '1rem' }}>
                          <h4 style={{ margin: '0 0 0.5rem 0' }}>Delivery Address</h4>
                          <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{order.delivery_address}</p>
                        </div>
                        <div>
                          <h4 style={{ margin: '0 0 0.5rem 0' }}>Order Items</h4>
                          <table style={{ width: '100%', marginTop: '0.5rem' }}>
                            <thead>
                              <tr style={{ background: 'white' }}>
                                <th style={{ textAlign: 'left', padding: '0.5rem' }}>Product</th>
                                <th style={{ textAlign: 'left', padding: '0.5rem' }}>Model</th>
                                <th style={{ textAlign: 'right', padding: '0.5rem' }}>Quantity</th>
                                <th style={{ textAlign: 'right', padding: '0.5rem' }}>Price</th>
                                <th style={{ textAlign: 'right', padding: '0.5rem' }}>Total</th>
                              </tr>
                            </thead>
                            <tbody>
                              {order.items?.map((item, idx) => (
                                <tr key={idx} style={{ background: 'white' }}>
                                  <td style={{ padding: '0.5rem' }}>{item.product_name}</td>
                                  <td style={{ padding: '0.5rem' }}>{item.product_model}</td>
                                  <td style={{ padding: '0.5rem', textAlign: 'right' }}>{item.quantity}</td>
                                  <td style={{ padding: '0.5rem', textAlign: 'right' }}>${item.price_at_purchase}</td>
                                  <td style={{ padding: '0.5rem', textAlign: 'right' }}>${item.total_price}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
