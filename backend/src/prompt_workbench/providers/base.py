"""Model provider abstraction — the swappable AI-services layer.

Every model call in the workbench goes through the :class:`ModelProvider` interface, so
the concrete engine can be replaced without touching the domain or service layers:

* :class:`~prompt_workbench.providers.mock.MockProvider` — deterministic, offline,
  schema-aware. Powers the demo, the test suite and any air-gapped usage.
* :class:`~prompt_workbench.providers.litellm_provider.LiteLLMProvider` — real models via
  the LiteLLM SDK (OpenAI, Anthropic, Gemini, Ollama, Azure, OpenAI-compatible).

Add a new engine by implementing :class:`ModelProvider` and registering it in
``registry.py``. Results are normalized to one envelope so provider objects never leak
into storage or the API.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelRequest:
    messages: list[dict[str, str]]
    provider: str
    model: str
    parameters: dict[str, Any] = field(default_factory=dict)
    output_mode: str = "text"
    output_schema: dict[str, Any] | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: Any = "auto"
    timeout_seconds: float = 120.0
    connection: dict[str, Any] = field(default_factory=dict)


@dataclass
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Cost:
    amount: str | None = None  # USD decimal string; None = unknown (never silently zero)
    source: str = "unknown"  # provider_reported | litellm_estimate | manual_rate | unknown
    rate_snapshot: dict[str, Any] | None = None


@dataclass
class ModelResult:
    text: str | None = None
    json: Any = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str | None = None
    refusal: str | None = None
    usage: Usage = field(default_factory=Usage)
    cost: Cost = field(default_factory=Cost)
    duration_ms: int | None = None
    provider_request_id: str | None = None
    resolved_model: str | None = None
    capability_warnings: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None

    def to_envelope(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "json": self.json,
            "tool_calls": self.tool_calls,
            "finish_reason": self.finish_reason,
            "refusal": self.refusal,
        }


class ProviderError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class ModelProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResult: ...

    def capability(self, request: ModelRequest, feature: str) -> str:
        """Return ``supported`` | ``unsupported`` | ``unknown`` for a feature."""
        return "unknown"
