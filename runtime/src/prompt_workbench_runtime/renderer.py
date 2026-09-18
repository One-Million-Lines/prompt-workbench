"""Portable ``simple-v1`` renderer with a dependency-free input validator.

Mirrors the workbench's engine so a release bundle renders identically in production
with no database and no third-party packages. The validator covers the subset of JSON
Schema the workbench emits (types, required, defaults, additionalProperties:false).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .canonical import canonical_json

_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


class TemplateError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class RenderedRequest:
    messages: list[dict[str, str]]
    output: dict[str, Any] | None
    tools: list[dict[str, Any]]
    model: dict[str, Any] | None
    provenance: dict[str, Any]


def _check_type(value: Any, type_spec: Any) -> bool:
    if isinstance(type_spec, list):
        return any(_check_type(value, t) for t in type_spec)
    checker = _TYPE_CHECKS.get(type_spec)
    return checker(value) if checker else True


def validate_and_default(schema: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    schema = schema or {"type": "object", "properties": {}}
    properties = schema.get("properties", {})
    result = dict(inputs or {})
    for name, prop in properties.items():
        if name not in result and isinstance(prop, dict) and "default" in prop:
            result[name] = prop["default"]

    for name in schema.get("required", []):
        if name not in result:
            raise TemplateError("missing_variable", f"Input '{name}' is required")

    for name, value in result.items():
        if name not in properties:
            raise TemplateError("unexpected_input", f"Input '{name}' is not declared in the schema")
        prop = properties[name]
        if isinstance(prop, dict) and "type" in prop and value is not None:
            if not _check_type(value, prop["type"]):
                raise TemplateError("invalid_type", f"Input '{name}' has the wrong type")
    return result


def _render_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return canonical_json(value)


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
            raise TemplateError("template_unmatched", "Unmatched '{{'")
        inner = template[start + 2 : end]
        if inner.startswith("!"):
            out.append("{{" + inner[1:] + "}}")
        else:
            name = inner.strip()
            if not _NAME_RE.match(name):
                raise TemplateError("template_unsupported_expression", f"Unsupported expression: {{{{{inner}}}}}")
            if name not in declared:
                raise TemplateError("template_undeclared_variable", f"Variable '{name}' is not declared")
            if name not in values:
                raise TemplateError("missing_variable", f"Input '{name}' is required")
            out.append(_render_value(values[name]))
        i = end + 2
    return "".join(out)


def render_prompt(portable: dict[str, Any], inputs: dict[str, Any]) -> RenderedRequest:
    schema = portable.get("input_schema") or {"type": "object", "properties": {}}
    declared = set((schema.get("properties") or {}).keys())
    normalized = validate_and_default(schema, inputs)

    if portable.get("kind") == "text":
        messages = [{"role": "user", "content": portable.get("text", "")}]
    else:
        messages = portable.get("messages") or []

    rendered = [{"role": m.get("role", "user"), "content": render_string(m.get("content", ""), normalized, declared)} for m in messages]
    return RenderedRequest(
        messages=rendered,
        output=portable.get("output"),
        tools=portable.get("tools", []),
        model=portable.get("model"),
        provenance={"prompt_id": portable.get("prompt_id"), "slug": portable.get("slug"), "revision": portable.get("revision")},
    )
