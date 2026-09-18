import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import { Modal, useDisclosure } from '../../components/Modal';
import { JsonEditor } from '../../components/JsonEditor';
import { compactJson } from '../../lib/json';
import type { DatasetCase, JsonObject, JsonValue } from '../../api/types';

/** Dataset detail: a table of cases with add / edit / delete. */
export function DatasetDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const toast = useToast();
  const editor = useDisclosure();
  const [editing, setEditing] = useState<DatasetCase | null>(null);

  const datasetQuery = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => api.getDataset(id!),
    enabled: !!id,
  });
  const casesQuery = useQuery({
    queryKey: ['cases', id],
    queryFn: () => api.listCases(id!),
    enabled: !!id,
  });

  const openNew = () => {
    setEditing(null);
    editor.open();
  };
  const openEdit = (c: DatasetCase) => {
    setEditing(c);
    editor.open();
  };

  const remove = async (caseId: string) => {
    if (!id) return;
    try {
      await api.deleteCase(id, caseId);
      qc.invalidateQueries({ queryKey: ['cases', id] });
      toast.success('Case deleted');
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Delete failed');
    }
  };

  if (!id) return <EmptyState title="No dataset" />;

  return (
    <div className="panel-scroll">
      <div className="toolbar">
        <div>
          <Link className="link small" to="/evaluations/datasets">
            ← Datasets
          </Link>
          <h2 className="toolbar__title">{datasetQuery.data?.name ?? 'Dataset'}</h2>
        </div>
        <button className="btn btn--primary btn--sm" onClick={openNew}>
          + Add case
        </button>
      </div>

      {casesQuery.isLoading ? (
        <Loading />
      ) : casesQuery.error ? (
        <ErrorNote message={(casesQuery.error as ApiClientError).message} />
      ) : (casesQuery.data ?? []).length === 0 ? (
        <EmptyState title="No cases" hint="Add a case with inputs and expected output." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Inputs</th>
              <th>Expected</th>
              <th>Critical</th>
              <th>Tags</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(casesQuery.data ?? []).map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td className="mono small">{compactJson(c.inputs, 60)}</td>
                <td className="mono small">{compactJson(c.expected, 60)}</td>
                <td>{c.critical ? <Badge tone="warn">critical</Badge> : '—'}</td>
                <td>
                  {(c.tags ?? []).map((t) => (
                    <Badge key={t} tone="muted">
                      {t}
                    </Badge>
                  ))}
                </td>
                <td className="row-actions">
                  <button className="btn btn--ghost btn--sm" onClick={() => openEdit(c)}>
                    Edit
                  </button>
                  <button
                    className="btn btn--ghost btn--sm btn--danger"
                    onClick={() => remove(c.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal
        open={editor.isOpen}
        title={editing ? `Edit case: ${editing.name}` : 'New case'}
        onClose={editor.close}
      >
        <CaseForm
          datasetId={id}
          existing={editing}
          onSaved={() => {
            editor.close();
            qc.invalidateQueries({ queryKey: ['cases', id] });
          }}
        />
      </Modal>
    </div>
  );
}

interface CaseFormProps {
  datasetId: string;
  existing: DatasetCase | null;
  onSaved: () => void;
}

/** Create/edit form for a single dataset case using JSON editors. */
function CaseForm({ datasetId, existing, onSaved }: CaseFormProps) {
  const toast = useToast();
  const [name, setName] = useState(existing?.name ?? '');
  const [inputs, setInputs] = useState<JsonObject>(existing?.inputs ?? {});
  const [inputsValid, setInputsValid] = useState(true);
  const [expected, setExpected] = useState<JsonValue>(existing?.expected ?? null);
  const [expectedValid, setExpectedValid] = useState(true);
  const [critical, setCritical] = useState(existing?.critical ?? false);
  const [tags, setTags] = useState((existing?.tags ?? []).join(', '));
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!inputsValid || !expectedValid) {
      toast.error('Fix invalid JSON before saving.');
      return;
    }
    setBusy(true);
    const tagList = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      if (existing) {
        await api.updateCase(datasetId, existing.id, {
          name,
          inputs,
          expected,
          critical,
          tags: tagList,
        });
        toast.success('Case updated');
      } else {
        await api.createCase(datasetId, {
          name,
          inputs,
          expected,
          critical,
          tags: tagList,
        });
        toast.success('Case added');
      }
      onSaved();
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="form">
      <label className="field">
        <span className="field-label">Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      </label>
      <JsonEditor
        label="Inputs (JSON object)"
        value={inputs}
        rows={6}
        onChange={(v, valid) => {
          setInputsValid(valid);
          if (valid && v && typeof v === 'object' && !Array.isArray(v)) {
            setInputs(v as JsonObject);
          }
        }}
      />
      <JsonEditor
        label="Expected (JSON, optional)"
        value={expected ?? null}
        rows={5}
        onChange={(v, valid) => {
          setExpectedValid(valid);
          if (valid) setExpected(v);
        }}
      />
      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={critical}
          onChange={(e) => setCritical(e.target.checked)}
        />
        <span>Critical case</span>
      </label>
      <label className="field">
        <span className="field-label">Tags (comma-separated)</span>
        <input value={tags} onChange={(e) => setTags(e.target.value)} />
      </label>
      <div className="form__actions">
        <button className="btn btn--primary" onClick={submit} disabled={busy || !name}>
          {busy ? 'Saving…' : existing ? 'Save changes' : 'Add case'}
        </button>
      </div>
    </div>
  );
}
