# Prompt Workbench — v1 product and engineering specification

Status: updated v1 scope (revision 2), superseding the earlier specification. Research date: 9 September 2026. Working name: Prompt Workbench; final project/package name must be checked before public distribution.

This is a specification for a new, fully open-source product. It is not an implementation or a claim that any acceptance test has already passed. Normative words MUST, SHOULD, and MAY identify requirements, recommendations, and permitted choices. Requirements outside the explicitly deferred scope are part of the finished v1, even where implementation is divided into milestones.

## 1. Product decision

Build a local developer application for creating, versioning, testing, comparing, and publishing prompts and linear prompt chains. Use Python for the backend and execution engine, React/TypeScript for the editor, SQLite for durable state, and the LiteLLM Python SDK for model access. Distribute a Python-installable application with a bundled frontend; Node is needed only when developing the frontend.

The main workflow is:

1. Create a named prompt with a stable UUID and dynamic variables.
2. Save named input examples, or import captured application requests.
3. Compare prompt revisions and model configurations on the same examples.
4. Inspect outputs, automatic checks, human judgments, latency, tokens, and estimated cost.
5. Save an immutable prompt revision and assign the `production` label to the preferred revision.
6. Publish a self-contained release bundle containing exact prompt, chain, and model configurations.
7. Load the bundle from Actor or another application without a connection to the workbench.
8. Bring selected application executions back as examples for later tests.

The public launch is the source code/package release. Installed dashboards remain private. Do not publish a user's instance, prompts, datasets, captures, or results.

### 1.1 Product promise

“Develop and compare prompts locally. Ship the exact versions you tested as ordinary files.”

### 1.2 Supported v1 operating envelope

- One installation, one workspace, multiple projects, one Python server process, one SQLite database on local disk.
- Primary deployment: a developer laptop. Secondary deployment: one private development server for a small trusted engineering team.
- Design/benchmark target: 1–10 developers, 100 prompts, 10,000 dataset cases, and 100,000 captured/model-call records with paginated reads. These are acceptance targets, not established performance claims.
- Default concurrent outbound model calls: 4 globally and 2 per configured connection.
- No Redis, PostgreSQL, message broker, cloud control plane, LiteLLM proxy server, or external telemetry service is required.
- Internet access is required only for explicitly configured remote model calls. Registry, editing, mock tests, imports, exports, and local model calls work offline after dependencies/models are installed.
- Keep this a practical local developer product. Use basic username/password login with JWT, ordinary version history, bounded model calls, and portable production artifacts. Keep account administration minimal.

## 2. PromptLayer research and deliberate v1 choices

### 2.1 Updated scope from the requested prompt-management page

