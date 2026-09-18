import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import { useToast } from '../../context/ToastContext';
import { EmptyState, Loading } from '../../components/Feedback';
import { JsonEditor } from '../../components/JsonEditor';
import { tryParseJson } from '../../lib/json';
import type {
  JsonObject,
  JsonValue,
  RunCheck,
  RunPreview,
  RunRequest,
} from '../../api/types';

type SelectorKind = 'label' | 'revision';

interface CandidateDraft {
  label: string;
  promptId: string;
  selectorKind: SelectorKind;
  selectorValue: string; // label string or revision number
  modelProfileId: string;
}

const CHECK_TYPES = [
  'json_valid',
  'json_schema',
  'array_length',
  'contains',
  'equals',
  'json_pointer_equals',
] as const;
type CheckType = (typeof CHECK_TYPES)[number];

interface CheckDraft {
  id: string;
  type: CheckType;
  required: boolean;
  // Type-specific params (kept as strings in the form).
  schema: string;
  pointer: string;
  min: string;
  max: string;
  value: string;
}

function emptyCheck(id: string): CheckDraft {
  return {
    id,
    type: 'json_valid',
    required: true,
    schema: '{}',
    pointer: '',
    min: '',
    max: '',
    value: '',
  };
}

/** New comparison run builder with a pre-run preview of counts. */
export function NewRun() {
  const { currentProjectId } = useProjects();
  const navigate = useNavigate();
  const toast = useToast();

  const datasetsQuery = useQuery({
    queryKey: ['datasets', currentProjectId],
    queryFn: () => api.listDatasets(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const promptsQuery = useQuery({
    queryKey: ['prompts', currentProjectId, false],
    queryFn: () => api.listPrompts(currentProjectId!, false),
    enabled: !!currentProjectId,
  });
  const profilesQuery = useQuery({
    queryKey: ['model-profiles', currentProjectId],
    queryFn: () => api.listModelProfiles(currentProjectId!),
    enabled: !!currentProjectId,
  });

  const [datasetId, setDatasetId] = useState('');
  const [candidates, setCandidates] = useState<CandidateDraft[]>([
    {
      label: 'A',
      promptId: '',
      selectorKind: 'label',
      selectorValue: 'production',
      modelProfileId: '',
    },
  ]);
  const [checks, setChecks] = useState<CheckDraft[]>([]);
  const [repeats, setRepeats] = useState(1);
  const [gateEnabled, setGateEnabled] = useState(false);
  const [minPassRate, setMinPassRate] = useState(0.95);
  const [baselineLabel, setBaselineLabel] = useState('');

  const [preview, setPreview] = useState<RunPreview | null>(null);
  const [busy, setBusy] = useState(false);

  const addCandidate = () => {
    if (candidates.length >= 8) return;
    const label = String.fromCharCode(65 + candidates.length); // A, B, C...
    setCandidates((prev) => [
      ...prev,
      {
        label,
        promptId: prev[0]?.promptId ?? '',
        selectorKind: 'label',
        selectorValue: 'production',
        modelProfileId: prev[0]?.modelProfileId ?? '',
      },
    ]);
  };
  const removeCandidate = (i: number) =>
    setCandidates((prev) => prev.filter((_, idx) => idx !== i));
  const updateCandidate = (i: number, patch: Partial<CandidateDraft>) =>
    setCandidates((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));

  const addCheck = () =>
    setChecks((prev) => [...prev, emptyCheck(`check_${prev.length + 1}`)]);
  const removeCheck = (i: number) =>
    setChecks((prev) => prev.filter((_, idx) => idx !== i));
  const updateCheck = (i: number, patch: Partial<CheckDraft>) =>
    setChecks((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));

  // Build the wire RunRequest from the form drafts.
  const buildRequest = (): RunRequest | null => {
    if (!currentProjectId || !datasetId) {
      toast.error('Pick a dataset first.');
      return null;
    }
    if (candidates.some((c) => !c.promptId || !c.modelProfileId)) {
      toast.error('Every candidate needs a prompt and a model profile.');
      return null;
    }
    const wireCandidates = candidates.map((c) => ({
      label: c.label,
      target: {
        kind: 'prompt' as const,
        id: c.promptId,
        selector:
          c.selectorKind === 'label'
            ? { label: c.selectorValue }
            : { revision: Number(c.selectorValue) },
      },
      model_profile_id: c.modelProfileId,
    }));

    const wireChecks: RunCheck[] = [];
    for (const c of checks) {
      const base: RunCheck = { id: c.id, type: c.type, required: c.required };
      if (c.type === 'json_schema') {
        const parsed = tryParseJson(c.schema);
        if (!parsed.ok) {
          toast.error(`Check ${c.id}: invalid schema JSON.`);
          return null;
        }
        base.schema = parsed.value;
      } else if (c.type === 'array_length') {
        base.pointer = c.pointer;
        if (c.min !== '') base.min = Number(c.min);
        if (c.max !== '') base.max = Number(c.max);
      } else if (c.type === 'contains' || c.type === 'equals') {
        base.value = c.value;
      } else if (c.type === 'json_pointer_equals') {
        base.pointer = c.pointer;
        const parsed = tryParseJson(c.value);
        base.value = (parsed.ok ? parsed.value : c.value) as JsonValue;
      }
      wireChecks.push(base);
    }

    const req: RunRequest = {
      project_id: currentProjectId,
      kind: 'evaluation',
      dataset_id: datasetId,
      candidates: wireCandidates,
      checks: wireChecks,
      repeats,
    };
    if (gateEnabled) req.gate = { min_pass_rate: minPassRate };
    if (baselineLabel) req.baseline_label = baselineLabel;
    return req;
  };

  const runPreview = async () => {
    const req = buildRequest();
    if (!req) return;
    setBusy(true);
    try {
      const p = await api.previewRun(req);
      setPreview(p);
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Preview failed');
    } finally {
      setBusy(false);
    }
  };

  const start = async () => {
    const req = buildRequest();
    if (!req) return;
    setBusy(true);
    try {
      const run = await api.createRun(req);
      toast.success('Run started');
      navigate(`/evaluations/runs/${run.id}`);
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Failed to start run');
    } finally {
      setBusy(false);
    }
  };

  const prompts = promptsQuery.data ?? [];
  const profiles = profilesQuery.data ?? [];
  const candidateLabels = useMemo(
    () => candidates.map((c) => c.label),
    [candidates],
  );

  if (!currentProjectId) return <EmptyState title="No project selected" />;
  if (datasetsQuery.isLoading || promptsQuery.isLoading) return <Loading />;

  return (
    <div className="panel-scroll new-run">
      <div className="toolbar">
        <h2 className="toolbar__title">New comparison run</h2>
      </div>

      <section className="form-section">
        <h3>Dataset</h3>
        <label className="field field--inline">
          <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
            <option value="">Select a dataset…</option>
            {(datasetsQuery.data ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="form-section">
        <div className="section-head">
          <h3>Candidates ({candidates.length}/8)</h3>
          <button
            className="btn btn--ghost btn--sm"
            onClick={addCandidate}
            disabled={candidates.length >= 8}
          >
            + Add candidate
          </button>
        </div>
        {candidates.map((c, i) => (
          <div className="candidate-row" key={i}>
            <input
              className="candidate-row__label"
              value={c.label}
              onChange={(e) => updateCandidate(i, { label: e.target.value })}
              title="Candidate label"
            />
            <select
              value={c.promptId}
              onChange={(e) => updateCandidate(i, { promptId: e.target.value })}
            >
              <option value="">Prompt…</option>
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <select
              value={c.selectorKind}
              onChange={(e) =>
                updateCandidate(i, {
                  selectorKind: e.target.value as SelectorKind,
                  selectorValue: e.target.value === 'label' ? 'production' : '1',
                })
              }
            >
              <option value="label">label</option>
              <option value="revision">revision</option>
            </select>
            {c.selectorKind === 'label' ? (
              <select
                value={c.selectorValue}
                onChange={(e) => updateCandidate(i, { selectorValue: e.target.value })}
              >
                <option value="production">production</option>
                <option value="staging">staging</option>
                <option value="development">development</option>
              </select>
            ) : (
              <input
                type="number"
                min={1}
                value={c.selectorValue}
                onChange={(e) => updateCandidate(i, { selectorValue: e.target.value })}
                placeholder="rev #"
              />
            )}
            <select
              value={c.modelProfileId}
              onChange={(e) => updateCandidate(i, { modelProfileId: e.target.value })}
            >
              <option value="">Model profile…</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              className="btn btn--icon btn--danger"
              onClick={() => removeCandidate(i)}
              disabled={candidates.length === 1}
              title="Remove candidate"
            >
              ✕
            </button>
          </div>
        ))}
      </section>

      <section className="form-section">
        <div className="section-head">
          <h3>Checks</h3>
          <button className="btn btn--ghost btn--sm" onClick={addCheck}>
            + Add check
          </button>
        </div>
        {checks.length === 0 && <p className="muted small">No checks configured.</p>}
        {checks.map((c, i) => (
          <div className="check-row" key={i}>
            <input
              className="check-row__id"
              value={c.id}
              onChange={(e) => updateCheck(i, { id: e.target.value })}
            />
            <select
              value={c.type}
              onChange={(e) => updateCheck(i, { type: e.target.value as CheckType })}
            >
              {CHECK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <label className="check-row__req">
              <input
                type="checkbox"
                checked={c.required}
                onChange={(e) => updateCheck(i, { required: e.target.checked })}
              />
              required
            </label>
            <CheckParams check={c} onChange={(patch) => updateCheck(i, patch)} />
            <button
              className="btn btn--icon btn--danger"
              onClick={() => removeCheck(i)}
              title="Remove check"
            >
              ✕
            </button>
          </div>
        ))}
      </section>

      <section className="form-section form-section--inline">
        <label className="field field--inline">
          <span className="field-label">Repeats</span>
          <input
            type="number"
            min={1}
            max={20}
            value={repeats}
            onChange={(e) => setRepeats(Math.max(1, Number(e.target.value)))}
          />
        </label>
        <label className="field field--inline">
          <span className="field-label">Baseline</span>
          <select value={baselineLabel} onChange={(e) => setBaselineLabel(e.target.value)}>
            <option value="">none</option>
            {candidateLabels.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="field field--checkbox">
          <input
            type="checkbox"
            checked={gateEnabled}
            onChange={(e) => setGateEnabled(e.target.checked)}
          />
          <span>Gate</span>
        </label>
        {gateEnabled && (
          <label className="field field--inline">
            <span className="field-label">min pass rate</span>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={minPassRate}
              onChange={(e) => setMinPassRate(Number(e.target.value))}
            />
          </label>
        )}
      </section>

      {preview && (
        <div className="preview-counts">
          <span>
            <strong>{preview.candidate_count}</strong> candidates
          </span>
          <span>
            <strong>{preview.case_count}</strong> cases
          </span>
          <span>
            <strong>{preview.generation_calls}</strong> generation calls
          </span>
        </div>
      )}

      <div className="form__actions form__actions--sticky">
        <button className="btn" onClick={runPreview} disabled={busy}>
          {busy ? 'Working…' : 'Preview counts'}
        </button>
        <button className="btn btn--primary" onClick={start} disabled={busy}>
          Start run
        </button>
      </div>
    </div>
  );
}

/** Renders the type-specific parameter inputs for a check. */
function CheckParams({
  check,
  onChange,
}: {
  check: CheckDraft;
  onChange: (patch: Partial<CheckDraft>) => void;
}) {
  switch (check.type) {
    case 'json_schema':
      return (
        <div className="check-row__params">
          <JsonEditor
            value={parseOr(check.schema)}
            rows={3}
            onChange={(_v, _valid, raw) => onChange({ schema: raw })}
          />
        </div>
      );
    case 'array_length':
      return (
        <div className="check-row__params">
          <input
            placeholder="pointer e.g. /items"
            value={check.pointer}
            onChange={(e) => onChange({ pointer: e.target.value })}
          />
          <input
            type="number"
            placeholder="min"
            value={check.min}
            onChange={(e) => onChange({ min: e.target.value })}
          />
          <input
            type="number"
            placeholder="max"
            value={check.max}
            onChange={(e) => onChange({ max: e.target.value })}
          />
        </div>
      );
    case 'contains':
    case 'equals':
      return (
        <div className="check-row__params">
          <input
            placeholder="value"
            value={check.value}
            onChange={(e) => onChange({ value: e.target.value })}
          />
        </div>
      );
    case 'json_pointer_equals':
      return (
        <div className="check-row__params">
          <input
            placeholder="pointer e.g. /status"
            value={check.pointer}
            onChange={(e) => onChange({ pointer: e.target.value })}
          />
          <input
            placeholder="expected value (JSON or text)"
            value={check.value}
            onChange={(e) => onChange({ value: e.target.value })}
          />
        </div>
      );
    default:
      return null;
  }
}

function parseOr(text: string): JsonObject {
  const p = tryParseJson(text);
  return p.ok && p.value && typeof p.value === 'object' && !Array.isArray(p.value)
    ? (p.value as JsonObject)
    : {};
}
