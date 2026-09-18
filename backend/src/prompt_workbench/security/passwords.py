"""Password hashing (Argon2id) and API-key secret hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash, treat as failure
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:  # noqa: BLE001
        return False


# --- API keys --------------------------------------------------------------
def generate_api_key() -> tuple[str, str, str]:
    """Return ``(full_key, prefix, secret_hash)``. The full key is shown once."""
    prefix = "pwk_" + secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    full = f"{prefix}.{secret}"
    return full, prefix, _hash_secret(secret)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_api_key_secret(secret: str, secret_hash: str) -> bool:
    return hmac.compare_digest(_hash_secret(secret), secret_hash)
