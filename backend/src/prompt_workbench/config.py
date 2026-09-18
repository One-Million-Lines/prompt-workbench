"""Application configuration.

Settings are loaded from environment variables (prefix ``PROMPT_WORKBENCH_``) with
sensible local defaults. The two most important choices are:

* ``storage_backend`` — ``sqlite`` (default, zero external dependency, used for the demo)
  or ``mongo`` (the preferred primary database for real installations).
* ``provider_mode`` — how model calls are executed. The app runs entirely on the
  deterministic ``mock`` provider unless real connections are configured.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_dir() -> Path:
    env = os.environ.get("PROMPT_WORKBENCH_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / "data").resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROMPT_WORKBENCH_",
        env_file=os.environ.get("PROMPT_WORKBENCH_ENV_FILE", ".env"),
        extra="ignore",
    )

    # --- Storage -----------------------------------------------------------
    storage_backend: Literal["sqlite", "mongo"] = "sqlite"
    data_dir: Path = Field(default_factory=default_data_dir)
    sqlite_path: Path | None = None
    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db: str = "prompt_workbench"

    # --- Server ------------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8765
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"])
    installation_id: str = "local-installation"

    # --- Auth --------------------------------------------------------------
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "prompt-workbench"
    access_token_ttl_seconds: int = 28800  # 8 hours per spec

    # --- Providers ---------------------------------------------------------
    # ``auto`` uses the litellm provider when a connection has real credentials,
    # otherwise the deterministic mock. ``mock`` forces offline deterministic mode.
    provider_mode: Literal["auto", "mock", "litellm"] = "auto"
    max_global_concurrency: int = 4
    max_connection_concurrency: int = 2

    # --- Demo --------------------------------------------------------------
    demo_mode: bool = False

    def resolved_sqlite_path(self) -> Path:
        if self.sqlite_path is not None:
            return self.sqlite_path
        return self.data_dir / "prompt_workbench.sqlite3"

    def resolved_jwt_secret(self) -> str:
        """Return the configured secret, or read/create a local secret file.

        The secret is never stored in the database. In demo mode a stable
        development secret is used so tokens survive restarts.
        """
        if self.jwt_secret:
            return self.jwt_secret
        if self.demo_mode:
            return "demo-insecure-jwt-secret-do-not-use-in-production"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        secret_file = self.data_dir / "jwt_secret"
        if secret_file.exists():
            return secret_file.read_text(encoding="utf-8").strip()
        secret = secrets.token_hex(32)
        secret_file.write_text(secret, encoding="utf-8")
        try:
            os.chmod(secret_file, 0o600)
        except OSError:
            pass
        return secret


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
