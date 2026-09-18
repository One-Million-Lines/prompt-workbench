# Contributing to Prompt Workbench

Thanks for your interest in contributing! This project aims to be a practical, local-first,
open-source tool. Contributions of all kinds are welcome: bug reports, docs, tests and features.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e 'backend[dev]'        # backend + test tooling
pip install -e runtime               # portable runtime package
cd frontend && npm install           # frontend deps (Node 20+)
```

Run the demo while developing:

```bash
prompt-workbench demo                 # SQLite + mock provider, seeded data
# in another terminal:
cd frontend && npm run dev            # proxies /api to http://127.0.0.1:8765
```

## Tests

```bash
cd backend && python -m pytest        # backend suite (must pass)
cd examples/javascript && node test.mjs   # cross-language renderer conformance (must pass)
cd frontend && npm run build          # frontend must build cleanly
```

Please add or update tests for any behavior you change. Mock-based tests must remain
deterministic and free of external credentials.

## Guidelines

- Keep the two core seams pluggable: the `Repository` (storage) and `ModelProvider` (AI)
  interfaces. Don't hardcode a specific database or provider into the domain/service layers.
- Runtime semantics (the `simple-v1` renderer, canonical JSON, digests) must stay consistent
  across the backend `domain/`, the `runtime/` package and the JavaScript reference. If you
  change one, update the shared fixtures in `examples/javascript/fixtures.json`.
- Never commit secrets, real customer data, or non-synthetic captures. Demo/seed data must be
  clearly synthetic.
- Follow the existing style: typed, small functions, comments only where they add clarity.
- Record non-obvious design choices in `docs/decisions.md`.

## Commit & PR

- Keep PRs focused. Describe the change and how you verified it.
- Ensure `pytest`, the JS conformance test, and the frontend build all pass.
- By contributing you agree your contributions are licensed under Apache-2.0.
