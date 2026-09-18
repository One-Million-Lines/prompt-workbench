import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { useDebouncedCallback } from '../../lib/useDebounced';
import { Loading, ErrorNote } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import { Modal, useDisclosure } from '../../components/Modal';
import { MessagesEditor } from './MessagesEditor';
import { SchemaEditor } from './SchemaEditor';
import { PreviewPanel } from './PreviewPanel';
import { HistoryPanel } from './HistoryPanel';
import { CommentsPanel } from './CommentsPanel';
import { AnalyticsPanel } from './AnalyticsPanel';
import { LabelsPanel } from './LabelsPanel';
import type { PromptContent } from '../../api/types';

type CenterTab = 'edit' | 'history' | 'comments' | 'analytics' | 'labels';
type SaveState = 'idle' | 'saving' | 'saved' | 'error';

const AUTOSAVE_MS = 800;

/**
 * The full prompt editor. Loads the draft, autosaves edits (with optimistic
 * edit-sequence tracking and 409 stale-draft recovery), supports viewing past
 * revisions read-only, saving named versions, and switching info panels.
 */
export function PromptEditor({ promptId }: { promptId: string }) {
  const qc = useQueryClient();
  const toast = useToast();

  const promptQuery = useQuery({
    queryKey: ['prompt', promptId],
    queryFn: () => api.getPrompt(promptId),
  });
  const draftQuery = useQuery({
    queryKey: ['draft', promptId],
    queryFn: () => api.getDraft(promptId),
  });
  const revisionsQuery = useQuery({
    queryKey: ['revisions', promptId],
    queryFn: () => api.listRevisions(promptId),
  });

  const projectId = promptQuery.data?.project_id;
  const profilesQuery = useQuery({
    queryKey: ['model-profiles', projectId],
    queryFn: () => api.listModelProfiles(projectId!),
    enabled: !!projectId,
  });

  const [content, setContent] = useState<PromptContent | null>(null);
  const [editSeq, setEditSeq] = useState(0);
  const editSeqRef = useRef(0);
  const initialized = useRef(false);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [centerTab, setCenterTab] = useState<CenterTab>('edit');
  const [viewVersion, setViewVersion] = useState<'draft' | number>('draft');
  const [modelProfileId, setModelProfileId] = useState<string>('');

  const saveDialog = useDisclosure();
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  // Initialize local content once from the loaded draft.
  useEffect(() => {
    if (!initialized.current && draftQuery.data) {
      setContent(draftQuery.data.content);
      setEditSeq(draftQuery.data.edit_sequence);
      editSeqRef.current = draftQuery.data.edit_sequence;
      initialized.current = true;
    }
  }, [draftQuery.data]);

  // Default model profile selection.
  useEffect(() => {
    if (!modelProfileId && profilesQuery.data && profilesQuery.data.length > 0) {
      setModelProfileId(profilesQuery.data[0]!.id);
    }
  }, [profilesQuery.data, modelProfileId]);

  // Read-only content for a past revision.
  const revisionQuery = useQuery({
    queryKey: ['revision', promptId, viewVersion],
    queryFn: () => api.getRevision(promptId, viewVersion as number),
    enabled: typeof viewVersion === 'number',
  });

  const editing = viewVersion === 'draft';

  // Debounced autosave. Reads the latest edit sequence from a ref so it never
  // sends a stale value.
  const autosave = useDebouncedCallback(async (next: PromptContent) => {
    setSaveState('saving');
    try {
      const res = await api.updateDraft(promptId, next, editSeqRef.current);
      editSeqRef.current = res.edit_sequence;
      setEditSeq(res.edit_sequence);
      setSaveState('saved');
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'stale_draft') {
        // Someone else advanced the draft — reload the latest and inform user.
        const fresh = await api.getDraft(promptId);
        setContent(fresh.content);
        setEditSeq(fresh.edit_sequence);
        editSeqRef.current = fresh.edit_sequence;
        setSaveState('idle');
        toast.error('Draft changed elsewhere — reloaded the latest version.');
      } else {
        setSaveState('error');
        toast.error(err instanceof ApiClientError ? err.message : 'Autosave failed');
      }
    }
  }, AUTOSAVE_MS);

  const handleChange = (next: PromptContent) => {
    setContent(next);
    setSaveState('saving');
    autosave(next);
  };

  const saveVersion = async () => {
    setSaving(true);
    try {
      let sequenceForRevision = editSeqRef.current;
      if (editing && content) {
        setSaveState('saving');
        const freshDraft = await api.updateDraft(promptId, content, editSeqRef.current);
        setContent(freshDraft.content);
        setEditSeq(freshDraft.edit_sequence);
        editSeqRef.current = freshDraft.edit_sequence;
        sequenceForRevision = freshDraft.edit_sequence;
        setSaveState('saved');
      }

      const rev = await api.createRevision(promptId, note.trim(), sequenceForRevision);
      if (rev.unchanged) {
        toast.push('No changes since the last version.', 'info');
      } else {
        toast.success(`Saved v${rev.version}`);
      }
      setNote('');
      saveDialog.close();
      qc.invalidateQueries({ queryKey: ['draft', promptId] });
      qc.invalidateQueries({ queryKey: ['revisions', promptId] });
      qc.invalidateQueries({ queryKey: ['labels', promptId] });
      qc.invalidateQueries({ queryKey: ['analytics', promptId] });
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'stale_draft') {
        const fresh = await api.getDraft(promptId);
        setContent(fresh.content);
        setEditSeq(fresh.edit_sequence);
        editSeqRef.current = fresh.edit_sequence;
        setSaveState('idle');
        toast.error('Draft changed elsewhere — reloaded the latest version.');
      } else {
        toast.error(err instanceof ApiClientError ? err.message : 'Save failed');
      }
    } finally {
      setSaving(false);
    }
  };

  const restoreToDraft = async (version: number) => {
    try {
      const fresh = await api.restoreDraft(promptId, version, editSeqRef.current);
      setContent(fresh.content);
      setEditSeq(fresh.edit_sequence);
      editSeqRef.current = fresh.edit_sequence;
      setViewVersion('draft');
      setCenterTab('edit');
      setSaveState('saved');
      toast.success(`Restored v${version} into draft`);
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Restore failed');
    }
  };

  if (promptQuery.isLoading || draftQuery.isLoading) return <Loading />;
  if (promptQuery.error)
    return <ErrorNote message={(promptQuery.error as ApiClientError).message} />;
  if (draftQuery.error)
    return <ErrorNote message={(draftQuery.error as ApiClientError).message} />;

  const prompt = promptQuery.data!;
  const revisions = revisionsQuery.data ?? [];
  const displayContent = editing ? content : revisionQuery.data?.content ?? null;

  return (
    <div className="editor">
      <div className="editor__topbar">
        <div className="editor__title">
          <h2>{prompt.name}</h2>
          <span className="editor__slug mono">{prompt.slug}</span>
          {editing ? (
            <SaveIndicator state={saveState} editSeq={editSeq} />
          ) : (
            <Badge tone="info">viewing v{viewVersion} (read-only)</Badge>
          )}
        </div>

        <div className="editor__controls">
          <label className="field field--inline">
            <span className="field-label">Version</span>
            <select
              value={String(viewVersion)}
              onChange={(e) =>
                setViewVersion(
                  e.target.value === 'draft' ? 'draft' : Number(e.target.value),
                )
              }
            >
              <option value="draft">Draft</option>
              {revisions.map((r) => (
                <option key={r.id} value={r.version}>
                  v{r.version}
                </option>
              ))}
            </select>
          </label>

          <label className="field field--inline">
            <span className="field-label">Model</span>
            <select
              value={modelProfileId}
              onChange={(e) => setModelProfileId(e.target.value)}
              disabled={(profilesQuery.data ?? []).length === 0}
            >
              {(profilesQuery.data ?? []).length === 0 ? (
                <option value="">No profiles</option>
              ) : (
                (profilesQuery.data ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} · {p.model}
                  </option>
                ))
              )}
            </select>
          </label>

          <button
            className="btn btn--primary btn--sm"
            onClick={saveDialog.open}
            disabled={!editing}
          >
            Save version
          </button>
        </div>
      </div>

      <div className="editor__tabs">
        {(['edit', 'history', 'comments', 'analytics', 'labels'] as CenterTab[]).map(
          (t) => (
            <button
              key={t}
              className={`tab${centerTab === t ? ' tab--active' : ''}`}
              onClick={() => setCenterTab(t)}
            >
              {t === 'edit' ? 'Editor' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ),
        )}
      </div>

      <div className="editor__body">
        <div className="editor__center">
          {centerTab === 'edit' && displayContent && (
            <>
              <MessagesEditor
                content={displayContent}
                disabled={!editing}
                onChange={handleChange}
              />
              <SchemaEditor
                content={displayContent}
                disabled={!editing}
                onChange={handleChange}
              />
            </>
          )}
          {centerTab === 'history' && (
            <HistoryPanel
              promptId={promptId}
              revisions={revisions}
              onRestore={restoreToDraft}
            />
          )}
          {centerTab === 'comments' && (
            <CommentsPanel promptId={promptId} revisions={revisions} />
          )}
          {centerTab === 'analytics' && <AnalyticsPanel promptId={promptId} />}
          {centerTab === 'labels' && (
            <LabelsPanel promptId={promptId} revisions={revisions} />
          )}
        </div>

        <div className="editor__right">
          {displayContent ? (
            <PreviewPanel promptId={promptId} content={displayContent} />
          ) : (
            <Loading />
          )}
        </div>
      </div>

      <Modal
        open={saveDialog.isOpen}
        title="Save new version"
        onClose={saveDialog.close}
      >
        <div className="form">
          <label className="field">
            <span className="field-label">Change note</span>
            <textarea
              rows={3}
              value={note}
              autoFocus
              placeholder="What changed in this version?"
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <div className="form__actions">
            <button className="btn" onClick={saveDialog.close}>
              Cancel
            </button>
            <button className="btn btn--primary" onClick={saveVersion} disabled={saving}>
              {saving ? 'Saving…' : 'Save version'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

/** Small draft/saved status indicator including the current edit sequence. */
function SaveIndicator({ state, editSeq }: { state: SaveState; editSeq: number }) {
  const tone =
    state === 'error' ? 'error' : state === 'saving' ? 'warn' : 'muted';
  const label =
    state === 'saving'
      ? 'saving…'
      : state === 'error'
        ? 'save failed'
        : state === 'saved'
          ? 'draft saved'
          : 'draft';
  return (
    <span className="save-indicator">
      <Badge tone={tone}>{label}</Badge>
      <span className="muted small">seq {editSeq}</span>
    </span>
  );
}
