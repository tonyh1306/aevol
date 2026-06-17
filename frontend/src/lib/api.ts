import type {
  ComparisonResult,
  Dataset,
  DatasetListResponse,
  DatasetRow,
  Experiment,
  ExperimentListResponse,
  FailureCluster,
  MetricSummary,
  Report,
  Task,
  TaskListResponse,
  Worker,
  WorkerListResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(`API error ${status}: ${JSON.stringify(detail)}`);
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  experiments: {
    list: (params?: { page?: number; limit?: number; status?: string; tags?: string[] }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set("page", String(params.page));
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.status) q.set("status", params.status);
      params?.tags?.forEach((t) => q.append("tags", t));
      return apiFetch<ExperimentListResponse>(`/api/v1/experiments?${q}`);
    },
    get: (id: string) => apiFetch<Experiment>(`/api/v1/experiments/${id}`),
    create: (body: Partial<Experiment>) =>
      apiFetch<Experiment>("/api/v1/experiments", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: Partial<Experiment>) =>
      apiFetch<Experiment>(`/api/v1/experiments/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) =>
      apiFetch<void>(`/api/v1/experiments/${id}`, { method: "DELETE" }),
    run: (id: string) =>
      apiFetch<Experiment>(`/api/v1/experiments/${id}/run`, { method: "POST" }),
    cancel: (id: string) =>
      apiFetch<Experiment>(`/api/v1/experiments/${id}/cancel`, { method: "POST" }),
    clone: (id: string, overrides?: Record<string, unknown>) =>
      apiFetch<Experiment>(`/api/v1/experiments/${id}/clone`, { method: "POST", body: JSON.stringify(overrides ?? null) }),
    tasks: (id: string, params?: { page?: number; limit?: number; status?: string }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set("page", String(params.page));
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.status) q.set("status", params.status);
      return apiFetch<TaskListResponse>(`/api/v1/experiments/${id}/tasks?${q}`);
    },
    metricsSummary: (id: string) => apiFetch<MetricSummary>(`/api/v1/experiments/${id}/metrics/summary`),
    failures: (id: string) => apiFetch<Array<{ error_type: string; count: number; sample_messages: string[] }>>(`/api/v1/experiments/${id}/failures`),
    clusters: (id: string) => apiFetch<FailureCluster[]>(`/api/v1/experiments/${id}/clusters`),
    compare: (a: string, b: string) => apiFetch<ComparisonResult>(`/api/v1/experiments/${a}/compare/${b}`),
  },

  datasets: {
    list: (params?: { page?: number; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set("page", String(params.page));
      if (params?.limit) q.set("limit", String(params.limit));
      return apiFetch<DatasetListResponse>(`/api/v1/datasets?${q}`);
    },
    get: (id: string) => apiFetch<Dataset>(`/api/v1/datasets/${id}`),
    upload: (formData: FormData) =>
      fetch(`${API_BASE}/api/v1/datasets/upload`, { method: "POST", body: formData }).then((r) => r.json() as Promise<Dataset>),
    rows: (id: string, params?: { page?: number; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set("page", String(params.page));
      if (params?.limit) q.set("limit", String(params.limit));
      return apiFetch<{ items: DatasetRow[]; total: number; page: number; limit: number }>(`/api/v1/datasets/${id}/rows?${q}`);
    },
    delete: (id: string) => apiFetch<void>(`/api/v1/datasets/${id}`, { method: "DELETE" }),
  },

  workers: {
    list: () => apiFetch<WorkerListResponse>("/api/v1/workers"),
    get: (id: string) => apiFetch<Worker>(`/api/v1/workers/${id}`),
  },

  tasks: {
    get: (id: string) => apiFetch<Task>(`/api/v1/tasks/${id}`),
    retry: (id: string) => apiFetch<Task>(`/api/v1/tasks/${id}/retry`, { method: "POST" }),
    trace: (id: string) => apiFetch<unknown[]>(`/api/v1/tasks/${id}/trace`),
  },

  reports: {
    list: () => apiFetch<{ items: Report[]; total: number }>("/api/v1/reports"),
    get: (id: string) => apiFetch<Report>(`/api/v1/reports/${id}`),
    create: (baselineId: string, candidateId: string, title?: string) =>
      apiFetch<Report>("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({ baseline_id: baselineId, candidate_id: candidateId, title }),
      }),
  },
};
