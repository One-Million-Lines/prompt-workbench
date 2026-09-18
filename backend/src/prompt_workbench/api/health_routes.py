"""Health probes (no configuration disclosure)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services import AppContext
from .deps import get_context

router = APIRouter()


@router.get("/health/live")
async def live():
    return {"status": "live"}


@router.get("/health/ready")
async def ready(ctx: AppContext = Depends(get_context)):
    try:
        await ctx.repo.count("users")
        return {"status": "ready"}
    except Exception:  # noqa: BLE001
        return {"status": "not_ready"}
