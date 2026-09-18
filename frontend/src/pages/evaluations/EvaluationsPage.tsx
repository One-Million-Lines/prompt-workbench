import { Link, Outlet, useLocation } from 'react-router-dom';

/** Evaluations screen shell with Datasets / Runs subtabs. */
export function EvaluationsPage() {
  const { pathname } = useLocation();
  // Highlight "Runs" for any /evaluations/runs* path, "Datasets" otherwise.
  const runsActive = pathname.startsWith('/evaluations/runs');
  return (
    <div className="page">
      <div className="subtabs">
        <Link
          className={`subtab${!runsActive ? ' subtab--active' : ''}`}
          to="/evaluations/datasets"
        >
          Datasets
        </Link>
        <Link
          className={`subtab${runsActive ? ' subtab--active' : ''}`}
          to="/evaluations/runs"
        >
          Runs
        </Link>
      </div>
      <Outlet />
    </div>
  );
}
