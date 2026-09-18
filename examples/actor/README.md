# Actor synthetic examples

These are **entirely synthetic** examples that mirror the kind of email-assistant work the
workbench is designed for. They contain no real customer data and are safe to seed publicly.

The same content is loaded automatically by `prompt-workbench demo` (see
`backend/src/prompt_workbench/seed/demo_seed.py`). The files here are provided for manual import
and as a reference for the file formats.

## Files

- `action-extraction.dataset.jsonl` — 12 action-extraction cases covering: an explicit task, an
  FYI-only email, a trivial link, a duplicate request, multiple tasks, German input, Romanian
  input, a long quoted thread, a historically-completed task, a task assigned to someone else, an
  ambiguous deadline, and an email containing hostile embedded instructions.
- `captures.jsonl` — two synthetic production captures (one `structured`, one `rendered`).

## Import a dataset

Create a dataset in the UI (or API), then:

```bash
# preview
curl -H "Authorization: Bearer $TOKEN" \
     --data-binary @action-extraction.dataset.jsonl \
     "http://127.0.0.1:8765/api/v1/datasets/$DATASET_ID/import-preview?fmt=jsonl"
```

## Import captures via the CLI

```bash
prompt-workbench capture import captures.jsonl --project <project-uuid>
```

Each case's `expected` is intentionally an empty/placeholder value: a capture or example is **not**
ground truth until a developer curates it.
