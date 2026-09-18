"""Shared test fixtures."""

from __future__ import annotations

import tempfile

import pytest
import pytest_asyncio

from prompt_workbench.config import Settings
from prompt_workbench.services import AppContext
from prompt_workbench.storage import build_repository


@pytest_asyncio.fixture
async def ctx():
    with tempfile.TemporaryDirectory() as d:
        settings = Settings(data_dir=d, storage_backend="sqlite", demo_mode=True, provider_mode="mock")
        repo = build_repository(settings)
        await repo.initialize()
        context = AppContext(settings, repo)
        try:
            yield context
        finally:
            await repo.close()


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=str(tmp_path), storage_backend="sqlite", demo_mode=True, provider_mode="mock")
