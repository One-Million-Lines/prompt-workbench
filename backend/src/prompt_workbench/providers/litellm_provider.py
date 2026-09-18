"""LiteLLM-backed provider for real model access.

Wraps ``litellm.acompletion`` behind the shared :class:`ModelProvider` contract. LiteLLM
is an optional dependency; this module imports it lazily so the app runs fully on the mock
provider without it. Credentials are resolved from the connection's ``secret_env_name``
environment variable at dispatch time and never persisted or returned to the browser.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from .base import Cost, ModelProvider, ModelRequest, ModelResult, ProviderError, Usage

_PROVIDER_PREFIX = {
    "openai": "",
    "anthropic": "anthropic/",
    "gemini": "gemini/",
    "google": "gemini/",
    "ollama": "ollama/",
    "azure": "azure/",
    "openai_compatible": "openai/",
}


class LiteLLMProvider(ModelProvider):
    name = "litellm"

    def __init__(self) -> None:
        self._litellm = None

    def _lib(self):
        if self._litellm is None:
            try:
                import litellm
            except ImportError as exc:  # pragma: no cover - requires the extra
                raise ProviderError(
                    "provider_unavailable",
                    "LiteLLM is not installed. Install with: pip install 'prompt-workbench[litellm]'",
                ) from exc
            litellm.suppress_debug_info = True
            litellm.drop_params = False  # never silently drop unsupported params
            litellm.telemetry = False
            self._litellm = litellm
        return self._litellm

    def _model_id(self, request: ModelRequest) -> str:
        prefix = _PROVIDER_PREFIX.get(request.provider, "")
        model = request.model
        if prefix and not model.startswith(prefix):
            return prefix + model
        return model

    def _build_kwargs(self, request: ModelRequest) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._model_id(request),
            "messages": request.messages,
            "timeout": request.timeout_seconds,
            "num_retries": 0,  # retries are controlled by the workbench, not nested here
        }
        params = request.parameters or {}
        for key in ("temperature", "top_p", "max_tokens", "reasoning_effort", "seed"):
            if params.get(key) is not None:
                kwargs[key] = params[key]

        connection = request.connection or {}
        if connection.get("api_base"):
            kwargs["api_base"] = connection["api_base"]
        if connection.get("api_version"):
            kwargs["api_version"] = connection["api_version"]
        secret_env = connection.get("secret_env_name")
        if secret_env:
            key_value = os.environ.get(secret_env)
            if not key_value and request.provider != "ollama":
                raise ProviderError("missing_credential", f"Environment variable {secret_env} is not set")
            if key_value:
                kwargs["api_key"] = key_value

        if request.output_mode == "json":
            kwargs["response_format"] = {"type": "json_object"}
        elif request.output_mode == "native_json_schema" and request.output_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "output", "schema": request.output_schema, "strict": True},
            }
        if request.tools:
            kwargs["tools"] = [_as_openai_tool(t) for t in request.tools]
            if request.tool_choice and request.tool_choice != "auto":
                kwargs["tool_choice"] = request.tool_choice
        return kwargs

    async def complete(self, request: ModelRequest) -> ModelResult:
        litellm = self._lib()
        kwargs = self._build_kwargs(request)
        started = time.monotonic()
        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:  # noqa: BLE001 - normalize provider exceptions
            code, retryable = _classify_exception(litellm, exc)
            raise ProviderError(code, str(exc), retryable=retryable) from exc
        duration_ms = int((time.monotonic() - started) * 1000)
        return self._normalize(litellm, request, response, duration_ms)

    def _normalize(self, litellm, request: ModelRequest, response: Any, duration_ms: int) -> ModelResult:
        result = ModelResult(duration_ms=duration_ms, resolved_model=getattr(response, "model", None))
        choice = response.choices[0]
        message = choice.message
        result.finish_reason = getattr(choice, "finish_reason", None)
        result.text = getattr(message, "content", None)
        tool_calls = getattr(message, "tool_calls", None) or []
        for call in tool_calls:
            fn = call.function
            try:
                arguments = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
            except (ValueError, TypeError):
                arguments = {"_raw": fn.arguments}
            result.tool_calls.append({"id": getattr(call, "id", None), "name": fn.name, "arguments": arguments})
        if request.output_mode in ("json", "native_json_schema") and result.text:
            try:
                result.json = json.loads(result.text)
            except (ValueError, TypeError):
                result.json = None

        usage = getattr(response, "usage", None)
        if usage is not None:
            result.usage = Usage(
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                detail={"provider": request.provider},
            )
        try:
            amount = litellm.completion_cost(completion_response=response)
            result.cost = Cost(amount=f"{amount:.6f}", source="litellm_estimate")
        except Exception:  # noqa: BLE001 - unknown cost is never silently zero
            result.cost = Cost(amount=None, source="unknown")
        result.provider_request_id = getattr(response, "id", None)
        return result

    def capability(self, request: ModelRequest, feature: str) -> str:
        litellm = self._lib()
        model = self._model_id(request)
        try:
            if feature == "json_schema":
                return "supported" if litellm.supports_response_schema(model) else "unsupported"
            if feature == "tools":
                return "supported" if litellm.supports_function_calling(model) else "unsupported"
        except Exception:  # noqa: BLE001
            return "unknown"
        return "unknown"


def _as_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    if tool.get("type") == "function":
        return tool
    return {"type": "function", "function": tool}


def _classify_exception(litellm, exc: Exception) -> tuple[str, bool]:
    name = type(exc).__name__
    retryable_names = {"RateLimitError", "ServiceUnavailableError", "InternalServerError", "APIConnectionError", "Timeout"}
    if name in retryable_names:
        return "provider_unavailable", True
    if name in {"AuthenticationError", "PermissionDeniedError"}:
        return "provider_auth", False
    if name in {"BadRequestError", "UnsupportedParamsError"}:
        return "provider_bad_request", False
    if name in {"ContentPolicyViolationError"}:
        return "content_policy", False
    return "provider_error", False
