// Centralized, typed API client for the Prompt Workbench backend.
//
// - Base URL is the relative path `/api/v1` (Vite proxies `/api` to the backend
//   during development).
// - The bearer token is read from sessionStorage on every request (except login
//   and health).
// - Responses are unwrapped to their typed payloads; errors are normalized to
//   `ApiClientError` carrying the backend `{ error: {...} }` envelope.
// - On any 401 the token is cleared and the browser is redirected to /login.

import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';
import type {
  AnalyticsResult,
  ApiError,
  ApiKey,
  Capture,
  ChangeEvent,
  Comment,
  Connection,
  Dataset,
  DatasetCase,
  DiffResult,
  Draft,
  JsonObject,
  JsonValue,
  LoginResponse,
  ModelProfile,
  Principal,
  Project,
  Prompt,
  PromptContent,
  PromptLabel,
  PromptSummary,
  Release,
  RenderResult,
  RenderSelector,
  ReviewStatus,
  Revision,
  Run,
  RunCell,
  RunPreview,
  RunRequest,
} from './types';

// --- Token storage ---------------------------------------------------------

export const TOKEN_STORAGE_KEY = 'pw_token';

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

// --- Error type ------------------------------------------------------------

/** Error thrown for any failed API call, carrying the normalized envelope. */
export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: JsonObject;
  readonly retryable: boolean;

  constructor(status: number, error: ApiError) {
    super(error.message || 'Request failed');
    this.name = 'ApiClientError';
    this.code = error.code || 'unknown';
    this.status = status;
    this.details = error.details;
    this.retryable = error.retryable ?? false;
  }
}

function normalizeError(err: unknown): ApiClientError {
  if (err instanceof ApiClientError) return err;
  const axiosErr = err as AxiosError<{ error?: ApiError }>;
  const status = axiosErr.response?.status ?? 0;
  const envelope = axiosErr.response?.data?.error;
  if (envelope) {
    return new ApiClientError(status, envelope);
  }
  return new ApiClientError(status, {
    code: axiosErr.code ?? 'network_error',
    message:
      axiosErr.message ||
      (status === 0
        ? 'Network error — is the backend running on :8765?'
        : 'Request failed'),
    retryable: status === 0 || status >= 500,
  });
}

