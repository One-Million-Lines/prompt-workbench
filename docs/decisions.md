# Design decisions

Non-obvious choices made while implementing the v1 specification. Recorded per the spec's
instruction to prefer the smallest reversible implementation and document it.

## D1 — MongoDB primary, SQLite for the demo (owner override)
The specification names SQLite as the durable store. The project owner requires **MongoDB as the
primary/production database**, with SQLite retained for a zero-dependency demo. We reconcile this
with a **storage abstraction** (`storage/base.py::Repository`) implemented by both backends. The
domain and service layers depend only on the interface. This keeps the spec's data contracts while
honoring the owner's database preference.

## D2 — Document store instead of a relational schema
Because MongoDB is document-oriented, the persistence model is a small document store (one
"collection" per logical table) rather than a normalized relational schema. On SQLite each
collection is a `(id, doc JSON)` table queried with `json_extract`. The specification's table
contracts are preserved as document shapes and enforced in the service layer.

## D3 — Optimistic concurrency instead of multi-document transactions
Multi-document ACID transactions need a Mongo replica set and are awkward across two backends. The
correctness properties the spec demands (stale draft → 409, no duplicate revision numbers, capture
dedupe) are enforced with `edit_sequence`/expected-revision guards and unique keys, which behave
identically on both backends. SQLite still uses a real transaction for the save-revision step.

## D4 — LiteLLM behind a provider interface; mock is first-class
Per the spec, LiteLLM is used in-process. We wrap it in a `ModelProvider` so the AI engine is
swappable (owner requirement). The deterministic `MockProvider` is a first-class citizen: it powers
the demo and the entire test suite offline, and is schema-aware so JSON-mode checks pass
deterministically. A `mock_variant` profile parameter enables demonstrating regressions.

## D5 — Canonical JSON number handling
Canonical JSON restricts numbers to the interoperable safe-integer range and formats
integer-valued floats as integers; non-finite numbers are rejected. Shared conformance fixtures
(`examples/javascript/fixtures.json`) pin Python/JavaScript agreement and deliberately avoid
ambiguous floating-point cases.

## D6 — Runtime renderer duplicated, kept honest by fixtures
The portable `runtime/` package and the JavaScript reference each contain a copy of the `simple-v1`
renderer and canonical JSON (the runtime must install with no third-party dependencies). Drift is
prevented by the shared fixtures, exercised from the backend pytest suite, the runtime, and the JS
test. Converging these onto one vendored module is possible future work.

## D7 — Runs execute in an in-process async task
The spec allows a single process with an asyncio scheduling loop and defers a separate worker.
`create_run` persists the run and all cells before returning `202`, then a background task executes
them with global/per-connection concurrency limits. Cells are persisted before and after each call
so completed results survive; on restart, non-terminal work is treated as interrupted (no replay).

## D8 — Scope of v1 implementation
Linear chains, rubric (LLM-judge) checks, and the optional resolve endpoint are represented in the
data model and contracts but are intentionally minimal in this first cut; the deterministic check
library, comparison matrix, publishing/runtime path, and capture intake are fully implemented.
These are the smallest reversible choices consistent with the specification and are safe to extend.
