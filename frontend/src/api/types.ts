// Centralized API type definitions for the Prompt Workbench backend (/api/v1).
// These interfaces intentionally mirror the documented API contract. Fields that
// the backend may omit are marked optional; unknown/loose JSON payloads use
// `JsonValue` rather than `any`.

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

/** Normalized error envelope returned by the backend. */
export interface ApiError {
  code: string;
  message: string;
  details?: JsonObject;
  retryable?: boolean;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Principal {
  id: string;
  kind: string;
  username: string;
  scopes: string[];
}

// ---------------------------------------------------------------------------
// Projects & model profiles
// ---------------------------------------------------------------------------

export interface Project {
  id: string;
  name: string;
  slug: string;
  settings?: JsonObject;
  created_at?: string;
}

export interface ModelProfile {
  id: string;
  name: string;
  provider: string;
  model: string;
  parameters?: JsonObject;
  connection_alias?: string | null;
}

export interface Connection {
  id: string;
  alias: string;
  provider: string;
  secret_configured: boolean;
}

export interface ApiKey {
  id: string;
  name?: string;
  prefix?: string;
  key_prefix?: string;
  scopes?: string[];
  created_at?: string;
  last_used_at?: string | null;
}

// ---------------------------------------------------------------------------
// Prompt content shape
// ---------------------------------------------------------------------------

export type PromptRole = 'system' | 'user' | 'assistant';

export interface PromptMessage {
  role: PromptRole;
  content: string;
}

export type SchemaType =
  | 'string'
  | 'integer'
  | 'number'
  | 'boolean'
  | 'object'
  | 'array';

export interface InputSchemaProperty {
  type: SchemaType;
  description?: string;
  [key: string]: JsonValue | undefined;
}

export interface InputSchema {
  type: 'object';
  properties: Record<string, InputSchemaProperty>;
  required: string[];
}

export type OutputMode = 'text' | 'json' | 'native_json_schema';

export interface PromptOutput {
  mode: OutputMode;
  schema: JsonObject | null;
}

/** The full editable prompt content document. */
export interface PromptContent {
  format_version: number;
  kind: 'chat' | 'text';
  template_engine: 'simple-v1';
  messages: PromptMessage[];
  text: string | null;
  input_schema: InputSchema;
  output: PromptOutput;
  tools: JsonValue[];
  tool_choice: string;
  default_model: string | null;
}

// ---------------------------------------------------------------------------
// Prompts, drafts, revisions
// ---------------------------------------------------------------------------

export interface PromptSummary {
  id: string;
  slug: string;
  name: string;
  description?: string;
  tags: string[];
  is_snippet: boolean;
  archived_at?: string | null;
}

export interface Prompt extends PromptSummary {
  project_id: string;
  content?: PromptContent;
}

export interface Draft {
  content: PromptContent;
  edit_sequence: number;
}

export interface Revision {
  id: string;
  version: number;
  note: string;
  semantic_sha256: string;
  created_at: string;
  content?: PromptContent;
  unchanged?: boolean;
}

export interface PromptLabel {
  label: string;
  version: number;
  revision_id: string;
}

export type RenderSelector =
  | { revision: number }
  | { label: string }
  | { draft: PromptContent };

export interface RenderResult {
  messages: PromptMessage[];
  normalized_inputs: JsonObject;
  output: JsonValue;
  tools: JsonValue[];
  provenance: JsonObject;
}

export interface DiffResult {
  text_diff: string;
  semantic_changed: boolean;
}

export interface Comment {
  id: string;
  body: string;
  author?: string;
  created_at: string;
  version?: number;
}

export interface AnalyticsGroup {
  revision: number;
  model: string;
  calls: number;
  pass_rate: number;
  known_cost: number;
  p50_latency_ms: number;
  p95_latency_ms?: number;
  [key: string]: JsonValue | undefined;
}

export interface AnalyticsResult {
  groups: AnalyticsGroup[];
}

// ---------------------------------------------------------------------------
// Datasets & cases
// ---------------------------------------------------------------------------

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  input_schema?: JsonObject;
  case_count?: number;
  created_at?: string;
}