The requested [PromptLayer prompt-management page](https://www.promptlayer.com/prompt-management/) describes versioning/diffs, provider-independent templates, visual function definitions, per-version usage analytics, comments, labels, regression automation, snippets, flexible templating, and runtime retrieval. This version adopts the corresponding simple developer workflows below. It retains offline file deployment and defers full template engines and live traffic segmentation. No compatibility with PromptLayer's API or file format is promised.

| Page capability | Updated v1 behavior |
|---|---|
| Version control | Immutable saves, change notes, diffs, and rollback of labels. |
| Model-independent blueprints | Provider-neutral message/schema definitions plus explicit LiteLLM profiles. |
| Function builder | Small visual parameter editor with raw JSON Schema access. |
| Usage analytics | Filter/group by exact prompt revision and selected model. |
| Collaboration | Flat revision comments and attribution; no approval hierarchy. |
| Regression automation | Opt-in evaluation after an explicit version save. |
| Snippets/templating | Pinned reusable text fragments compiled into portable templates; existing strict variables. |
| Runtime access | Optional authenticated resolve endpoint; file bundles remain the recommended Actor path. |

### 2.2 Original requirement coverage

| Original requirement | Concrete implementation |
|---|---|
| Prompt name and UUID | Stable prompt identity, immutable numbered revisions, readable slug. |
| Dynamic prompt tags | Typed `{{variable}}` inputs with validation and preview. |
| Saved dynamic data | Named input sets backed by versioned dataset cases. |
| Compare various models in a dashboard | Explicit candidate columns, identical cases, LiteLLM, scores/tokens/cost/latency. |
| Activate preferred version for a UUID | Static labels; `production` is the preferred revision selector. |
| Development-only interface | Local Python server, private React UI, basic JWT login. |
| Publish for production use | Immutable export bundle containing exact resolved definitions. |
| Any language can use published files | JSON format, specified renderer, Python runtime, JavaScript reference. |
| Local database | SQLite for prompts, examples, runs, metrics, and metadata. |
| Full prompt chains | Ordered steps with separately selected prompt revisions and explicit bindings. |
| Published or overridden chain steps | Resolve saved labels or development overrides once per run/bundle. |
| External service saves prompt/data | Registry write API plus a separate capture-only ingestion API. |
| Capture merged or structured requests | Distinct replay modes; explicit mapping when original variables are unavailable. |
| Fully open-source | All v1 functions included, no cloud account or paid license feature gates. |

### 2.3 Detailed workflow references

Research is based on official documentation and the two user-supplied screenshots. The screenshots guide interaction density and layout; they do not establish undocumented functionality. Reproduce the useful workflow with original branding and assets.

| Verified reference behavior | Our v1 decision | Deferred work |
|---|---|---|
| PromptLayer's editor stores messages, variables, settings, and version history; saves support diffs and commit messages. [Editor documentation](https://docs.promptlayer.com/features/prompt-registry/prompt-editor-versioning) | Role-based message editor; mutable draft; explicit immutable saves; revision diff and change note. | AI prompt writer. |
| Named input variable sets can be reused, loaded into prompts/workflows, and imported from files or logs. [Input sets](https://docs.promptlayer.com/features/prompt-registry/input-variable-sets) | One reusable case/dataset model; editor calls selected cases “Input sets.” JSON, JSONL, CSV, and captures feed the same cases. | Cross-workspace sharing and nested folders. |
| Labels select prompt versions; dynamic labels also support traffic segmentation. [Release labels](https://docs.promptlayer.com/features/prompt-registry/release-labels) | Static `development`, `staging`, and `production` labels. Resolve labels to exact revisions when testing or publishing. | Dynamic routing, A/B traffic allocation, and canary deployment. |
| Current PromptLayer documentation uses Tables for datasets, computed outputs, checks, history, and batch work, including selected-cell reruns. [Tables](https://docs.promptlayer.com/features/tables/overview) | Keep the user's familiar “Evaluations” tab; rows are cases and columns are explicit candidates. Selected reruns create linked runs. | General spreadsheet formulas, arbitrary computed columns, and multiple sheet types. |
| Structured output configuration uses JSON Schema. [Structured outputs](https://docs.promptlayer.com/features/prompt-registry/structured-outputs) | Static JSON Schema and explicit native-versus-validation-only mode. | Dynamic schema templating and elaborate visual schema builders. |
| Workflows support multi-step orchestration. [Workflows](https://docs.promptlayer.com/why-promptlayer/workflows) | Linear ordered prompt steps with typed bindings and individual/full-chain testing. | Graph canvas, branching, looping, arbitrary code, and external actions. |
| Request logs and traces expose model input/output, timing, usage, cost, and parent-child execution. [Observability](https://docs.promptlayer.com/features/observability/overview) | Local run log, linear-chain step detail, capture inbox, filters, and simple aggregates. | Full application observability, OpenTelemetry ingestion, and distributed tracing infrastructure. |

Our portable release contract and database-backed local scheduler are original design decisions, not claims about PromptLayer compatibility. No PromptLayer SDK or service dependency is permitted.

## 3. Scope and priorities

### 3.1 Required for v1 completion

| ID | Capability | Required outcome |
|---|---|---|
| PR | Prompt registry | Create, search, tag, archive, edit drafts, save revisions, diff, restore into draft, assign labels, reuse pinned snippets, and comment on revisions. |
| TM | Templates | Text/chat prompts, strict variables, typed inputs, deterministic rendering, JSON output validation, function tool definitions. |
| DS | Input sets/datasets | Named examples, schema validation, revisioned rows, imports/exports, expected values, tags. |
| MP | Multiple models | LiteLLM SDK integration; configured connections/profiles; explicit provider capability handling. |
| PG | Playground | Unsaved draft tests, saved inputs, multiple candidates, output inspection, cancellation. |
| EV | Evaluations | Persistent runs, comparisons, deterministic checks, optional rubric judge, human review, CI gates, and opt-in tests on version save. |
| CH | Chains | Linear steps, version selection, input mappings, step/full-chain tests, comparison of chain candidates. |
| PB | Publishing | Atomic release snapshots, portable files, local runtime loader, rollback, Python example and JavaScript reference loader. |
| IN | Capture intake | Authenticated ingestion, idempotency, JSONL import, structured/merged requests, capture-to-case review. |
| OB | Observability | Runs and captures with token/cost/error details and chain hierarchy. |
| OP | Operations | SQLite migrations, basic JWT login, scoped integration keys, retention, bounded jobs, packaged local launch. |
| OSS | Public distribution | Open license, runnable demo, dependency locks, tests, installation and contribution documentation. |

### 3.2 Explicitly outside v1

Organizations/billing; public sharing links; high availability; multi-host or multi-process worker fleets; a required runtime registry dependency; proxying Actor's production calls; automatic deployments; automatic model routing/fallback; prompt optimization agents; RAG/vector databases; arbitrary code evaluators; user-supplied Python execution; shell/HTTP workflow steps; MCP execution; autonomous tool loops; image/audio/video generation or inputs; dynamic schemas; nested snippets; full Jinja2/f-string engines; Git bidirectional synchronization; rich branching workflows; attachments or remote URL fetching; full telemetry infrastructure.

Function tool schemas and returned tool calls are supported, but the workbench MUST NOT execute their functions. This makes testing tool selection and arguments possible without building an agent runtime.

## 4. Access and navigation

### 4.1 Basic local authentication

- Local username/password accounts authenticate with signed JWT access tokens. All authenticated users have the same developer access; no role hierarchy or permission-management UI.
- Create the first account with `init`; add or reset local accounts through CLI. Disable public registration.
- Use scoped opaque API keys for external integrations, separate from interactive JWTs. Keep project restriction and the scopes `captures:write`, `registry:write`, `registry:read`, `runs:write`, `runs:read`, and `releases:read` because an intake-only service should not be able to publish or spend model credits.
- Projects organize prompts and tests. They are not isolated tenants. Settings and connection configuration are available to signed-in developers.
- Implement JWT details in section 17.1. Do not implement an additional cookie-session login system.

### 4.2 Navigation

Three primary tabs: **Prompt Registry**, **Evaluations**, **Observability**. Workspace/project switcher and Settings are secondary controls. Registry has Prompts, Snippets, Chains, and Releases subviews. Evaluations contains Datasets and Runs. Observability contains All Calls and Capture Inbox. Prompt details include History, Comments, and Analytics panels.

Keep the main editor visible without navigating through a wizard. Use drawers for model settings, schema/tools, input sets, and run detail.

## 5. Identity and revision semantics

- All durable entities receive server-generated UUIDv4 identifiers. Display readable slugs beside UUIDs; UUID is the authoritative identity.
- Names are editable. Slugs match `[a-z0-9][a-z0-9._-]{0,79}` and are unique within project/entity type. Slugs become immutable once the first revision is saved; changing one requires creating a new entity.
- Prompt revision numbers are positive, monotonically increasing integers within a prompt. The revision also has its own UUID.
- A prompt has one shared mutable draft with an integer `edit_sequence`. Autosave changes only the draft; it never publishes a version.
- `Save version` creates an immutable revision from the submitted draft sequence, with non-empty change note and author. Identical content to the newest revision returns that revision with `unchanged: true`, without consuming a number.
- A stale draft update returns HTTP 409 with current sequence and changed fields; the UI offers reload or save as a new prompt, never silently overwrites.
- The application computes a SHA-256 content digest over canonical JSON of the complete semantic configuration. IDs, timestamps, and change notes are outside the semantic digest. Preserve whitespace inside prompt strings.
- Labels point to one revision of one prompt or chain. Label update includes the expected previous revision (including explicit null for first assignment), so stale updates return 409.
- Restoring an old version copies its content into the draft. Saving then creates a new revision if content differs from the latest revision. Existing revisions never change.
- Archive hides entities from default lists but retains references. Archived entities cannot start new tests or be newly selected for releases. Existing bundles remain usable.
- Prompt and chain version numbers are independently scoped. A label is never silently interpreted as `latest`. Missing selections fail clearly.

## 6. Prompt contract and rendering

### 6.1 Prompt definition

Canonical prompt revision payload fields:

| Field | Contract |
|---|---|
| `format_version` | `1` |
| `kind` | `chat` or `text` |
| `template_engine` | `simple-v1` |
| `messages` | Ordered chat items with `role` and `content`; roles system, user, assistant in editable v1 prompts. |
| `text` | Used only for kind=text; adapter converts it to one user message. |
| `input_schema` | JSON Schema object with named top-level properties and required list. |
| `output` | `mode`: text/json/native_json_schema; `schema` when JSON validation is required. |
| `tools` | Array of JSON function definitions, empty by default. |
| `tool_choice` | none/auto/required or a named function; validated against tools/capability. |
| `default_model` | Optional embedded snapshot of profile execution fields. |

V1 editable chat prompts contain string message bodies only. Captures can retain normalized tool messages and tool calls without exposing them as an interactive conversation-history editor. A message role is never interpolated from user input.

### 6.2 `simple-v1` rules

1. Only top-level variable names matching `[A-Za-z_][A-Za-z0-9_]*` are supported. `{{name}}` and `{{ name }}` reference the same variable.
2. `{{!literal}}` emits `{{literal}}`. Parse this escape before ordinary placeholders. Unsupported expressions such as `{{user.name}}`, filters, function calls, and unmatched delimiters fail template validation.
3. Values are substituted once. A variable containing `{{another}}` remains literal data; no recursive expansion.
4. Strings are inserted exactly as strings. Other JSON values render as RFC 8785 canonical JSON. This rule also governs content digests. Use a tested implementation with Python/JS conformance fixtures. Reject non-finite numbers, invalid Unicode, and integers outside the interoperable safe-integer range.
5. Input schemas support string, number, integer, boolean, null, array, and object; a type array may express nullability. Only `string` values insert without JSON quotes. JSON Schema validation occurs before rendering.
6. Defaults are applied only to missing top-level properties; explicit null never invokes a default. No recursive default filling or type coercion.
7. Referenced variables must be declared. Every required property must exist after defaults. Extra dataset fields are excluded by an explicit input mapping; unmapped extras are not injected. The normalized input object validates with `additionalProperties: false`.
8. Template interpolation is performed after parsing the prompt JSON structure. Never interpolate into raw JSON file bytes. JSON escaping then belongs to the serializer.
9. Rendering does not HTML-escape strings or execute code. Displayed data is safely escaped by the frontend. Untrusted email content remains user data, with its own message boundary where feasible.
10. Validate all messages and the final request size before scheduling calls. UI preview and production loader use the same Python renderer; the JS reference must pass the same fixtures.

Input/output schemas use JSON Schema Draft 2020-12. Allow local `$defs`/local references; reject external references and remote schema fetching. Reject schema documents over 64 KiB or nesting over 20. Compile schemas once per run snapshot. Native provider schema restrictions can be narrower than this local validator.

### 6.3 Output modes

- `text`: preserve response text; no automatic parsing or hidden transformations.
- `json`: preserve original text and parse as exactly one JSON value, then validate against the saved schema if present. No Markdown-fence stripping, repair calls, or invented values. Do not claim provider-native enforcement.
- `native_json_schema`: pass an equivalent provider schema through LiteLLM only when supported; also validate locally. Unsupported combinations fail preflight. User may explicitly create another candidate in json mode; never silently degrade.
- Refusals, truncation, no text, and invalid JSON remain visible, distinct outcomes. An HTTP-successful model response can have a validation failure.
- V1 disallows combining non-empty function tools with native_json_schema to avoid inconsistent provider combinations. Tool-mode results expose structured `tool_calls`, validate names/arguments against their definitions, and stop after that model response.

### 6.4 Reusable snippets, kept simple

PromptLayer documents reusable template references. Our implementation uses pinned text fragments and explicit inclusion controls rather than duplicating its syntax. [Snippet reference](https://docs.promptlayer.com/features/prompt-registry/snippets)

- Reuse the prompt registry for snippets: a snippet is a `kind=text` prompt with `is_snippet=true`. It has UUID, revisions, text, input schema, and tags. It cannot include another snippet in v1.
- In the editor, an Insert snippet button selects a snippet and exact saved revision. Show a pill with its name/version and an expanded preview. No implicit latest selection. Labels may help the user choose but are resolved to a revision immediately on insertion.
- Store authoring content as ordered parts per message: `{type: "text", text: "..."}` or `{type: "snippet", prompt_id: "...", revision: 2}`. This is editor metadata; executable `messages[].content` remains a string after compilation.
- During save or draft-test snapshot creation, expand pinned fragments, concatenate parts without hidden separators, and validate the resulting `simple-v1` template. Save source parts, exact dependency IDs/digests, and flattened executable content. Include all of these in revision identity; compute the runtime configuration digest from the flattened executable fields.
- All fragment variables become parent input properties. Merge nonconflicting schemas; identical shared definitions are permitted; conflicting definitions/defaults fail until the user resolves them. Required lists are unioned. No fragment-local variable namespace or automatic variable renaming.
- Updating a snippet does not change saved parents. A usage list shows referencing parents; the user chooses Update snippet reference, reviews the expanded diff, and saves a new parent revision. This new parent save can trigger its configured regression test.
- Release bundles contain flattened strings and optional non-executable dependency provenance, so production needs no snippet lookup/engine. Snippets are not independently executable entrypoints unless explicitly selected and given a model profile.
- API draft/revision schemas distinguish optional `authoring_source` from the compiled runtime definition. Server compilation is authoritative; reject mismatched client-supplied compiled content rather than trusting it.

### 6.5 Tools & Output visual editor

Provide a minimal form for function name/description and parameter name, type, description, required flag, and enum values. Support simple object nesting/array item types, with JSON Schema mode for advanced definitions. Switching modes must preserve fields; unsupported visual constructs stay in JSON mode rather than being discarded. Use the same small schema editor for structured outputs. These are schema definitions only; the application never executes generated function calls. [PromptLayer tool editor reference](https://docs.promptlayer.com/features/prompt-registry/tool-calling)

## 7. Connections, model profiles, and LiteLLM

Use the LiteLLM **Python SDK in-process**, not its separately deployed proxy. Async completions are documented by LiteLLM; use an application-owned adapter around that interface. [Async SDK reference](https://docs.litellm.ai/docs/completion/stream)

### 7.1 Separation of configuration

- Connection: installation-specific provider, optional approved base URL, optional API version, and secret reference. Secrets resolve from environment variables. Do not store provider API-key values in SQLite or expose them to React.
- Model profile: readable name, exact LiteLLM model identifier, connection reference, temperature/top_p when supported, output token limit, reasoning settings when supported, timeout, and allowlisted provider options.
- Portable model snapshot fields are `profile_id` (optional provenance), `name`, `connection_alias`, `provider`, `model`, `parameters`, `timeout_seconds`, and `retry_policy`. Installation endpoint/credential fields are excluded. At run start snapshot the approved non-secret connection endpoint/configuration as internal provenance as well; subsequent developer edits apply only to new runs. Resolve only secret values at dispatch, so credential rotation remains possible without changing prompt content.
- Profile edits increment `edit_sequence`. Prompt saves and test candidates embed a full non-secret profile snapshot. Editing the original profile never changes an already-saved prompt, job, or release.
- Credentials/base URLs are installation bindings, outside portable artifacts. A release uses `connection_alias`, resolved from a runtime-supplied configuration. Alias mappings must be available when executing, but plain rendering does not require them.
- Model identifiers are configurable strings. Never infer that every model on a provider supports all features or hardcode the current model catalog as authoritative.

### 7.2 Required provider paths

| Provider path | V1 requirement |
|---|---|
| OpenAI | Direct API via LiteLLM; text/chat and supported structured output. |
| Anthropic | Direct API via LiteLLM; same normalized result envelope. |
| Google Gemini | AI Studio API via LiteLLM; same envelope. |
| Ollama | Explicit localhost/private model endpoint through LiteLLM; no cloud dependency. |
| OpenAI-compatible | Developer-approved base URL, explicit provider/model configuration. |
| Azure OpenAI | Configurable deployment identifier, API version, and endpoint; contract-tested, live-tested when credentials exist. |

Additional LiteLLM providers are best effort until covered by adapter contract tests. No claim of universal model compatibility.

### 7.3 Capability and request handling

- Consult LiteLLM capability helpers, supplemented by tested adapter rules. Unsupported/unknown status is shown explicitly. [Schema capability reference](https://docs.litellm.ai/docs/completion/json_mode)
- Do not enable silent parameter dropping. Do not send temperature, seed, or tool settings that the selected model rejects. Optional settings default to unset, rather than fabricated cross-provider defaults.
- Allow advanced model settings only through a typed allowlist. Reject options that change credentials, networking, callbacks, logging, executable classes, routing, or filesystem access.
- Record requested profile, resolved model name, LiteLLM version, effective non-secret request, provider request ID if available, and capability warnings.
- No automatic fallback to another model: that would invalidate comparisons.
- Capture normalization is application-owned; provider response objects must not leak throughout the data model.
- Non-streaming model calls are sufficient for v1. UI gets durable job/cell progress through polling. Token streaming is deferred to avoid mixing unreliable deltas with stored final outputs.

### 7.4 Usage and costs

Store input/output/total token counts as nullable integers, provider usage detail as sanitized JSON, duration in milliseconds, and cost in USD as decimal strings persisted in TEXT columns. Include cached/reasoning token fields when available, without adding them again to totals that already include them.

`cost_source`: provider_reported / litellm_estimate / manual_rate / unknown. Preserve the rate snapshot and date. A missing cost or token count is null, not zero. Aggregates report known subtotal and unknown count. Local models have zero external API cost only if explicitly configured that way; hardware cost is not measured.

LiteLLM documents token/cost helpers and a local model-price map option. Use the bundled/local map by default, allow developer-configured manual rates, and require an explicit action to refresh remote pricing. Disable telemetry and external callbacks; verify startup/run egress in tests. [Usage/cost reference](https://docs.litellm.ai/docs/completion/token_usage)

## 8. Datasets and input sets

### 8.1 Data model and editing

- A dataset has UUID, project, name, description, mutable head, tags, and monotonically increasing revision counter.
- A case has stable UUID, readable name, `inputs`, optional `expected`, optional `reference_notes`, tags, `critical` boolean, and optional source capture ID.
- Each create/update/delete increments the dataset revision in the same transaction. Updates append immutable case revisions; deletion adds a tombstone. Store schema versions with the dataset.
- At test start, create a dataset snapshot listing exact case revision IDs and copied case payloads. Later edits cannot change old results.
- Input sets shown within the prompt editor are simply cases selected from datasets. “Save input set” defaults to a per-project Scratch examples dataset. Do not maintain a duplicate input-set storage system.
- Dataset schemas describe `inputs`; prompt mapping determines which subset feeds a candidate. Expected values never go into the candidate prompt unless explicitly mapped and visibly disclosed.

### 8.2 Import/export

- JSON array and JSONL: native case format.
- CSV: preview headers; map columns to variable names; explicitly select string/JSON interpretation. Defaults to strings, preserving IDs and leading zeros. `expected` and tags use explicit mappings.
- Validate before commit; display row-specific errors. Default is all-or-nothing import. An explicit “Import valid rows” option returns accepted/rejected counts and an error report.
- Limits: 10 MiB per import, 5,000 rows per import; configurable by a developer. Do not load unbounded files into memory.
- JSONL export preserves types and metadata. CSV export neutralizes formula-leading cells and records that a spreadsheet-safe transformation was applied.
- Importing the same file does not silently replace cases: default create, optional upsert by case UUID within the selected dataset with conflict preview.

## 9. Playground and comparison UI

### 9.1 Editor based on the supplied references

- Top bar: prompt name, draft/save status, revision selector, model profile picker, Tools & Output button, Save version split button.
- Main body: vertically ordered message editors with role selection, move/delete, highlighted `{{variables}}`, line numbers, and wrap enabled by default.
- Right drawer: variable schema, current values, saved input-set selector, required-field errors.
- Bottom resizable pane: Outputs, input-set count, primary Run action. Empty state explains the next action.
- Comparison mode adds candidate columns: a candidate is one prompt snapshot plus one model snapshot. Add up to 8 candidates and 20 input sets in the playground. Larger batches move to Evaluations.
- Unsaved draft runs are permitted; first freeze an anonymous immutable snapshot in the run. Display “Draft snapshot” and its digest. It is never relabeled or mutated if the draft changes.
- `Cmd/Ctrl+S`: save version dialog. `Cmd/Ctrl+Enter`: run after preflight. Shortcuts do nothing destructive when a dialog/input composition is active.
- Browser refresh reloads the saved draft and current run status after authentication. No fake output, simulated progress, or silent failure in connected mode.

### 9.2 Result cell and detail

Each result cell displays status, short output, checks summary, duration, tokens, and cost availability. Click opens original rendered messages, raw response text, parsed JSON/tool calls, errors, model/profile snapshot, checks, and attempt history. Side-by-side view can compare two outputs; text diff and JSON structural diff are available. HTML is displayed as text; no automatic HTML-email execution/preview in v1.

Every result links back to exact source revision/snapshot. A banner marks results stale when the current editor or dataset differs, while preserving the original result.

### 9.3 Version discussion

Add a flat Comments panel on a prompt/chain revision. A comment has UUID, author, UTC timestamp, and plain-text body up to 4,000 characters. The author may edit/delete their own comment; these changes do not create a prompt revision or modify release digests. No mentions, notifications, threads, required reviewers, or approval workflow. Change notes explain a save; comments discuss it. Existing result reviews remain separate.

## 10. Evaluations, checks, and decisions

### 10.1 Experiment definition

An evaluation definition contains name, project, target kind prompt/chain, dataset reference, selected case filter, explicit candidate array, check definitions, optional baseline candidate ID, repeat count, concurrency, cost policy, and pass thresholds.

Candidates are explicit combinations, not an automatically exploding Cartesian product. Provide a UI helper to generate combinations and show the count before execution. Each chain candidate specifies one chain revision/snapshot and optional step overrides. Expand all selectors and bindings once into a frozen experiment manifest.

Default repeats: 1; allowed 1–5. Show the planned number of generation and judge calls. Default maximum 5,000 generation calls per batch after counting all chain steps and repeats; reject larger requests until split into smaller runs.

### 10.2 Required check types

| Check | Behavior |
|---|---|
| `json_valid` | Whole output parses as a JSON value. |
| `json_schema` | Parsed value satisfies a saved schema; include paths of violations. |
| `equals` | Exact string or deep typed JSON equality; normalization only if explicitly configured. |
| `contains` / `not_contains` | Explicit case-sensitivity setting, default sensitive. |
| `json_pointer_equals` | Resolve RFC 6901 pointer and compare to literal expected value or expected-data pointer. Missing path fails. |
| `array_length` | Assert min/max at a JSON pointer. |
| `tool_call` | Expected function name, optional call count, and argument schema/field assertions. |
| `rubric` | Optional model judge scores output from 0 to 1 and gives a concise justification in validated JSON. |

No arbitrary code or regular-expression evaluator is required. Each check has ID, name, type, immutable config snapshot, `required` flag, and threshold where relevant. Check target is final output by default; chains may specify a step ID. Assertion expected values live outside generation inputs.

### 10.3 Judge and human review

- Rubric judges use a separately selected frozen model profile, fixed instruction template, rubric text, and threshold. Run one judgment per candidate/case/repeat; no hidden ensembles.
- Judge prompt clearly delimits case input, expected data, rubric, and candidate output as data. Output instructions in the candidate result must not become judge instructions.
- Malformed/refused judge output records evaluator error; never a pass or invented score. No automatic judge repair call in v1.
- Judge calls count separately in cost and usage totals and in scheduling limits. Judge changes create a new run/rescore operation, never overwrite previous scores.
- Human review: pass/fail/unreviewed and note; optional A/B/tie preference. Append each review event with actor and timestamp; show latest judgment while retaining history.
- Human judgments do not silently replace machine checks. If `requires_human_review` is enabled in a release policy, unresolved/failing review blocks the gate separately.

### 10.4 Scores and CI gate semantics

Separate provider execution outcome from quality outcome:

- Execution: queued/running/succeeded/failed/cancelled/interrupted/skipped.
- Quality: pass/fail/error/unscored; human review is a separate field.
- A successful response passes a case only when all required checks pass. No required checks means unscored, never 100% pass.
- Generation errors, required evaluator errors, skipped/cancelled planned cells, and missing results contribute zero to pass numerator. Pass rate denominator is all planned case-repeat cells for that candidate. Show completion rate separately.
- Optional checks show scores but do not change pass/fail. For rubric checks, compare score against their own threshold; no opaque mixed-score average.
- Baseline regression: compare pass rates on identical case snapshots/repeats and check definitions. Otherwise mark comparison non-comparable. Show per-case pass→fail regressions.
- A critical case must pass on every repeat when a gate is enabled. Keep flaky-case counts visible.
- Suggested default gate after checks are configured: pass rate ≥95%, maximum baseline drop 0 percentage points, all critical cases pass, and no execution/evaluator errors. These are editable project policies, not universal quality guarantees.
- An evaluation without a baseline can pass absolute gates; no baseline delta is fabricated. A run with no checks cannot satisfy an automated quality gate.
- Save evaluation report as JSON and JUnit XML; CLI exits 0 for gate pass, 1 for completed evaluation with gate failure, 2 for setup/infrastructure/incomplete run. If execution errors exist, exit 2 even if quality also failed.

### 10.5 Comparison surface

Rows: frozen cases. Columns: candidates. Sticky inputs and expected columns, filter by status/tag/regression, and column headers with pass rate, known cost plus unknown count, p50/p95 latency, and completion count. Use completed fresh generation durations for latency, show sample count, and exclude judge duration from generation latency. Chain latency is end-to-end elapsed time. Never present statistical significance from a single sample.

Rerun failed/selected cells creates a new child run with `parent_run_id` and selected cell keys. Preserve the original. Rescore saved outputs is another explicit child run and makes no generation calls; judge calls may still cost money.

### 10.6 Optional regression test after save

- Disabled by default. Each prompt/chain can link one saved evaluation definition and designate which candidate should use its newly saved revision. Other candidates remain the configured baseline/model choices.
- Enabling requires an explicit model-spend confirmation and a per-run budget/call limit; show the selected dataset, models, and checks. Validate credentials and capabilities before enabling.
- Only an explicit successful new revision save triggers a run. Draft autosave, comments, label moves, unchanged saves, and capture ingestion never trigger paid calls.
- Snapshot the evaluation definition and dataset at save time. Insert the accepted run alongside the revision transaction after validation. Use unique `(target_revision_id, trigger_rule_id)` to prevent duplicate scheduled runs on request retries.
- If evaluation setup becomes invalid, save the revision and return a visible `auto_evaluation: blocked` reason; do not roll back the user's prompt edit or silently claim a test ran. No later background retry.
- Execution uses the same scheduler, cancellation, costs, and reports as manual runs. Show queued/running/pass/fail/error beside the version; never automatically move labels or publish.
- A service-created revision triggers only if its request explicitly permits `run_linked_evaluation=true` and the service key also has `runs:write`; default false. This prevents registry-only keys from spending money indirectly.

### 10.7 Prompt-version analytics

The prompt detail page includes an Analytics view grouped by exact revision and model: call count, generation success/error count, known cost subtotal, unknown cost count, tokens where known, p50/p95 latency, check pass rate with denominator, and human feedback count. Filter by date, source (playground/evaluation/capture), and environment. Default views keep tests and production captures separate. Unknown/unresolved capture references form their own group; no guessing the current version. Use SQLite aggregates/paginated detail, not a new analytics service. Apply the cost/latency/score semantics already defined in sections 7 and 10.

## 11. Linear chain contract

### 11.1 Supported behavior

- A chain is named/versioned/labeled like a prompt, with its own input schema and 1–10 ordered steps.
- Each step has a unique stable `step_id`, selected prompt revision or label, optional model override, and bindings for every required prompt input.
- Bindings are typed descriptors: `{source: "input", pointer: "/email"}`, `{source: "step", step_id: "classify", pointer: "/json/category"}`, or `{source: "literal", value: ...}`.
- Runtime step envelope exposes `text`, `json`, and `tool_calls`. Mapping to JSON uses the parsed value; no reparsing or implicit string-to-object conversion.
- Only earlier steps may be referenced. Reject cycles/forward references/duplicate IDs at save or preflight. Missing pointers fail with a binding error.
- Each step is one LLM request (plus bounded transport retries). Tool calls are outputs, not executable operations.
- Stop on any failed generation, failed required output validation, missing binding, or tool argument validation failure. Remaining steps become skipped. Optional evaluation check failure after a valid response does not stop execution unless designated as the prompt's output validation.
- Final output is the last step envelope. Arbitrary final transformations are deferred.
- Label selectors saved in a chain revision remain symbolic authoring selections. Resolve them once, under the same DB snapshot, when creating a run or a release. Store the resolved dependency lock and digest. Never resolve again between steps.
- Override step prompt/model versions during development via candidate configuration; mark changed steps visibly. Released bundles contain exact resolved choices only.

### 11.2 Testing one step

“Test this step” uses chain input plus explicitly selected saved upstream envelopes from a previous run or provided fixtures. Display their source and digest. It does not silently rerun upstream calls. Full-chain tests always execute all steps afresh in v1; response caching is deferred.

### 11.3 Actor example

A synthetic chain may classify an email and then extract actions using that category. Another may summarize meeting context then draft a meeting brief. Calendar/email retrieval remains Actor's responsibility; supply it as input. Actor continues to own sending, permissions, task creation, and all business side effects.

## 12. Execution engine, persistence, and failure handling

### 12.1 Small architecture

One FastAPI/Uvicorn process serves the API, compiled React assets, and an asyncio scheduling loop started through application lifespan. SQLite stores jobs before they execute. Keep scheduling and persistence behind interfaces so a separate worker could be added later; do not build that infrastructure now.

Required technology choices: Python 3.12 baseline; FastAPI; Pydantic v2; SQLAlchemy 2 with aiosqlite; Alembic; LiteLLM SDK; jsonschema; an RFC 8785 implementation; Typer CLI; pytest. Frontend: React, TypeScript, Vite, TanStack Query and Table, CodeMirror 6, and ordinary CSS or Tailwind. Use open-source UI dependencies without commercial feature requirements. Resolve and pin compatible maintained versions during implementation; commit Python and frontend lockfiles. These are architectural selections, not assertions that arbitrary latest versions interoperate.

Do not place paid work inside untracked FastAPI background tasks. Store every accepted run/cell before execution so completed results remain available. Global and per-connection semaphores limit outbound calls; SQLite transactions remain short and never span network awaits.

### 12.2 Job lifecycle

1. API validates request, resolves snapshots, computes plan limits and estimates, and atomically inserts run, candidates, cells, and queued jobs. Return 202 only after commit.
2. Scheduler atomically claims an eligible cell using a status predicate and assigns process instance ID. Persist running status and attempt record before calling the provider.
3. Render, validate, resolve environment secret, call adapter outside DB transaction, normalize output, persist attempt and cell outcome, then enqueue/check downstream evaluation work.
4. A periodic heartbeat updates process liveness. Only one server may own the database, enforced by an OS-level exclusive lock on a sibling lock file for the process lifetime. Starting a second instance fails with a clear diagnostic.
5. On server startup, mark every nonterminal run/cell from the previous process `interrupted`, including queued cells. Retain completed results. No automatic restart/resume/replay machinery is required. Formerly dispatched calls have unknown completion/billing; queued calls have not been dispatched.
6. The existing explicit Rerun action creates a new child run for interrupted tests. Full-chain reruns start from the beginning; step-only testing uses explicitly selected fixtures.

### 12.3 Retry and cancellation policy

- Default transport retry: one retry after an explicit provider 429 or retryable 5xx response, using bounded exponential backoff with jitter and honoring Retry-After up to 30 seconds. Overall per-call deadline defaults to 120 seconds including backoff.
- No retry for auth/validation/content-policy failures, unsupported settings, ambiguous timeout/disconnect after dispatch, or malformed output. These errors need a new explicit run.
- Set LiteLLM/provider retry behavior explicitly so nested libraries do not multiply attempts. Adapter tests verify the effective retry count. [LiteLLM exception mapping](https://docs.litellm.ai/docs/exception_mapping)
- Cancel marks queued cells cancelled and asks active coroutines to stop. A provider may continue processing/billing after local cancellation. Persist any known usage and `usage_uncertain: true` when unknown.
- A cancelled run cannot launch subsequent chain steps or judges. Completed outputs stay available.
- Independent cells continue when another cell fails. Batch status becomes `completed_with_errors` when all scheduled work terminates but one or more execution/evaluation errors remain; pure assertion failures are completed quality failures.
- Application shutdown stops claiming work, attempts a grace period up to 10 seconds, then marks unfinished calls interrupted. Never hold shutdown open indefinitely.

### 12.4 Spending and limits

- Preflight returns planned call count and estimated cost where rates/token estimates exist. “Run” displays these alongside dataset/candidate/repeat counts.
- A configured budget is a best-effort scheduling ceiling, not a guaranteed provider invoice cap. Already dispatched calls, unknown usage, variable provider billing, and retries can overshoot estimates.
- Before dispatch reserve estimated input plus maximum-output cost for generation and judge calls. Store reservations atomically. Replace reservation with known actual/estimated cost at completion.
- For chains, downstream input sizes depend on upstream outputs. Preview gives an estimate/range, then each step recalculates against its actual rendered input before dispatch. Do not promise an exact full-chain cost upfront. Reserve known costs cumulatively and enforce the remaining budget before every step/judge/attempt; a cell may stop partway through when its next step cannot fit.
- Strict budget mode blocks profiles with unknown rates or unbounded output limits. Local/custom profiles can use developer-specified rates. Without strict mode, unknown cost is clearly shown and must be acknowledged in run configuration.
- Budget exhaustion skips undispatched work with `budget_exhausted`; gate fails as incomplete. Resume requires an explicit new run/budget choice.
- No response cache in v1. Repeats are fresh calls. Provider-internal prompt caching may still affect billing and timing; preserve reported usage details.
- Enforce bounds on input bytes, returned output bytes (default 2 MiB), schema size, step count, rows, candidates, and generated jobs. Large responses are marked truncated-by-storage-limit with digest/size metadata; never silently treated as complete output.

## 13. Capture API and production example intake

### 13.1 Two independent write capabilities

- Registry authoring API creates prompts/revisions using `registry:write`.
- Capture API accepts execution examples using `captures:write`. It cannot mutate templates, assign labels, create release bundles, or execute models.

This separation permits Actor to send examples without giving its capture key prompt-publishing access.

### 13.2 Intake modes

- `structured`: prompt reference plus input variables; rendered messages and output are strongly recommended. An embedded template snapshot can supplement an unknown registry reference.
- `rendered`: exact normalized messages, or a merged prompt string with explicit role (default user if unavailable), plus optional output. The original dynamic template is unknown.
- Both modes allow sanitized model metadata, trace/parent trace identifiers, external event ID, UTC timestamps, duration, usage, cost source, and tags.
- A capture does not imply the output is correct. `expected` is set only when a developer curates a dataset case.
- Unmatched prompt references are accepted as `unresolved`, not auto-created registry entries. Never infer a revision from name alone. An embedded snapshot digest may link a revision only when exact content matches.

### 13.3 Capture body example

```json
{
  "schema_version": 1,
  "project_id": "8e7f2e79-cb8b-42d6-881d-c47d6f6dd356",
  "source": "actor",
  "external_event_id": "synthetic-email-event-001",
  "mode": "structured",
  "occurred_at": "2026-09-09T12:00:00Z",
  "prompt_ref": {
    "prompt_id": "496970ea-26c1-485b-8d95-af73ae9f42b2",
    "revision": 3,
    "release_id": "f73a0b7e-a271-4603-a40f-5d9ebfbe6d38"
  },
  "inputs": {"email_text": "Please send the revised proposal by Friday."},
  "rendered_messages": [
    {"role": "system", "content": "Extract significant actions as JSON."},
    {"role": "user", "content": "Please send the revised proposal by Friday."}
  ],
  "output": {"text": "{\"actions\":[{\"title\":\"Send revised proposal\"}]}"},
  "model": {"provider": "example", "requested_model": "configured-model"},
  "usage": {"input_tokens": 40, "output_tokens": 18},
  "duration_ms": 900,
  "metadata": {"environment": "production", "feature": "action-extraction"},
  "tags": ["synthetic", "english"]
}
```

IDs and counts above are synthetic. Do not seed real customer captures in the public repository.

### 13.4 Delivery and idempotency

- `POST /api/v1/captures` requires a scoped bearer key or developer JWT, JSON body ≤1 MiB, and `Idempotency-Key` ≤128 ASCII characters. Prefer a stable external event ID; key uniqueness is project + source + idempotency key.
- After validation/redaction, insert capture and idempotency digest in one transaction. New event: 201. Same key and same canonical sanitized payload: 200 and original ID. Same key with different sanitized payload: 409.
- Store the redaction policy version; retry after policy changes that alters the normalized payload can conflict and must be reported, not duplicated silently.
- Response is an acknowledgment, never a model result. No model is called on ingestion. Default limit: 60 requests/minute per key and 10 MiB/minute per key; configurable locally. Return 429 + Retry-After on rate limit.
- Export/import JSONL supports disconnected development. File imports use the same schema/redaction/idempotency service, with per-line outcomes.
- Capture file imports are capped at 10 MiB and 5,000 lines, with the 1 MiB per-event cap still enforced. File import is an explicit developer action and uses separate bounded import processing, not the per-key live-event rate counter.
- Reference Python capture client sends asynchronously with a bounded in-memory queue (default 100), short timeout (2 seconds), and at most two background retries for explicit transient responses. It never blocks or raises into Actor's main request path. A full queue drops captures and increments a local metric.
- This optional helper is best effort and not durable. Recommended reliable offline method: Actor explicitly writes sanitized capture JSONL through its own existing logging/export infrastructure, then a developer imports the file. Do not add a broker or expose a laptop to receive production calls.
- A private always-on development server may accept captures over HTTPS/VPN with capture-only keys. No need to keep it available for Actor inference.

### 13.5 Capture inbox and replay

States: new, reviewed, promoted, ignored. Filters: prompt reference, environment, model, error, tag, date, source. Show duplicate counts separately if tracked.

Actions: inspect; assign an existing prompt reference; save as input set; add to dataset; create a draft prompt from merged text; ignore; delete payload. Promotion previews editable inputs and expected values; it never copies the captured answer into expected silently.

Structured captures can be replayed against a new template if inputs validate. Rendered captures can be replayed as a fixed message snapshot on another model. To test a new dynamic template against a rendered-only capture, the developer must explicitly map/reconstruct variables first. UI explains why a replay action is unavailable.

## 14. Publishing and production runtime contract

### 14.1 Semantics

- “Set production version” moves a registry label. “Publish bundle” creates immutable files from selected prompt/chain versions or labels. Neither operation deploys Actor.
- A release has UUID, project, name, creation timestamp, author, selection manifest, resolved dependency manifest, semantic digest, optional evaluation evidence, and optional parent release.
- Publication runs under a consistent read snapshot: resolve labels, prompt/chain revisions, dependency closure, embedded model snapshots, schemas, and binding rules. No mutable label remains in runtime definitions.
- Bundle export is deterministic for the same release: same bytes/hashes/order/ZIP metadata. Rebuilding a different release may differ by ID/time even with identical semantic content.
- If a chain includes a different revision of a prompt than the standalone selected prompt, include both immutable revisions. Only standalone selections populate the public UUID/slug entrypoint mapping. Chain steps reference exact bundled revision paths. Do not silently unify incompatible selections.
- Release configuration uses connection aliases and model IDs/settings, never API keys, internal endpoints, captures, datasets, raw test results, or tenant identifiers.
- Publishing can operate without model credentials; executing cannot.

### 14.2 File structure

| Path | Content |
|---|---|
| `manifest.json` | Format version, release identity, entrypoint map, dependency lock, required connection aliases, semantic digest, file digest map, optional evidence metadata. |
| `prompts/<uuid>/v<revision>.json` | Full portable prompt revision; messages remain readable JSON strings. |
| `chains/<uuid>/v<revision>.json` | Chain input schema and ordered, fully resolved steps. |
| `schemas/bundle.schema.json` | Bundled format contract for independent consumers. |
| `README.md` | How to verify/load this release, required connection alias names, and runtime format compatibility. |

Standalone prompt files include their default non-secret model snapshot when present. Chain steps can override it with their own explicit snapshot. No separate mutable model registry is required in production. Do not export `latest.json` files per prompt because they can produce mixed releases.

### 14.3 Illustrative manifest

```json
{
  "format_version": 1,
  "template_engine": "simple-v1",
  "release_id": "f73a0b7e-a271-4603-a40f-5d9ebfbe6d38",
  "project_id": "8e7f2e79-cb8b-42d6-881d-c47d6f6dd356",
  "name": "actor-prompts-001",
  "created_at": "2026-09-09T12:00:00Z",
  "entrypoints": {
    "prompts": {
      "496970ea-26c1-485b-8d95-af73ae9f42b2": {
        "slug": "extract-actions",
        "revision": 3,
        "path": "prompts/496970ea-26c1-485b-8d95-af73ae9f42b2/v3.json"
      }
    },
    "chains": {}
  },
  "required_connections": ["actor-default"],
  "files": {
    "prompts/496970ea-26c1-485b-8d95-af73ae9f42b2/v3.json": "<sha256-of-file-bytes>",
    "schemas/bundle.schema.json": "<sha256-of-file-bytes>",
    "README.md": "<sha256-of-file-bytes>"
  },
  "semantic_sha256": "<sha256-of-canonical-runtime-definitions>"
}
```

Angle-bracket hash values are explanatory placeholders, not valid fixture digests. Builder MUST produce real digests. `manifest.json` is excluded from its own file map. `verify` rejects missing files, hash mismatch, duplicate/unsafe paths, unsupported format versions, and ambiguous slug entries. Hashes detect corruption; authenticity comes from the trusted application build/release channel, not from a hash alone. Bundle signing is deferred.

### 14.4 Publication transaction and gates

1. Freeze release records in SQLite with status `building` and exact source snapshot.
2. Generate bundle into a server-controlled temporary directory; no user-controlled absolute paths through HTTP.
3. Validate files, closure, schemas, runtime fixtures, and hashes; write ZIP with safe deterministic paths.
4. Rename finished directory/ZIP atomically to its UUID location and mark release `ready`. Download is unavailable until ready.
5. On startup, reconcile building releases: verify a completed artifact or mark failed for explicit retry. Never display partial output as ready.
6. Publication requires valid saved revisions and complete dependencies. Unchecked prompts can be published only when project policy allows it; display “Not evaluated.”
7. With a quality gate enabled, evidence must match the exact prompt/chain resolved configuration digest, checks, dataset snapshot, and all published entrypoints. Evidence for a chain can cover its internal dependencies for that chain, but not an independently exported standalone prompt entrypoint unless that entrypoint was also tested.
8. Evidence age and policy thresholds are evaluated at publication. An explicit developer override requires a reason saved with the release. It does not change failed scores.

### 14.5 Independent runtime

Deliver a separate small `prompt_workbench_runtime` package with no FastAPI, SQLite, React, or mandatory LiteLLM dependency. Core runtime reads/validates bundle files, resolves UUID/slug, validates inputs, and renders prompts. An optional `[litellm]` extra executes prompts and linear chains through the shared engine/adapter contracts.

Required Python public interface:

```python
bundle = Bundle.load("./prompts/release-001", verify=True)
request = bundle.render("extract-actions", {"email_text": "Please send the proposal."})
# request.messages, request.output, request.tools, request.model, request.provenance
# Actor can pass these to its existing model integration.

runner = BundleRunner(bundle, connections=runtime_connections)
result = await runner.run_prompt("extract-actions", {"email_text": "..."})
chain_result = await runner.run_chain("email-analysis", {"email_text": "..."})
```

These are specified interfaces to implement, not existing package APIs. Core render does not read secrets or make network calls. Optional execution returns the same output/provenance/error contract as the workbench. No database or remote registry lookup is allowed.

Provide a standalone JavaScript reference loader/renderer and fixtures demonstrating identical messages, JSON serialization, digests, and error behavior. It need not execute chains in v1; document the portable chain algorithm so any language can implement it. Production portability means the format is usable from any language, not that SDKs exist for every language.

### 14.6 Actor rollout

- Keep the existing Actor output schemas and side-effect logic. Port one prompt and compare its rendered messages against the existing implementation before changing behavior.
- Commit the exported release directory to Actor's repository or attach it to Actor's build artifact using existing CI. Run regression checks before deployment.
- Load a release at application startup and keep it immutable in memory. Default v1 has no hot reload. A process restart/deploy chooses a different bundle; rollback restores the prior application/bundle artifact.
- Every execution exposes release ID, prompt revision IDs, and configuration digest for optional capture logging.
- Actor can execute rendered requests through its existing integrations. Workbench and production must use equivalent provider/settings adapters; pin/test their versions. File equality does not guarantee model-provider determinism.

### 14.7 Optional registry resolution API

`GET /api/v1/projects/{project_id}/resolve/{kind}/{uuid_or_slug}?label=production` returns the complete flattened prompt or resolved chain, exact revisions, non-secret execution configuration, dependency lock, and configuration digest. `kind` is prompts/chains. `version=N` is an alternative selector; exactly one of label/version is required. Authenticate using JWT or a `registry:read` integration key. Return an ETag derived from the resolved digest and honor `If-None-Match` with 304. Never return installation secrets or private base URLs.

This endpoint is useful for developer tools and applications that explicitly choose dynamic retrieval. An application using it depends on workbench availability and sees label changes on its next fetch, subject to its own caching. V1 provides no automatic background refresh or fallback service. Actor's default remains a deployed file bundle that works while the workbench is stopped. Moving a registry label is not evidence that any consumer has fetched/deployed it.

## 15. SQLite schema and persistence requirements

All timestamps are UTC ISO 8601 in APIs and UTC-compatible stored values. UUIDs use TEXT. JSON fields use validated JSON text. Enable foreign keys on every connection. Use database uniqueness/check constraints, not only Pydantic validation. Each table includes `created_at`; mutable rows also include `updated_at` and optimistic sequence where appropriate.

| Table | Essential fields and constraints |
|---|---|
| `users` | id, username unique, password_hash, token_version integer default 0, disabled_at. |
| `api_keys` | id, key_prefix, secret_hash, scopes_json, project_id nullable FK, expires_at, revoked_at, last_used_at. |
| `projects` | id, slug unique, name, settings_json including gates/retention. |
| `connections` | id, alias unique, provider, api_base, api_version, secret_env_name, enabled, network_policy_json, edit_sequence. No secret values. |
| `model_profiles` | id, project_id, name, execution_config_json, connection_id, edit_sequence, archived_at. |
| `prompts` | id, project_id, slug, name, description, tags_json, is_snippet boolean default false, archived_at; unique(project_id, slug). |
| `prompt_drafts` | prompt_id PK/FK, content_json, base_revision_id nullable, edit_sequence, updated_by. |
| `prompt_revisions` | id, prompt_id, version, content_json, semantic_sha256, note, created_by; unique(prompt_id, version). |
| `prompt_labels` | prompt_id, label, revision_id, edit_sequence; unique(prompt_id, label); referenced revision must belong to prompt. |
| `chains`, `chain_drafts`, `chain_revisions`, `chain_labels` | Same identity/revision semantics; revision content contains step definitions. |
| `datasets` | id, project_id, name, input_schema_json, revision, archived_at. |
| `cases` | id, dataset_id, head_revision_id, deleted_at. |
| `case_revisions` | id, case_id, version, payload_json, source_capture_id nullable, dataset_revision, content_sha256; unique(case_id, version). |
| `dataset_snapshots` | id, dataset_id, dataset_revision, frozen_cases_json, content_sha256. |
| `evaluation_definitions` | id, project_id, name, config_json, edit_sequence. |
| `runs` | id, project_id, kind, definition_snapshot_json, dataset_snapshot_id nullable, manifest_sha256, status, parent_run_id nullable, cancel_requested_at, budget_json, summary_json, submitted_by. |
| `plan_previews` | id, project_id, principal_id, resolved_manifest_json, content_sha256, expires_at; default expiry 15 minutes. Start from an unexpired preview preserves all selected snapshots, rechecks authorization and current spending/connection availability, and does not reread mutable prompt labels. |
| `run_candidates` | id, run_id, label, resolved_definition_json, config_sha256, baseline flag; unique(run_id, label). |
| `run_cells` | id, run_id, candidate_id, case_revision_id nullable, input_snapshot_json, repeat_index, status, quality_status, output_json, error_json, worker_instance, started_at, ended_at; unique(run_id, candidate_id, case key, repeat_index). |
| `call_attempts` | id, cell_id, step_id nullable, purpose generation/judge, attempt_number, request_json, response_json, outcome, provider_request_id, model_json, usage_json, cost_decimal, cost_source, duration_ms. Unique attempt identity includes cell/step/purpose/check/attempt. |
| `step_results` | id, cell_id, step_id, ordinal, resolved_prompt_json, inputs_json, output_json, status, error_json. Unique(cell_id, step_id). |
| `check_results` | id, cell_id, step_id nullable, check_id, config_json, outcome, score_decimal nullable, evidence_json, judge_attempt_id nullable. |
| `review_events` | id, cell_id, actor_id, verdict, preferred_candidate_id nullable, note; append-only. |
| `revision_comments` | id, resource_kind prompt/chain, revision_id, author_id, body, updated_at, deleted_at; only author may edit/delete; validate revision ownership. |
| `evaluation_triggers` | id, project_id, resource_kind/id, evaluation_definition_id, target_candidate_label, enabled, budget_json, edit_sequence; unique(resource_kind, resource_id). |
| `trigger_executions` | id, trigger_rule_id, target_revision_id, config_snapshot_json, status, run_id nullable, error_json; unique(trigger_rule_id, target_revision_id). |
| `captures` | id, project_id, source, idempotency_key, payload_digest, normalized_payload_json, redaction_version, review_status, reference_status, payload_deleted_at, occurred_at. Unique(project_id, source, idempotency_key). |
| `releases` | id, project_id, name, status, selection_snapshot_json, resolved_manifest_json, semantic_sha256, artifact_path, evidence_json, created_by, parent_release_id nullable. |
| `change_events` | id, actor_type/id, action, resource_type/id, project_id nullable, metadata_json, request_id; append-only through application API. |

Implementation may normalize large JSON lists into join tables where necessary, while preserving these contracts. A logical case key must be non-null for the `run_cells` uniqueness constraint; do not rely on SQLite null uniqueness semantics. Match composite ownership constraints in service transactions and database constraints/triggers where practical.

`run_cells` are the durable scheduling jobs; no separate generic queue table is required. Chain step/check progress is durably recorded in their associated rows. After restart, do not resume any previous nonterminal cell automatically. Persist budget reservations in a small `cost_reservations` table keyed by call attempt (run ID, attempt ID, amount, state), or an equivalently transactional normalized structure. Persist general mutation idempotency in `idempotency_records` keyed by principal/project/operation/key with payload digest and result reference, expiring after 24 hours; capture dedupe uses its longer dedicated retention. These tables must not store secrets.

### 15.1 Indexes and transaction rules

- Index all FK columns used for joins, prompts/chains by project+slug, revisions by entity+version, captures by project+occurred_at and source/external reference, runs by project+created_at/status, cells by run+status, attempts by cell+step.
- Paginate metadata endpoints and fetch large payloads only on detail routes. No unbounded `SELECT *` histories.
- Use SQLite WAL mode, busy timeout 5 seconds, and synchronous FULL for durable local writes. SQLite permits one writer at a time; WAL does not turn it into a distributed database. Local filesystem only, not NFS/SMB. [SQLite WAL documentation](https://www.sqlite.org/wal.html)
- Critical multi-row changes (save revision+draft baseline, label move+change event, capture+dedupe record, run snapshots+jobs) commit atomically.
- Busy timeout returns retryable `database_busy` without corrupting job state. Retry transactions with a bounded backoff only before external effects.
- Full-text search is optional future work; v1 uses indexed metadata filters and bounded text search on selected records.
- Migrations run via CLI before server start; record schema version, preserve existing data, and reject unsupported downgrade/newer-schema combinations.

## 16. HTTP API contract

Base prefix `/api/v1`. JSON UTF-8. FastAPI-generated OpenAPI document is part of the deliverable and must reflect actual behavior. Browser and CLI use the same services; no parallel business logic in React.

### 16.1 Common semantics

- IDs in paths are UUIDs; explicit lookup endpoints support project+slug.
- List routes use opaque cursor + limit (default 50, maximum 200), stable sort by created_at and ID, and `next_cursor` nullable. Only allowlisted filter/sort fields.
- Successful create returns 201; accepted asynchronous execution 202; reads/updates 200; empty deletion 204.
- Standard errors: 400 malformed request, 401 authentication, 403 integration scope, 404 missing or inaccessible object, 409 stale sequence/idempotency conflict, 413 size limit, 422 schema/configuration invalid, 429 rate limited, 503 database/provider setup unavailable where appropriate.
- Error body: `{ "error": { "code": "missing_variable", "message": "Input email_text is required", "details": {"path": "/inputs/email_text"}, "request_id": "...", "retryable": false } }`. Never include credentials, raw provider headers, or stack traces.
- Mutable writes include `expected_edit_sequence` in the body. Run/capture/publish POSTs support idempotency keys; persistence is scoped by authenticated principal/project/operation, with payload digest conflicts returning 409. Captures additionally use the source scope described earlier.
- No remote URL fetching, provider credentials, arbitrary file paths, or Python expressions accepted in run/capture payloads.

### 16.2 Endpoint inventory

| Method and path | Purpose / main request |
|---|---|
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Username/password login, JWT issuance/invalidation, and current user. |
| `GET/POST /projects`, `PATCH /projects/{id}` | Projects and policy settings. Authenticated writes. |
| `GET/POST /connections`, `PATCH /connections/{id}` | Authenticated connection metadata/config; GET returns no secrets. |
| `POST /connections/{id}/test` | Explicit small billable model test with selected model; no automatic call on save. |
| `GET/POST /model-profiles`, `PATCH /model-profiles/{id}` | Non-secret model configurations. |
| `GET/POST /prompts`, `GET/PATCH /prompts/{id}` | Registry metadata, archive flag. |
| `GET/PUT /prompts/{id}/draft` | Read/write shared draft with expected edit sequence. |
| `GET/POST /prompts/{id}/revisions` | List or save immutable revision with draft sequence and change note. |
| `GET /prompts/{id}/revisions/{version}` | Exact definition. |
| `GET /prompts/{id}/diff?from=...&to=...` | Text and structured configuration diff. |
| `GET/POST /prompts/{id}/revisions/{version}/comments`, `PATCH/DELETE /comments/{id}` | Flat revision discussion; author-only edit/delete. Equivalent chain route. |
| `GET /prompts/{id}/usage` | Parents referencing this prompt as a snippet, with pinned versions. |
| `GET/PUT /prompts/{id}/evaluation-trigger` | Configure one opt-in save-triggered evaluation; equivalent chain route; writes require runs access. |
| `GET /prompts/{id}/analytics` | Aggregates grouped by revision/model and filtered by source/environment/date. |
| `POST /prompts/{id}/restore-draft` | Copy a saved revision into draft using expected sequence. |
| `GET/PUT /prompts/{id}/labels/{label}` | Read/change selected revision using expected previous revision. |
| `POST /prompts/{id}/render` | Render saved revision/label or supplied draft snapshot; no model call. |
| Equivalent `/chains/...` routes | Identity, drafts, revisions, labels, and resolved-plan preview. |
| `GET/POST /datasets`, `GET/PATCH /datasets/{id}` | Dataset metadata/schema. |
| `GET/POST /datasets/{id}/cases`, `GET/PATCH/DELETE /datasets/{id}/cases/{case_id}` | Case revisions and tombstones; optimistic dataset revision guard. |
| `POST /datasets/{id}/import-preview`, `POST /datasets/{id}/imports` | Validate then commit uploaded case data; import uses matching content digest. |
| `GET /datasets/{id}/export?format=jsonl|csv` | Explicit dataset export. |
| `GET/POST /evaluations`, `GET/PATCH /evaluations/{id}` | Saved evaluation definitions. |
| `POST /runs/preview`, `POST /runs` | Validate/freeze plan and estimates; start playground/evaluation/chain/rescore run. |
| `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/cells` | Run progress, aggregates, paginated matrix. |
| `GET /runs/{id}/cells/{cell_id}` | Full cell, attempts, steps, checks; separate payload download when large. |
| `POST /runs/{id}/cancel`, `POST /runs/{id}/rerun` | Cooperative cancel; create child run for selected cells. |
| `POST /runs/{id}/rescore` | New check snapshot over saved outputs. |
| `POST /runs/{id}/cells/{cell_id}/reviews` | Append review event. |
| `GET /runs/{id}/report?format=json|junit` | Machine-readable report and gate outcome. |
| `POST /captures`, `GET /captures`, `GET /captures/{id}` | Ingestion/list/detail. |
| `PATCH /captures/{id}/review`, `POST /captures/{id}/promote` | Review state or create curated dataset case. |
| `DELETE /captures/{id}/payload` | Explicit content purge with dependency/redaction handling. |
| `POST /captures/import-preview`, `POST /captures/import` | JSONL intake validation/import. |
| `POST /releases/preview`, `POST /releases` | Validate selection/gate and build immutable bundle. |
| `GET /releases`, `GET /releases/{id}`, `GET /releases/{id}/download` | Metadata/status/ready ZIP only. |
| `GET /projects/{project_id}/resolve/{kind}/{uuid_or_slug}` | Authenticated compiled definition by explicit label/version; supports ETag. |
| `GET/POST /api-keys`, `DELETE /api-keys/{id}` | Scoped integration keys; secret returned once on creation. |
| `GET /change-events` | Basic revision/label/release history, paginated; no compliance dashboard. |
| `GET /health/live`, `GET /health/ready` | Minimal health; no configuration disclosure. |

All table paths are relative to `/api/v1`, except health may also be exposed unprefixed for probes. Poll active run status every 1 second initially, then 3 seconds; stop when terminal and when browser hidden. Query invalidation must not lose editor state.

### 16.3 Run request example

```json
{
  "project_id": "8e7f2e79-cb8b-42d6-881d-c47d6f6dd356",
  "kind": "evaluation",
  "dataset_id": "e3b3b1ed-118d-4b47-a8af-98c275175d43",
  "dataset_revision": 8,
  "candidates": [
    {
      "label": "Current",
      "target": {"kind": "prompt", "id": "496970ea-26c1-485b-8d95-af73ae9f42b2", "selector": {"revision": 3}},
      "model_profile_id": "684b3314-3194-4c04-8c77-c7ff8de7174c"
    },
    {
      "label": "Candidate",
      "target": {"kind": "prompt", "id": "496970ea-26c1-485b-8d95-af73ae9f42b2", "selector": {"revision": 4}},
      "model_profile_id": "d0c651d5-3eae-4bfb-a0e9-bc370ce98c58"
    }
  ],
  "checks": [
    {"id": "valid-json", "type": "json_valid", "required": true},
    {"id": "actions-match", "type": "json_pointer_equals", "required": true,
     "actual_pointer": "/actions", "expected_pointer": "/actions"}
  ],
  "baseline_label": "Current",
  "repeats": 1,
  "concurrency": 4,
  "budget": {"max_usd": "5.00", "strict": true},
  "gate": {"min_pass_rate": 0.95, "max_regression_percentage_points": 0}
}
```

The example's second check compares the complete actions array; real suites should use `array_length` when only count matters. Referencing dataset revision 8 requires it still match the dataset head or an existing immutable snapshot supplied instead; stale selection returns 409. Preview returns a manifest token/digest. Start may accept that token to run exactly the previewed plan; expired previews are revalidated and changes reported.

Run `kind` is playground/evaluation/chain/rescore. Exactly one target selector is permitted: revision number, label, or draft snapshot. Snapshot content is validated through the same prompt/chain schema, not treated as trusted stored content. A chain candidate expresses step overrides as a map keyed by `step_id`, with optional prompt selector and optional model profile selector; unknown steps fail validation. `input_mapping` uses the typed binding descriptors from the chain contract, restricted to case inputs for standalone prompts. If omitted, map matching top-level case input names, exclude extras, apply defaults, then validate. API responses include the complete resolved mapping to make this default visible.

### 16.4 Normalized result envelope

Each cell returns `id`, `status`, `quality_status`, `candidate_id`, `case_revision_id`, `repeat_index`, `output: {text, json, tool_calls, finish_reason, refusal}`, `usage`, `cost`, `timing`, `checks`, `provenance`, and `error`. Null is permitted where a provider did not supply a value. `provenance` includes source revision IDs, content/manifest digests, renderer version, adapter/LiteLLM versions, requested/resolved model, and release ID if present. `error` uses the common error schema. Do not return secrets with request snapshots.

## 17. Security, privacy, and internal deployment

### 17.1 Basic JWT authentication

- Bind to `127.0.0.1` by default. `init` creates a local username/password account interactively; no default password and no public signup.
- Hash passwords with Argon2id. Implement JWT signing/verification with a maintained library such as PyJWT. Use an explicit HS256 algorithm allowlist and an installation secret of at least 32 random bytes loaded from `PROMPT_WORKBENCH_JWT_SECRET` or an owner-readable local secret file created by `init`. Never commit/export that secret or put it in SQLite.
- Login accepts JSON `{username, password}` and returns `{access_token, token_type: "bearer", expires_in: 28800}`. JWT claims: `sub` (user UUID), `iat`, `exp`, `iss` (installation ID), `aud` (`prompt-workbench`), and `token_version`. Validate every claim, algorithm, signature, expiry, and the account's active/token-version state on every authenticated request.
- Browser sends `Authorization: Bearer <token>`. Store the token in sessionStorage for tab reload continuity; never in URLs or logs. Clear it on logout/401. No refresh tokens or automatic silent renewal: log in again after 8 hours. Escape all rendered content to reduce XSS exposure.
- Logout increments that user's `token_version` and clears the browser token; all outstanding interactive JWTs for that account become invalid. Password change/account disable does the same. These actions do not revoke separately issued integration keys.
- No cookie-session store, session table, or cookie-based authenticated requests. Require JSON and configured Origin/CORS rules for browser calls; do not add a second CSRF-token mechanism for this bearer-only design. Disallow wildcard credentialed CORS. An external CLI using bearer auth need not supply Origin.
- Use the same JSON login endpoint from CLI when necessary; also allow scoped integration keys for CLI automation. Do not store passwords in CLI config.
- Rate-limit failed login attempts. Return generic authentication failures, not username-existence details. HTTP 401 returns `WWW-Authenticate: Bearer`.
- Serve compiled React/API from one origin. Development Vite uses its API proxy. Validate Host against explicit configured hosts. Private shared hosting uses HTTPS and an existing proxy/VPN; never trust an unauthenticated identity header.
- Integration keys remain high-entropy opaque keys hashed in SQLite, scoped, expirable, revocable, and displayed once. JWTs authenticate people; these keys authenticate narrow service integrations.

Implementation reference: [FastAPI JWT/password authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/). The exact lifetime, storage choice, claims, and local account model above are this product's design decisions.

### 17.2 Secrets and outbound access

- Connection settings save an environment variable name, not its value. UI displays configured/missing only. Credentials resolve just before calling the adapter.
- No provider secrets in HTML, browser storage, SQLite, exports, fixture data, request snapshots, debug errors, or change-history metadata. Only the interactive JWT may be stored in browser sessionStorage; provider keys never reach the browser.
- A developer registers provider base URLs. Run/capture payloads cannot override them. Disallow URL userinfo, query-string credentials, metadata service/link-local destinations, and unsupported schemes. Private/loopback endpoints are allowed only when a developer explicitly marks a connection local/private, needed for Ollama.
- Validate destinations after DNS resolution and on redirects; reject cross-origin redirects for credentialed requests. Custom endpoint support must not become an arbitrary URL-fetching API.
- Use TLS certificate validation for remote calls. No “verify=false” UI switch.
- Disable model-call content debug logging and LiteLLM callbacks to external observability systems. Use local pricing/capability data and test that no background telemetry/model-list network requests occur in offline mode.

### 17.3 Content handling and redaction

- Prompt/test data and results are stored locally. Selecting a remote model sends the chosen inputs to that provider; show the provider/connection before Run. “Local app” does not imply local inference.
- Default capture policy stores content only after the caller explicitly sends it and a developer has enabled content capture for the project. Otherwise accept metadata with `content_omitted: true`; explain that replay is unavailable.
- Require sender-side redaction for Actor exports. Provide optional deterministic key/pointer-based redaction on the server before persistence as defense in depth. Default forbidden secret key names include authorization, api_key, access_token, refresh_token, cookie, and password. Do not claim automatic detection of every personal datum in prose.
- Store redaction policy version. Rendering or comparing redacted inputs measures behavior on redacted data, not guaranteed reproduction of the original event.
- Render all model/input text as escaped text. No unsafe HTML injection, remote image loading, or automatic link previews. JSON/tool-call viewers never execute content.
- File import rejects oversized files, malformed encodings, unsafe paths, and archive traversal. V1 imports data files, not executable projects/plugins.
- Change-history metadata excludes full prompts, input/output text, credentials, and content hashes of secret values. It contains resource IDs, actors, action, timestamps, change reasons, and non-sensitive revision/digest references.

### 17.4 Retention and deletion

- Default raw capture retention: 30 days. Default ad hoc/evaluation run payload retention: 90 days. Dataset cases and saved prompt revisions persist until explicitly deleted/archived; publication evidence retains summary/digests after raw payload expiry.
- Promoting a capture creates a separate curated case. Deleting the raw capture does not silently delete that case. Deletion UI lists known derived cases/runs and offers explicit purge of all linked sensitive payloads; provenance links make these discoverable.
- Purge may replace payloads in otherwise immutable historical records with tombstones. Preserve event IDs, timestamps, non-sensitive status, and a `payload_deleted` marker; do not claim a purged run is fully replayable. Privacy deletion is the explicit exception to payload immutability.
- Keep idempotency tombstone and normalized digest for 90 days from capture acceptance unless a stronger deletion request requires removing it. Dedupe is no longer guaranteed once that retention expires.
- Retention jobs run in bounded batches on startup and daily while running.
- SQLite has no encryption-at-rest promise here. Recommend encrypted local disk/volume for sensitive Actor datasets; record the deployment requirement in operations docs. Keep data directory private to the OS user. Do not label this application SOC 2/GDPR certified.

## 18. Installation, CLI, packaging, and repository

### 18.1 Distribution

- One installable Python workbench package ships prebuilt React static assets. One separate runtime package supports lightweight production consumption.
- Source contributors run the React build using Node; end users do not need Node or a separate frontend server.
- Primary user commands below are interfaces to implement. The final project/package name may differ after naming checks.

| Command | Behavior |
|---|---|
| `prompt-workbench init --data-dir ./data` | Create config/database/migrations and first local user interactively. Refuse accidental reinitialization of an existing store. |
| `prompt-workbench serve --data-dir ./data` | Start one server and durable scheduler on localhost, default port 8765. |
| `prompt-workbench demo --data-dir ./demo-data` | Explicitly seed synthetic examples and mock provider; never load real Actor content. |
| `prompt-workbench eval --file evaluation.json --wait --report report.json` | Execute via the running local API using configured credentials; stream textual progress; return defined CI exit code. |
| `prompt-workbench capture import captures.jsonl --project <uuid>` | Authenticated import into running server with per-line outcomes. |
| `prompt-workbench release export <release-id> --out ./release.zip` | Download ready release through API; refuse overwrite unless explicitly requested. |
| `prompt-workbench bundle verify ./release` | Offline bundle validation, no DB or model calls. |
| `prompt-workbench migrate --data-dir ./data` | Require stopped server; apply versioned migrations. |
| `prompt-workbench user reset-password --data-dir ./data --username alex` | Local account change with exclusive lock; prompt securely for new password. |
| `prompt-workbench user add --data-dir ./data --username alex` | Create another equal-access local developer account interactively while server is stopped. |
| `prompt-workbench user disable --data-dir ./data --username alex` | Disable local account and invalidate its JWT token version while server is stopped. |

CLI API credentials live in environment variables or an owner-readable configuration, never command-line parameters. `eval --file` JSON uses the same API contract; do not introduce arbitrary executable evaluation files in v1. CI starts a local server with seeded synthetic config, waits for readiness, runs eval, then shuts down.

### 18.2 Docker and platforms

- Provide a single Dockerfile using a multi-stage React build and Python runtime. Container process runs as non-root. SQLite data and exported releases live in a mounted local volume. Compose is one service with loopback port mapping and environment-file secret references.
- Support macOS ARM64 and Linux x86_64 for local development/use; test package installation on both when runners are available. Linux ARM64 and Windows are best effort until tested. Avoid native build surprises by documenting dependencies and using available wheels.
- Config paths must be platform-aware through a maintained path library; do not hardcode Unix home paths into the app.

### 18.3 Repository layout

| Directory | Responsibility |
|---|---|
| `backend/src/prompt_workbench/api/` | Routes, authentication, request/response models. |
| `backend/src/prompt_workbench/services/` | Registry, datasets, evaluations, intake, publication policies. |
| `backend/src/prompt_workbench/db/` | SQLAlchemy models, transaction helpers, repositories. |
| `backend/src/prompt_workbench/jobs/` | Persistent run records, scheduler, limits, cancellation. |
| `backend/src/prompt_workbench/providers/` | LiteLLM and deterministic mock adapters. |
| `backend/migrations/` | Alembic migrations. |
| `runtime/src/prompt_workbench_runtime/` | Portable schema, renderer, loader, binding/chain contracts; optional execution extra. |
| `frontend/src/` | React routes/components/editor/table/API client. |
| `schemas/` | Versioned JSON Schema contracts for prompts/chains/bundles/captures/evals. |
| `examples/actor/` | Synthetic extraction/classification/meeting examples and migration walkthrough. |
| `examples/javascript/` | Portable loader/renderer reference and compatibility fixtures. |
| `tests/` | Unit, API, persistence/interruption, bundle, security, end-to-end tests. |
| `docs/` | Product workflow, developer setup, API, capture intake, deployment, architecture, limitations. |

Runtime semantics must live in one shared package used by workbench and production runtime. Do not create competing renderers or chain binding implementations. Keep provider SDK-specific adaptation in a shared optional execution module or adapter package, without pulling LiteLLM into the render-only installation.

### 18.4 Open-source launch requirements

Use Apache-2.0 as the proposed repository license, subject to the owner's final choice before release. Include LICENSE, README, CONTRIBUTING, SECURITY, CHANGELOG, CODE_OF_CONDUCT, dependency notices where required, and issue templates. Review dependency licenses, pin dependency versions, scan for committed credentials, and include an SBOM generation command.

All specified features remain in the open-source distribution; no cloud login, paid feature flag, or license server. Provider usage can incur the provider's own charges. Do not copy PromptLayer logos, proprietary source, screenshots into product marketing, or imply affiliation. The attached screenshots are design references for this task.

## 19. Performance targets

### 19.1 Measurable local acceptance targets

Benchmark on a documented laptop/server configuration with at least 4 CPU cores, 8 GiB RAM, and SSD. Use synthetic payloads. Exclude provider latency from UI/API targets.

| Operation | Target |
|---|---|
| Fresh install → successful mock comparison | ≤5 minutes following README, excluding initial dependency downloads. |
| Warm metadata list of 50 prompts/runs/captures | p95 ≤300 ms at the target dataset scale. |
| Save a normal ≤20 KiB draft/revision | p95 ≤500 ms with four concurrent mock calls. |
| Create/preflight 1,000-cell run | ≤3 seconds, UI responsive and bounded payload response. |
| First evaluation matrix render, 50 visible rows | ≤1 second after API response; virtualize large tables. |
| Default process idle memory | Target ≤500 MiB including LiteLLM/backend; report actual platform result, investigate material excess. |
| Restart with interrupted/queued jobs | Ready within 10 seconds at target scale; completed cells preserved; previous unfinished work marked interrupted without replay. |
| Capture burst | 1 request/second per default-limited key for 5 minutes without lost acknowledged events. |

Benchmark failures require a documented fix or an explicit owner-approved scope change before claiming these targets. Do not fabricate performance data. Storage grows with payload size; display database/artifact disk usage and configurable retention.

## 20. Detailed acceptance test catalog

Mock-based tests are mandatory, deterministic, and free of external credentials. Live model tests are explicit opt-in and report the actual provider/model/date. A skipped live test is not a pass. Test behaviors and invariants rather than mirroring private helper implementations.

| ID | Scenario | Required observable result |
|---|---|---|
| A01 | Fresh local install | Python CLI launches bundled frontend without Node or cloud login; authentication works. |
| A02 | Full mock golden path | Create prompt, save cases, compare two candidates, review, label, publish, load bundle in separate process. |
| A03 | Draft vs revision | Autosave changes draft only; explicit save adds immutable numbered version. |
| A04 | Concurrent draft edits | Stale update receives 409 and does not overwrite newer content. |
| A05 | Simultaneous revision saves | No duplicate version numbers or partial revision/draft state. |
| A06 | Label ownership/conflict | Cannot label another prompt's revision; expected-target mismatch returns 409. |
| A07 | Restore | Old content becomes editable draft/new revision; historical content is unchanged. |
| A08 | Render validation | Missing/undeclared variables and invalid types fail before any model call. |
| A09 | Renderer conformance | Python and JavaScript agree on Unicode, quotes, backslashes, null, arrays, key order, numeric edge cases, literal braces, and single-pass substitution. |
| A10 | No template execution | Jinja/Python/JS expressions are rejected; replacement text is never interpreted as syntax. |
| A11 | Dataset snapshot | Editing/deleting a case after run start cannot alter that run's input or expected value. |
| A12 | Import typing | CSV leading zeros are preserved; malformed JSONL reports row errors; default import is atomic. |
| A13 | Provider contracts | All six required provider paths normalize mocked success/errors/usage and use intended request options. |
| A14 | Live providers | Successful explicit tests on at least two independent hosted providers plus Ollama before broad compatibility is claimed; report skipped/unavailable integrations accurately. |
| A15 | Capability rejection | Unsupported required schema/tool/settings combination fails preflight without silently dropping configuration. |
| A16 | Native/validation-only JSON | UI labels modes correctly; malformed/truncated/refused output remains visible and fails required validation. |
| A17 | Tools | Valid returned tool arguments are inspectable; unexpected name/schema mismatch fails check; no tool function executes. |
| A18 | Comparison isolation | Candidate A failure does not erase/stop unrelated B results. |
| A19 | Repeat behavior | Each repeat dispatches a fresh generation; all repeats retain separate outputs. |
| A20 | Retry cap | Explicit transient response triggers at most one configured retry; nested SDK retries do not multiply it. |
| A21 | Ambiguous timeout | Cell records uncertain usage and failed/interrupted outcome; no silent replay. |
| A22 | Process interruption | Kill process after provider dispatch; completed cells survive and all unfinished work becomes interrupted on next launch; no automatic replay. |
| A23 | Duplicate server | Second server using the same database cannot start. |
| A24 | Cancellation | Queued work stops, downstream chain steps/judges do not launch, completed outputs persist. |
| A25 | Spending limit | Reservations and concurrency do not overschedule against known configured estimates; unknown-cost strict mode is rejected. |
| A26 | Usage uncertainty | Unknown cost shows unknown, never free; judge and retry costs are separately attributable. |
| A27 | Scoring denominator | Cancelled/error/missing cells cannot inflate pass rate; unscored run is not a 100% pass. |
| A28 | CI exit codes | Pass=0, completed quality failure=1, infrastructure/incomplete=2; report matches. |
| A29 | Judge failure | Invalid judge JSON produces evaluator error, not a positive score. |
| A30 | Human review | Review events retain actor/history and do not overwrite machine evaluations. |
| A31 | Chain binding | Earlier typed outputs map correctly; invalid/missing/forward reference fails clearly. |
| A32 | Chain freeze | Moving a label midway through execution cannot change a remaining step. |
| A33 | Step-only tests | Frozen upstream fixtures are visible and no upstream call occurs. |
| A34 | Capture dedupe | Same key+same sanitized payload returns original ID; changed payload returns 409. |
| A35 | Capture authorization | Capture-only key cannot read captures, edit registry, run models, or publish. |
| A36 | Capture promotion | Structured case promotion preserves types/source; captured answer is not automatically ground truth. |
| A37 | Rendered-only capture | Fixed-message replay works; dynamic replay asks for explicit variable mapping. |
| A38 | Bundle portability | Exported release renders identically with workbench stopped and no DB in both reference languages. |
| A39 | Bundle chain execution | Separate Python runtime executes exact bundled chain against mock adapter; override resolution is preserved. |
| A40 | Bundle integrity | Missing/hash-mismatched/unsafe/unknown-format files fail loading; corrupt publish never becomes ready. |
| A41 | Dependency closure | Bundle includes both prompt revisions when standalone and chain selections differ. |
| A42 | Publication evidence | Changed prompt/model/chain dependency/check/dataset cannot reuse mismatched successful evidence. |
| A43 | Rollback | Prior bundle loads and reproduces prior rendered requests; label edits do not affect it. |
| A44 | Secret containment | Canary secret never appears in API/UI/database/export/logs/errors; environment name may appear. |
| A45 | Browser security | Hostile Origin/Host, unauthorized calls, and stored script payload tests are rejected/escaped; authentication is bearer-only. |
| A46 | Connection security | Unauthenticated/custom per-request endpoint changes rejected; metadata address and credentialed redirects blocked. |
| A47 | Offline behavior | No background telemetry/price fetch/remote fonts; mock suite and registry/export work with egress blocked. |
| A48 | Retention/purge | Payload deletion/tombstones and derived-case handling match documented policy. |
| A49 | JWT lifecycle | Expired/wrong-signature/wrong-audience/wrong-issuer/disabled-user tokens fail; logout/password change invalidates old token versions; integration keys remain independent. |
| A50 | Migration safety | Upgrade seeded previous schema; preserve revisions/references; reject wrong newer schema. |
| A51 | Size/pagination | Large imports/calls fail within limits; history routes remain paginated and memory bounded. |
| A52 | Public package hygiene | Wheel contains frontend, license/docs included, no private data/keys, demo is synthetic and clearly labeled. |
| A53 | Snippet compilation | Pinned text/variables expand into the same portable messages; snippet edits do not change saved parents; nested references/conflicting schemas are rejected. |
| A54 | Revision comments | Create/list comments, enforce author-only edit/delete; prompt/runtime digests stay unchanged. |
| A55 | Visual schema editor | Form and JSON modes preserve supported fields; unsupported visual constructs remain editable JSON; tool execution never occurs. |
| A56 | Save-triggered evaluation | Explicit opted-in save schedules once; autosave/unchanged save/capture do not; invalid setup is shown; registry-only key cannot launch paid tests. |
| A57 | Revision analytics | Group exact revision/model, distinguish captures from tests, show unknown-cost counts, and keep unresolved references separate. |
| A58 | Resolve endpoint | JWT/scoped-key auth, correct label/version expansion and dependency lock, ETag/304, no secrets/endpoints; bundles still work offline. |

### 20.1 Actor synthetic regression pack

Ship at least 12 action-extraction cases covering: explicit task; FYI-only email; trivial link/open instruction; duplicate request; multiple meaningful tasks; German input; Romanian input; long quoted thread; completed task mentioned historically; task assigned to another person; ambiguous deadline; email containing hostile instructions. Add 6 classification cases and 4 meeting-brief cases. These are starter examples with explicit expected behavior, not claims about Actor's existing private schema.

For actual Actor adoption, import its exact current output schema and reviewed representative samples. Do not replace Actor's schema with the synthetic example schema by accident. Require a comparison on the same inputs before declaring migration complete.

## 21. Implementation milestones and completion gates

| Milestone | Scope | Exit gate |
|---|---|---|
| M1: local foundation | Python package, bundled frontend path, DB migrations, auth, projects, mock provider, CLI init/serve. | Fresh authenticated local app and health checks; A01/A23/A45 basics. |
| M2: registry and runtime core | Drafts/revisions/labels, renderer/schema contracts, input sets/datasets, portable loader core. | Immutable saves and cross-language renderer conformance; A03–A12. |
| M3: real comparison engine | LiteLLM adapter, durable scheduler, playground, matrix, normalized usage, interruption/cancel. | Two candidates and datasets execute end-to-end; A13–A26 and A47. |
| M4: evaluation and chains | Check library, judge, review, CI reports, chain mappings/overrides/step replay. | Reproducible full-chain comparison and gates; A27–A33. |
| M5: production handoff | Capture API/inbox, promotion, release builder/verification, independent runtime execution, Actor examples. | A34–A43; workbench-off production bundle demo. |
| M6: hardening and release | Retention, JWT security, performance, docs, Docker, distribution tests. | All remaining acceptance tests; real provider smoke report; installable public-ready package. |

Include snippets/comments/schema forms in M2 (A53–A55), automatic save tests and version analytics in M4 (A56–A57), and the optional resolve endpoint in M5 (A58). These are required v1 features; automatic test execution remains opt-in for each prompt/chain.

Each milestone must end in working software. M1–M5 alone are not the completed v1. Do not substitute screenshots, stubs, in-memory fake APIs, or mocked-only provider integrations for the required behavior.

## 22. Instructions for the implementing agent

1. Treat this document as the product contract. Read it fully before coding. Create a short traceability checklist linking PR/TM/DS/MP/PG/EV/CH/PB/IN/OB/OP/OSS requirements and acceptance IDs to code/tests.
2. Start with M1 and one vertical workflow; keep domain services reusable. Generate the real OpenAPI and JSON Schema files from validated models and commit them with compatibility tests.
3. Use Python for all server and execution behavior; React/TypeScript only for the UI/reference renderer. SQLite remains the only required database.
4. Use LiteLLM through one adapter. Pin the actual dependency version, inspect that version's public API, and write normalization/capability/retry tests against it. Do not assume a model identifier or documented helper works without validation.
5. Implement the portable contract before release UI polish. Workbench, CLI, and runtime must agree on resolved configuration, rendering, validation, and chain behavior.
6. Preserve secrets and synthetic/real data separation. Seed fake data only in explicit demo/test mode. Never automatically send fixture data to a paid provider.
7. Do not add deferred cloud/agent framework features to appear complete. The prescribed local functionality must work fully.
8. When a requirement is ambiguous, choose the smallest reversible implementation consistent with this document, record it in `docs/decisions.md`, and continue. Raise only incompatibilities that materially change scope, safety, or public API semantics.
9. Record actual verification results and missing credentials/platform coverage honestly. A mock provider test is not a live provider test.
10. Deliver source, runnable packages/build commands, schemas, migrations, examples, automated tests, API docs, operator docs, and a requirements/test report. No TODO placeholders in the required happy paths.
11. Public source/package publication is a later explicit action. Prepare a release-ready repository; do not upload private data, publish an instance, or deploy Actor as part of implementing this specification.

## 23. Final definition of done

A developer installs the application locally, signs in, creates and versions a dynamic prompt, saves input sets, compares real models, inspects scored results, tests a complete linear chain, ingests a synthetic external capture, turns it into a regression case, assigns preferred versions, and exports a verified bundle. A separate Python process renders and executes that bundle with the workbench stopped. The JavaScript reference renders the same messages. Cancellation, interruption status, JWT authentication, secret containment, and retention behave as specified. All mandatory automated tests pass and live provider/platform coverage is reported accurately.

## 24. Research register and limitations

The product specification above is an original proposal. External sources establish reference features and integration constraints, not guarantees about the future implementation. Official documentation was reviewed on 9 September 2026; the implementing agent must recheck version-specific APIs when pinning dependencies.

| Source | Applied finding |
|---|---|
| [PromptLayer prompt management](https://www.promptlayer.com/prompt-management/) | Requested feature baseline for this updated specification. |
| [PromptLayer snippets](https://docs.promptlayer.com/features/prompt-registry/snippets) | Reusable fragments; our v1 pins and flattens them. |
| [PromptLayer tools](https://docs.promptlayer.com/features/prompt-registry/tool-calling) | Visual function-schema editing. |
| [FastAPI JWT authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) | Python password-hashing and JWT implementation reference. |
| [PromptLayer editor/versioning](https://docs.promptlayer.com/features/prompt-registry/prompt-editor-versioning) | Save/diff/history workflow and role-based editing. |
| [PromptLayer input sets](https://docs.promptlayer.com/features/prompt-registry/input-variable-sets) | Reusable variables and capture/file import workflow. |
| [PromptLayer release labels](https://docs.promptlayer.com/features/prompt-registry/release-labels) | Static version-selection labels; advanced routing intentionally deferred. |
| [PromptLayer Tables](https://docs.promptlayer.com/features/tables/overview) | Case rows, output/check columns, cell execution and history. |
| [PromptLayer structured outputs](https://docs.promptlayer.com/features/prompt-registry/structured-outputs) | JSON Schema output configuration. |
| [PromptLayer workflows](https://docs.promptlayer.com/why-promptlayer/workflows) | Multi-step workflow reference, reduced here to linear prompt chains. |
| [PromptLayer observability](https://docs.promptlayer.com/features/observability/overview) | Request details and hierarchical execution inspection. |
| [LiteLLM async calls](https://docs.litellm.ai/docs/completion/stream) | Async SDK integration without a separate proxy. |
| [LiteLLM input parameters](https://docs.litellm.ai/docs/completion/input) | Normalized message/settings interface; provider-specific support still varies. |
| [LiteLLM structured output support](https://docs.litellm.ai/docs/completion/json_mode) | Capability checks and local validation. |
| [LiteLLM token usage and cost](https://docs.litellm.ai/docs/completion/token_usage) | Usage/cost helpers and local pricing data option. |
| [LiteLLM exceptions](https://docs.litellm.ai/docs/exception_mapping) | Normalized provider error handling. |
| [SQLite WAL](https://www.sqlite.org/wal.html) | Local filesystem and single-writer constraints. |

Visual references supplied by the user: `bc4d363b-8687-4e2b-9601-1112bd502349.png` (prompt editor) and `3f560ab1-f1b8-442e-9cb1-d576a5d88975.png` (evaluation table). The implementer need not possess these images to follow the explicit UI requirements in this specification.
