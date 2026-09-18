import { useEffect, useState } from 'react';
import { formatJson, tryParseJson } from '../lib/json';
import type { JsonValue } from '../api/types';

interface JsonEditorProps {
  value: JsonValue | undefined;
  onChange: (value: JsonValue, valid: boolean, raw: string) => void;
  rows?: number;
  placeholder?: string;
  label?: string;
  disabled?: boolean;
}

/**
 * Controlled JSON textarea that validates on every edit and surfaces parse
 * errors inline. The parent receives both the parsed value and a validity flag
 * so it can block saves on invalid JSON.
 */
export function JsonEditor({
  value,
  onChange,
  rows = 8,
  placeholder,
  label,
  disabled,
}: JsonEditorProps) {
  const [raw, setRaw] = useState<string>(() =>
    value === undefined ? '' : formatJson(value),
  );
  const [error, setError] = useState<string | null>(null);

  // Re-sync when the upstream value identity changes (e.g. switching records).
  useEffect(() => {
    setRaw(value === undefined ? '' : formatJson(value));
    setError(null);
  }, [value]);

  const handle = (text: string) => {
    setRaw(text);
    const result = tryParseJson(text);
    if (result.ok) {
      setError(null);
      onChange(result.value, true, text);
    } else {
      setError(result.error);
      onChange(null, false, text);
    }
  };

  return (
    <div className="json-editor">
      {label ? <label className="field-label">{label}</label> : null}
      <textarea
        className={`json-editor__area${error ? ' json-editor__area--invalid' : ''}`}
        value={raw}
        rows={rows}
        spellCheck={false}
        disabled={disabled}
        placeholder={placeholder ?? '{ }'}
        onChange={(e) => handle(e.target.value)}
      />
      {error ? <div className="json-editor__error">Invalid JSON: {error}</div> : null}
    </div>
  );
}
