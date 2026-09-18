import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Badge, statusTone } from '../../components/Badge';

const ACTIVE_STATUSES = new Set(['queued', 'running']);

/** Lists runs newest-first for the current project; polls while any are active. */
export function RunsList() {
  const { currentProjectId } = useProjects();

  const query = useQuery({
    queryKey: ['runs', currentProjectId],
    queryFn: () => api.listRuns(currentProjectId!),
    enabled: !!currentProjectId,
    refetchInterval: (q) => {
      const runs = q.state.data ?? [];
      return runs.some((r) => ACTIVE_STATUSES.has(r.status)) ? 3000 : false;
    },
  });

  if (!currentProjectId) return <EmptyState title="No project selected" />;

  return (
    <div className="panel-scroll">
      <div className="toolbar">
        <h2 className="toolbar__title">Runs</h2>
        <Link className="btn btn--primary btn--sm" to="/evaluations/runs/new">
          + New comparison
        </Link>
      </div>

      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNote message={(query.error as ApiClientError).message} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="No runs yet" hint="Start a comparison run to evaluate prompts." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Kind</th>
              <th>Status</th>
              <th>Candidates</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {(query.data ?? []).map((r) => (
              <tr key={r.id}>
                <td>
                  <Link className="link mono" to={`/evaluations/runs/${r.id}`}>
                    {r.id.slice(0, 10)}
                  </Link>
                </td>
                <td>{r.kind}</td>
                <td>
                  <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                </td>
                <td>{r.candidates?.length ?? 0}</td>
                <td className="muted">{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
