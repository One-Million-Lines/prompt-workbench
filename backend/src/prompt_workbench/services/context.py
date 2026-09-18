"""Application context wiring the repository, settings and provider registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import Settings
from ..domain.ids import new_uuid, utcnow
from ..providers import ProviderRegistry
from ..storage import Collections, Repository


@dataclass
class Principal:
    """The authenticated caller — a human (JWT) or an integration key."""

    kind: str  # "user" | "api_key"
    id: str
    username: str | None = None
    scopes: list[str] | None = None
    project_id: str | None = None  # api keys may be project-restricted

    def has_scope(self, scope: str) -> bool:
        if self.kind == "user":
            return True
        return bool(self.scopes and scope in self.scopes)


class AppContext:
    def __init__(self, settings: Settings, repo: Repository):
        self.settings = settings
        self.repo = repo
        self.providers = ProviderRegistry(settings)

    async def log_event(
        self,
        actor: Principal | None,
        action: str,
        resource_type: str,
        resource_id: str,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a non-sensitive change event (never full prompt/content/secrets)."""
        await self.repo.insert_one(
            Collections.CHANGE_EVENTS,
            {
                "id": new_uuid(),
                "actor_type": actor.kind if actor else "system",
                "actor_id": actor.id if actor else "system",
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "project_id": project_id,
                "metadata": metadata or {},
                "created_at": utcnow(),
            },
        )
