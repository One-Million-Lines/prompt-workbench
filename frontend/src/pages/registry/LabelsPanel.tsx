import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { Loading, ErrorNote } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import type { Revision } from '../../api/types';

interface LabelsPanelProps {
  promptId: string;
  revisions: Revision[];
}

const LABELS = ['development', 'staging', 'production'] as const;

/** Labels panel: assign development/staging/production labels to a version. */
export function LabelsPanel({ promptId, revisions }: LabelsPanelProps) {
  const qc = useQueryClient();
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);

  const labelsQuery = useQuery({
    queryKey: ['labels', promptId],
    queryFn: () => api.listLabels(promptId),
  });

  const setLabel = async (label: string, version: number) => {
    const previous = (labelsQuery.data ?? []).find((l) => l.label === label);
    setBusy(label);
    try {
      await api.setLabel(promptId, label, version, previous?.revision_id);
      toast.success(`Set ${label} → v${version}`);
      qc.invalidateQueries({ queryKey: ['labels', promptId] });
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Failed to set label');
    } finally {
      setBusy(null);
    }
  };

  if (labelsQuery.isLoading) return <Loading />;
  if (labelsQuery.error)
    return <ErrorNote message={(labelsQuery.error as ApiClientError).message} />;
  if (revisions.length === 0) {
    return <p className="muted small">Save a version before assigning labels.</p>;
  }

  const current = labelsQuery.data ?? [];

  return (
    <div className="labels-panel">
      {LABELS.map((label) => {
        const active = current.find((l) => l.label === label);
        return (
          <div className="label-row" key={label}>
            <div className="label-row__name">
              <Badge tone={label === 'production' ? 'pass' : label === 'staging' ? 'warn' : 'info'}>
                {label}
              </Badge>
              <span className="muted small">
                {active ? `→ v${active.version}` : 'unset'}
              </span>
            </div>
            <label className="field field--inline">
              <select
                value={active?.version ?? revisions[0]!.version}
                onChange={(e) => setLabel(label, Number(e.target.value))}
                disabled={busy === label}
              >
                {revisions.map((r) => (
                  <option key={r.id} value={r.version}>
                    v{r.version}
                  </option>
                ))}
              </select>
            </label>
          </div>
        );
      })}
    </div>
  );
}
