"""Prompt registry: drafts, immutable revisions, labels, rendering, comments.

Implements the identity/revision semantics from specification section 5: one shared
mutable draft guarded by ``edit_sequence`` (stale writes → 409), immutable numbered
revisions addressed by a semantic SHA-256 digest, and labels that point at exact
revisions with optimistic previous-revision guards.
"""

from __future__ import annotations

import difflib
from typing import Any

from ..domain import (
    SchemaValidationError,
    new_uuid,
    normalize_prompt_content,
    render_prompt,
    semantic_prompt_digest,
    utcnow,
    validate_schema_document,
)
from ..domain.rendering import TemplateError
from ..storage import Collections
from .context import AppContext, Principal
from .errors import ConflictError, NotFoundError, ValidationError

VALID_LABELS = {"development", "staging", "production"}

_EMPTY_CONTENT = {
    "format_version": 1,
    "kind": "chat",
    "template_engine": "simple-v1",
    "messages": [{"role": "system", "content": ""}, {"role": "user", "content": ""}],
    "text": None,
    "input_schema": {"type": "object", "properties": {}, "required": []},
    "output": {"mode": "text", "schema": None},
    "tools": [],
    "tool_choice": "auto",
    "default_model": None,
}


class PromptsService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    # --- registry metadata -------------------------------------------------
    async def list_prompts(self, project_id: str, *, include_archived: bool = False, is_snippet: bool | None = None) -> list[dict]:
        flt: dict[str, Any] = {"project_id": project_id}
        if not include_archived:
            flt["archived_at"] = None
        if is_snippet is not None:
            flt["is_snippet"] = is_snippet
        return await self.repo.find_many(Collections.PROMPTS, flt, sort=[("created_at", 1)])

    async def get(self, prompt_id: str) -> dict:
        prompt = await self.repo.find_one(Collections.PROMPTS, {"id": prompt_id})
        if not prompt:
            raise NotFoundError(f"Prompt {prompt_id} not found")
        return prompt

    async def create(
        self,
        project_id: str,
        name: str,
        slug: str,
        *,
        description: str = "",
        tags: list[str] | None = None,
        is_snippet: bool = False,
        content: dict | None = None,
        actor: Principal | None = None,
    ) -> dict:
        from ..domain.ids import is_valid_slug

        if not is_valid_slug(slug):
            raise ValidationError(f"Invalid slug {slug!r}", code="invalid_slug")
        if await self.repo.find_one(Collections.PROMPTS, {"project_id": project_id, "slug": slug}):
            raise ConflictError(f"Prompt slug {slug!r} already exists in project", code="slug_exists")
        prompt = {
            "id": new_uuid(),
            "project_id": project_id,
            "slug": slug,
            "name": name,
            "description": description,
            "tags": tags or [],
            "is_snippet": is_snippet,
            "archived_at": None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.PROMPTS, prompt)
        draft = {
            "id": prompt["id"],
            "prompt_id": prompt["id"],
            "content": normalize_prompt_content(content or _EMPTY_CONTENT),
            "base_revision_id": None,
            "edit_sequence": 0,
            "updated_by": actor.id if actor else None,
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.PROMPT_DRAFTS, draft)
        await self.ctx.log_event(actor, "prompt.create", "prompt", prompt["id"], project_id, {"slug": slug})
        return prompt

    async def archive(self, prompt_id: str, archived: bool, actor: Principal | None = None) -> dict:
        prompt = await self.get(prompt_id)
        prompt["archived_at"] = utcnow() if archived else None
        prompt["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.PROMPTS, {"id": prompt_id}, prompt)
        return prompt

    # --- draft -------------------------------------------------------------
    async def get_draft(self, prompt_id: str) -> dict:
        draft = await self.repo.find_one(Collections.PROMPT_DRAFTS, {"prompt_id": prompt_id})
        if not draft:
            raise NotFoundError(f"Draft for prompt {prompt_id} not found")
        return draft

    async def update_draft(self, prompt_id: str, content: dict, expected_edit_sequence: int, actor: Principal | None = None) -> dict:
        draft = await self.get_draft(prompt_id)
        current = int(draft.get("edit_sequence", 0))
        if current != expected_edit_sequence:
            raise ConflictError(
                "Draft has been modified since you loaded it",
                code="stale_draft",
                details={"current_edit_sequence": current, "your_edit_sequence": expected_edit_sequence},
            )
        try:
            normalized = normalize_prompt_content(content)
            _validate_content(normalized)
        except SchemaValidationError as exc:
            raise ValidationError("Invalid input schema", code="invalid_schema", details={"errors": exc.errors}) from exc
        draft["content"] = normalized
        draft["edit_sequence"] = current + 1
        draft["updated_by"] = actor.id if actor else None
        draft["updated_at"] = utcnow()
        updated = await self.repo.replace_one(
            Collections.PROMPT_DRAFTS, {"prompt_id": prompt_id, "edit_sequence": current}, draft
        )
        if updated is None:
            raise ConflictError("Draft has been modified concurrently", code="stale_draft")
        return draft

    # --- revisions ---------------------------------------------------------
    async def list_revisions(self, prompt_id: str) -> list[dict]:
        return await self.repo.find_many(Collections.PROMPT_REVISIONS, {"prompt_id": prompt_id}, sort=[("version", -1)])

    async def get_revision(self, prompt_id: str, version: int) -> dict:
        revision = await self.repo.find_one(Collections.PROMPT_REVISIONS, {"prompt_id": prompt_id, "version": version})
        if not revision:
            raise NotFoundError(f"Revision {version} of prompt {prompt_id} not found")
        return revision

    async def latest_revision(self, prompt_id: str) -> dict | None:
        revisions = await self.repo.find_many(Collections.PROMPT_REVISIONS, {"prompt_id": prompt_id}, sort=[("version", -1)], limit=1)
        return revisions[0] if revisions else None

    async def save_revision(self, prompt_id: str, note: str, expected_edit_sequence: int | None = None, actor: Principal | None = None) -> dict:
        prompt = await self.get(prompt_id)
        draft = await self.get_draft(prompt_id)
        if expected_edit_sequence is not None and int(draft.get("edit_sequence", 0)) != expected_edit_sequence:
            raise ConflictError(
                "Draft changed before saving",
                code="stale_draft",
                details={"current_edit_sequence": int(draft.get("edit_sequence", 0))},
            )
        if not note or not note.strip():
            raise ValidationError("A non-empty change note is required to save a version", code="missing_note")

        content = draft["content"]
        _validate_content(content)
        digest = semantic_prompt_digest(content)
        latest = await self.latest_revision(prompt_id)
        if latest and latest.get("semantic_sha256") == digest:
            return {**latest, "unchanged": True}

        version = (latest["version"] + 1) if latest else 1
        revision = {
            "id": new_uuid(),
            "prompt_id": prompt_id,
            "project_id": prompt["project_id"],
            "version": version,
            "content": content,
            "semantic_sha256": digest,
            "note": note.strip(),
            "created_by": actor.id if actor else None,
            "created_at": utcnow(),
        }
        async with self.repo.transaction():
            await self.repo.insert_one(Collections.PROMPT_REVISIONS, revision)
            draft["base_revision_id"] = revision["id"]
            await self.repo.replace_one(Collections.PROMPT_DRAFTS, {"prompt_id": prompt_id}, draft)
        await self.ctx.log_event(actor, "prompt.save_revision", "prompt", prompt_id, prompt["project_id"], {"version": version, "digest": digest})
        return {**revision, "unchanged": False}

    async def restore_draft(self, prompt_id: str, version: int, expected_edit_sequence: int, actor: Principal | None = None) -> dict:
        revision = await self.get_revision(prompt_id, version)
        draft = await self.get_draft(prompt_id)
        if int(draft.get("edit_sequence", 0)) != expected_edit_sequence:
            raise ConflictError("Draft changed before restore", code="stale_draft")
        draft["content"] = revision["content"]
        draft["edit_sequence"] = int(draft.get("edit_sequence", 0)) + 1
        draft["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.PROMPT_DRAFTS, {"prompt_id": prompt_id}, draft)
        return draft

    # --- labels ------------------------------------------------------------
    async def get_labels(self, prompt_id: str) -> list[dict]:
        return await self.repo.find_many(Collections.PROMPT_LABELS, {"prompt_id": prompt_id})

    async def get_label(self, prompt_id: str, label: str) -> dict | None:
        return await self.repo.find_one(Collections.PROMPT_LABELS, {"prompt_id": prompt_id, "label": label})

    async def set_label(self, prompt_id: str, label: str, version: int, expected_previous_revision_id: str | None, actor: Principal | None = None) -> dict:
        if label not in VALID_LABELS:
            raise ValidationError(f"Unknown label {label!r}; allowed: {sorted(VALID_LABELS)}", code="invalid_label")
        prompt = await self.get(prompt_id)
        revision = await self.get_revision(prompt_id, version)  # ensures ownership
        existing = await self.get_label(prompt_id, label)
        current_revision_id = existing["revision_id"] if existing else None
        if current_revision_id != expected_previous_revision_id:
            raise ConflictError(
                "Label was moved since you last read it",
                code="stale_label",
                details={"current_revision_id": current_revision_id},
            )
        if existing:
            existing["revision_id"] = revision["id"]
            existing["version"] = version
            existing["edit_sequence"] = int(existing.get("edit_sequence", 0)) + 1
            existing["updated_at"] = utcnow()
            await self.repo.replace_one(Collections.PROMPT_LABELS, {"id": existing["id"]}, existing)
            record = existing
        else:
            record = {
                "id": new_uuid(),
                "prompt_id": prompt_id,
                "label": label,
                "revision_id": revision["id"],
                "version": version,
                "edit_sequence": 0,
                "updated_at": utcnow(),
            }
            await self.repo.insert_one(Collections.PROMPT_LABELS, record)
        await self.ctx.log_event(actor, "prompt.set_label", "prompt", prompt_id, prompt["project_id"], {"label": label, "version": version})
        return record

    # --- resolution + rendering -------------------------------------------
    async def resolve_content(self, prompt_id: str, selector: dict[str, Any]) -> tuple[dict, dict]:
        """Resolve a selector to (content, provenance). Selector is exactly one of
        ``{"revision": N}``, ``{"label": "production"}`` or ``{"draft": {...content}}``."""
        if "draft" in selector and selector["draft"] is not None:
            content = normalize_prompt_content(selector["draft"])
            return content, {"source": "draft_snapshot", "digest": semantic_prompt_digest(content)}
        if "revision" in selector and selector["revision"] is not None:
            revision = await self.get_revision(prompt_id, int(selector["revision"]))
            return revision["content"], {"source": "revision", "revision_id": revision["id"], "version": revision["version"], "digest": revision["semantic_sha256"]}
        if "label" in selector and selector["label"] is not None:
            label = await self.get_label(prompt_id, selector["label"])
            if not label:
                raise NotFoundError(f"Label {selector['label']!r} is not set on this prompt")
            revision = await self.get_revision(prompt_id, label["version"])
            return revision["content"], {"source": "label", "label": selector["label"], "revision_id": revision["id"], "version": revision["version"], "digest": revision["semantic_sha256"]}
        raise ValidationError("A selector (revision, label or draft) is required", code="missing_selector")

    async def render(self, prompt_id: str, selector: dict[str, Any], inputs: dict[str, Any]) -> dict:
        content, provenance = await self.resolve_content(prompt_id, selector)
        try:
            result = render_prompt(content, inputs)
        except TemplateError as exc:
            raise ValidationError(str(exc), code=exc.code, details=exc.details) from exc
        return {
            "messages": [{"role": m.role, "content": m.content} for m in result.messages],
            "normalized_inputs": result.normalized_inputs,
            "output": content.get("output"),
            "tools": content.get("tools", []),
            "provenance": provenance,
        }

    # --- diff --------------------------------------------------------------
    async def diff(self, prompt_id: str, from_version: int, to_version: int) -> dict:
        a = await self.get_revision(prompt_id, from_version)
        b = await self.get_revision(prompt_id, to_version)
        text_a = _content_as_text(a["content"])
        text_b = _content_as_text(b["content"])
        diff = list(difflib.unified_diff(text_a.splitlines(), text_b.splitlines(), fromfile=f"v{from_version}", tofile=f"v{to_version}", lineterm=""))
        return {
            "from": from_version,
            "to": to_version,
            "text_diff": "\n".join(diff),
            "semantic_changed": a["semantic_sha256"] != b["semantic_sha256"],
        }

    # --- comments ----------------------------------------------------------
    async def add_comment(self, prompt_id: str, version: int, body: str, actor: Principal) -> dict:
        revision = await self.get_revision(prompt_id, version)
        if len(body) > 4000:
            raise ValidationError("Comment body exceeds 4000 characters", code="comment_too_long")
        comment = {
            "id": new_uuid(),
            "resource_kind": "prompt",
            "revision_id": revision["id"],
            "prompt_id": prompt_id,
            "version": version,
            "author_id": actor.id,
            "author_username": actor.username,
            "body": body,
            "created_at": utcnow(),
            "updated_at": utcnow(),
            "deleted_at": None,
        }
        await self.repo.insert_one(Collections.REVISION_COMMENTS, comment)
        return comment

    async def list_comments(self, prompt_id: str, version: int) -> list[dict]:
        revision = await self.get_revision(prompt_id, version)
        rows = await self.repo.find_many(
            Collections.REVISION_COMMENTS, {"revision_id": revision["id"], "deleted_at": None}, sort=[("created_at", 1)]
        )
        return rows

    async def delete_comment(self, comment_id: str, actor: Principal) -> None:
        comment = await self.repo.find_one(Collections.REVISION_COMMENTS, {"id": comment_id})
        if not comment or comment.get("deleted_at"):
            raise NotFoundError("Comment not found")
        if comment["author_id"] != actor.id:
            from .errors import ForbiddenError

            raise ForbiddenError("Only the author may delete this comment")
        comment["deleted_at"] = utcnow()
        await self.repo.replace_one(Collections.REVISION_COMMENTS, {"id": comment_id}, comment)


def _validate_content(content: dict) -> None:
    input_schema = content.get("input_schema") or {"type": "object", "properties": {}}
    validate_schema_document(input_schema)
    output = content.get("output") or {}
    if output.get("schema"):
        validate_schema_document(output["schema"])
    if content.get("tools") and output.get("mode") == "native_json_schema":
        raise ValidationError("Function tools cannot be combined with native_json_schema output", code="tools_native_conflict")


def _content_as_text(content: dict) -> str:
    lines = [f"kind: {content.get('kind')}", f"output_mode: {content.get('output', {}).get('mode')}"]
    for message in content.get("messages", []):
        lines.append(f"[{message.get('role')}]")
        lines.extend(message.get("content", "").splitlines())
    if content.get("text"):
        lines.extend(content["text"].splitlines())
    return "\n".join(lines)
