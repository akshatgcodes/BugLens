import { postStream } from "./lib/sse";
import type { Report, ReportSummary, RuleInfo, Sample } from "./types";

// Empty in dev (Vite proxies /api). Set VITE_API_URL when the API is elsewhere.
export const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, credentials: "include" });
  } catch {
    throw new ApiError(0, "Can't reach the BugLens server");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = typeof body.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export interface AnalyzeBody {
  code: string;
  language: string;
  filename: string | null;
  ai: boolean;
}

export const api = {
  me: () => request<{ owner: boolean }>("/api/auth/me"),
  login: (password: string) => request("/api/auth/login", json("POST", { password })),
  logout: () => request("/api/auth/logout", json("POST")),

  analyze: (body: AnalyzeBody, onEvent: (event: string, data: unknown) => void, signal?: AbortSignal) =>
    postStream(`${BASE}/api/analyze`, body, onEvent, signal),
  reports: () => request<ReportSummary[]>("/api/reports"),
  report: (id: string) => request<Report>(`/api/reports/${id}`),
  removeReport: (id: string) => request<void>(`/api/reports/${id}`, { method: "DELETE" }),
  rules: () => request<{ languages: Record<string, string>; rules: RuleInfo[] }>("/api/rules"),
  samples: () => request<Sample[]>("/api/samples"),
};