// --- Axios instance --------------------------------------------------------

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Attach bearer token except for auth/login and health endpoints.
http.interceptors.request.use((config) => {
  const url = config.url ?? '';
  const isAuthExempt =
    url.startsWith('/auth/login') || url.startsWith('/health');
  if (!isAuthExempt) {
    const token = getToken();
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 globally: clear token and redirect to /login.
http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    if (status === 401) {
      clearToken();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  },
);

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const res = await http.request<T>(config);
    return res.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

const get = <T>(url: string, params?: Record<string, unknown>): Promise<T> =>
  request<T>({ method: 'GET', url, params });
const post = <T>(url: string, data?: unknown): Promise<T> =>
  request<T>({ method: 'POST', url, data });
const put = <T>(url: string, data?: unknown): Promise<T> =>
  request<T>({ method: 'PUT', url, data });
const patch = <T>(url: string, data?: unknown): Promise<T> =>
  request<T>({ method: 'PATCH', url, data });
const del = <T>(url: string): Promise<T> =>
  request<T>({ method: 'DELETE', url });

// --- Typed API surface -----------------------------------------------------

export const api = {
  // Auth ---------------------------------------------------------------
  login: (username: string, password: string) =>
    post<LoginResponse>('/auth/login', { username, password }),
  me: () => get<Principal>('/auth/me'),
  logout: () => post<void>('/auth/logout'),

  // Projects & profiles ------------------------------------------------
  listProjects: () => get<Project[]>('/projects'),
  createProject: (body: { name: string; slug?: string }) =>
    post<Project>('/projects', body),
  listModelProfiles: (projectId: string) =>
    get<ModelProfile[]>('/model-profiles', { project_id: projectId }),
  listConnections: () => get<Connection[]>('/connections'),
  listApiKeys: () => get<ApiKey[]>('/api-keys'),

  // Prompts ------------------------------------------------------------
  listPrompts: (projectId: string, isSnippet = false) =>
    get<PromptSummary[]>('/prompts', {
      project_id: projectId,
      is_snippet: isSnippet,
    }),
  createPrompt: (body: {
    project_id: string;
    name: string;
    slug: string;
    description?: string;
    is_snippet?: boolean;
    content?: PromptContent;
  }) => post<Prompt>('/prompts', body),
  getPrompt: (id: string) => get<Prompt>(`/prompts/${id}`),

  getDraft: (id: string) => get<Draft>(`/prompts/${id}/draft`),
  updateDraft: (id: string, content: PromptContent, expectedEditSequence: number) =>
    put<Draft>(`/prompts/${id}/draft`, {
      content,
      expected_edit_sequence: expectedEditSequence,
    }),

  listRevisions: (id: string) => get<Revision[]>(`/prompts/${id}/revisions`),
  createRevision: (id: string, note: string, expectedEditSequence?: number) =>
    post<Revision>(`/prompts/${id}/revisions`, {
      note,
      expected_edit_sequence: expectedEditSequence,
    }),
  getRevision: (id: string, version: number) =>
    get<Revision>(`/prompts/${id}/revisions/${version}`),
  restoreDraft: (id: string, version: number, expectedEditSequence: number) =>
    post<Draft>(`/prompts/${id}/restore-draft`, {
      version,
      expected_edit_sequence: expectedEditSequence,
    }),

  listLabels: (id: string) => get<PromptLabel[]>(`/prompts/${id}/labels`),
  setLabel: (
    id: string,
    label: string,
    version: number,
    expectedPreviousRevisionId?: string,
  ) =>
    put<PromptLabel>(`/prompts/${id}/labels/${label}`, {
      version,
      expected_previous_revision_id: expectedPreviousRevisionId,
    }),

  render: (id: string, selector: RenderSelector, inputs: JsonObject) =>
    post<RenderResult>(`/prompts/${id}/render`, { selector, inputs }),

  diff: (id: string, fromVersion: number, toVersion: number) =>
    get<DiffResult>(`/prompts/${id}/diff`, {
      from_version: fromVersion,
      to_version: toVersion,
    }),

  listComments: (id: string, version: number) =>
    get<Comment[]>(`/prompts/${id}/revisions/${version}/comments`),
  addComment: (id: string, version: number, body: string) =>
    post<Comment>(`/prompts/${id}/revisions/${version}/comments`, { body }),
  deleteComment: (commentId: string) =>
    del<void>(`/comments/${commentId}`),

  analytics: (id: string) => get<AnalyticsResult>(`/prompts/${id}/analytics`),

  // Datasets -----------------------------------------------------------
  listDatasets: (projectId: string) =>
    get<Dataset[]>('/datasets', { project_id: projectId }),
  createDataset: (body: {
    project_id: string;
    name: string;
    description?: string;
    input_schema?: JsonObject;
  }) => post<Dataset>('/datasets', body),
  getDataset: (id: string) => get<Dataset>(`/datasets/${id}`),
  listCases: (id: string) => get<DatasetCase[]>(`/datasets/${id}/cases`),
  createCase: (
    id: string,
    body: {
      name: string;
      inputs: JsonObject;
      expected?: JsonValue;
      tags?: string[];
      critical?: boolean;
    },
  ) => post<DatasetCase>(`/datasets/${id}/cases`, body),
  updateCase: (
    id: string,
    caseId: string,
    body: Partial<{
      name: string;
      inputs: JsonObject;
      expected: JsonValue;
      tags: string[];
      critical: boolean;
    }>,
  ) => patch<DatasetCase>(`/datasets/${id}/cases/${caseId}`, body),
  deleteCase: (id: string, caseId: string) =>
    del<void>(`/datasets/${id}/cases/${caseId}`),

  // Runs ---------------------------------------------------------------
  previewRun: (body: RunRequest) => post<RunPreview>('/runs/preview', body),
  createRun: (body: RunRequest) => post<Run>('/runs', body),
  listRuns: (projectId: string) =>
    get<Run[]>('/runs', { project_id: projectId }),
  getRun: (id: string) => get<Run>(`/runs/${id}`),
  getRunCells: (id: string) => get<RunCell[]>(`/runs/${id}/cells`),
  cancelRun: (id: string) => post<Run>(`/runs/${id}/cancel`),
  getRunReport: (id: string) => get<JsonValue>(`/runs/${id}/report`),
  reviewCell: (
    runId: string,
    cellId: string,
    body: { verdict: string; note?: string },
  ) => post<JsonValue>(`/runs/${runId}/cells/${cellId}/reviews`, body),

  // Captures -----------------------------------------------------------
  listCaptures: (projectId: string, reviewStatus?: ReviewStatus) =>
    get<Capture[]>('/captures', {
      project_id: projectId,
      review_status: reviewStatus,
    }),
  getCapture: (id: string) => get<Capture>(`/captures/${id}`),
  reviewCapture: (id: string, reviewStatus: ReviewStatus) =>
    patch<Capture>(`/captures/${id}/review`, { review_status: reviewStatus }),
  promoteCapture: (id: string, datasetId: string, name?: string) =>
    post<JsonValue>(`/captures/${id}/promote`, {
      dataset_id: datasetId,
      name,
    }),

  // Releases -----------------------------------------------------------
  listReleases: (projectId: string) =>
    get<Release[]>('/releases', { project_id: projectId }),
  createRelease: (body: {
    project_id: string;
    name: string;
    selection: { prompts: Array<{ prompt_id: string; selector: JsonObject }> };
  }) => post<Release>('/releases', body),
  releaseDownloadUrl: (id: string) => `/api/v1/releases/${id}/download`,

  // Change events ------------------------------------------------------
  listChangeEvents: (projectId: string) =>
    get<ChangeEvent[]>('/change-events', { project_id: projectId }),
};

// (Project type is imported at the top of the file.)
