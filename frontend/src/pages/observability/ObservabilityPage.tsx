import { Link, Outlet, useLocation } from 'react-router-dom';

/** Observability shell with All Calls / Capture Inbox subtabs. */
export function ObservabilityPage() {
  const { pathname } = useLocation();
  const capturesActive = pathname.startsWith('/observability/captures');
  return (
    <div className="page">
      <div className="subtabs">
        <Link
          className={`subtab${!capturesActive ? ' subtab--active' : ''}`}
          to="/observability/calls"
        >
          All Calls
        </Link>
        <Link
          className={`subtab${capturesActive ? ' subtab--active' : ''}`}
          to="/observability/captures"
        >
          Capture Inbox
        </Link>
      </div>
      <Outlet />
    </div>
  );
}
