// simple-v1 renderer — JavaScript reference implementation.
// Must produce identical messages to the Python renderer for the shared fixtures.

import { canonicalJson } from "./canonical.mjs";

const NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

export class TemplateError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

function renderValue(value) {
  if (typeof value === "string") return value;
  return canonicalJson(value);
}

export function renderString(template, values, declared) {
  let out = "";
  let i = 0;
  const n = template.length;
  while (i < n) {
    const start = template.indexOf("{{", i);
    if (start === -1) {
      out += template.slice(i);
      break;
    }
    out += template.slice(i, start);
    const end = template.indexOf("}}", start + 2);
    if (end === -1) throw new TemplateError("template_unmatched", "Unmatched '{{'");
    const inner = template.slice(start + 2, end);
    if (inner.startsWith("!")) {
      out += "{{" + inner.slice(1) + "}}";
    } else {
      const name = inner.trim();
      if (!NAME_RE.test(name)) throw new TemplateError("template_unsupported_expression", `Unsupported expression: {{${inner}}}`);
      if (!declared.has(name)) throw new TemplateError("template_undeclared_variable", `Variable '${name}' is not declared`);
      if (!(name in values)) throw new TemplateError("missing_variable", `Input '${name}' is required`);
      out += renderValue(values[name]);
    }
    i = end + 2;
  }
  return out;
}

export function applyDefaults(schema, inputs) {
  const result = { ...inputs };
  const props = (schema && schema.properties) || {};
  for (const [name, prop] of Object.entries(props)) {
    if (!(name in result) && prop && "default" in prop) result[name] = prop.default;
  }
  return result;
}

export function renderPrompt(portable, inputs) {
  const schema = portable.input_schema || { type: "object", properties: {} };
  const declared = new Set(Object.keys(schema.properties || {}));
  const normalized = applyDefaults(schema, inputs || {});
  for (const name of schema.required || []) {
    if (!(name in normalized)) throw new TemplateError("missing_variable", `Input '${name}' is required`);
  }
  let messages;
  if (portable.kind === "text") {
    messages = [{ role: "user", content: portable.text || "" }];
  } else {
    messages = portable.messages || [];
  }
  return {
    messages: messages.map((m) => ({ role: m.role || "user", content: renderString(m.content || "", normalized, declared) })),
    output: portable.output || null,
    tools: portable.tools || [],
    model: portable.model || null,
  };
}
