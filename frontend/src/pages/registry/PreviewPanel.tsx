import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { extractVariables } from '../../lib/prompt';
import { useDebounced } from '../../lib/useDebounced';
import { JsonView, TextView } from '../../components/JsonView';
import { Spinner } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import type { JsonObject, JsonValue, PromptContent } from '../../api/types';

interface PreviewPanelProps {
  promptId: string;
  content: PromptContent;
}

/**
 * Coerce a raw string input into a typed JSON value based on the declared
 * schema type, so previews send integers/numbers/booleans correctly. Falls back
 * to the raw string if coercion fails.
 */
function coerce(raw: string, type: string | undefined): JsonValue {
  if (raw === '') return '';
  switch (type) {
    case 'integer':
    case 'number': {
      const n = Number(raw);
      return Number.isNaN(n) ? raw : n;
    }
    case 'boolean':
      return raw === 'true';
    case 'object':
    case 'array':
      try {
        return JSON.parse(raw) as JsonValue;
      } catch {
        return raw;
      }
    default:
      return raw;
  }
}

/**
 * Right-side live preview: renders variable inputs derived from the prompt's
 * templates + input schema, then calls POST /render with the {draft} selector,
 * debounced ~600ms, whenever the content or inputs change.
 */
export function PreviewPanel({ promptId, content }: PreviewPanelProps) {
  const variables = useMemo(() => {
    const fromTemplates = extractVariables(content);
    const fromSchema = Object.keys(content.input_schema.properties ?? {});
    return Array.from(new Set([...fromSchema, ...fromTemplates]));
  }, [content]);

  const [values, setValues] = useState<Record<string, string>>({});

  const inputs: JsonObject = useMemo(() => {
    const obj: JsonObject = {};
    for (const v of variables) {
      const raw = values[v];
      if (raw === undefined || raw === '') continue;
      const type = content.input_schema.properties[v]?.type;
      obj[v] = coerce(raw, type);
    }
    return obj;
  }, [values, variables, content.input_schema.properties]);

  // Debounce the render trigger key (~600ms) as required for live preview.
  const debouncedKey = useDebounced(
    JSON.stringify({ content, inputs }),
    600,
  );

  const renderQuery = useQuery({
    queryKey: ['render-preview', promptId, debouncedKey],
    queryFn: () => api.render(promptId, { draft: content }, inputs),
    enabled: !!promptId,
    retry: false,
  });

  return (
    <div className="preview-panel">
      <section className="preview-section">
        <h4 className="preview-heading">
          Inputs
          <Badge tone="muted">{content.output.mode}</Badge>
        </h4>
        {variables.length === 0 ? (
          <p className="muted small">No variables detected.</p>
        ) : (
          <div className="var-form">
            {variables.map((v) => {
              const prop = content.input_schema.properties[v];
              const required = content.input_schema.required.includes(v);
              return (
                <label className="var-field" key={v}>
                  <span className="var-field__label">
                    {v}
                    {required ? <span className="req">*</span> : null}
                    <span className="var-field__type">{prop?.type ?? 'string'}</span>
                  </span>
                  <input
                    value={values[v] ?? ''}
                    placeholder={prop?.type === 'boolean' ? 'true / false' : ''}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [v]: e.target.value }))
                    }
                  />
                </label>
              );
            })}
          </div>
        )}
      </section>

      <section className="preview-section">
        <h4 className="preview-heading">
          Rendered preview
          {renderQuery.isFetching ? <Spinner /> : null}
        </h4>
        {renderQuery.error ? (
          <div className="error-note">
            {(renderQuery.error as ApiClientError).message}
          </div>
        ) : renderQuery.data ? (
          <div className="preview-result">
            {renderQuery.data.messages.map((m, i) => (
              <div className="preview-msg" key={i}>
                <div className="preview-msg__role">{m.role}</div>
                <TextView value={m.content} />
              </div>
            ))}
            {renderQuery.data.output !== undefined &&
            renderQuery.data.output !== null ? (
              <div className="preview-output">
                <div className="preview-msg__role">output</div>
                <JsonView value={renderQuery.data.output} />
              </div>
            ) : null}
          </div>
        ) : (
          <p className="muted small">Edit the prompt to see a live preview.</p>
        )}
      </section>
    </div>
  );
}
