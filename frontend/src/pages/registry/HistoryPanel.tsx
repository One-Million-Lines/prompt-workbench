import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { Loading, ErrorNote, EmptyState } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import type { Revision } from '../../api/types';

interface HistoryPanelProps {
  promptId: string;
  revisions: Revision[];
  onRestore: (version: number) => void;
}

/**
 * History panel: revision list (newest first) with a two-version diff viewer.
 */
export function HistoryPanel({ promptId, revisions, onRestore }: HistoryPanelProps) {
  const [fromVersion, setFromVersion] = useState<number | null>(
    revisions.length > 1 ? revisions[1]!.version : null,
  );
  const [toVersion, setToVersion] = useState<number | null>(
    revisions.length > 0 ? revisions[0]!.version : null,
  );

  useEffect(() => {
    if (revisions.length === 0) {
      setFromVersion(null);
      setToVersion(null);
      return;
    }
    const versions = new Set(revisions.map((r) => r.version));
    setToVersion((prev) =>
      prev != null && versions.has(prev) ? prev : revisions[0]!.version,
    );
    setFromVersion((prev) =>
      prev != null && versions.has(prev)
        ? prev
        : (revisions[1]?.version ?? revisions[0]!.version),
    );
  }, [revisions]);

  const diffQuery = useQuery({
    queryKey: ['diff', promptId, fromVersion, toVersion],
    queryFn: () => api.diff(promptId, fromVersion!, toVersion!),
    enabled: fromVersion != null && toVersion != null && fromVersion !== toVersion,
  });

  if (revisions.length === 0) {
    return <EmptyState title="No revisions yet" hint="Save a version to start history." />;
  }

  return (
    <div className="history-panel">
      <div className="diff-controls">
        <label className="field field--inline">
          <span className="field-label">From</span>
          <select
            value={fromVersion ?? ''}
            onChange={(e) => setFromVersion(Number(e.target.value))}
          >
            {revisions.map((r) => (
              <option key={r.id} value={r.version}>
                v{r.version}
              </option>
            ))}
          </select>
        </label>
        <label className="field field--inline">
          <span className="field-label">To</span>
          <select
            value={toVersion ?? ''}
            onChange={(e) => setToVersion(Number(e.target.value))}
          >
            {revisions.map((r) => (
              <option key={r.id} value={r.version}>
                v{r.version}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="diff-view">
        {fromVersion === toVersion ? (
          <p className="muted small">Pick two different versions to compare.</p>
        ) : diffQuery.isLoading ? (
          <Loading />
        ) : diffQuery.error ? (
          <ErrorNote message={(diffQuery.error as ApiClientError).message} />
        ) : diffQuery.data ? (
          <>
            <div className="diff-meta">
              {diffQuery.data.semantic_changed ? (
                <Badge tone="warn">semantic change</Badge>
              ) : (
                <Badge tone="muted">no semantic change</Badge>
              )}
            </div>
            <pre className="diff-text">{renderDiff(diffQuery.data.text_diff)}</pre>
          </>
        ) : null}
      </div>

      <ul className="revision-list">
        {revisions.map((r) => (
          <li key={r.id} className="revision-list__item">
            <div className="revision-list__main">
              <span className="revision-list__version">v{r.version}</span>
              <span className="revision-list__note">{r.note || <em>no note</em>}</span>
            </div>
            <div className="revision-list__meta">
              <span className="mono small">{r.semantic_sha256?.slice(0, 10)}</span>
              <span className="muted small">
                {new Date(r.created_at).toLocaleString()}
              </span>
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => onRestore(r.version)}
              >
                Restore to draft
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Diff text is already a unified-diff string; we render it verbatim (as text). */
function renderDiff(text: string): string {
  return text || '(no differences)';
}
