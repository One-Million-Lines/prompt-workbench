"""Prompt registry routes: metadata, drafts, revisions, labels, render, comments."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services import AnalyticsService, AppContext, PromptsService
from .deps import get_context, get_principal, require_scopes
from .schemas import (
    CommentCreate,
    DraftUpdate,
    LabelUpdate,
    PromptCreate,
    RenderRequest,
    RestoreDraft,
    SaveRevision,
)

router = APIRouter(dependencies=[Depends(require_scopes("registry:read"))])


@router.get("/prompts")
async def list_prompts(project_id: str, include_archived: bool = False, is_snippet: bool | None = None, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).list_prompts(project_id, include_archived=include_archived, is_snippet=is_snippet)


@router.post("/prompts", status_code=201)
async def create_prompt(body: PromptCreate, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).create(
        body.project_id,
        body.name,
        body.slug,
        description=body.description,
        tags=body.tags,
        is_snippet=body.is_snippet,
        content=body.content,
        actor=principal,
    )


@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).get(prompt_id)


@router.patch("/prompts/{prompt_id}/archive")
async def archive_prompt(prompt_id: str, archived: bool = True, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).archive(prompt_id, archived, actor=principal)


@router.get("/prompts/{prompt_id}/draft")
async def get_draft(prompt_id: str, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).get_draft(prompt_id)


@router.put("/prompts/{prompt_id}/draft")
async def update_draft(prompt_id: str, body: DraftUpdate, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).update_draft(prompt_id, body.content, body.expected_edit_sequence, actor=principal)


@router.get("/prompts/{prompt_id}/revisions")
async def list_revisions(prompt_id: str, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).list_revisions(prompt_id)


@router.post("/prompts/{prompt_id}/revisions", status_code=201)
async def save_revision(prompt_id: str, body: SaveRevision, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).save_revision(prompt_id, body.note, body.expected_edit_sequence, actor=principal)


@router.get("/prompts/{prompt_id}/revisions/{version}")
async def get_revision(prompt_id: str, version: int, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).get_revision(prompt_id, version)


@router.post("/prompts/{prompt_id}/restore-draft")
async def restore_draft(prompt_id: str, body: RestoreDraft, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).restore_draft(prompt_id, body.version, body.expected_edit_sequence, actor=principal)


@router.get("/prompts/{prompt_id}/labels")
async def get_labels(prompt_id: str, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).get_labels(prompt_id)


@router.put("/prompts/{prompt_id}/labels/{label}")
async def set_label(prompt_id: str, label: str, body: LabelUpdate, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).set_label(prompt_id, label, body.version, body.expected_previous_revision_id, actor=principal)


@router.post("/prompts/{prompt_id}/render")
async def render_prompt_route(prompt_id: str, body: RenderRequest, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).render(prompt_id, body.selector, body.inputs)


@router.get("/prompts/{prompt_id}/diff")
async def diff(prompt_id: str, from_version: int, to_version: int, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).diff(prompt_id, from_version, to_version)


@router.get("/prompts/{prompt_id}/revisions/{version}/comments")
async def list_comments(prompt_id: str, version: int, ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).list_comments(prompt_id, version)


@router.post("/prompts/{prompt_id}/revisions/{version}/comments", status_code=201)
async def add_comment(prompt_id: str, version: int, body: CommentCreate, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    return await PromptsService(ctx).add_comment(prompt_id, version, body.body, actor=principal)


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: str, principal=Depends(require_scopes("registry:write")), ctx: AppContext = Depends(get_context)):
    await PromptsService(ctx).delete_comment(comment_id, actor=principal)
    return None


@router.get("/prompts/{prompt_id}/analytics")
async def prompt_analytics(prompt_id: str, ctx: AppContext = Depends(get_context)):
    return await AnalyticsService(ctx).prompt_analytics(prompt_id)
