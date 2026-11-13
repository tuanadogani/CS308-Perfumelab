import { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import '../../styles/admin.css';

export default function CommentApproval() {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [statusFilter, setStatusFilter] = useState('pending');

  useEffect(() => {
    fetchComments();
  }, [statusFilter]);

  const fetchComments = async () => {
    try {
      const url = statusFilter
        ? `/api/comments/?status=${statusFilter}`
        : '/api/comments/';
      const data = await apiClient(url);
      setComments(data);
    } catch (err) {
      setError('Failed to load comments');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (commentId) => {
    setError('');
    setSuccess('');

    try {
      await apiClient(`/api/comments/${commentId}/approve/`, {
        method: 'PATCH'
      });

      setSuccess('Comment approved successfully');
      fetchComments();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to approve comment');
    }
  };

  const handleReject = async (commentId) => {
    if (!confirm('Are you sure you want to reject this comment?')) return;

    setError('');
    setSuccess('');

    try {
      await apiClient(`/api/comments/${commentId}/reject/`, {
        method: 'PATCH'
      });

      setSuccess('Comment rejected successfully');
      fetchComments();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to reject comment');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: 'badge-pending',
      approved: 'badge-approved',
      rejected: 'badge-rejected'
    };
    return badges[status] || 'badge-pending';
  };

  const stats = {
    pending: comments.filter(c => c.status === 'pending').length,
    approved: comments.filter(c => c.status === 'approved').length,
    rejected: comments.filter(c => c.status === 'rejected').length
  };

  if (loading) return <div className="container section loading">Loading...</div>;

  return (
    <div className="container section">
      <h1>Comment Approval</h1>
      <p className="muted" style={{ marginTop: '0.5rem' }}>
        Review and moderate customer product reviews
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <h4>Pending Review</h4>
          <p style={{ color: '#d97706' }}>{stats.pending}</p>
        </div>
        <div className="stat-card">
          <h4>Approved</h4>
          <p style={{ color: '#059669' }}>{stats.approved}</p>
        </div>
        <div className="stat-card">
          <h4>Rejected</h4>
          <p style={{ color: '#dc2626' }}>{stats.rejected}</p>
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Filter by Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Comments</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div className="data-table">
        {comments.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#6b7280', background: 'white', borderRadius: '8px' }}>
            No comments found with the selected filter.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {comments.map((comment) => (
              <div
                key={comment.id}
                style={{
                  background: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '1.5rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1rem' }}>
                      {comment.product_name}
                    </h3>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      By <strong>{comment.customer_name}</strong> ({comment.customer_email})
                    </div>
                    <div style={{ fontSize: '0.8125rem', color: '#9ca3af', marginTop: '0.25rem' }}>
                      {new Date(comment.created_at).toLocaleString()}
                    </div>
                  </div>
                  <span className={`badge ${getStatusBadge(comment.status)}`}>
                    {comment.status.charAt(0).toUpperCase() + comment.status.slice(1)}
                  </span>
                </div>

                <div style={{
                  padding: '1rem',
                  background: '#f9fafb',
                  borderRadius: '6px',
                  marginBottom: '1rem',
                  fontStyle: 'italic',
                  color: '#374151'
                }}>
                  "{comment.comment_text}"
                </div>

                {comment.status === 'pending' && (
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    <button
                      className="btn btn-success"
                      onClick={() => handleApprove(comment.id)}
                    >
                      ✓ Approve
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => handleReject(comment.id)}
                    >
                      ✗ Reject
                    </button>
                  </div>
                )}

                {comment.status !== 'pending' && comment.reviewed_at && (
                  <div style={{ fontSize: '0.8125rem', color: '#6b7280', textAlign: 'right' }}>
                    Reviewed on {new Date(comment.reviewed_at).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
