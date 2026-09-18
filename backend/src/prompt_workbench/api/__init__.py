"""API package: aggregate router."""

from fastapi import APIRouter

from . import (
    auth_routes,
    capture_routes,
    core_routes,
    dataset_routes,
    prompt_routes,
    release_routes,
    run_routes,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_routes.router, tags=["auth"])
api_router.include_router(core_routes.router, tags=["projects"])
api_router.include_router(prompt_routes.router, tags=["prompts"])
api_router.include_router(dataset_routes.router, tags=["datasets"])
api_router.include_router(run_routes.router, tags=["runs"])
api_router.include_router(capture_routes.router, tags=["captures"])
api_router.include_router(release_routes.router, tags=["releases"])

__all__ = ["api_router"]
