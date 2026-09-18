"""The ``simple-v1`` template engine.

Deliberately tiny and non-Turing-complete, per specification section 6.2:

* Only top-level ``{{name}}`` / ``{{ name }}`` variables (``[A-Za-z_][A-Za-z0-9_]*``).
* ``{{!literal}}`` emits a literal ``{{literal}}`` and is parsed before placeholders.
* Single-pass substitution: substituted values are never re-scanned.
* String values are inserted verbatim; every other JSON value is inserted as canonical
  JSON (RFC 8785). No filters, function calls, dotted paths, HTML escaping or code.
* Referenced variables must be declared in the input schema and present after defaults.

The workbench UI preview, the evaluation engine and the portable production runtime all
call this one implementation; the JavaScript reference mirrors it exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .canonical import canonical_json
from .schema import SchemaValidationError, apply_defaults, validate_instance

_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VARIABLE_SCAN = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)


class TemplateError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


@dataclass
class RenderedMessage:
    role: str
    content: str


def extract_variables(text: str) -> list[str]:
    """Return declared variable names referenced by a template string (excluding escapes)."""
    names: list[str] = []
    for match in _VARIABLE_SCAN.finditer(text):
        inner = match.group(1)
        if inner.startswith("!"):
            continue
        name = inner.strip()
        if _NAME_RE.match(name) and name not in names:
            names.append(name)
    return names


def render_string(template: str, values: dict[str, Any], declared: set[str]) -> str:
    out: list[str] = []
    i = 0
    n = len(template)
    while i < n:
        start = template.find("{{", i)
        if start == -1:
            out.append(template[i:])
            break
        out.append(template[i:start])
        end = template.find("}}", start + 2)
        if end == -1:
            raise TemplateError("template_unmatched", "Unmatched '{{' in template")
        inner = template[start + 2 : end]
        if inner.startswith("!"):
            out.append("{{" + inner[1:] + "}}")
        else:
            name = inner.strip()
            if not _NAME_RE.match(name):
                raise TemplateError(
                    "template_unsupported_expression",
                    f"Unsupported template expression: {{{{{inner}}}}}",
                    {"expression": inner},
                )
            if name not in declared:
                raise TemplateError(
                    "template_undeclared_variable",
                    f"Variable '{name}' is used but not declared in the input schema",
                    {"variable": name},
                )
            if name not in values:
                raise TemplateError(
                    "missing_variable",
                    f"Input '{name}' is required",
                    {"path": f"/inputs/{name}"},
                )
            out.append(_render_value(values[name]))
        i = end + 2
    return "".join(out)


def _render_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return canonical_json(value)


@dataclass
class RenderResult:
    messages: list[RenderedMessage]
    normalized_inputs: dict[str, Any]


def render_prompt(definition: dict[str, Any], raw_inputs: dict[str, Any]) -> RenderResult:
    """Validate inputs and render a prompt definition into chat messages.

    ``definition`` follows the canonical prompt payload (``kind``, ``messages``/``text``,
    ``input_schema``). Raises :class:`TemplateError` on any validation or template failure
    — always *before* a model would be called.
    """
    input_schema = definition.get("input_schema") or {"type": "object", "properties": {}}
    declared = set((input_schema.get("properties") or {}).keys())

    normalized = apply_defaults(input_schema, raw_inputs or {})
    # Strict boundary: extras are excluded rather than injected.
    strict_schema = dict(input_schema)
    strict_schema.setdefault("type", "object")
    strict_schema["additionalProperties"] = False
    try:
        validate_instance(strict_schema, normalized)
    except SchemaValidationError as exc:
        # Surface as a TemplateError so all render-time failures share one type and
        # are caught uniformly by callers (service render, run engine) before any
        # model call happens.
        raise TemplateError("input_validation_failed", str(exc), {"errors": exc.errors}) from exc

    kind = definition.get("kind", "chat")
    if kind == "text":
        text = definition.get("text", "")
        messages = [{"role": "user", "content": text}]
    else:
        messages = definition.get("messages") or []

    rendered: list[RenderedMessage] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        # Message roles are never interpolated from user input.
        rendered.append(RenderedMessage(role=role, content=render_string(content, normalized, declared)))

    return RenderResult(messages=rendered, normalized_inputs=normalized)
