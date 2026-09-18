# JSON Schema contracts

Versioned, language-neutral contracts for the durable formats independent consumers rely on.

- `prompt.schema.json` — canonical prompt revision content (`format_version` 1).
- `capture.schema.json` — capture ingestion payload for `POST /captures` (`schema_version` 1).
  Note: JSONL **import files** (e.g. `examples/actor/captures.jsonl`) omit `project_id` because the
  CLI supplies it via `--project <uuid>`; the field is required only on the HTTP ingestion body.
- `bundle.schema.json` — release bundle `manifest.json` (`format_version` 1). The release builder
  also writes a copy of the bundle contract into every exported bundle at
  `schemas/bundle.schema.json`.

The authoritative validators live in the backend (`domain/schema.py`, service layer) and the
portable runtime; these files document the wire format for other languages and tools.
