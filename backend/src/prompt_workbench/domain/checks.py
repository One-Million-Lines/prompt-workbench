"""Deterministic evaluation checks (specification section 10.2).

Each check receives the normalized output envelope ``{text, json, tool_calls}`` plus the
case ``expected`` data and returns a :class:`CheckResult`. The ``rubric`` check needs a
model judge and is handled by the run service; everything here is pure and deterministic.
No arbitrary code or regex evaluators are exposed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .schema import validate_instance


@dataclass
class CheckResult:
    outcome: str  # "pass" | "fail" | "error"
    score: float | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


class PointerError(ValueError):
    pass


def resolve_pointer(document: Any, pointer: str) -> Any:
    """RFC 6901 JSON pointer resolution. Raises :class:`PointerError` on a missing path."""
    if pointer in ("", "/"):
        return document
    if not pointer.startswith("/"):
        raise PointerError(f"invalid pointer: {pointer!r}")
    current = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise PointerError(f"missing path: {pointer}")
            current = current[token]
        elif isinstance(current, list):
            try:
                idx = int(token)
            except ValueError as exc:
                raise PointerError(f"invalid array index in {pointer}") from exc
            if idx < 0 or idx >= len(current):
                raise PointerError(f"array index out of range in {pointer}")
            current = current[idx]
        else:
            raise PointerError(f"cannot descend into scalar at {pointer}")
    return current


def _parse_json(envelope: dict[str, Any]) -> tuple[bool, Any]:
    if envelope.get("json") is not None:
        return True, envelope["json"]
    text = envelope.get("text")
    if text is None:
        return False, None
    try:
        return True, json.loads(text)
    except (ValueError, TypeError):
        return False, None


def evaluate_check(config: dict[str, Any], envelope: dict[str, Any], expected: Any) -> CheckResult:
    check_type = config.get("type")
    handler = _HANDLERS.get(check_type)
    if handler is None:
        return CheckResult("error", evidence={"reason": f"unknown check type {check_type!r}"})
    try:
        return handler(config, envelope, expected)
    except PointerError as exc:
        return CheckResult("fail", evidence={"reason": str(exc)})
    except Exception as exc:  # noqa: BLE001 - a check must never crash the run
        return CheckResult("error", evidence={"reason": str(exc)})


def _json_valid(config, envelope, expected) -> CheckResult:
    ok, value = _parse_json(envelope)
    return CheckResult("pass" if ok else "fail", evidence={"parsed": ok})


def _json_schema(config, envelope, expected) -> CheckResult:
    ok, value = _parse_json(envelope)
    if not ok:
        return CheckResult("fail", evidence={"reason": "output is not valid JSON"})
    schema = config.get("schema") or {}
    try:
        validate_instance(schema, value)
    except Exception as exc:  # SchemaValidationError carries .errors
        return CheckResult("fail", evidence={"errors": getattr(exc, "errors", str(exc))})
    return CheckResult("pass")


def _target_value(config, envelope):
    target = config.get("target", "text")
    if target == "json":
        _, value = _parse_json(envelope)
        return value
    return envelope.get("text")


def _equals(config, envelope, expected) -> CheckResult:
    want = config["expected"] if "expected" in config else expected
    got = _target_value(config, envelope)
    if config.get("normalize_whitespace") and isinstance(got, str) and isinstance(want, str):
        got = " ".join(got.split())
        want = " ".join(want.split())
    ok = got == want
    return CheckResult("pass" if ok else "fail", evidence={"expected": want, "actual": got})


def _contains(config, envelope, expected) -> CheckResult:
    needle = config.get("value", expected)
    text = envelope.get("text") or ""
    if not config.get("case_sensitive", True):
        text, needle = text.lower(), str(needle).lower()
    ok = str(needle) in text
    return CheckResult("pass" if ok else "fail", evidence={"needle": config.get("value", expected)})


def _not_contains(config, envelope, expected) -> CheckResult:
    inner = _contains(config, envelope, expected)
    inner.outcome = "fail" if inner.outcome == "pass" else "pass"
    return inner


def _json_pointer_equals(config, envelope, expected) -> CheckResult:
    ok, value = _parse_json(envelope)
    if not ok:
        return CheckResult("fail", evidence={"reason": "output is not valid JSON"})
    actual = resolve_pointer(value, config.get("actual_pointer", ""))
    if "expected" in config:
        want = config["expected"]
    else:
        want = resolve_pointer(expected, config.get("expected_pointer", ""))
    ok = actual == want
    return CheckResult("pass" if ok else "fail", evidence={"expected": want, "actual": actual})


def _array_length(config, envelope, expected) -> CheckResult:
    ok, value = _parse_json(envelope)
    if not ok:
        return CheckResult("fail", evidence={"reason": "output is not valid JSON"})
    target = resolve_pointer(value, config.get("pointer", ""))
    if not isinstance(target, list):
        return CheckResult("fail", evidence={"reason": "target is not an array"})
    length = len(target)
    lo, hi = config.get("min"), config.get("max")
    if lo is not None and length < lo:
        return CheckResult("fail", evidence={"length": length, "min": lo})
    if hi is not None and length > hi:
        return CheckResult("fail", evidence={"length": length, "max": hi})
    return CheckResult("pass", evidence={"length": length})


def _tool_call(config, envelope, expected) -> CheckResult:
    calls = envelope.get("tool_calls") or []
    name = config.get("name")
    matching = [c for c in calls if c.get("name") == name] if name else calls
    if name and not matching:
        return CheckResult("fail", evidence={"reason": f"no tool call named {name!r}", "calls": [c.get("name") for c in calls]})
    if "count" in config and len(matching) != config["count"]:
        return CheckResult("fail", evidence={"expected_count": config["count"], "actual_count": len(matching)})
    arg_schema = config.get("arguments_schema")
    if arg_schema:
        for call in matching:
            try:
                validate_instance(arg_schema, call.get("arguments", {}))
            except Exception as exc:
                return CheckResult("fail", evidence={"errors": getattr(exc, "errors", str(exc))})
    return CheckResult("pass", evidence={"matched": len(matching)})


_HANDLERS = {
    "json_valid": _json_valid,
    "json_schema": _json_schema,
    "equals": _equals,
    "contains": _contains,
    "not_contains": _not_contains,
    "json_pointer_equals": _json_pointer_equals,
    "array_length": _array_length,
    "tool_call": _tool_call,
}

DETERMINISTIC_CHECK_TYPES = set(_HANDLERS.keys())
