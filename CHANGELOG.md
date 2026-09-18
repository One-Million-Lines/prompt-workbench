# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to semantic versioning.

## [1.0.0] - 2026-09-16

Initial open-source release.

### Added
- **Storage abstraction** with a single `Repository` interface and two backends: MongoDB
  (primary/production) and SQLite (zero-dependency demo & tests).
- **AI-services abstraction** with a `ModelProvider` interface: deterministic offline `mock`
  provider and a `LiteLLM` provider (OpenAI, Anthropic, Gemini, Ollama, Azure, OpenAI-compatible).
- **Prompt registry**: drafts with optimistic `edit_sequence` concurrency, immutable numbered
  revisions with semantic SHA-256 digests, diffs, restore, static labels, and revision comments.
- **`simple-v1` renderer** (Python + JavaScript reference) with cross-language conformance
  fixtures and canonical JSON / content digests.
- **Datasets & cases** with schema validation, immutable case revisions, snapshots, and
  JSON/JSONL/CSV import/export.
- **Evaluation engine**: candidate comparison matrix, deterministic checks (`json_valid`,
  `json_schema`, `equals`, `contains`/`not_contains`, `json_pointer_equals`, `array_length`,
  `tool_call`), pass/fail gates, cost/latency aggregation, cancellation, and CI report exit codes.
- **Publishing**: hash-verified, self-contained release bundles and a separate dependency-light
  `prompt-workbench-runtime` package that loads/renders them with the workbench stopped.
- **Capture intake**: authenticated, idempotent ingestion with redaction, capture inbox and
  promotion to dataset cases.
- **Auth & operations**: Argon2id + JWT login, scoped integration keys, Typer CLI
  (`init`, `serve`, `demo`, `user`, `bundle verify`, `migrate`), and a seeded synthetic demo.
- **Frontend**: React + TypeScript + Vite UI (registry editor, evaluation matrix, capture inbox).
- **Presentation website** (`website/index.html`) and documentation.
