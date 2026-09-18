"""Run engine routes: preview, create, read progress, cancel, review, report."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services import AppContext, RunsService
from .deps import get_context, get_principal
from .schemas import ReviewCreate, RunRequest

router = APIRouter(dependencies=[Depends(get_principal)])


@router.post("/runs/preview")
async def preview_run(body: RunRequest, ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).preview(body.model_dump())


@router.post("/runs", status_code=202)
async def create_run(body: RunRequest, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).create_run(body.model_dump(), actor=principal, background=True)


@router.get("/runs")
async def list_runs(project_id: str, limit: int = 50, ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).list_runs(project_id, limit=limit)


@router.get("/runs/{run_id}")
async def get_run(run_id: str, ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).get_run(run_id)


@router.get("/runs/{run_id}/cells")
async def list_cells(run_id: str, ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).list_cells(run_id)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).cancel(run_id)


@router.post("/runs/{run_id}/cells/{cell_id}/reviews", status_code=201)
async def add_review(run_id: str, cell_id: str, body: ReviewCreate, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).add_review(run_id, cell_id, body.verdict, body.note, actor=principal)


@router.get("/runs/{run_id}/report")
async def report(run_id: str, ctx: AppContext = Depends(get_context)):
    return await RunsService(ctx).report(run_id)
