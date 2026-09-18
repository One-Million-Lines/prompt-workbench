"""Storage abstraction layer.

The whole application talks to a single :class:`Repository` interface, a small
document store modelled on MongoDB semantics. This is what lets us keep
**MongoDB as the primary/production database** while running the **demo and tests on
SQLite** with zero external services — the domain and service layers never know
which backend is active.

Filters use a MongoDB-style subset understood by every backend::

    {"project_id": "abc"}                        # equality
    {"version": {"$gt": 3}}                       # comparison
    {"label": {"$in": ["production", "staging"]}}  # membership
    {"$or": [{"a": 1}, {"b": 2}]}                  # logical

Documents are plain ``dict`` objects carrying a string ``id`` primary key.
"""

from __future__ import annotations

import abc
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Iterable

Document = dict[str, Any]
Filter = dict[str, Any]
# Mongo-style sort: list of (field, direction) with direction 1=asc, -1=desc.
Sort = list[tuple[str, int]]

_OPERATORS = {"$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin", "$exists", "$contains", "$regex"}


def matches(doc: Document, flt: Filter | None) -> bool:
    """Pure-python filter evaluation, shared by in-memory logic and the mock backend."""
    if not flt:
        return True
    for key, condition in flt.items():
        if key == "$or":
            if not any(matches(doc, sub) for sub in condition):
                return False
            continue
        if key == "$and":
            if not all(matches(doc, sub) for sub in condition):
                return False
            continue
        value = _dig(doc, key)
        if isinstance(condition, dict) and any(k in _OPERATORS for k in condition):
            if not _match_operators(value, condition):
                return False
        else:
            if value != condition:
                return False
    return True


def _dig(doc: Any, dotted: str) -> Any:
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _match_operators(value: Any, condition: dict[str, Any]) -> bool:
    for op, operand in condition.items():
        if op == "$eq" and value != operand:
            return False
        if op == "$ne" and value == operand:
            return False
        if op == "$gt" and not (value is not None and value > operand):
            return False
        if op == "$gte" and not (value is not None and value >= operand):
            return False
        if op == "$lt" and not (value is not None and value < operand):
            return False
        if op == "$lte" and not (value is not None and value <= operand):
            return False
        if op == "$in" and value not in operand:
            return False
        if op == "$nin" and value in operand:
            return False
        if op == "$exists" and (value is not None) != bool(operand):
            return False
        if op == "$contains" and (value is None or operand not in value):
            return False
        if op == "$regex":
            import re

            if value is None or re.search(operand, str(value)) is None:
                return False
    return True


class Repository(abc.ABC):
    """Backend-agnostic document store."""

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Prepare the store (create files, indexes, collections)."""

    @abc.abstractmethod
    async def close(self) -> None: ...

    @abc.abstractmethod
    async def insert_one(self, collection: str, doc: Document) -> Document: ...

    @abc.abstractmethod
    async def find_one(self, collection: str, flt: Filter) -> Document | None: ...

    @abc.abstractmethod
    async def find_many(
        self,
        collection: str,
        flt: Filter | None = None,
        sort: Sort | None = None,
        limit: int | None = None,
        skip: int = 0,
    ) -> list[Document]: ...

    @abc.abstractmethod
    async def count(self, collection: str, flt: Filter | None = None) -> int: ...

    @abc.abstractmethod
    async def replace_one(
        self, collection: str, flt: Filter, doc: Document, *, upsert: bool = False
    ) -> Document | None:
        """Replace the first matching document. Returns the stored doc or ``None``
        when nothing matched and ``upsert`` is false. Used for optimistic writes:
        include the expected ``edit_sequence`` in *flt* to fail stale updates."""

    @abc.abstractmethod
    async def delete_one(self, collection: str, flt: Filter) -> bool: ...

    @abc.abstractmethod
    async def delete_many(self, collection: str, flt: Filter) -> int: ...

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["Repository"]:
        """Best-effort atomic scope. SQLite provides a real transaction; the Mongo
        backend yields itself (single-document operations are already atomic)."""
        yield self

    async def get(self, collection: str, doc_id: str) -> Document | None:
        return await self.find_one(collection, {"id": doc_id})

    async def find_all(self, collection: str, flt: Filter | None = None, sort: Sort | None = None) -> list[Document]:
        return await self.find_many(collection, flt, sort)


def ensure_ids(docs: Iterable[Document]) -> list[Document]:
    return [d for d in docs if d.get("id")]
