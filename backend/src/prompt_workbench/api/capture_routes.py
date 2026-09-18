"""Capture intake and inbox routes with scoped-key enforcement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response

from ..services import AppContext, CapturesService
from .deps import get_context, get_principal, require_scopes
from .schemas import CapturePromote, CaptureReview, CaptureIngest

router = APIRouter()


@router.post("/captures")
async def ingest_capture(
    body: CaptureIngest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal=Depends(require_scopes("captures:write")),
    ctx: AppContext = Depends(get_context),
):
    capture, status = await CapturesService(ctx).ingest(body.model_dump(), idempotency_key, principal)
    response.status_code = status
    return {"id": capture["id"], "review_status": capture["review_status"], "status": "accepted"}


@router.get("/captures")
async def list_captures(
    project_id: str,
    review_status: str | None = None,
    limit: int = 50,
    principal=Depends(require_scopes("captures:read")),
    ctx: AppContext = Depends(get_context),
):
    return await CapturesService(ctx).list(project_id, review_status=review_status, limit=limit)


@router.get("/captures/{capture_id}")
async def get_capture(capture_id: str, principal=Depends(require_scopes("captures:read")), ctx: AppContext = Depends(get_context)):
    return await CapturesService(ctx).get(capture_id)


@router.patch("/captures/{capture_id}/review")
async def review_capture(capture_id: str, body: CaptureReview, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    return await CapturesService(ctx).set_review(capture_id, body.review_status)


@router.post("/captures/{capture_id}/promote", status_code=201)
async def promote_capture(capture_id: str, body: CapturePromote, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    return await CapturesService(ctx).promote(capture_id, body.dataset_id, name=body.name, expected=body.expected)


@router.delete("/captures/{capture_id}/payload")
async def delete_capture_payload(capture_id: str, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    return await CapturesService(ctx).delete_payload(capture_id)
