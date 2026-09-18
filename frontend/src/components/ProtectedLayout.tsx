import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { ProjectProvider } from '../context/ProjectContext';
import { Header } from './Header';
import { Loading } from './Feedback';

/**
 * Guards all non-login routes. Unauthenticated users are redirected to /login
 * (preserving the attempted location). Authenticated users get the app chrome
 * (header + project provider) around the routed page.
 */
export function ProtectedLayout() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <Loading label="Authenticating…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return (
    <ProjectProvider>
      <div className="app-shell">
        <Header />
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </ProjectProvider>
  );
}
