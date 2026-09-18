"""Authentication and local user accounts."""

from __future__ import annotations

from ..config import Settings
from ..domain.ids import new_uuid, utcnow
from ..security import (
    decode_access_token,
    hash_password,
    issue_access_token,
    verify_api_key_secret,
    verify_password,
)
from ..security.jwt import TokenError
from ..storage import Collections, Repository
from .context import AppContext, Principal
from .errors import AuthError, ConflictError, ForbiddenError, NotFoundError


class AuthService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo: Repository = ctx.repo
        self.settings: Settings = ctx.settings

    # --- user management ---------------------------------------------------
    async def create_user(self, username: str, password: str) -> dict:
        username = username.strip().lower()
        if not username or len(password) < 6:
            raise ConflictError("Username required and password must be at least 6 characters", code="invalid_account")
        existing = await self.repo.find_one(Collections.USERS, {"username": username})
        if existing:
            raise ConflictError(f"User {username!r} already exists", code="user_exists")
        user = {
            "id": new_uuid(),
            "username": username,
            "password_hash": hash_password(password),
            "token_version": 0,
            "disabled_at": None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.USERS, user)
        return _public_user(user)

    async def set_password(self, username: str, password: str) -> None:
        user = await self.repo.find_one(Collections.USERS, {"username": username.strip().lower()})
        if not user:
            raise NotFoundError(f"User {username!r} not found")
        user["password_hash"] = hash_password(password)
        user["token_version"] = int(user.get("token_version", 0)) + 1
        user["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.USERS, {"id": user["id"]}, user)

    async def disable_user(self, username: str) -> None:
        user = await self.repo.find_one(Collections.USERS, {"username": username.strip().lower()})
        if not user:
            raise NotFoundError(f"User {username!r} not found")
        user["disabled_at"] = utcnow()
        user["token_version"] = int(user.get("token_version", 0)) + 1
        user["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.USERS, {"id": user["id"]}, user)

    async def count_users(self) -> int:
        return await self.repo.count(Collections.USERS)

    # --- login/logout ------------------------------------------------------
    async def login(self, username: str, password: str) -> dict:
        user = await self.repo.find_one(Collections.USERS, {"username": username.strip().lower()})
        # Constant-ish behaviour: always verify against a hash to reduce user enumeration.
        password_hash = user["password_hash"] if user else "$argon2id$v=19$m=65536,t=3,p=4$0000000000000000$0000000000000000000000000000000000000000000"
        valid = verify_password(password_hash, password)
        if not user or not valid or user.get("disabled_at"):
            raise AuthError("Invalid username or password")
        token, ttl = issue_access_token(self.settings, user["id"], int(user.get("token_version", 0)))
        return {"access_token": token, "token_type": "bearer", "expires_in": ttl}

    async def logout(self, user_id: str) -> None:
        user = await self.repo.find_one(Collections.USERS, {"id": user_id})
        if not user:
            return
        user["token_version"] = int(user.get("token_version", 0)) + 1
        user["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.USERS, {"id": user_id}, user)

    # --- principal resolution ---------------------------------------------
    async def principal_from_token(self, token: str) -> Principal:
        try:
            claims = decode_access_token(self.settings, token)
        except TokenError as exc:
            raise AuthError(f"Invalid token: {exc}") from exc
        user = await self.repo.find_one(Collections.USERS, {"id": claims.sub})
        if not user or user.get("disabled_at"):
            raise AuthError("Account is not active")
        if int(user.get("token_version", 0)) != claims.token_version:
            raise AuthError("Token has been invalidated")
        return Principal(kind="user", id=user["id"], username=user["username"])

    async def principal_from_api_key(self, raw_key: str) -> Principal:
        if "." not in raw_key:
            raise AuthError("Malformed API key")
        prefix, secret = raw_key.split(".", 1)
        record = await self.repo.find_one(Collections.API_KEYS, {"key_prefix": prefix})
        if not record or record.get("revoked_at"):
            raise AuthError("Invalid API key")
        if record.get("expires_at") and record["expires_at"] < utcnow():
            raise AuthError("API key expired")
        if not verify_api_key_secret(secret, record["secret_hash"]):
            raise AuthError("Invalid API key")
        return Principal(
            kind="api_key",
            id=record["id"],
            scopes=record.get("scopes", []),
            project_id=record.get("project_id"),
        )

    async def require_scope(self, principal: Principal, scope: str) -> None:
        if not principal.has_scope(scope):
            raise ForbiddenError(f"This credential lacks the required scope: {scope}")


def _public_user(user: dict) -> dict:
    return {"id": user["id"], "username": user["username"], "created_at": user.get("created_at")}
