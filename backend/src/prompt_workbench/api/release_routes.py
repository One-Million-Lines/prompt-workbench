"""Release build/list/download and change-event history routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..services import AppContext, ReleasesService
from ..storage import Collections
from .deps import get_context, get_principal
from .schemas import ReleaseBuild

router = APIRouter(dependencies=[Depends(get_principal)])


@router.post("/releases", status_code=201)
async def build_release(body: ReleaseBuild, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    return await ReleasesService(ctx).build(body.project_id, body.name, body.selection, actor=principal)


@router.get("/releases")
async def list_releases(project_id: str, ctx: AppContext = Depends(get_context)):
    return await ReleasesService(ctx).list(project_id)


@router.get("/releases/{release_id}")
async def get_release(release_id: str, ctx: AppContext = Depends(get_context)):
    from ..services.releases_service import _public_release

    return _public_release(await ReleasesService(ctx).get(release_id))


@router.get("/releases/{release_id}/download")
async def download_release(release_id: str, ctx: AppContext = Depends(get_context)):
    path = await ReleasesService(ctx).artifact_path(release_id)
    return FileResponse(path, media_type="application/zip", filename=f"{release_id}.zip")


@router.get("/change-events")
async def change_events(project_id: str | None = None, limit: int = 50, ctx: AppContext = Depends(get_context)):
    flt = {"project_id": project_id} if project_id else None
    return await ctx.repo.find_many(Collections.CHANGE_EVENTS, flt, sort=[("created_at", -1)], limit=limit)
