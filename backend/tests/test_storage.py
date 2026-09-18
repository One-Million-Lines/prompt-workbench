"""Storage abstraction behaviour on the SQLite backend."""

from __future__ import annotations

import pytest

from prompt_workbench.storage.sqlite import SqliteRepository


@pytest.mark.asyncio
async def test_crud_filters_sort_and_optimistic_replace(tmp_path):
    repo = SqliteRepository(tmp_path / "t.sqlite3")
    await repo.initialize()
    try:
        await repo.insert_one("items", {"id": "a", "group": "g1", "n": 1})
        await repo.insert_one("items", {"id": "b", "group": "g1", "n": 2})
        await repo.insert_one("items", {"id": "c", "group": "g2", "n": 3})

        desc = await repo.find_many("items", {"group": "g1"}, sort=[("n", -1)])
        assert [d["id"] for d in desc] == ["b", "a"]

        assert await repo.count("items", {"n": {"$gte": 2}}) == 2
        assert await repo.count("items", {"group": {"$in": ["g1", "g2"]}}) == 3

        # optimistic replace: only succeeds when the guard field matches
        ok = await repo.replace_one("items", {"id": "a", "n": 1}, {"id": "a", "group": "g1", "n": 9})
        assert ok is not None
        stale = await repo.replace_one("items", {"id": "a", "n": 1}, {"id": "a", "n": 99})
        assert stale is None
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_transaction_rollback(tmp_path):
    repo = SqliteRepository(tmp_path / "t.sqlite3")
    await repo.initialize()
    try:
        with pytest.raises(RuntimeError):
            async with repo.transaction():
                await repo.insert_one("x", {"id": "1"})
                raise RuntimeError("boom")
        assert await repo.find_one("x", {"id": "1"}) is None

        async with repo.transaction():
            await repo.insert_one("x", {"id": "2"})
        assert await repo.find_one("x", {"id": "2"}) is not None
    finally:
        await repo.close()
