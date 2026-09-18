"""Auth, current-user, and API-key management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..domain.ids import new_uuid, utcnow
from ..security import generate_api_key
from ..services import AppContext, AuthService
from ..storage import Collections
from .deps import get_context, get_principal
from .schemas import ApiKeyCreate, LoginRequest

router = APIRouter()


@router.post("/auth/login")
async def login(body: LoginRequest, ctx: AppContext = Depends(get_context)):
    return await AuthService(ctx).login(body.username, body.password)


@router.post("/auth/logout")
async def logout(principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    if principal.kind == "user":
        await AuthService(ctx).logout(principal.id)
    return {"ok": True}


@router.get("/auth/me")
async def me(principal=Depends(get_principal)):
    return {"id": principal.id, "kind": principal.kind, "username": principal.username, "scopes": principal.scopes}


@router.get("/api-keys")
async def list_api_keys(principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    rows = await ctx.repo.find_many(Collections.API_KEYS, sort=[("created_at", 1)])
    return [
        {
            "id": r["id"],
            "name": r.get("name"),
            "key_prefix": r["key_prefix"],
            "scopes": r.get("scopes", []),
            "project_id": r.get("project_id"),
            "expires_at": r.get("expires_at"),
            "revoked_at": r.get("revoked_at"),
            "created_at": r.get("created_at"),
        }
        for r in rows
    ]


@router.post("/api-keys", status_code=201)
async def create_api_key(body: ApiKeyCreate, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    if principal.kind != "user":
        raise HTTPException(status_code=403, detail="Only interactive users can create API keys")
    full, prefix, secret_hash = generate_api_key()
    record = {
        "id": new_uuid(),
        "name": body.name,
        "key_prefix": prefix,
        "secret_hash": secret_hash,
        "scopes": body.scopes,
        "project_id": body.project_id,
        "expires_at": body.expires_at,
        "revoked_at": None,
        "last_used_at": None,
        "created_at": utcnow(),
    }
    await ctx.repo.insert_one(Collections.API_KEYS, record)
    # The full key is returned exactly once.
    return {"id": record["id"], "api_key": full, "key_prefix": prefix, "scopes": body.scopes}


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: str, principal=Depends(get_principal), ctx: AppContext = Depends(get_context)):
    record = await ctx.repo.find_one(Collections.API_KEYS, {"id": key_id})
    if record:
        record["revoked_at"] = utcnow()
        await ctx.repo.replace_one(Collections.API_KEYS, {"id": key_id}, record)
    return None
