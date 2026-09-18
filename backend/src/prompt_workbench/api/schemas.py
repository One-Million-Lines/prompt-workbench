"""Pydantic request models for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ProjectCreate(BaseModel):
    name: str
    slug: str | None = None
    settings: dict[str, Any] | None = None


class ProjectSettingsUpdate(BaseModel):
    settings: dict[str, Any]


class ConnectionCreate(BaseModel):
    alias: str
    provider: str
    api_base: str | None = None
    api_version: str | None = None
    secret_env_name: str | None = None
    enabled: bool = True


class ModelProfileCreate(BaseModel):
    project_id: str
    name: str
    provider: str
    model: str
    connection_alias: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 120
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_retries": 1})


class PromptCreate(BaseModel):
    project_id: str
    name: str
    slug: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    is_snippet: bool = False
    content: dict[str, Any] | None = None


class DraftUpdate(BaseModel):
    content: dict[str, Any]
    expected_edit_sequence: int


class SaveRevision(BaseModel):
    note: str
    expected_edit_sequence: int | None = None


class RestoreDraft(BaseModel):
    version: int
    expected_edit_sequence: int


class LabelUpdate(BaseModel):
    version: int
    expected_previous_revision_id: str | None = None


class RenderRequest(BaseModel):
    selector: dict[str, Any]
    inputs: dict[str, Any] = Field(default_factory=dict)


class CommentCreate(BaseModel):
    body: str


class DatasetCreate(BaseModel):
    project_id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)


class CaseCreate(BaseModel):
    name: str
    inputs: dict[str, Any]
    expected: Any = None
    tags: list[str] = Field(default_factory=list)
    critical: bool = False


class CaseUpdate(BaseModel):
    name: str | None = None
    inputs: dict[str, Any] | None = None
    expected: Any = None
    tags: list[str] | None = None
    critical: bool | None = None


class ImportCommit(BaseModel):
    rows: list[dict[str, Any]]
    atomic: bool = True


class RunCandidate(BaseModel):
    label: str
    target: dict[str, Any]
    model_profile_id: str


class RunRequest(BaseModel):
    project_id: str
    kind: Literal["playground", "evaluation", "chain", "rescore"] = "evaluation"
    dataset_id: str | None = None
    case_ids: list[str] | None = None
    candidates: list[RunCandidate]
    checks: list[dict[str, Any]] = Field(default_factory=list)
    baseline_label: str | None = None
    repeats: int = 1
    budget: dict[str, Any] = Field(default_factory=lambda: {"max_usd": None, "strict": False})
    gate: dict[str, Any] | None = None
    parent_run_id: str | None = None


class ReviewCreate(BaseModel):
    verdict: Literal["pass", "fail", "unreviewed"]
    note: str = ""


class CaptureIngest(BaseModel):
    schema_version: int = 1
    project_id: str
    source: str = "unknown"
    mode: Literal["structured", "rendered"] = "rendered"
    external_event_id: str | None = None
    occurred_at: str | None = None
    prompt_ref: dict[str, Any] | None = None
    inputs: dict[str, Any] | None = None
    rendered_messages: list[dict[str, Any]] | None = None
    output: dict[str, Any] | None = None
    model: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class CaptureReview(BaseModel):
    review_status: Literal["new", "reviewed", "promoted", "ignored"]


class CapturePromote(BaseModel):
    dataset_id: str
    name: str | None = None
    expected: Any = None


class ReleaseBuild(BaseModel):
    project_id: str
    name: str
    selection: dict[str, Any]


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str]
    project_id: str | None = None
    expires_at: str | None = None
