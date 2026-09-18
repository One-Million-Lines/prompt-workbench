import { formatJson } from '../lib/json';

/**
 * Render JSON/text safely inside a <pre>. Never uses dangerouslySetInnerHTML —
 * all content is set via React text nodes so model/prompt output cannot inject
 * markup.
 */
export function JsonView({ value }: { value: unknown }) {
  const text = typeof value === 'string' ? value : formatJson(value);
  return <pre className="json-view">{text}</pre>;
}

/** Render plain text safely inside a <pre>. */
export function TextView({ value }: { value: string | null | undefined }) {
  return <pre className="text-view">{value ?? ''}</pre>;
}
