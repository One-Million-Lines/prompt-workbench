"""Provider selection — decides which engine executes a given model profile."""

from __future__ import annotations

import os

from ..config import Settings
from .base import ModelProvider, ModelRequest
from .mock import MockProvider


class ProviderRegistry:
    """Chooses a :class:`ModelProvider` per request based on configuration.

    * ``provider_mode="mock"`` — always deterministic/offline.
    * ``provider_mode="litellm"`` — always LiteLLM.
    * ``provider_mode="auto"`` (default) — LiteLLM when the connection has real
      credentials available in the environment, otherwise the mock.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._mock = MockProvider()
        self._litellm: ModelProvider | None = None

    def _litellm_provider(self) -> ModelProvider:
        if self._litellm is None:
            from .litellm_provider import LiteLLMProvider

            self._litellm = LiteLLMProvider()
        return self._litellm

    def for_request(self, request: ModelRequest) -> ModelProvider:
        mode = self._settings.provider_mode
        if mode == "mock":
            return self._mock
        if mode == "litellm":
            return self._litellm_provider()
        # auto
        if request.provider == "mock":
            return self._mock
        connection = request.connection or {}
        secret_env = connection.get("secret_env_name")
        has_credential = request.provider == "ollama" or (secret_env and os.environ.get(secret_env))
        if has_credential:
            try:
                return self._litellm_provider()
            except Exception:  # noqa: BLE001 - fall back to mock when litellm missing
                return self._mock
        return self._mock
