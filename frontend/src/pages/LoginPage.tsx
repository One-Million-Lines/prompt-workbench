import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useToast } from '../context/ToastContext';
import { ApiClientError } from '../api/client';
import { Spinner } from '../components/Feedback';

const DEMO_USERNAME = 'demo@promptworkbench.dev';
const DEMO_PASSWORD = 'workbench';

interface LocationState {
  from?: { pathname: string };
}

/** Login screen with a demo-credential hint and a one-click fill button. */
export function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from = (location.state as LocationState | null)?.from?.pathname ?? '/registry';

  if (!loading && isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const fillDemo = () => {
    setUsername(DEMO_USERNAME);
    setPassword(DEMO_PASSWORD);
    setError(null);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      toast.success('Signed in');
      navigate(from, { replace: true });
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : 'Login failed';
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login">
      <form className="login__card" onSubmit={onSubmit}>
        <div className="login__brand">
          <span className="login__logo">◇</span>
          <h1>Prompt Workbench</h1>
        </div>
        <p className="login__subtitle">Sign in to your workspace</p>

        <label className="field">
          <span className="field-label">Username</span>
          <input
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="you@example.com"
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Password</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </label>

        {error ? <div className="error-note" role="alert">{error}</div> : null}

        <button className="btn btn--primary login__submit" type="submit" disabled={submitting}>
          {submitting ? <Spinner label="Signing in…" /> : 'Sign in'}
        </button>

        <div className="login__demo">
          <div className="login__demo-hint">
            <strong>Demo:</strong> {DEMO_USERNAME} / {DEMO_PASSWORD}
          </div>
          <button type="button" className="btn btn--ghost" onClick={fillDemo}>
            Fill demo login
          </button>
        </div>
      </form>
    </div>
  );
}
