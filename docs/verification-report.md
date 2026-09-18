# Verification report

Honest record of what was actually executed while building this v1, and what remains for full
coverage. Mock-provider tests are deterministic and require no credentials; a mock test is **not**
a live-provider test.

## Executed and passing

- **Backend test suite** — `cd backend && python -m pytest` → **43 passed**. Covers renderer +
  canonical-JSON conformance, SQLite storage (filters, optimistic replace, transaction rollback),
  prompt draft/revision/label semantics, deterministic checks, run scoring, capture dedupe, release
  build + offline runtime rendering + tamper detection, and API auth/scope/JWT behavior.
- **Cross-language renderer conformance** — `node examples/javascript/test.mjs` → all shared
  fixtures pass; the same fixtures pass from Python. Python and JavaScript agree on canonical JSON
  and `simple-v1` rendering (Unicode, quotes, backslashes, null, arrays, key order, safe integers,
  literal braces, single-pass substitution).
- **End-to-end demo (SQLite + mock)** — `prompt-workbench demo` seeds a login user and synthetic
  data across every entity, executes an evaluation comparing a **Baseline** candidate (pass rate
  1.0) against a **Regressed** candidate (pass rate 0.0), builds a verifiable release, and ingests
  captures. Verified over HTTP via `curl` (login → projects → runs).
- **Portable runtime** — the separate `prompt_workbench_runtime` package loads a workbench-built
  release bundle with the workbench stopped, verifies file hashes, and renders identical messages.
- **CLI CI exit codes** — `prompt-workbench eval` returned **0** for a passing gate and **1** for a
  failing gate against a live local server.

## Environment used

- macOS (Darwin), Python 3.13, Node 24. MongoDB and Docker were **not** available in the build
  environment, so:
  - The MongoDB backend (`storage/mongo.py`) is implemented against `motor` but was **not** run
    against a live MongoDB server here. The SQLite backend is fully exercised by the suite. Both
    implement the same `Repository` interface; the service layer is backend-agnostic.
  - The Docker image (`Dockerfile`, `docker-compose.yml`) is provided but was **not** built here.

## Not yet covered (honest gaps)

- **Live provider tests (A14).** No real OpenAI/Anthropic/Gemini/Ollama/Azure calls were made; the
  LiteLLM adapter is implemented and unit-oriented but requires credentials and a live smoke run to
  claim provider compatibility.
- **Linear chain execution (A31–A33).** The chain contract exists in the data model; full-chain
  execution and step-only replay are minimal in this cut.
- **Rubric (LLM-judge) checks (A29).** Represented as `unscored` in the engine; the judge call path
  is not wired to a provider yet.
- **Optional resolve endpoint (A58)** and **save-triggered evaluations (A56)** are specified but not
  implemented in this cut.
- **Performance benchmarks (section 19)** were not formally measured.

## How to reproduce

```bash
cd backend && python -m pytest
cd ../examples/javascript && node test.mjs
cd ../.. && prompt-workbench demo    # then browse http://127.0.0.1:8765
```
