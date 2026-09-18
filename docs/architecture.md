# Architecture

Prompt Workbench is a single-process local application. One FastAPI/Uvicorn process serves the
JSON API, the bundled React assets, and an in-process async run scheduler.

```
┌──────────────────────────────────────────────────────────────────────┐
│ FastAPI process                                                        │
│                                                                        │
│  api/ (routers, JWT auth deps, request models)                         │
│     │                                                                  │
│     ▼                                                                  │
│  services/ (registry, datasets, runs, captures, releases, auth)        │
│     │                    │                                             │
│     ▼                    ▼                                             │
│  storage.Repository   providers.ModelProvider                          │
│   ├─ MongoRepository    ├─ MockProvider (deterministic, offline)       │
│   └─ SqliteRepository   └─ LiteLLMProvider (OpenAI/Anthropic/…)         │
│                                                                        │
│  domain/ (shared): simple-v1 renderer · canonical JSON · schema · checks│
└──────────────────────────────────────────────────────────────────────┘
        │ publish
        ▼
  release bundle ──► runtime/ package (+ JS reference) renders anywhere, no DB
```

## The two pluggable seams

### Storage — `storage/base.py::Repository`
A small MongoDB-style document store: `insert_one`, `find_one`, `find_many`, `count`,
`replace_one` (optimistic), `delete_one/many`, and a `transaction()` scope.

- **`MongoRepository`** (`storage/mongo.py`) — the primary/production backend via `motor`. Maps the
  app's `id` to Mongo `_id`.
- **`SqliteRepository`** (`storage/sqlite.py`) — the demo/test backend via `aiosqlite`. Each
  collection is a `(id, doc JSON)` table; MongoDB-style filters are translated to `json_extract`.

Correctness properties that the spec requires atomically (stale draft → 409, no duplicate revision
numbers, capture dedupe) are enforced with **optimistic concurrency** (`edit_sequence` guards +
unique keys), which works identically on both backends. SQLite additionally provides a real
transaction; Mongo single-document ops are atomic.

### AI services — `providers/base.py::ModelProvider`
Every model call builds a `ModelRequest` and returns a normalized `ModelResult` envelope
(`text`, `json`, `tool_calls`, `usage`, `cost`, `timing`, `provenance`, `error`). Provider objects
never leak into storage or the API.

- **`MockProvider`** — deterministic and schema-aware; used by the demo and tests. A profile
  parameter `mock_variant` lets demos show meaningful candidate differences (e.g. a regression
  that returns an empty array).
- **`LiteLLMProvider`** — wraps `litellm.acompletion`; retries are controlled by the workbench,
  telemetry disabled, credentials resolved from env vars at dispatch.

`ProviderRegistry.for_request` chooses the engine: always mock in `provider_mode=mock`, always
LiteLLM in `litellm`, and (default) `auto` picks LiteLLM only when a connection has real
credentials available — otherwise the mock.

## Shared runtime semantics
`domain/rendering.py` (`simple-v1`), `domain/canonical.py` (RFC-8785-style canonical JSON and
SHA-256 digests) and `domain/checks.py` are the single source of truth. The `runtime/` package and
`examples/javascript/` mirror the renderer and canonical JSON; `examples/javascript/fixtures.json`
is shared by the Python and JavaScript conformance tests to prevent drift.

## Run lifecycle
1. API validates the request, resolves candidate snapshots (prompt content + model snapshot) and a
   dataset snapshot, and persists the run + cells (`queued`).
2. A background async task claims cells, renders, calls the provider (global + per-connection
   concurrency semaphores), runs checks, and persists each cell outcome.
3. The run is finalized: per-candidate pass-rate/latency/cost aggregates and gate outcome.
   Execution status (`succeeded`/`completed_with_errors`/`cancelled`) is separate from quality.
