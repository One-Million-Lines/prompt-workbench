import { useState, type FormEvent } from 'react';
import { api, ApiClientError } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { defaultPromptContent } from '../../lib/prompt';

interface NewPromptFormProps {
  projectId: string;
  isSnippet: boolean;
  onCreated: (id: string) => void;
}

/** Slugify a display name into a URL-safe slug. */
function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** Form to create a new prompt or snippet. */
export function NewPromptForm({ projectId, isSnippet, onCreated }: NewPromptFormProps) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const effectiveSlug = slugTouched ? slug : slugify(name);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.createPrompt({
        project_id: projectId,
        name,
        slug: effectiveSlug,
        description,
        is_snippet: isSnippet,
        content: defaultPromptContent(),
      });
      toast.success(`Created ${created.name}`);
      onCreated(created.id);
    } catch (err) {
      const message = err instanceof ApiClientError ? err.message : 'Create failed';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="form" onSubmit={onSubmit}>
      <label className="field">
        <span className="field-label">Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
      </label>
      <label className="field">
        <span className="field-label">Slug</span>
        <input
          value={effectiveSlug}
          onChange={(e) => {
            setSlugTouched(true);
            setSlug(e.target.value);
          }}
          placeholder="auto-generated from name"
          required
        />
      </label>
      <label className="field">
        <span className="field-label">Description</span>
        <textarea
          value={description}
          rows={3}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <div className="form__actions">
        <button className="btn btn--primary" type="submit" disabled={submitting || !name}>
          {submitting ? 'Creating…' : 'Create'}
        </button>
      </div>
    </form>
  );
}
