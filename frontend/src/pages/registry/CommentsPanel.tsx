import { useEffect, useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { Loading, ErrorNote, EmptyState } from '../../components/Feedback';
import type { Revision } from '../../api/types';

interface CommentsPanelProps {
  promptId: string;
  revisions: Revision[];
}

/**
 * Comments panel scoped to a chosen revision version. Supports add and delete.
 */
export function CommentsPanel({ promptId, revisions }: CommentsPanelProps) {
  const qc = useQueryClient();
  const toast = useToast();
  const [version, setVersion] = useState<number | null>(
    revisions.length > 0 ? revisions[0]!.version : null,
  );
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (revisions.length === 0) {
      setVersion(null);
      return;
    }
    const versions = new Set(revisions.map((r) => r.version));
    if (version == null || !versions.has(version)) {
      setVersion(revisions[0]!.version);
    }
  }, [revisions, version]);

  const commentsQuery = useQuery({
    queryKey: ['comments', promptId, version],
    queryFn: () => api.listComments(promptId, version!),
    enabled: version != null,
  });

  if (revisions.length === 0) {
    return <EmptyState title="No revisions" hint="Save a version to comment on it." />;
  }

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (version == null || !body.trim()) return;
    setBusy(true);
    try {
      await api.addComment(promptId, version, body.trim());
      setBody('');
      qc.invalidateQueries({ queryKey: ['comments', promptId, version] });
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Failed to comment');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.deleteComment(id);
      qc.invalidateQueries({ queryKey: ['comments', promptId, version] });
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Delete failed');
    }
  };

  return (
    <div className="comments-panel">
      <label className="field field--inline">
        <span className="field-label">Revision</span>
        <select value={version ?? ''} onChange={(e) => setVersion(Number(e.target.value))}>
          {revisions.map((r) => (
            <option key={r.id} value={r.version}>
              v{r.version}
            </option>
          ))}
        </select>
      </label>

      {commentsQuery.isLoading ? (
        <Loading />
      ) : commentsQuery.error ? (
        <ErrorNote message={(commentsQuery.error as ApiClientError).message} />
      ) : (commentsQuery.data ?? []).length === 0 ? (
        <p className="muted small">No comments on v{version}.</p>
      ) : (
        <ul className="comment-list">
          {(commentsQuery.data ?? []).map((c) => (
            <li key={c.id} className="comment">
              <div className="comment__head">
                <span className="comment__author">{c.author ?? 'anonymous'}</span>
                <span className="muted small">
                  {new Date(c.created_at).toLocaleString()}
                </span>
                <button
                  className="btn btn--icon btn--danger"
                  onClick={() => remove(c.id)}
                  title="Delete"
                >
                  ✕
                </button>
              </div>
              <div className="comment__body">{c.body}</div>
            </li>
          ))}
        </ul>
      )}

      <form className="comment-form" onSubmit={add}>
        <textarea
          rows={3}
          value={body}
          placeholder="Add a comment…"
          onChange={(e) => setBody(e.target.value)}
        />
        <button className="btn btn--primary btn--sm" type="submit" disabled={busy || !body.trim()}>
          {busy ? 'Posting…' : 'Comment'}
        </button>
      </form>
    </div>
  );
}
