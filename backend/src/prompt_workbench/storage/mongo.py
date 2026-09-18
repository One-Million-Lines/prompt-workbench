"""MongoDB implementation of :class:`Repository` — the preferred primary backend.

Uses ``motor`` (async driver). The application's ``id`` field is mapped to Mongo's
``_id`` for a free unique primary key and fast lookups; callers only ever see ``id``.
Filters are already MongoDB-style so they pass through with minimal translation.

``motor`` is an optional dependency (installed via the ``mongo`` extra); importing this
module without it raises a clear error only when the Mongo backend is actually selected.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from .base import Document, Filter, Repository, Sort


def _to_storage(doc: Document) -> Document:
    stored = dict(doc)
    if "id" in stored:
        stored["_id"] = stored["id"]
    return stored


def _from_storage(doc: Document | None) -> Document | None:
    if doc is None:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out


def _translate_filter(flt: Filter | None) -> Filter:
    """Map the application ``id`` field to ``_id`` recursively."""
    if not flt:
        return {}
    out: Filter = {}
    for key, value in flt.items():
        if key in ("$or", "$and"):
            out[key] = [_translate_filter(sub) for sub in value]
        elif key == "id":
            out["_id"] = value
        else:
            out[key] = value
    return out


class MongoRepository(Repository):
    def __init__(self, uri: str, db_name: str):
        self._uri = uri
        self._db_name = db_name
        self._client: Any = None
        self._db: Any = None

    async def initialize(self) -> None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise RuntimeError(
                "MongoDB backend selected but 'motor' is not installed. "
                "Install it with: pip install 'prompt-workbench[mongo]'"
            ) from exc
        self._client = AsyncIOMotorClient(self._uri, uuidRepresentation="standard")
        self._db = self._client[self._db_name]
        # Confirm connectivity early with a clear error if Mongo is unreachable.
        await self._db.command("ping")

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def db(self) -> Any:
        if self._db is None:
            raise RuntimeError("MongoRepository not initialized")
        return self._db

    async def insert_one(self, collection: str, doc: Document) -> Document:
        await self.db[collection].insert_one(_to_storage(doc))
        return doc

    async def find_one(self, collection: str, flt: Filter) -> Document | None:
        found = await self.db[collection].find_one(_translate_filter(flt))
        return _from_storage(found)

    async def find_many(
        self,
        collection: str,
        flt: Filter | None = None,
        sort: Sort | None = None,
        limit: int | None = None,
        skip: int = 0,
    ) -> list[Document]:
        cursor = self.db[collection].find(_translate_filter(flt))
        if sort:
            cursor = cursor.sort([("_id" if f == "id" else f, d) for f, d in sort])
        if skip:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
        return [d for d in (_from_storage(x) for x in await cursor.to_list(length=limit or 10_000)) if d is not None]

    async def count(self, collection: str, flt: Filter | None = None) -> int:
        return await self.db[collection].count_documents(_translate_filter(flt) or {})

    async def replace_one(
        self, collection: str, flt: Filter, doc: Document, *, upsert: bool = False
    ) -> Document | None:
        result = await self.db[collection].replace_one(
            _translate_filter(flt), _to_storage(doc), upsert=upsert
        )
        if result.matched_count == 0 and not (upsert and result.upserted_id is not None):
            return None
        return doc

    async def delete_one(self, collection: str, flt: Filter) -> bool:
        result = await self.db[collection].delete_one(_translate_filter(flt))
        return result.deleted_count > 0

    async def delete_many(self, collection: str, flt: Filter) -> int:
        result = await self.db[collection].delete_many(_translate_filter(flt))
        return result.deleted_count

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Repository]:
        # Multi-document transactions require a replica set. For single-node local
        # installs we rely on optimistic concurrency (edit_sequence guards) instead,
        # matching how the service layer enforces correctness on either backend.
        yield self
