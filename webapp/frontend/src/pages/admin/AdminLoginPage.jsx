import { Lock, Shield } from 'lucide-react';
import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../../hooks/useAdminAuth.jsx';

export function AdminLoginPage() {
  const { admin, login } = useAdminAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (admin) {
    return <Navigate to={location.state?.from || '/admin'} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(location.state?.from || '/admin', { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-rr-plum px-4 py-12 text-rr-light">
      <div className="rr-card w-full max-w-md p-7 shadow-rr">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-rr-pink/15 text-rr-pink">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-extrabold tracking-tight text-rr-light">Admin Console Login</h1>
          <p className="mt-1 text-xs text-rr-lavender">
            RR PERFORMANCE LAB · Protected Operational Console (No Public Registration)
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-rr-coral/40 bg-rr-coral/10 px-3.5 py-2.5 text-xs text-rr-coral" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-xs font-semibold text-rr-lavender">
            Administrator Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@domain.com"
              className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-3.5 py-2 text-sm text-rr-light focus:border-rr-pink focus:outline-none"
            />
          </label>

          <label className="block text-xs font-semibold text-rr-lavender">
            Password
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="mt-1 w-full rounded-lg border border-rr-lavender/25 bg-rr-plum px-3.5 py-2 text-sm text-rr-light focus:border-rr-pink focus:outline-none"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-rr-pink px-4 py-2.5 text-sm font-bold text-white transition hover:bg-rr-pink/90 disabled:opacity-60"
          >
            <Lock className="h-4 w-4" />
            {submitting ? 'Authenticating...' : 'Sign In Securely'}
          </button>
        </form>

        <div className="mt-6 border-t border-rr-lavender/15 pt-4 text-center text-xs text-rr-lavender">
          <Link to="/overview" className="hover:text-rr-pink">
            ← Return to Public Analytics Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

