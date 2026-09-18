"""JWT issuance and verification (HS256, per specification section 17.1)."""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt

from ..config import Settings


class TokenError(Exception):
    pass


@dataclass
class TokenClaims:
    sub: str
    token_version: int


def issue_access_token(settings: Settings, user_id: str, token_version: int) -> tuple[str, int]:
    now = int(time.time())
    ttl = settings.access_token_ttl_seconds
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ttl,
        "iss": settings.installation_id,
        "aud": settings.jwt_audience,
        "token_version": token_version,
    }
    token = jwt.encode(payload, settings.resolved_jwt_secret(), algorithm=settings.jwt_algorithm)
    return token, ttl


def decode_access_token(settings: Settings, token: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.resolved_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.installation_id,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    return TokenClaims(sub=payload["sub"], token_version=int(payload.get("token_version", 0)))
