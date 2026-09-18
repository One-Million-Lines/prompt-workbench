"""Domain layer: identity, canonical JSON, rendering, schema, checks, models."""

from .canonical import CanonicalizationError, canonical_json, content_digest, sha256_bytes
from .checks import CheckResult, evaluate_check, resolve_pointer
from .ids import is_valid_slug, new_uuid, slugify, utcnow
from .models import (
    PromptContent,
    normalize_prompt_content,
    semantic_chain_digest,
    semantic_prompt_digest,
)
from .rendering import RenderResult, TemplateError, extract_variables, render_prompt, render_string
from .schema import SchemaValidationError, apply_defaults, validate_instance, validate_schema_document

__all__ = [
    "canonical_json",
    "content_digest",
    "sha256_bytes",
    "CanonicalizationError",
    "new_uuid",
    "utcnow",
    "slugify",
    "is_valid_slug",
    "render_prompt",
    "render_string",
    "extract_variables",
    "RenderResult",
    "TemplateError",
    "validate_instance",
    "validate_schema_document",
    "apply_defaults",
    "SchemaValidationError",
    "evaluate_check",
    "CheckResult",
    "resolve_pointer",
    "PromptContent",
    "normalize_prompt_content",
    "semantic_prompt_digest",
    "semantic_chain_digest",
]
