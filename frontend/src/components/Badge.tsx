import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  tone?:
    | 'neutral'
    | 'pass'
    | 'fail'
    | 'error'
    | 'warn'
    | 'info'
    | 'accent'
    | 'muted';
  title?: string;
}

/** A small pill/label badge with semantic color tones. */
export function Badge({ children, tone = 'neutral', title }: BadgeProps) {
  return (
    <span className={`badge badge--${tone}`} title={title}>
      {children}
    </span>
  );
}

/** Maps a run/cell status string to a badge tone. */
export function statusTone(status: string): BadgeProps['tone'] {
  switch (status) {
    case 'pass':
    case 'succeeded':
    case 'passed':
      return 'pass';
    case 'fail':
    case 'failed':
      return 'fail';
    case 'error':
      return 'error';
    case 'running':
    case 'queued':
      return 'info';
    case 'completed_with_errors':
      return 'warn';
    case 'cancelled':
      return 'muted';
    default:
      return 'neutral';
  }
}
