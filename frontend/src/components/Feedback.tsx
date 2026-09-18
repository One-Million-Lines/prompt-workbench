import type { ReactNode } from 'react';

/** Small inline loading indicator. */
export function Spinner({ label }: { label?: string }) {
  return (
    <span className="spinner" role="status">
      <span className="spinner__dot" />
      {label ? <span className="spinner__label">{label}</span> : null}
    </span>
  );
}

/** Full-panel centered loading state. */
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="loading">
      <Spinner label={label} />
    </div>
  );
}

/** Generic empty-state block. */
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-state__title">{title}</div>
      {hint ? <div className="empty-state__hint">{hint}</div> : null}
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}

/** Inline error message block. */
export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="error-note" role="alert">
      {message}
    </div>
  );
}
