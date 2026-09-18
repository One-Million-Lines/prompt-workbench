"""SQLite implementation of :class:`Repository`.

Each *collection* becomes a table ``(id TEXT PRIMARY KEY, doc JSON)``. Documents are
stored as canonical JSON text and queried with SQLite's ``json_extract`` so the same
MongoDB-style filters work unchanged. This backend needs no external services which
makes it ideal for the bundled demo and the test suite.
"""

from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from .base import Document, Filter, Repository, Sort

_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _json_path(field: str) -> str:
    # Convert dotted field to a JSON path expression argument.
    parts = field.split(".")
    return "$." + ".".join(parts)


class SqliteRepository(Repository):
    def __init__(self, path: str | Path):
        self._path = str(path)
        self._db: aiosqlite.Connection | None = None
        self._tables: set[str] = set()
        self._in_tx = False

    async def _commit(self) -> None:
        # Suppress intermediate commits while inside an explicit transaction so the
        # whole scope stays atomic.
        if not self._in_tx:
            await self.db.commit()

    async def initialize(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._db.execute("PRAGMA synchronous=FULL")
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("SqliteRepository not initialized")
        return self._db

    async def _ensure_table(self, collection: str) -> None:
        if not _SAFE_NAME.match(collection):
            raise ValueError(f"Unsafe collection name: {collection!r}")
        if collection in self._tables:
            return
        await self.db.execute(
            f'CREATE TABLE IF NOT EXISTS "{collection}" '
            f"(id TEXT PRIMARY KEY, doc TEXT NOT NULL)"
        )
        await self._commit()
        # Only cache as created when not inside a transaction: a rollback would
        # otherwise drop the table while the cache still claims it exists.
        if not self._in_tx:
            self._tables.add(collection)

    # --- query translation -------------------------------------------------
    def _translate(self, flt: Filter | None) -> tuple[str, list[Any]]:
        if not flt:
            return "1=1", []
        clauses: list[str] = []
        params: list[Any] = []
        for key, condition in flt.items():
            if key == "$or":
                subs = [self._translate(sub) for sub in condition]
                clauses.append("(" + " OR ".join(f"({c})" for c, _ in subs) + ")")
                for _, p in subs:
                    params.extend(p)
                continue
            if key == "$and":
                subs = [self._translate(sub) for sub in condition]
                clauses.append("(" + " AND ".join(f"({c})" for c, _ in subs) + ")")
                for _, p in subs:
                    params.extend(p)
                continue
            col = "json_extract(doc, ?)"
            path = _json_path(key)
            if isinstance(condition, dict) and condition:
                for op, operand in condition.items():
                    c, p = self._operator(col, path, op, operand)
                    clauses.append(c)
                    params.extend(p)
            else:
                clauses.append(f"{col} IS ?")
                params.extend([path, _encode_scalar(condition)])
        return " AND ".join(clauses) if clauses else "1=1", params

    def _operator(self, col: str, path: str, op: str, operand: Any) -> tuple[str, list[Any]]:
        if op in ("$eq",):
            return f"{col} IS ?", [path, _encode_scalar(operand)]
        if op == "$ne":
            return f"({col} IS NOT ? OR {col} IS NULL)", [path, _encode_scalar(operand), path]
        if op == "$gt":
            return f"{col} > ?", [path, _encode_scalar(operand)]
        if op == "$gte":
            return f"{col} >= ?", [path, _encode_scalar(operand)]
        if op == "$lt":
            return f"{col} < ?", [path, _encode_scalar(operand)]
        if op == "$lte":
            return f"{col} <= ?", [path, _encode_scalar(operand)]
        if op == "$in":
            values = list(operand) or [None]
            placeholders = ", ".join("?" for _ in values)
            params: list[Any] = [path] + [_encode_scalar(v) for v in values]
            return f"{col} IN ({placeholders})", params
        if op == "$nin":
            values = list(operand) or [None]
            placeholders = ", ".join("?" for _ in values)
            params = [path] + [_encode_scalar(v) for v in values]
            return f"({col} NOT IN ({placeholders}) OR {col} IS NULL)", params
        if op == "$exists":
            if operand:
                return f"{col} IS NOT NULL", [path]
            return f"{col} IS NULL", [path]
        if op == "$contains":
            return f"instr(coalesce({col}, ''), ?) > 0", [path, str(operand)]
        if op == "$regex":
            return f"{col} REGEXP ?", [path, operand]
        raise ValueError(f"Unsupported operator {op}")

    def _order_by(self, sort: Sort | None) -> str:
        if not sort:
            return ""
        parts = []
        for field, direction in sort:
            path = _json_path(field)
            escaped = path.replace("'", "''")
            parts.append(f"json_extract(doc, '{escaped}') {'DESC' if direction < 0 else 'ASC'}")
        return " ORDER BY " + ", ".join(parts)

    # --- CRUD --------------------------------------------------------------
    async def insert_one(self, collection: str, doc: Document) -> Document:
        await self._ensure_table(collection)
        doc_id = doc["id"]
        await self.db.execute(
            f'INSERT INTO "{collection}" (id, doc) VALUES (?, ?)',
            (doc_id, json.dumps(doc, ensure_ascii=False)),
        )
        await self._commit()
        return doc

    async def find_one(self, collection: str, flt: Filter) -> Document | None:
        rows = await self.find_many(collection, flt, limit=1)
        return rows[0] if rows else None

    async def find_many(
        self,
        collection: str,
        flt: Filter | None = None,
        sort: Sort | None = None,
        limit: int | None = None,
        skip: int = 0,
    ) -> list[Document]:
        await self._ensure_table(collection)
        where, params = self._translate(flt)
        sql = f'SELECT doc FROM "{collection}" WHERE {where}{self._order_by(sort)}'
        if limit is not None:
            sql += f" LIMIT {int(limit)} OFFSET {int(skip)}"
        elif skip:
            sql += f" LIMIT -1 OFFSET {int(skip)}"
        cursor = await self.db.execute(sql, params)
        rows = await cursor.fetchall()
        return [json.loads(r["doc"]) for r in rows]

    async def count(self, collection: str, flt: Filter | None = None) -> int:
        await self._ensure_table(collection)
        where, params = self._translate(flt)
        cursor = await self.db.execute(f'SELECT COUNT(*) AS n FROM "{collection}" WHERE {where}', params)
        row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    async def replace_one(
        self, collection: str, flt: Filter, doc: Document, *, upsert: bool = False
    ) -> Document | None:
        await self._ensure_table(collection)
        where, params = self._translate(flt)
        cursor = await self.db.execute(f'SELECT id FROM "{collection}" WHERE {where} LIMIT 1', params)
        row = await cursor.fetchone()
        if row is None:
            if upsert:
                return await self.insert_one(collection, doc)
            return None
        await self.db.execute(
            f'UPDATE "{collection}" SET doc = ? WHERE id = ?',
            (json.dumps(doc, ensure_ascii=False), row["id"]),
        )
        await self._commit()
        return doc

    async def delete_one(self, collection: str, flt: Filter) -> bool:
        await self._ensure_table(collection)
        where, params = self._translate(flt)
        cursor = await self.db.execute(f'SELECT id FROM "{collection}" WHERE {where} LIMIT 1', params)
        row = await cursor.fetchone()
        if row is None:
            return False
        await self.db.execute(f'DELETE FROM "{collection}" WHERE id = ?', (row["id"],))
        await self._commit()
        return True

    async def delete_many(self, collection: str, flt: Filter) -> int:
        await self._ensure_table(collection)
        where, params = self._translate(flt)
        cursor = await self.db.execute(f'DELETE FROM "{collection}" WHERE {where}', params)
        await self._commit()
        return cursor.rowcount

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Repository]:
        if self._in_tx:
            # Already inside a transaction: reuse the enclosing scope.
            yield self
            return
        await self.db.execute("BEGIN")
        self._in_tx = True
        try:
            yield self
        except Exception:
            self._in_tx = False
            await self.db.rollback()
            raise
        else:
            self._in_tx = False
            await self.db.commit()


def _encode_scalar(value: Any) -> Any:
    """Match how json_extract returns values: booleans become 1/0."""
    if isinstance(value, bool):
        return 1 if value else 0
    return value
