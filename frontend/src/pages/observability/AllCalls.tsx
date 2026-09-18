import { useQueries, useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import { compactJson } from '../../lib/json';
import type { ModelSnapshot, RunCell } from '../../api/types';

/**
 * "All Calls" view: flattens every run's cells into a single call log showing
 * model/tokens/cost/status where available.
 */
export function AllCalls() {
  const { currentProjectId } = useProjects();

  const runsQuery = useQuery({
    queryKey: ['runs', currentProjectId],
    queryFn: () => api.listRuns(currentProjectId!),
    enabled: !!currentProjectId,
  });

  const runs = runsQuery.data ?? [];

  // Fetch cells for each run in parallel.
  const cellQueries = useQueries({
    queries: runs.map((r) => ({
      queryKey: ['run-cells', r.id],
      queryFn: () => api.getRunCells(r.id),
      enabled: !!r.id,
    })),
  });

  if (!currentProjectId) return <EmptyState title="No project selected" />;
  if (runsQuery.isLoading) return <Loading />;
  if (runsQuery.error)
    return <ErrorNote message={(runsQuery.error as ApiClientError).message} />;

  const rows: Array<{ runId: string; cell: RunCell; model: string }> = [];
  cellQueries.forEach((q, i) => {
    const run = runs[i];
    if (!run) return;
    for (const cell of q.data ?? []) {
      const candidate = run.candidates.find((c) => c.id === cell.candidate_id);
      rows.push({
        runId: run.id,
        cell,
        model: formatModel(candidate?.model_snapshot),
      });
    }
  });

  const loadingCells = cellQueries.some((q) => q.isLoading);

  if (rows.length === 0 && !loadingCells) {
    return <EmptyState title="No calls yet" hint="Run an evaluation to populate the call log." />;
  }

  return (
    <div className="panel-scroll">
      <div className="toolbar">
        <h2 className="toolbar__title">All Calls</h2>
        {loadingCells && <span className="muted small">Loading cells…</span>}
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Run</th>
            <th>Model</th>
            <th>Case</th>
            <th>Status</th>
            <th>Tokens (in/out)</th>
            <th>Cost</th>
            <th>Duration</th>
            <th>Output</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ runId, cell, model }) => (
            <tr key={cell.id}>
              <td className="mono small">{runId.slice(0, 8)}</td>
              <td className="mono small">{model}</td>
              <td>{cell.case_name}</td>
              <td>
                <Badge tone={cell.quality_status === 'pass' ? 'pass' : cell.quality_status === 'error' ? 'error' : cell.quality_status === 'fail' ? 'fail' : 'neutral'}>
                  {cell.quality_status}
                </Badge>{' '}
                <span className="muted small">{cell.status}</span>
              </td>
              <td className="mono small">
                {cell.usage
                  ? `${cell.usage.input_tokens ?? '—'} / ${cell.usage.output_tokens ?? '—'}`
                  : '—'}
              </td>
              <td className="mono small">
                {cell.cost ? formatCost(cell.cost.amount) : '—'}
              </td>
              <td className="mono small">
                {cell.timing?.duration_ms != null ? `${cell.timing.duration_ms} ms` : '—'}
              </td>
              <td className="mono small">
                {compactJson(cell.output?.text ?? cell.output?.json, 50)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatModel(snapshot: ModelSnapshot | undefined): string {
  if (!snapshot) return '—';
  const model = snapshot.model ?? snapshot.name;
  if (!model) return '—';
  return snapshot.provider ? `${snapshot.provider}/${model}` : model;
}

function formatCost(v: number | string): string {
  const n = typeof v === 'string' ? Number(v) : v;
  return Number.isFinite(n) ? `$${n.toFixed(4)}` : `$${String(v)}`;
}
