"""JSON Schema helpers (Draft 2020-12).

Enforces the v1 limits from the specification: object schemas only, no external
references, bounded size and nesting. Applies top-level defaults and validates
instances, returning structured error paths.
"""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

MAX_SCHEMA_BYTES = 64 * 1024
MAX_SCHEMA_DEPTH = 20


class SchemaValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]]):
        self.errors = errors
        super().__init__("; ".join(f"{e['path']}: {e['message']}" for e in errors) or "schema validation failed")


def _depth(node: Any, current: int = 0) -> int:
    if current > MAX_SCHEMA_DEPTH:
        return current
    if isinstance(node, dict):
        return max([current] + [_depth(v, current + 1) for v in node.values()])
    if isinstance(node, list):
        return max([current] + [_depth(v, current + 1) for v in node])
    return current


def _reject_external_refs(node: Any) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and not ref.startswith("#"):
            raise SchemaValidationError([{"path": "$ref", "message": "external references are not allowed"}])
        for value in node.values():
            _reject_external_refs(value)
    elif isinstance(node, list):
        for item in node:
            _reject_external_refs(item)


def validate_schema_document(schema: dict[str, Any]) -> None:
    encoded = json.dumps(schema).encode("utf-8")
    if len(encoded) > MAX_SCHEMA_BYTES:
        raise SchemaValidationError([{"path": "", "message": "schema exceeds 64 KiB"}])
    if _depth(schema) > MAX_SCHEMA_DEPTH:
        raise SchemaValidationError([{"path": "", "message": "schema nesting exceeds 20 levels"}])
    _reject_external_refs(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise SchemaValidationError([{"path": list(exc.path), "message": exc.message}]) from exc


def apply_defaults(schema: dict[str, Any], instance: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *instance* with defaults applied to missing top-level
    properties only. Explicit ``null`` never triggers a default."""
    result = dict(instance)
    for name, prop in (schema.get("properties") or {}).items():
        if name not in result and isinstance(prop, dict) and "default" in prop:
            result[name] = prop["default"]
    return result


def validate_instance(schema: dict[str, Any], instance: Any) -> None:
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        pointer = "/" + "/".join(str(p) for p in err.path) if err.path else ""
        errors.append({"path": pointer, "message": err.message})
    if errors:
        raise SchemaValidationError(errors)
