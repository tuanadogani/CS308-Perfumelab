import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { USE_MOCK } from '../api/client';
import { STAFF_ROLES } from '../constants/roles';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.email || !form.password) return setError('Please fill in all fields.');
    setLoading(true);
    try {
      const user = await login(form);
      // Staff → admin panel, customer → the page they came from, or the collection
      const fallback = STAFF_ROLES.includes(user.role) ? '/admin' : '/shop';
      navigate(location.state?.from || fallback, { replace: true });
    } catch (err) {
      setError(err.message); // Generic message: we don't reveal which field was wrong (security)
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="auth-page">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <p className="eyebrow">Welcome back</p>
        <h1>Log In</h1>

        <label>Email
          <input name="email" type="email" autoComplete="email" value={form.email} onChange={onChange} required />
        </label>
        <label>Password
          <input name="password" type="password" autoComplete="current-password" value={form.password} onChange={onChange} required />
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <button className="btn btn-dark btn-block" disabled={loading}>
          {loading ? 'Logging in…' : 'Log In'}
        </button>
        <p className="muted small center">Don’t have an account? <Link to="/register">Sign up</Link></p>

        {USE_MOCK && (
          <div className="demo-box">
            <strong>Demo accounts</strong> (password: <code>Demo1234</code>)
            <ul>
              <li>customer@demo.com — Customer</li>
              <li>sales@demo.com — Sales Manager</li>
              <li>product@demo.com — Product Manager</li>
              <li>support@demo.com — Support Agent</li>
            </ul>
          </div>
        )}
      </form>
    </section>
  );
}
