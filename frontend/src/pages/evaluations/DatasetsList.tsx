import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import { useToast } from '../../context/ToastContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Modal, useDisclosure } from '../../components/Modal';

/** Lists datasets for the current project and lets the user create one. */
export function DatasetsList() {
  const { currentProjectId } = useProjects();
  const qc = useQueryClient();
  const toast = useToast();
  const create = useDisclosure();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);

  const query = useQuery({
    queryKey: ['datasets', currentProjectId],
    queryFn: () => api.listDatasets(currentProjectId!),
    enabled: !!currentProjectId,
  });

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!currentProjectId) return;
    setBusy(true);
    try {
      await api.createDataset({ project_id: currentProjectId, name, description });
      toast.success('Dataset created');
      setName('');
      setDescription('');
      create.close();
      qc.invalidateQueries({ queryKey: ['datasets', currentProjectId] });
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Create failed');
    } finally {
      setBusy(false);
    }
  };

  if (!currentProjectId) return <EmptyState title="No project selected" />;

  return (
    <div className="panel-scroll">
      <div className="toolbar">
        <h2 className="toolbar__title">Datasets</h2>
        <button className="btn btn--primary btn--sm" onClick={create.open}>
          + New dataset
        </button>
      </div>

      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorNote message={(query.error as ApiClientError).message} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="No datasets" hint="Create a dataset to hold evaluation cases." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Cases</th>
            </tr>
          </thead>
          <tbody>
            {(query.data ?? []).map((d) => (
              <tr key={d.id}>
                <td>
                  <Link className="link" to={`/evaluations/datasets/${d.id}`}>
                    {d.name}
                  </Link>
                </td>
                <td className="muted">{d.description || '—'}</td>
                <td>{d.case_count ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal open={create.isOpen} title="New dataset" onClose={create.close}>
        <form className="form" onSubmit={onCreate}>
          <label className="field">
            <span className="field-label">Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </label>
          <label className="field">
            <span className="field-label">Description</span>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <div className="form__actions">
            <button className="btn btn--primary" type="submit" disabled={busy || !name}>
              {busy ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
