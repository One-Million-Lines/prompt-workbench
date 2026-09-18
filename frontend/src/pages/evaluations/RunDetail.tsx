import { useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Badge, statusTone } from '../../components/Badge';
import { Drawer } from '../../components/Drawer';
import { JsonView, TextView } from '../../components/JsonView';
import { compactJson } from '../../lib/json';
import type { ModelSnapshot, RunCell } from '../../api/types';

const TERMINAL = new Set(['succeeded', 'failed', 'completed_with_errors', 'cancelled']);

/** Run detail: header stats, comparison matrix (cases × candidates), cell drawer. */
export function RunDetail() {
  const { id } = useParams();
  const toast = useToast();
  const startedAt = useRef(Date.now());
  const [selectedCell, setSelectedCell] = useState<RunCell | null>(null);

  const runQuery = useQuery({
    queryKey: ['run', id],
    queryFn: () => api.getRun(id!),
    enabled: !!id,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (!status || TERMINAL.has(status)) return false;
      // Poll fast for the first 10s, then back off to 3s.
      return Date.now() - startedAt.current < 10_000 ? 1000 : 3000;
    },
  });

  const isActive = !!runQuery.data && !TERMINAL.has(runQuery.data.status);

  const cellsQuery = useQuery({
    queryKey: ['run-cells', id],
    queryFn: () => api.getRunCells(id!),
    enabled: !!id,
    refetchInterval: isActive
      ? Date.now() - startedAt.current < 10_000
        ? 1000
        : 3000
      : false,
  });

  const cancel = async () => {
    if (!id) return;
    try {
      await api.cancelRun(id);
      toast.success('Cancellation requested');
      runQuery.refetch();
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Cancel failed');
    }
  };

  // Group cells into a matrix: rows = case names, cols = candidate ids.
  const matrix = useMemo(() => {
    const cells = cellsQuery.data ?? [];
    const caseNames: string[] = [];
    const byKey = new Map<string, RunCell>();
    for (const cell of cells) {
      if (!caseNames.includes(cell.case_name)) caseNames.push(cell.case_name);
      // For repeats, keep the first cell per (case, candidate) for the matrix view.
      const key = `${cell.case_name}::${cell.candidate_id}`;
      if (!byKey.has(key)) byKey.set(key, cell);
    }
    return { caseNames, byKey };
  }, [cellsQuery.data]);

  const candidateViews = useMemo(() => {
    const run = runQuery.data;
    if (!run) return [];
    const summaries = new Map(
      (run.summary?.candidates ?? []).map((s) => [s.candidate_id, s]),
    );
    return (run.candidates ?? []).map((candidate) => ({
      candidate,
      summary: summaries.get(candidate.id),
    }));
  }, [runQuery.data]);

  if (!id) return <EmptyState title="No run" />;
  if (runQuery.isLoading) return <Loading />;
  if (runQuery.error)
    return <ErrorNote message={(runQuery.error as ApiClientError).message} />;

  const run = runQuery.data!;

  return (
    <div className="panel-scroll run-detail">
      <div className="toolbar">
        <div>
          <Link className="link small" to="/evaluations/runs">
            ← Runs
          </Link>
          <h2 className="toolbar__title">
            Run <span className="mono">{run.id.slice(0, 10)}</span>{' '}
            <Badge tone={statusTone(run.status)}>{run.status}</Badge>
          </h2>
        </div>
        <div className="toolbar__actions">
          <a className="btn btn--ghost btn--sm" href={`/api/v1/runs/${run.id}/report`}>
            Report
          </a>
          {isActive && (
            <button className="btn btn--danger btn--sm" onClick={cancel}>
              Cancel
            </button>
          )}
        </div>
      </div>

      {cellsQuery.isLoading ? (
        <Loading />
      ) : candidateViews.length === 0 ? (
        <EmptyState title="No candidates" />
      ) : (
        <div className="matrix-wrap">
          <table className="matrix">
            <thead>
              <tr>
                <th className="matrix__corner">Case</th>
                {candidateViews.map(({ candidate, summary }) => (
                  <th key={candidate.id} className="matrix__candidate">
                    <div className="matrix__candidate-label">
                      {candidate.label}
                      {summary?.gate_pass != null && (
                        <Badge tone={summary.gate_pass ? 'pass' : 'fail'}>
                          {summary.gate_pass ? 'gate ✓' : 'gate ✗'}
                        </Badge>
                      )}
                    </div>
                    <div className="matrix__candidate-model">
                      {formatModel(candidate.model_snapshot)}
                    </div>
                    <div className="matrix__candidate-stats">
                      <span>pass {formatPct(summary?.pass_rate)}</span>
                      <span>{formatCost(summary?.known_cost)}</span>
                      <span>
                        p50 {formatMs(summary?.p50_latency_ms)}
                        {summary?.p95_latency_ms != null
                          ? ` / p95 ${formatMs(summary.p95_latency_ms)}`
                          : ''}{' '}
                        ms
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.caseNames.map((caseName) => (
                <tr key={caseName}>
                  <td className="matrix__case">{caseName}</td>
                  {candidateViews.map(({ candidate }) => {
                    const cell = matrix.byKey.get(`${caseName}::${candidate.id}`);
                    return (
                      <td key={candidate.id} className="matrix__cell">
                        {cell ? (
                          <button
                            className={`cell cell--${qualityTone(cell.quality_status)}`}
                            onClick={() => setSelectedCell(cell)}
                          >
                            <div className="cell__status">
                              <Badge tone={qualityTone(cell.quality_status)}>
                                {cell.quality_status}
                              </Badge>
                            </div>
                            <div className="cell__output">
                              {compactJson(cell.output?.text ?? cell.output?.json, 60)}
                            </div>
                            <div className="cell__meta">
                              {cell.timing?.duration_ms != null
                                ? `${cell.timing.duration_ms} ms`
                                : ''}
                              {cell.cost ? ` · ${formatCost(cell.cost.amount)}` : ''}
                            </div>
                          </button>
                        ) : (
                          <span className="muted small">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CellDrawer
        runId={run.id}
        cell={selectedCell}
        onClose={() => setSelectedCell(null)}
      />
    </div>
  );
}

/** Detail drawer for a single run cell. */
function CellDrawer({
  runId,
  cell,
  onClose,
}: {
  runId: string;
  cell: RunCell | null;
  onClose: () => void;
}) {
  const toast = useToast();
  const [note, setNote] = useState('');

  const review = async (verdict: string) => {
    if (!cell) return;
    try {
      await api.reviewCell(runId, cell.id, { verdict, note });
      toast.success(`Marked ${verdict}`);
      setNote('');
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Review failed');
    }
  };

  return (
    <Drawer open={!!cell} title="Cell detail" onClose={onClose} width={560}>
      {cell && (
        <div className="cell-detail">
          <div className="cell-detail__head">
            <Badge tone={qualityTone(cell.quality_status)}>{cell.quality_status}</Badge>
            <span className="muted small">
              {cell.case_name} · repeat {cell.repeat_index}
            </span>
          </div>

          {cell.error != null && (
            <section>
              <h4>Error</h4>
              <JsonView value={cell.error} />
            </section>
          )}

          {cell.output?.text != null && (
            <section>
              <h4>Output text</h4>
              <TextView value={cell.output.text} />
            </section>
          )}
          {cell.output?.json !== undefined && cell.output?.json !== null && (
            <section>
              <h4>Parsed JSON</h4>
              <JsonView value={cell.output.json} />
            </section>
          )}
          {cell.output?.tool_calls && cell.output.tool_calls.length > 0 && (
            <section>
              <h4>Tool calls</h4>
              <JsonView value={cell.output.tool_calls} />
            </section>
          )}

          {cell.checks && cell.checks.length > 0 && (
            <section>
              <h4>Checks</h4>
              <ul className="check-results">
                {cell.checks.map((ch) => (
                  <li key={ch.id} className="check-result">
                    <Badge tone={qualityTone(ch.outcome)}>{ch.outcome}</Badge>
                    <span className="mono small">{ch.id}</span>
                    <span className="muted small">{ch.type}</span>
                    {ch.required ? <Badge tone="muted">required</Badge> : null}
                    {ch.evidence != null && (
                      <span className="mono small">{compactJson(ch.evidence, 50)}</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {cell.usage && (
            <section>
              <h4>Usage</h4>
              <JsonView value={cell.usage} />
            </section>
          )}
          {cell.provenance && (
            <section>
              <h4>Provenance</h4>
              <JsonView value={cell.provenance} />
            </section>
          )}

          <section>
            <h4>Review</h4>
            <textarea
              rows={2}
              value={note}
              placeholder="Reviewer note (optional)"
              onChange={(e) => setNote(e.target.value)}
            />
            <div className="form__actions">
              <button className="btn btn--sm" onClick={() => review('pass')}>
                Mark pass
              </button>
              <button className="btn btn--sm btn--danger" onClick={() => review('fail')}>
                Mark fail
              </button>
            </div>
          </section>
        </div>
      )}
    </Drawer>
  );
}

function qualityTone(status: string): 'pass' | 'fail' | 'error' | 'neutral' {
  if (status === 'pass' || status === 'passed') return 'pass';
  if (status === 'fail' || status === 'failed') return 'fail';
  if (status === 'error') return 'error';
  return 'neutral';
}

function formatModel(snapshot: ModelSnapshot | undefined): string {
  if (!snapshot) return '—';
  const model = snapshot.model ?? snapshot.name;
  if (!model) return '—';
  return snapshot.provider ? `${snapshot.provider}/${model}` : model;
}

function formatPct(v: number | null | undefined): string {
  if (v == null) return '—';
  return `${Math.round(v * 100)}%`;
}

function formatMs(v: number | null | undefined): string {
  if (v == null) return '—';
  return String(Math.round(v));
}

function formatCost(v: number | string | null | undefined): string {
  if (v == null || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  return Number.isFinite(n) ? `$${n.toFixed(4)}` : `$${String(v)}`;
}
