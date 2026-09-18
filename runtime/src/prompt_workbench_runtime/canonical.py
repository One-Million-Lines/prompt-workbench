"""Canonical JSON (RFC 8785 style) — standalone copy for the portable runtime.

Kept byte-for-byte compatible with the workbench's ``domain/canonical.py`` and the
JavaScript reference so digests and rendered values agree across languages.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

MAX_SAFE_INTEGER = 2**53 - 1
MIN_SAFE_INTEGER = -(2**53 - 1)


class CanonicalizationError(ValueError):
    pass


def _format_number(value: int | float) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if value > MAX_SAFE_INTEGER or value < MIN_SAFE_INTEGER:
            raise CanonicalizationError(f"integer {value} outside safe range")
        return str(value)
    if math.isnan(value) or math.isinf(value):
        raise CanonicalizationError("non-finite numbers are not allowed")
    if value == int(value) and abs(value) <= MAX_SAFE_INTEGER:
        return str(int(value))
    return repr(value)


def _escape_string(s: str) -> str:
    out = ['"']
    for ch in s:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def canonical_json(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical_json(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        return "{" + ",".join(_escape_string(str(k)) + ":" + canonical_json(v) for k, v in items) + "}"
    raise CanonicalizationError(f"unsupported type: {type(value).__name__}")


def content_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()
