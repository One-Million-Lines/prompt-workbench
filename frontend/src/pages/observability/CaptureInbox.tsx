import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import { useToast } from '../../context/ToastContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import { Drawer } from '../../components/Drawer';
import { Modal, useDisclosure } from '../../components/Modal';
import { JsonView } from '../../components/JsonView';
import type { Capture, ReviewStatus } from '../../api/types';

const FILTERS: Array<{ value: ReviewStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'new', label: 'New' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'ignored', label: 'Ignored' },
  { value: 'promoted', label: 'Promoted' },
];

/** Capture Inbox: review captured calls and promote them into datasets. */
export function CaptureInbox() {
  const { currentProjectId } = useProjects();
  const qc = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState<ReviewStatus | 'all'>('new');
  const [selected, setSelected] = useState<Capture | null>(null);

  const query = useQuery({
    queryKey: ['captures', currentProjectId, filter],
    queryFn: () =>
      api.listCaptures(currentProjectId!, filter === 'all' ? undefined : filter),
    enabled: !!currentProjectId,
  });

  const setReview = async (capture: Capture, status: ReviewStatus) => {
    try {
      await api.reviewCapture(capture.id, status);
      toast.success(`Marked ${status}`);
      qc.invalidateQueries({ queryKey: ['captures', currentProjectId] });
      setSelected(null);
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Update failed');
    }
  };

  if (!currentProjectId) return <EmptyState title="No project selected" />;

  return (
    <div className="panel-scroll">
      <div className="toolbar">
        <h2 className="toolbar__title">Capture Inbox</h2>
        <div className="filter-group">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              className={`chip${filter === f.value ? ' chip--active' : ''}`}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNote message={(query.error as ApiClientError).message} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="Inbox empty" hint="No captures match this filter." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Occurred</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(query.data ?? []).map((c) => (
              <tr key={c.id}>
                <td>{c.source}</td>
                <td>{c.mode}</td>
                <td>
                  <Badge tone={reviewTone(c.review_status)}>{c.review_status}</Badge>
                </td>
                <td className="muted">
                  {c.occurred_at ? new Date(c.occurred_at).toLocaleString() : '—'}
                </td>
                <td>
                  <button className="btn btn--ghost btn--sm" onClick={() => setSelected(c)}>
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <CaptureDrawer
        capture={selected}
        projectId={currentProjectId}
        onClose={() => setSelected(null)}
        onReview={setReview}
      />
    </div>
  );
}

function CaptureDrawer({
  capture,
  projectId,
  onClose,
  onReview,
}: {
  capture: Capture | null;
  projectId: string;
  onClose: () => void;
  onReview: (capture: Capture, status: ReviewStatus) => void;
}) {
  const toast = useToast();
  const qc = useQueryClient();
  const promote = useDisclosure();
  const [datasetId, setDatasetId] = useState('');
  const [caseName, setCaseName] = useState('');
  const [busy, setBusy] = useState(false);

  const datasetsQuery = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => api.listDatasets(projectId),
    enabled: promote.isOpen,
  });

  const doPromote = async () => {
    if (!capture || !datasetId) return;
    setBusy(true);
    try {
      await api.promoteCapture(capture.id, datasetId, caseName || undefined);
      toast.success('Promoted to dataset case');
      promote.close();
      qc.invalidateQueries({ queryKey: ['captures', projectId] });
      qc.invalidateQueries({ queryKey: ['cases', datasetId] });
      onClose();
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Promote failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Drawer open={!!capture} title="Capture detail" onClose={onClose} width={560}>
      {capture && (
        <div className="capture-detail">
          <div className="capture-detail__head">
            <Badge tone={reviewTone(capture.review_status)}>
              {capture.review_status}
            </Badge>
            <span className="muted small">
              {capture.source} · {capture.mode}
            </span>
          </div>

          <section>
            <h4>Inputs</h4>
            <JsonView value={capture.inputs} />
          </section>
          <section>
            <h4>Output</h4>
            <JsonView value={capture.output} />
          </section>
          {capture.metadata && (
            <section>
              <h4>Metadata</h4>
              <JsonView value={capture.metadata} />
            </section>
          )}
          {capture.prompt_ref != null && (
            <section>
              <h4>Prompt reference</h4>
              <JsonView value={capture.prompt_ref} />
            </section>
          )}

          <section>
            <h4>Actions</h4>
            <div className="form__actions">
              <button
                className="btn btn--sm"
                onClick={() => onReview(capture, 'reviewed')}
              >
                Mark reviewed
              </button>
              <button
                className="btn btn--sm"
                onClick={() => onReview(capture, 'ignored')}
              >
                Ignore
              </button>
              <button className="btn btn--primary btn--sm" onClick={promote.open}>
                Promote to dataset
              </button>
            </div>
          </section>
        </div>
      )}

      <Modal open={promote.isOpen} title="Promote to dataset case" onClose={promote.close}>
        <div className="form">
          <label className="field">
            <span className="field-label">Dataset</span>
            <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
              <option value="">Select…</option>
              {(datasetsQuery.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field-label">Case name (optional)</span>
            <input value={caseName} onChange={(e) => setCaseName(e.target.value)} />
          </label>
          <div className="form__actions">
            <button
              className="btn btn--primary"
              onClick={doPromote}
              disabled={busy || !datasetId}
            >
              {busy ? 'Promoting…' : 'Promote'}
            </button>
          </div>
        </div>
      </Modal>
    </Drawer>
  );
}

function reviewTone(status: string): 'pass' | 'warn' | 'muted' | 'info' | 'neutral' {
  switch (status) {
    case 'reviewed':
      return 'pass';
    case 'new':
      return 'warn';
    case 'ignored':
      return 'muted';
    case 'promoted':
      return 'info';
    default:
      return 'neutral';
  }
}
