"""FastAPI dependencies: context access and authentication."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from ..services import AppContext, AuthService, Principal
from ..services.errors import AuthError


def get_context(request: Request) -> AppContext:
    return request.app.state.context


async def get_principal(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Principal:
    ctx: AppContext = request.app.state.context
    auth = AuthService(ctx)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    token = authorization[7:].strip()
    try:
        # Integration keys have the pwk_ prefix; everything else is a JWT.
        if token.startswith("pwk_"):
            return await auth.principal_from_api_key(token)
        return await auth.principal_from_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc


def require_scopes(*scopes: str):
    """Dependency factory enforcing integration-key scopes (users always pass)."""

    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        for scope in scopes:
            if not principal.has_scope(scope):
                raise HTTPException(status_code=403, detail=f"Missing required scope: {scope}")
        return principal

    return _dep
