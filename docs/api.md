# HTTP API

Base prefix: `/api/v1`. All responses are JSON (UTF-8). FastAPI serves an OpenAPI document at
`/docs` (Swagger UI) and `/openapi.json`.

## Authentication
- `POST /auth/login` — body `{username, password}` → `{access_token, token_type, expires_in}`.
- Send `Authorization: Bearer <token>` on every other request.
- Interactive users authenticate with JWTs; service integrations use scoped API keys
  (prefix `pwk_...`). Scopes: `captures:write`, `captures:read`, `registry:read`,
  `registry:write`, `runs:write`, `runs:read`, `releases:read`.
- `POST /auth/logout`, `GET /auth/me`.

## Error shape
```json
{ "error": { "code": "stale_draft", "message": "…", "details": {}, "request_id": "…", "retryable": false } }
```
Status codes: 400 malformed, 401 auth, 403 scope, 404 missing, 409 conflict/stale, 413 too large,
422 invalid config, 429 rate limited.

## Endpoint summary

| Method & path | Purpose |
|---|---|
| `GET/POST /projects`, `PATCH /projects/{id}` | Projects & policy settings |
| `GET/POST /connections` | Provider connections (secrets by env-var name only) |
| `GET/POST /model-profiles` | Non-secret model configurations |
| `GET/POST /prompts`, `GET /prompts/{id}` | Registry metadata |
| `GET/PUT /prompts/{id}/draft` | Shared draft (optimistic `expected_edit_sequence`) |
| `GET/POST /prompts/{id}/revisions`, `GET …/{version}` | Immutable revisions |
| `POST /prompts/{id}/restore-draft` | Copy a revision into the draft |
| `GET/PUT /prompts/{id}/labels/{label}` | Move a label (expected previous revision) |
| `POST /prompts/{id}/render` | Render a selector + inputs (no model call) |
| `GET /prompts/{id}/diff?from=&to=` | Text/structural diff |
| `GET/POST …/revisions/{v}/comments`, `DELETE /comments/{id}` | Revision discussion |
| `GET /prompts/{id}/analytics` | Aggregates grouped by revision/model |
| `GET/POST /datasets`, `GET /datasets/{id}` | Datasets |
| `GET/POST/PATCH/DELETE /datasets/{id}/cases[/{case_id}]` | Cases |
| `POST /datasets/{id}/import-preview`, `POST /datasets/{id}/imports` | Import |
| `GET /datasets/{id}/export?format=jsonl\|csv` | Export |
| `POST /runs/preview`, `POST /runs` | Plan estimate; start a run (202) |
| `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/cells` | Progress & matrix |
| `POST /runs/{id}/cancel`, `POST /runs/{id}/cells/{cell}/reviews` | Cancel; human review |
| `GET /runs/{id}/report` | JSON report + CI `exit_code` |
| `POST /captures`, `GET /captures[/{id}]` | Ingest / inbox |
| `PATCH /captures/{id}/review`, `POST /captures/{id}/promote` | Review / promote to case |
| `POST /releases`, `GET /releases[/{id}][/download]` | Build / list / download bundle |
| `GET/POST /api-keys`, `DELETE /api-keys/{id}` | Scoped integration keys (secret shown once) |
| `GET /change-events` | Non-sensitive change history |
| `GET /health/live`, `GET /health/ready` | Probes (also unprefixed) |

## Run request (example)
```json
{
  "project_id": "…",
  "kind": "evaluation",
  "dataset_id": "…",
  "candidates": [
    {"label": "Baseline",  "target": {"kind": "prompt", "id": "…", "selector": {"revision": 2}}, "model_profile_id": "…"},
    {"label": "Candidate", "target": {"kind": "prompt", "id": "…", "selector": {"label": "production"}}, "model_profile_id": "…"}
  ],
  "checks": [
    {"id": "vj", "type": "json_valid", "required": true},
    {"id": "len", "type": "array_length", "required": true, "pointer": "/actions", "min": 1}
  ],
  "baseline_label": "Baseline",
  "repeats": 1,
  "gate": {"min_pass_rate": 0.95}
}
```

A selector is exactly one of `{"revision": N}`, `{"label": "production"}`, or `{"draft": <content>}`.
