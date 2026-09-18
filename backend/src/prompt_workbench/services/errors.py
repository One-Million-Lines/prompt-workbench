"""Service-layer errors mapped to HTTP responses at the API boundary."""

from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    status_code = 400

    def __init__(self, code: str, message: str, *, status_code: int | None = None, details: dict[str, Any] | None = None, retryable: bool = False):
        self.code = code
        self.details = details or {}
        self.retryable = retryable
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(ServiceError):
    status_code = 404

    def __init__(self, message: str = "Not found", **kwargs):
        super().__init__("not_found", message, status_code=404, **kwargs)


class ConflictError(ServiceError):
    status_code = 409

    def __init__(self, message: str, code: str = "conflict", **kwargs):
        super().__init__(code, message, status_code=409, **kwargs)


class ValidationError(ServiceError):
    status_code = 422

    def __init__(self, message: str, code: str = "invalid", **kwargs):
        super().__init__(code, message, status_code=422, **kwargs)


class AuthError(ServiceError):
    status_code = 401

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__("unauthorized", message, status_code=401, **kwargs)


class ForbiddenError(ServiceError):
    status_code = 403

    def __init__(self, message: str = "Insufficient scope", **kwargs):
        super().__init__("forbidden", message, status_code=403, **kwargs)