export interface DatasetCase {
  id: string;
  name: string;
  inputs: JsonObject;
  expected?: JsonValue;
  tags: string[];
  critical: boolean;
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export type RunStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'completed_with_errors'
  | 'cancelled'
  | string;

export interface RunCandidateTarget {
  kind: 'prompt';
  id: string;
  selector: { revision?: number; label?: string };
}

export interface RunCandidateSpec {
  label: string;
  target: RunCandidateTarget;
  model_profile_id: string;
}

export interface RunCheck {
  id: string;
  type: string;
  required: boolean;
  [key: string]: JsonValue | undefined;
}

export interface RunGate {
  min_pass_rate: number;
}

export interface RunRequest {
  project_id: string;
  kind: 'evaluation';
  dataset_id: string;
  candidates: RunCandidateSpec[];
  checks: RunCheck[];
  baseline_label?: string;
  repeats: number;
  gate?: RunGate;
}

export interface RunPreview {
  candidate_count: number;
  case_count: number;
  generation_calls: number;
  candidates: Array<{ label: string; model?: string }>;
}

export interface ModelSnapshot {
  id?: string;
  name?: string;
  provider?: string;
  model?: string;
  parameters?: JsonObject;
  connection_alias?: string | null;
  [key: string]: JsonValue | undefined;
}

export interface RunCandidateSummary {
  id: string;
  label: string;
  target?: RunCandidateTarget;
  model_snapshot?: ModelSnapshot;
  content_provenance?: JsonObject;
  config_digest?: string;
  baseline?: boolean;
}

export interface RunSummaryCandidate {
  candidate_id: string;
  label: string;
  planned: number;
  completed: number;
  passed: number;
  pass_rate?: number | null;
  completion_rate?: number | null;
  known_cost?: number | string | null;
  unknown_cost_count?: number;
  p50_latency_ms?: number | null;
  p95_latency_ms?: number | null;
  errors?: number;
  gate_pass?: boolean;
}

export interface RunSummary {
  candidates?: RunSummaryCandidate[];
  gate?: JsonObject | null;
  gate_pass?: boolean | null;
  has_required_checks?: boolean;
}

export interface Run {
  id: string;
  kind: string;
  status: RunStatus;
  created_at: string;
  summary?: RunSummary | null;
  candidates: RunCandidateSummary[];
}

export type CellStatus = string;
export type QualityStatus = 'pass' | 'fail' | 'error' | string;

export interface CellCheck {
  id: string;
  type: string;
  outcome: 'pass' | 'fail' | 'error' | string;
  required: boolean;
  evidence?: JsonValue;
}

export interface CellOutput {
  text?: string;
  json?: JsonValue;
  tool_calls?: JsonValue[];
}

export interface CellUsage {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  [key: string]: JsonValue | undefined;
}

export interface RunCell {
  id: string;
  candidate_id: string;
  case_name: string;
  repeat_index: number;
  status: CellStatus;
  quality_status: QualityStatus;
  output?: CellOutput;
  usage?: CellUsage;
  cost?: { amount: number | string; source: string };
  timing?: { duration_ms: number };
  checks?: CellCheck[];
  error?: JsonValue;
  provenance?: JsonObject;
}

// ---------------------------------------------------------------------------
// Captures
// ---------------------------------------------------------------------------

export type ReviewStatus =
  | 'new'
  | 'reviewed'
  | 'ignored'
  | 'promoted'
  | string;

export interface Capture {
  id: string;
  source: string;
  mode: string;
  review_status: ReviewStatus;
  occurred_at: string;
  inputs?: JsonValue;
  output?: JsonValue;
  metadata?: JsonObject;
  tags?: string[];
  prompt_ref?: JsonValue;
  reference_status?: string;
}

// ---------------------------------------------------------------------------
// Releases & change events
// ---------------------------------------------------------------------------

export interface Release {
  id: string;
  name: string;
  status: string;
  semantic_sha256: string;
  created_at: string;
  manifest?: JsonObject;
}

export interface ChangeEvent {
  id: string;
  type?: string;
  entity?: string;
  actor?: string;
  summary?: string;
  created_at: string;
  [key: string]: JsonValue | undefined;
}
