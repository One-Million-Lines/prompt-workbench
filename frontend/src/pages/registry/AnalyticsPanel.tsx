import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { Loading, ErrorNote, EmptyState } from '../../components/Feedback';

/** Analytics panel: per revision/model call stats. */
export function AnalyticsPanel({ promptId }: { promptId: string }) {
  const query = useQuery({
    queryKey: ['analytics', promptId],
    queryFn: () => api.analytics(promptId),
  });

  if (query.isLoading) return <Loading />;
  if (query.error) return <ErrorNote message={(query.error as ApiClientError).message} />;

  const groups = query.data?.groups ?? [];
  if (groups.length === 0) {
    return <EmptyState title="No analytics yet" hint="Run evaluations to populate metrics." />;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Revision</th>
          <th>Model</th>
          <th>Calls</th>
          <th>Pass rate</th>
          <th>Known cost</th>
          <th>p50 (ms)</th>
        </tr>
      </thead>
      <tbody>
        {groups.map((g, i) => (
          <tr key={`${g.revision}-${g.model}-${i}`}>
            <td>v{g.revision}</td>
            <td className="mono">{g.model}</td>
            <td>{g.calls}</td>
            <td>{formatPct(g.pass_rate)}</td>
            <td>{formatCost(g.known_cost)}</td>
            <td>{g.p50_latency_ms ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function formatPct(v: number | undefined): string {
  if (v == null) return '—';
  return `${Math.round(v * 100)}%`;
}

function formatCost(v: number | undefined): string {
  if (v == null) return '—';
  return `$${v.toFixed(4)}`;
}
