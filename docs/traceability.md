# Requirements traceability

Maps the specification's capability IDs and a representative subset of the acceptance-test
catalog to the code and tests that implement/verify them. "Provider" = deterministic mock unless a
real LiteLLM connection is configured.

## Capability areas (section 3.1)

| ID | Capability | Where |
|---|---|---|
| PR | Prompt registry | `services/prompts_service.py`, `api/prompt_routes.py` |
| TM | Templates (`simple-v1`) | `domain/rendering.py`, `domain/schema.py`, `domain/models.py` |
| DS | Datasets / input sets | `services/datasets_service.py`, `api/dataset_routes.py` |
| MP | Multiple models | `providers/` (`base`, `mock`, `litellm_provider`, `registry`) |
| PG | Playground / draft tests | `services/runs_service.py` (kind=playground), render with `{draft}` selector |
| EV | Evaluations | `services/runs_service.py`, `domain/checks.py`, `api/run_routes.py` |
| CH | Chains | `domain/models.py::ChainContent` (contract; execution minimal in v1) |
| PB | Publishing | `services/releases_service.py`, `runtime/` package |
| IN | Capture intake | `services/captures_service.py`, `api/capture_routes.py` |
| OB | Observability | runs + captures reads, `services/analytics_service.py` |
| OP | Operations | `cli.py`, `security/`, `storage/`, `config.py` |
| OSS | Public distribution | `LICENSE`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, tests, demo |

## Acceptance tests (representative)

| ID | Scenario | Test / evidence |
|---|---|---|
| A01 | Fresh local install, auth works | `prompt-workbench demo`; `tests/test_api.py::test_login_and_me` |
| A03 | Draft vs revision | `tests/test_prompts.py::test_autosave_changes_draft_only…` |
| A04 | Concurrent draft edits → 409 | `tests/test_prompts.py::test_stale_draft_returns_conflict` |
| A05 | Simultaneous saves / unchanged | `tests/test_prompts.py::test_unchanged_save_does_not_consume_version` |
| A06 | Label ownership/conflict | `tests/test_prompts.py::test_label_conflict_and_ownership` |
| A07 | Restore | `tests/test_prompts.py::test_restore_creates_new_revision…` |
| A08 | Render validation before model call | `tests/test_renderer.py::test_missing_variable_before_model_call` |
| A09 | Renderer conformance (Py/JS) | `tests/test_renderer.py`, `examples/javascript/test.mjs` (shared fixtures) |
| A10 | No template execution | `tests/test_renderer.py::test_unsupported_expression_rejected` |
| A11 | Dataset snapshot isolation | `services/datasets_service.py::snapshot_cases` |
| A16/A17 | JSON/tool checks | `tests/test_checks.py` |
| A18 | Comparison isolation | `services/runs_service.py` (independent cells); `tests/test_runs.py` |
| A27 | Scoring denominator (unscored ≠ 100%) | `tests/test_runs.py::test_no_required_checks_is_unscored…` |
| A28 | CI exit codes | `services/runs_service.py::report`; `cli.py::eval` (verified 0 and 1) |
| A34 | Capture dedupe | `tests/test_runs.py::test_capture_idempotency` |
| A35 | Capture-key authorization | `tests/test_api.py::test_capture_key_scope_enforcement` |
| A38 | Bundle portability (offline render) | `tests/test_release_runtime.py::…renders_offline` |
| A40 | Bundle integrity | `tests/test_release_runtime.py::test_tampered_bundle_fails_verification` |
| A44 | Secret containment | `tests/test_api.py::test_secret_never_leaks_in_connection_read` |
| A49 | JWT lifecycle | `tests/test_api.py::test_logout_invalidates_token`, `test_protected_routes_require_auth` |
| A52 | Public package hygiene / synthetic demo | `seed/demo_seed.py` (synthetic), `LICENSE`, docs |

See `docs/verification-report.md` for what was actually run and what remains for live-provider and
platform coverage.
