import { useState } from 'react';
import type {
  OutputMode,
  PromptContent,
  SchemaType,
} from '../../api/types';
import { JsonEditor } from '../../components/JsonEditor';
import type { JsonObject } from '../../api/types';

interface SchemaEditorProps {
  content: PromptContent;
  disabled?: boolean;
  onChange: (content: PromptContent) => void;
}

const TYPES: SchemaType[] = ['string', 'integer', 'number', 'boolean', 'object', 'array'];
const OUTPUT_MODES: OutputMode[] = ['text', 'json', 'native_json_schema'];

/** Editor for the prompt input schema (variables) and output configuration. */
export function SchemaEditor({ content, disabled, onChange }: SchemaEditorProps) {
  const [newVar, setNewVar] = useState('');
  const props = content.input_schema.properties;
  const required = content.input_schema.required;

  const setSchema = (properties: typeof props, req: string[]) =>
    onChange({
      ...content,
      input_schema: { type: 'object', properties, required: req },
    });

  const addVar = () => {
    const name = newVar.trim();
    if (!name || props[name]) return;
    setSchema({ ...props, [name]: { type: 'string' } }, required);
    setNewVar('');
  };

  const removeVar = (name: string) => {
    const next = { ...props };
    delete next[name];
    setSchema(
      next,
      required.filter((r) => r !== name),
    );
  };

  const setType = (name: string, type: SchemaType) =>
    setSchema({ ...props, [name]: { ...props[name], type } }, required);

  const toggleRequired = (name: string) =>
    setSchema(
      props,
      required.includes(name)
        ? required.filter((r) => r !== name)
        : [...required, name],
    );

  const setOutputMode = (mode: OutputMode) =>
    onChange({ ...content, output: { ...content.output, mode } });

  return (
    <div className="schema-editor">
      <h4 className="preview-heading">Input schema</h4>
      <div className="schema-vars">
        {Object.keys(props).length === 0 ? (
          <p className="muted small">No variables declared.</p>
        ) : (
          Object.entries(props).map(([name, prop]) => (
            <div className="schema-var" key={name}>
              <span className="schema-var__name mono">{name}</span>
              <select
                value={prop.type}
                disabled={disabled}
                onChange={(e) => setType(name, e.target.value as SchemaType)}
              >
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <label className="schema-var__req">
                <input
                  type="checkbox"
                  checked={required.includes(name)}
                  disabled={disabled}
                  onChange={() => toggleRequired(name)}
                />
                required
              </label>
              <button
                className="btn btn--icon btn--danger"
                disabled={disabled}
                onClick={() => removeVar(name)}
                title="Remove variable"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>
      {!disabled && (
        <div className="schema-add">
          <input
            value={newVar}
            placeholder="new variable name"
            onChange={(e) => setNewVar(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addVar();
              }
            }}
          />
          <button className="btn btn--ghost btn--sm" onClick={addVar}>
            + Add variable
          </button>
        </div>
      )}

      <h4 className="preview-heading">Output</h4>
      <label className="field field--inline">
        <span className="field-label">Mode</span>
        <select
          value={content.output.mode}
          disabled={disabled}
          onChange={(e) => setOutputMode(e.target.value as OutputMode)}
        >
          {OUTPUT_MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>
      {content.output.mode !== 'text' && (
        <JsonEditor
          label="Output schema (JSON)"
          value={content.output.schema ?? {}}
          rows={6}
          disabled={disabled}
          onChange={(value, valid) => {
            if (valid) {
              onChange({
                ...content,
                output: { ...content.output, schema: value as JsonObject | null },
              });
            }
          }}
        />
      )}
    </div>
  );
}
