"""Build the configured :class:`Repository` backend."""

from __future__ import annotations

from ..config import Settings
from .base import Repository
from .sqlite import SqliteRepository


def build_repository(settings: Settings) -> Repository:
    if settings.storage_backend == "mongo":
        from .mongo import MongoRepository

        return MongoRepository(settings.mongo_uri, settings.mongo_db)
    return SqliteRepository(settings.resolved_sqlite_path())


# Logical collection names — one place so both backends stay in sync.
class Collections:
    USERS = "users"
    API_KEYS = "api_keys"
    PROJECTS = "projects"
    CONNECTIONS = "connections"
    MODEL_PROFILES = "model_profiles"
    PROMPTS = "prompts"
    PROMPT_DRAFTS = "prompt_drafts"
    PROMPT_REVISIONS = "prompt_revisions"
    PROMPT_LABELS = "prompt_labels"
    CHAINS = "chains"
    CHAIN_DRAFTS = "chain_drafts"
    CHAIN_REVISIONS = "chain_revisions"
    CHAIN_LABELS = "chain_labels"
    DATASETS = "datasets"
    CASES = "cases"
    CASE_REVISIONS = "case_revisions"
    EVALUATIONS = "evaluation_definitions"
    RUNS = "runs"
    RUN_CANDIDATES = "run_candidates"
    RUN_CELLS = "run_cells"
    CHECK_RESULTS = "check_results"
    REVIEW_EVENTS = "review_events"
    REVISION_COMMENTS = "revision_comments"
    CAPTURES = "captures"
    RELEASES = "releases"
    CHANGE_EVENTS = "change_events"
