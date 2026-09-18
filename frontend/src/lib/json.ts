import type { JsonValue } from '../api/types';

/** Result of attempting to parse a JSON string. */
export type JsonParseResult =
  | { ok: true; value: JsonValue }
  | { ok: false; error: string };

/**
 * Safely parse a JSON string, returning a discriminated union rather than
 * throwing. Empty input parses to `null` for convenience in optional fields.
 */
export function tryParseJson(text: string): JsonParseResult {
  const trimmed = text.trim();
  if (trimmed === '') return { ok: true, value: null };
  try {
    return { ok: true, value: JSON.parse(trimmed) as JsonValue };
  } catch (err) {
    return { ok: false, error: (err as Error).message };
  }
}

/** Pretty-print any JSON-serializable value; falls back to String() on error. */
export function formatJson(value: unknown, indent = 2): string {
  try {
    return JSON.stringify(value, null, indent);
  } catch {
    return String(value);
  }
}

/** Compact single-line JSON for dense table cells. */
export function compactJson(value: unknown, max = 80): string {
  let s: string;
  try {
    s = JSON.stringify(value);
  } catch {
    s = String(value);
  }
  if (s == null) return '';
  return s.length > max ? `${s.slice(0, max)}…` : s;
}
