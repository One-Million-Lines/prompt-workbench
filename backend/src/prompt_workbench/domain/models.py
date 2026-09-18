"""Domain models and semantic digests for prompt/chain content."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .canonical import content_digest

# Fields that make up the semantic identity of a prompt revision. IDs, timestamps and
# change notes are deliberately excluded from the digest.
_PROMPT_SEMANTIC_FIELDS = (
    "format_version",
    "kind",
    "template_engine",
    "messages",
    "text",
    "input_schema",
    "output",
    "tools",
    "tool_choice",
    "default_model",
)


class Message(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str = ""


class PromptOutput(BaseModel):
    mode: Literal["text", "json", "native_json_schema"] = "text"
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


class PromptContent(BaseModel):
    """Canonical prompt revision payload (specification section 6.1)."""

    format_version: int = 1
    kind: Literal["chat", "text"] = "chat"
    template_engine: Literal["simple-v1"] = "simple-v1"
    messages: list[Message] = Field(default_factory=list)
    text: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}, "required": []})
    output: PromptOutput = Field(default_factory=PromptOutput)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: Any = "auto"
    default_model: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}

    def to_document(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=False)


def normalize_prompt_content(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a prompt content payload into a canonical dict."""
    return PromptContent.model_validate(raw).to_document()


def semantic_prompt_digest(content: dict[str, Any]) -> str:
    semantic = {k: content.get(k) for k in _PROMPT_SEMANTIC_FIELDS if k in content}
    return content_digest(semantic)


# --- Chains ---------------------------------------------------------------
class ChainStep(BaseModel):
    step_id: str
    prompt_id: str
    selector: dict[str, Any] = Field(default_factory=dict)  # {"revision": N} | {"label": "production"}
    model_profile_id: str | None = None
    bindings: dict[str, Any] = Field(default_factory=dict)


class ChainContent(BaseModel):
    format_version: int = 1
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}, "required": []})
    steps: list[ChainStep] = Field(default_factory=list)

    def to_document(self) -> dict[str, Any]:
        return self.model_dump()


def semantic_chain_digest(content: dict[str, Any]) -> str:
    return content_digest({"input_schema": content.get("input_schema"), "steps": content.get("steps")})
