// Canonical JSON (RFC 8785 style) — JavaScript reference.
// Kept byte-compatible with the Python implementation for shared digests/fixtures.

const MAX_SAFE = Number.MAX_SAFE_INTEGER;

export class CanonicalizationError extends Error {}

function formatNumber(value) {
  if (!Number.isFinite(value)) throw new CanonicalizationError("non-finite numbers are not allowed");
  if (Number.isInteger(value)) {
    if (value > MAX_SAFE || value < -MAX_SAFE) throw new CanonicalizationError("integer outside safe range");
    return String(value);
  }
  return String(value);
}

function escapeString(s) {
  let out = '"';
  for (const ch of s) {
    const code = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === "\\") out += "\\\\";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\b") out += "\\b";
    else if (ch === "\f") out += "\\f";
    else if (code < 0x20) out += "\\u" + code.toString(16).padStart(4, "0");
    else out += ch;
  }
  return out + '"';
}

export function canonicalJson(value) {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "string") return escapeString(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (typeof value === "object") {
    const keys = Object.keys(value).sort();
    return "{" + keys.map((k) => escapeString(k) + ":" + canonicalJson(value[k])).join(",") + "}";
  }
  throw new CanonicalizationError("unsupported type: " + typeof value);
}
