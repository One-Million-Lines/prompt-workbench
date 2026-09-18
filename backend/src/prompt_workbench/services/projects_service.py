"""Projects, connections and model profiles."""

from __future__ import annotations

from typing import Any

from ..domain.ids import new_uuid, slugify, utcnow
from ..storage import Collections
from .context import AppContext, Principal
from .errors import ConflictError, NotFoundError, ValidationError

DEFAULT_PROJECT_SETTINGS = {
    "gates": {"min_pass_rate": 0.95, "max_regression_percentage_points": 0, "require_all_critical": True},
    "retention": {"capture_days": 30, "run_payload_days": 90},
    "allow_publish_unevaluated": True,
    "capture_content_enabled": True,
}


class ProjectsService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    async def list_projects(self) -> list[dict]:
        return await self.repo.find_many(Collections.PROJECTS, sort=[("created_at", 1)])

    async def get(self, project_id: str) -> dict:
        project = await self.repo.find_one(Collections.PROJECTS, {"id": project_id})
        if not project:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def create(self, name: str, slug: str | None = None, settings: dict | None = None) -> dict:
        slug = slug or slugify(name)
        if await self.repo.find_one(Collections.PROJECTS, {"slug": slug}):
            raise ConflictError(f"Project slug {slug!r} already exists", code="slug_exists")
        project = {
            "id": new_uuid(),
            "slug": slug,
            "name": name,
            "settings": {**DEFAULT_PROJECT_SETTINGS, **(settings or {})},
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.PROJECTS, project)
        return project

    async def update_settings(self, project_id: str, settings: dict) -> dict:
        project = await self.get(project_id)
        project["settings"] = {**project.get("settings", {}), **settings}
        project["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.PROJECTS, {"id": project_id}, project)
        return project


class ConnectionsService:
    """Provider connections. Secrets are referenced by env var name, never stored."""

    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    async def list(self) -> list[dict]:
        rows = await self.repo.find_many(Collections.CONNECTIONS, sort=[("created_at", 1)])
        return [_public_connection(r) for r in rows]

    async def create(self, alias: str, provider: str, **fields: Any) -> dict:
        if await self.repo.find_one(Collections.CONNECTIONS, {"alias": alias}):
            raise ConflictError(f"Connection alias {alias!r} already exists", code="alias_exists")
        if "secret_value" in fields:
            raise ValidationError("Provide secret_env_name (an env var name), never a secret value", code="secret_inline")
        connection = {
            "id": new_uuid(),
            "alias": alias,
            "provider": provider,
            "api_base": fields.get("api_base"),
            "api_version": fields.get("api_version"),
            "secret_env_name": fields.get("secret_env_name"),
            "enabled": fields.get("enabled", True),
            "network_policy": fields.get("network_policy", {"allow_private": provider == "ollama"}),
            "edit_sequence": 0,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.CONNECTIONS, connection)
        return _public_connection(connection)

    async def get_raw(self, connection_id: str) -> dict:
        connection = await self.repo.find_one(Collections.CONNECTIONS, {"id": connection_id})
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")
        return connection


class ModelProfilesService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    async def list(self, project_id: str | None = None) -> list[dict]:
        flt = {"archived_at": None}
        if project_id:
            flt["project_id"] = project_id
        return await self.repo.find_many(Collections.MODEL_PROFILES, flt, sort=[("created_at", 1)])

    async def get(self, profile_id: str) -> dict:
        profile = await self.repo.find_one(Collections.MODEL_PROFILES, {"id": profile_id})
        if not profile:
            raise NotFoundError(f"Model profile {profile_id} not found")
        return profile

    async def create(self, project_id: str, name: str, provider: str, model: str, **fields: Any) -> dict:
        profile = {
            "id": new_uuid(),
            "project_id": project_id,
            "name": name,
            "provider": provider,
            "model": model,
            "connection_alias": fields.get("connection_alias"),
            "connection_id": fields.get("connection_id"),
            "parameters": fields.get("parameters", {}),
            "timeout_seconds": fields.get("timeout_seconds", 120),
            "retry_policy": fields.get("retry_policy", {"max_retries": 1}),
            "edit_sequence": 0,
            "archived_at": None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.MODEL_PROFILES, profile)
        return profile

    async def snapshot(self, profile_id: str) -> dict:
        """Non-secret portable profile snapshot embedded in runs/releases."""
        profile = await self.get(profile_id)
        return {
            "profile_id": profile["id"],
            "name": profile["name"],
            "provider": profile["provider"],
            "model": profile["model"],
            "connection_alias": profile.get("connection_alias"),
            "parameters": profile.get("parameters", {}),
            "timeout_seconds": profile.get("timeout_seconds", 120),
            "retry_policy": profile.get("retry_policy", {"max_retries": 1}),
        }


def _public_connection(connection: dict) -> dict:
    """Never expose secrets; only whether a secret env var is configured."""
    return {
        "id": connection["id"],
        "alias": connection["alias"],
        "provider": connection["provider"],
        "api_base": connection.get("api_base"),
        "api_version": connection.get("api_version"),
        "secret_configured": bool(connection.get("secret_env_name")),
        "enabled": connection.get("enabled", True),
        "created_at": connection.get("created_at"),
    }
