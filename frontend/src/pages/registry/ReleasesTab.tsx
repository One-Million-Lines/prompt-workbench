import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { Badge, statusTone } from '../../components/Badge';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Modal, useDisclosure } from '../../components/Modal';

/** Releases subtab: list releases and create a new one from production labels. */
export function ReleasesTab({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const create = useDisclosure();
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const releasesQuery = useQuery({
    queryKey: ['releases', projectId],
    queryFn: () => api.listReleases(projectId),
  });
  const promptsQuery = useQuery({
    queryKey: ['prompts', projectId, false],
    queryFn: () => api.listPrompts(projectId, false),
  });

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const prompts = (promptsQuery.data ?? []).map((p) => ({
        prompt_id: p.id,
        selector: { label: 'production' },
      }));
      await api.createRelease({
        project_id: projectId,
        name,
        selection: { prompts },
      });
      toast.success('Release created');
      setName('');
      create.close();
      qc.invalidateQueries({ queryKey: ['releases', projectId] });
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Create failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel-scroll">
      <div className="toolbar">
        <h2 className="toolbar__title">Releases</h2>
        <button className="btn btn--primary btn--sm" onClick={create.open}>
          + New release
        </button>
      </div>

      {releasesQuery.isLoading ? (
        <Loading />
      ) : releasesQuery.error ? (
        <ErrorNote message={(releasesQuery.error as ApiClientError).message} />
      ) : (releasesQuery.data ?? []).length === 0 ? (
        <EmptyState title="No releases" hint="Bundle production prompts into a release." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Semantic SHA</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(releasesQuery.data ?? []).map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>
                  <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                </td>
                <td className="mono">{r.semantic_sha256?.slice(0, 12)}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <a className="link" href={api.releaseDownloadUrl(r.id)}>
                    Download
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal open={create.isOpen} title="New release" onClose={create.close}>
        <form className="form" onSubmit={onCreate}>
          <p className="muted">
            Bundles the <strong>production</strong> label of every prompt in this
            project.
          </p>
          <label className="field">
            <span className="field-label">Release name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </label>
          <div className="form__actions">
            <button className="btn btn--primary" type="submit" disabled={busy || !name}>
              {busy ? 'Creating…' : 'Create release'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
