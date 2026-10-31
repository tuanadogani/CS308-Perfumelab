import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { validateRegister } from '../utils/validation';

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', taxId: '', homeAddress: '', password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    const v = validateRegister(form);
    setErrors(v);
    if (Object.keys(v).length) return;
    setLoading(true); setServerError('');
    try {
      const { confirm, ...payload } = form; // "confirm" is not sent to the backend
      await register(payload);
      navigate('/shop', { replace: true });
    } catch (err) {
      setServerError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const field = (name, label, type = 'text', autoComplete) => (
    <label>{label}
      <input name={name} type={type} autoComplete={autoComplete} value={form[name]} onChange={onChange}
        aria-invalid={!!errors[name]} />
      {errors[name] && <span className="field-error">{errors[name]}</span>}
    </label>
  );

  return (
    <section className="auth-page">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <p className="eyebrow">Join Maison Lumière</p>
        <h1>Sign Up</h1>
        {field('name', 'Full Name', 'text', 'name')}
        {field('email', 'Email', 'email', 'email')}
        {field('taxId', 'Tax ID', 'text', 'off')}
        <label>Home Address
          <textarea name="homeAddress" rows="2" value={form.homeAddress} onChange={onChange} aria-invalid={!!errors.homeAddress} />
          {errors.homeAddress && <span className="field-error">{errors.homeAddress}</span>}
        </label>
        {field('password', 'Password', 'password', 'new-password')}
        {field('confirm', 'Confirm Password', 'password', 'new-password')}

        {serverError && <p className="form-error" role="alert">{serverError}</p>}
        <button className="btn btn-dark btn-block" disabled={loading}>
          {loading ? 'Creating account…' : 'Create Account'}
        </button>
        <p className="muted small center">Already have an account? <Link to="/login">Log in</Link></p>
      </form>
    </section>
  );
}
