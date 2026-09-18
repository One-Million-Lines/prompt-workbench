# Prompt Workbench

Prompt Workbench is a local, open-source developer application for creating, versioning,
testing, comparing and publishing LLM prompts and linear prompt chains. Develop and compare
prompts locally, then ship the exact versions you tested as ordinary, portable files that any
language can load — with no cloud account and no vendor lock-in.

> Product promise: **"Develop and compare prompts locally. Ship the exact versions you tested as ordinary files."**

## What it does

- **Prompt registry & versioning** — stable UUIDs, immutable numbered revisions with change
  notes, diffs, restore, and static `development` / `staging` / `production` labels.
- **Strict templating** — the tiny, non-executable `simple-v1` engine: typed `{{variables}}`,
  JSON-Schema validation, deterministic rendering (identical in Python and JavaScript).
- **Datasets & input sets** — named example cases with schema validation, immutable revisions,
  imports/exports (JSON/JSONL/CSV) and snapshots.
- **Evaluations** — compare candidates (prompt snapshot × model snapshot) on identical dataset
  snapshots with deterministic checks, pass/fail gates, latency and cost. Execution outcome is
  kept separate from quality outcome.
- **Publishing** — build hash-verified, self-contained release bundles and load them from a
  separate runtime package (or any language) with the workbench stopped.
- **Capture intake** — ingest production examples over a scoped, idempotent API and promote them
  into regression datasets, without granting publish or model-spend access.

## Why it exists

Prompts are production artifacts, but they are usually scattered across code and notebooks with
no history, no way to A/B two revisions on the same examples, and no safe way to promote "the
version we actually tested" to production. Prompt Workbench gives prompts the same discipline we
give code: immutable versions, reproducible comparisons, and portable, verifiable releases.

## Features

| Area | Capability |
|---|---|
| Registry | Create, search, tag, archive, draft, save immutable revisions, diff, restore, label, comment. |
| Templates | Chat/text prompts, strict typed variables, JSON output validation, function tool definitions. |
| Datasets | Named cases, schema validation, revisioned rows, import/export, expected values, tags. |
| Models | Swappable providers via one adapter — deterministic mock (offline) + LiteLLM (real models). |
| Evaluations | Persistent runs, comparison matrix, deterministic checks, human review, CI gates & reports. |
| Publishing | Atomic release snapshots, portable files, integrity verification, independent runtime loader. |
| Intake | Authenticated, idempotent capture ingestion and capture-to-case promotion. |
| Operations | Basic JWT login, scoped integration keys, bounded jobs, packaged local launch. |

## How it works

1. **Author** a prompt with typed variables; preview the render live (no model call).
2. **Save a version** — freeze an immutable revision with a change note and content digest.
3. **Compare** candidates over a dataset snapshot and read the scored matrix.
4. **Label** — point `production` at the revision you trust.
5. **Publish** a verified release bundle; **load** it from Python/JS with the workbench stopped.
6. **Capture** production runs back as examples for the next regression test.

The core loop runs fully offline on the deterministic mock provider — no API keys required.

## Architecture

Two deliberate, swappable seams sit at the center of the design:

- **Pluggable storage.** Everything talks to a single `Repository` interface. **MongoDB is the
  primary/production backend**; a zero-dependency **SQLite** backend powers the bundled demo and
  the test suite. Choose with one setting — the domain and service layers never change.
- **Pluggable AI services.** Every model call goes through a `ModelProvider`. The **mock**
  provider is deterministic and offline (used by the demo and tests); the **LiteLLM** provider
  reaches OpenAI, Anthropic, Gemini, Ollama, Azure OpenAI and OpenAI-compatible endpoints.
  Add a new engine by implementing the interface and registering it.

```
HTTP API (FastAPI)  ──►  Services (domain logic)  ──►  Repository interface ──► { MongoDB | SQLite }
                                    │
                                    └──►  ModelProvider interface ──► { Mock | LiteLLM }
Shared domain: simple-v1 renderer · canonical JSON / digests · JSON-Schema · checks
Portable runtime package (+ JS reference) renders release bundles anywhere.
```

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, `aiosqlite` (SQLite) / `motor` (MongoDB),
  PyJWT + Argon2id, `jsonschema`, Typer CLI, LiteLLM (optional), pytest.
- **Frontend:** React, TypeScript, Vite, TanStack Query.
- **Runtime:** dependency-light `prompt-workbench-runtime` package + JavaScript reference renderer.

## Quickstart

```bash
# from the prompt-workbench/ directory
python -m venv .venv && source .venv/bin/activate
pip install -e backend           # core install (SQLite demo, mock provider)

prompt-workbench demo            # seed synthetic data + serve on http://127.0.0.1:8765
# login: demo@promptworkbench.dev / workbench
```

Optional extras:

```bash
pip install -e 'backend[mongo]'     # MongoDB primary backend (set PROMPT_WORKBENCH_STORAGE_BACKEND=mongo)
pip install -e 'backend[litellm]'   # real model access via LiteLLM
pip install -e runtime              # portable bundle loader/renderer
```

Run a real (non-demo) instance:

```bash
prompt-workbench init --data-dir ./data      # create the store + first user
prompt-workbench serve --data-dir ./data     # start the API + scheduler
```

### Frontend (contributors)

```bash
cd frontend
npm install
npm run dev        # dev server with API proxy to http://127.0.0.1:8765
npm run build      # production build; copy dist/ into backend/src/prompt_workbench/static/
```

## Project structure

```
prompt-workbench/
├── backend/                     # Python FastAPI application (installable package)
│   └── src/prompt_workbench/
│       ├── api/                 # HTTP routes, auth deps, request models
│       ├── services/            # registry, datasets, runs, captures, releases, auth
│       ├── domain/              # simple-v1 renderer, canonical JSON, schema, checks, models
│       ├── providers/           # ModelProvider interface + mock + litellm + registry
│       ├── storage/             # Repository interface + mongo + sqlite + factory
│       ├── security/            # Argon2id passwords + JWT
│       ├── seed/                # synthetic demo data
│       ├── app.py               # FastAPI app factory
│       └── cli.py               # Typer CLI (init/serve/demo/user/bundle/migrate)
│   └── tests/                   # pytest suite (renderer, storage, prompts, runs, api, runtime)
├── runtime/                     # portable bundle loader/renderer (separate package)
├── frontend/                    # React + TypeScript + Vite UI
├── examples/
│   ├── javascript/              # JS reference renderer + cross-language fixtures
│   └── actor/                   # synthetic prompt/dataset examples
├── website/                     # one-page presentation site (index.html)
├── docs/                        # architecture, API, deployment, security notes
└── prompt-workbench-v1-specification.md   # the full product/engineering specification
```

## Testing

```bash
cd backend && python -m pytest              # backend unit/integration/api tests
cd examples/javascript && node test.mjs     # cross-language renderer conformance
```

## Security & privacy (summary)

- Binds to `127.0.0.1` by default. Passwords hashed with Argon2id; JWT (HS256) with claim checks.
- Provider secrets are referenced by environment-variable name and never stored in the database,
  returned to the browser, or written into exports/releases.
- The demo and tests are entirely synthetic and never call a paid provider.

See [`SECURITY.md`](SECURITY.md) and [`docs/`](docs/) for details.

## License

[Apache-2.0](LICENSE). Not affiliated with any third-party prompt-management product; provider
usage may incur that provider's own charges.
