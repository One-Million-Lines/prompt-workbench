"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .api.health_routes import router as health_router
from .config import Settings, get_settings
from .domain.ids import new_uuid
from .services import AppContext, ServiceError
from .storage import build_repository

logger = logging.getLogger("prompt_workbench")

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo = build_repository(settings)
        await repo.initialize()
        app.state.context = AppContext(settings, repo)
        if settings.demo_mode:
            from .seed.demo_seed import ensure_demo_data

            await ensure_demo_data(app.state.context)
        try:
            yield
        finally:
            await repo.close()

    app = FastAPI(
        title="Prompt Workbench",
        version="1.0.0",
        description="Local, open-source prompt management, versioning, evaluation and publishing.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": exc.details,
                    "request_id": new_uuid(),
                    "retryable": exc.retryable,
                }
            },
        )

    app.include_router(api_router)
    app.include_router(health_router)  # also exposed unprefixed for probes

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the bundled React build when present (single-origin deployment)."""
    if not STATIC_DIR.exists():
        return
    assets = STATIC_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index_file = STATIC_DIR / "index.html"

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Not found"}})
