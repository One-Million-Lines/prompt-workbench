"""Deterministic, offline mock provider.

Produces stable outputs from the request so the whole product — comparison matrix,
checks, costs, latency — works with no network and no credentials. It is *schema-aware*:
in JSON mode it emits an instance that satisfies the output schema, so ``json_valid`` and
``json_schema`` checks pass deterministically. A profile parameter ``mock_variant`` lets
the demo show meaningful differences between candidates (e.g. a regression that returns an
empty array). This is the provider's own configuration namespace; it never sees the
expected answer.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .base import Cost, ModelProvider, ModelRequest, ModelResult, Usage

# A small, explicit demo rate so the UI shows non-zero (but clearly synthetic) costs.
_MOCK_INPUT_RATE = 0.0000005
_MOCK_OUTPUT_RATE = 0.0000015


class MockProvider(ModelProvider):
    name = "mock"

    async def complete(self, request: ModelRequest) -> ModelResult:
        context = "\n".join(m.get("content", "") for m in request.messages if m.get("role") != "system")
        variant = str(request.parameters.get("mock_variant", "default"))
        seed = hashlib.sha256((context + "|" + variant + "|" + request.model).encode("utf-8")).hexdigest()

        result = ModelResult(resolved_model=f"mock/{request.model}")
        result.finish_reason = "stop"

        if request.tools and request.tool_choice in ("required", "auto") and _wants_tool(request):
            tool = request.tools[0]
            fn = tool.get("function", tool)
            args = _instance_for_schema(fn.get("parameters", {}), context, variant)
            result.tool_calls = [{"id": "call_" + seed[:8], "name": fn.get("name", "tool"), "arguments": args}]
            result.text = None
            output_text = json.dumps(result.tool_calls)
        elif request.output_mode in ("json", "native_json_schema"):
            instance = _instance_for_schema(request.output_schema or {"type": "object"}, context, variant)
            text = json.dumps(instance, ensure_ascii=False)
            result.text = text
            result.json = instance
            output_text = text
        else:
            text = _summarize(context, seed)
            result.text = text
            output_text = text

        input_tokens = max(1, len(context) // 4)
        output_tokens = max(1, len(output_text) // 4)
        result.usage = Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            detail={"provider": "mock"},
        )
        amount = input_tokens * _MOCK_INPUT_RATE + output_tokens * _MOCK_OUTPUT_RATE
        result.cost = Cost(amount=f"{amount:.6f}", source="manual_rate", rate_snapshot={"input": _MOCK_INPUT_RATE, "output": _MOCK_OUTPUT_RATE})
        result.duration_ms = 40 + int(seed[:4], 16) % 400
        result.provider_request_id = "mock-" + seed[:16]
        return result

    def capability(self, request: ModelRequest, feature: str) -> str:
        return "supported"


def _wants_tool(request: ModelRequest) -> bool:
    if request.tool_choice == "required":
        return True
    if isinstance(request.tool_choice, dict):
        return True
    return request.tool_choice == "auto" and bool(request.tools)


def _summarize(context: str, seed: str) -> str:
    snippet = " ".join(context.split())[:180]
    return f"[mock:{seed[:6]}] {snippet}" if snippet else f"[mock:{seed[:6]}] (no input)"


def _instance_for_schema(schema: dict[str, Any], context: str, variant: str, depth: int = 0) -> Any:
    if depth > 8 or not isinstance(schema, dict):
        return None
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((t for t in schema_type if t != "null"), schema_type[0])
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    if "default" in schema:
        return schema["default"]

    if schema_type == "object" or "properties" in schema:
        obj: dict[str, Any] = {}
        props = schema.get("properties", {})
        required = set(schema.get("required", list(props.keys())))
        for name, prop in props.items():
            if name in required:
                obj[name] = _instance_for_schema(prop, context, variant, depth + 1)
                if isinstance(obj[name], str) and _looks_like_text_field(name):
                    obj[name] = _text_value(name, context)
        return obj
    if schema_type == "array":
        if variant == "empty_array":
            return []
        items = schema.get("items", {"type": "string"})
        count = 2 if variant == "extra_items" else 1
        return [_instance_for_schema(items, context, variant, depth + 1) for _ in range(count)]
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return True
    if schema_type == "null":
        return None
    return "sample"


def _looks_like_text_field(name: str) -> bool:
    return any(k in name.lower() for k in ("title", "summary", "text", "category", "label", "name", "brief"))


def _text_value(name: str, context: str) -> str:
    words = context.split()
    if not words:
        return f"mock-{name}"
    if "category" in name.lower() or "label" in name.lower():
        return "informational"
    return " ".join(words[:6])
