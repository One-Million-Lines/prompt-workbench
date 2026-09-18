"""Identifiers, slugs and timestamps."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> str:
    """UTC ISO-8601 timestamp with a trailing ``Z``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))


def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-.")
    slug = slug[:80]
    if not slug or not _SLUG_RE.match(slug):
        slug = "item-" + new_uuid()[:8]
    return slug
