"""Capture intake (production example ingestion) and the capture inbox."""

from __future__ import annotations

from typing import Any

from ..domain import content_digest, new_uuid, utcnow
from ..storage import Collections
from .context import AppContext, Principal
from .errors import ConflictError, NotFoundError, ValidationError

REDACTION_VERSION = 1
FORBIDDEN_KEYS = {"authorization", "api_key", "access_token", "refresh_token", "cookie", "password"}


class CapturesService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    async def ingest(self, payload: dict, idempotency_key: str | None, principal: Principal) -> tuple[dict, int]:
        project_id = payload.get("project_id")
        if not project_id:
            raise ValidationError("project_id is required", code="missing_project")
        source = payload.get("source", "unknown")
        mode = payload.get("mode", "rendered")
        if mode not in ("structured", "rendered"):
            raise ValidationError("mode must be 'structured' or 'rendered'", code="invalid_mode")

        normalized = _redact(dict(payload))
        digest = content_digest(normalized)
        key = idempotency_key or payload.get("external_event_id") or digest

        existing = await self.repo.find_one(
            Collections.CAPTURES, {"project_id": project_id, "source": source, "idempotency_key": key}
        )
        if existing:
            if existing["payload_digest"] == digest:
                return existing, 200
            raise ConflictError("Idempotency key reused with a different payload", code="idempotency_conflict")

        capture = {
            "id": new_uuid(),
            "project_id": project_id,
            "source": source,
            "mode": mode,
            "idempotency_key": key,
            "external_event_id": payload.get("external_event_id"),
            "payload_digest": digest,
            "normalized_payload": normalized,
            "prompt_ref": payload.get("prompt_ref"),
            "inputs": normalized.get("inputs"),
            "rendered_messages": normalized.get("rendered_messages"),
            "output": normalized.get("output"),
            "model": normalized.get("model"),
            "usage": normalized.get("usage"),
            "metadata": normalized.get("metadata", {}),
            "tags": normalized.get("tags", []),
            "redaction_version": REDACTION_VERSION,
            "review_status": "new",
            "reference_status": "resolved" if (payload.get("prompt_ref") or {}).get("prompt_id") else "unresolved",
            "occurred_at": payload.get("occurred_at", utcnow()),
            "payload_deleted_at": None,
            "created_at": utcnow(),
        }
        await self.repo.insert_one(Collections.CAPTURES, capture)
        return capture, 201

    async def list(self, project_id: str, *, review_status: str | None = None, limit: int = 50) -> list[dict]:
        flt: dict[str, Any] = {"project_id": project_id}
        if review_status:
            flt["review_status"] = review_status
        return await self.repo.find_many(Collections.CAPTURES, flt, sort=[("occurred_at", -1)], limit=limit)

    async def get(self, capture_id: str) -> dict:
        capture = await self.repo.find_one(Collections.CAPTURES, {"id": capture_id})
        if not capture:
            raise NotFoundError(f"Capture {capture_id} not found")
        return capture

    async def set_review(self, capture_id: str, review_status: str) -> dict:
        if review_status not in ("new", "reviewed", "promoted", "ignored"):
            raise ValidationError("Invalid review status", code="invalid_status")
        capture = await self.get(capture_id)
        capture["review_status"] = review_status
        await self.repo.replace_one(Collections.CAPTURES, {"id": capture_id}, capture)
        return capture

    async def promote(self, capture_id: str, dataset_id: str, *, name: str | None = None, expected: Any = None) -> dict:
        from .datasets_service import DatasetsService

        capture = await self.get(capture_id)
        inputs = capture.get("inputs")
        if inputs is None:
            raise ValidationError("This capture has no structured inputs to promote; map variables first", code="no_inputs")
        datasets = DatasetsService(self.ctx)
        case = await datasets.add_case(
            dataset_id,
            name=name or f"from-capture-{capture_id[:8]}",
            inputs=inputs,
            expected=expected,  # captured answer is never silently used as ground truth
            source_capture_id=capture_id,
        )
        capture["review_status"] = "promoted"
        await self.repo.replace_one(Collections.CAPTURES, {"id": capture_id}, capture)
        return case

    async def delete_payload(self, capture_id: str) -> dict:
        capture = await self.get(capture_id)
        for field in ("normalized_payload", "inputs", "rendered_messages", "output"):
            capture[field] = None
        capture["payload_deleted_at"] = utcnow()
        await self.repo.replace_one(Collections.CAPTURES, {"id": capture_id}, capture)
        return capture


def _redact(payload: dict) -> dict:
    """Defense-in-depth redaction of forbidden secret-like keys anywhere in the payload."""

    def scrub(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: ("[redacted]" if k.lower() in FORBIDDEN_KEYS else scrub(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [scrub(v) for v in node]
        return node

    return scrub(payload)
