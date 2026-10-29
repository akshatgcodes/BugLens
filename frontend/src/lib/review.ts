import { SEVERITIES, type Counts, type Issue, type Patch, type Report, type Severity, type Status } from "../types";

export interface ReviewState {
  phase: "idle" | "running" | "done";
  code: string; // what was analysed (the editor may have moved on)
  id?: string;
  language?: string;
  model?: string;
  issues: Issue[];
  aiRunning: boolean;
  aiFixes: number; // rule findings the rules couldn't fix, fixed by the model
  staticMs?: number;
  totalMs?: number;
  fixed?: string;
  fixedSource?: "model" | "rules";
  notices: string[];
  status?: Status;
  error?: string;
}

export const initialReview: ReviewState = { phase: "idle", code: "", issues: [], aiRunning: false, aiFixes: 0, notices: [] };

export type ReviewAction =
  | { type: "start"; code: string }
  | { type: "event"; event: string; data: any }
  | { type: "error"; message: string }
  | { type: "load"; report: Report }
  | { type: "reset" };

export function reviewReducer(s: ReviewState, a: ReviewAction): ReviewState {
  switch (a.type) {
    case "start":
      return { ...initialReview, phase: "running", code: a.code };
    case "reset":
      return initialReview;
    case "error":
      return { ...s, phase: "done", aiRunning: false, error: a.message };
    case "load": {
      const r = a.report;
      return {
        phase: "done",
        code: r.code,
        id: r.id,
        language: r.language,
        model: r.model,
        issues: r.issues,
        aiRunning: false,
        aiFixes: 0,
        fixed: r.fixed,
        fixedSource: r.fixed_source,
        notices: r.ai_error ? [r.ai_error] : [],
        status: r.status,
      };
    }
    case "event":
      return applyEvent(s, a.event, a.data);
  }
}

function applyEvent(s: ReviewState, event: string, d: any): ReviewState {
  switch (event) {
    case "meta":
      return { ...s, id: d.id, language: d.language, model: d.model };
    case "static":
      return { ...s, issues: d.issues, fixed: d.fixed, fixedSource: "rules", staticMs: d.ms };
    case "ai_start":
      return { ...s, aiRunning: true };
    case "issue":
      return { ...s, issues: [...s.issues, d as Issue] };
    case "static_fix":
      return {
        ...s,
        aiFixes: s.aiFixes + 1,
        issues: s.issues.map((i) => (i.id === d.id ? { ...i, fixable: true, patch: d.patch as Patch } : i)),
      };
    case "notice":
      return { ...s, notices: [...s.notices, d.message] };
    case "fixed":
      return { ...s, fixed: d.code, fixedSource: d.source };
    case "done":
      return { ...s, phase: "done", aiRunning: false, status: d.status, totalMs: d.ms };
    default:
      return s;
  }
}

const RANK: Record<Severity, number> = { critical: 0, warning: 1, info: 2 };

export function sortIssues(issues: Issue[]): Issue[] {
  return [...issues].sort((a, b) => RANK[a.severity] - RANK[b.severity] || a.line - b.line || a.id.localeCompare(b.id));
}

export function countIssues(issues: Issue[]): Counts {
  const c: Counts = { critical: 0, warning: 0, info: 0 };
  for (const i of issues) c[i.severity]++;
  return c;
}

/** line number -> the worst severity of any issue covering it */
export function worstByLine(issues: Issue[]): Map<number, Severity> {
  const out = new Map<number, Severity>();
  for (const i of issues) {
    for (let n = i.line; n <= Math.max(i.line, i.end_line); n++) {
      const cur = out.get(n);
      if (!cur || RANK[i.severity] < RANK[cur]) out.set(n, i.severity);
    }
  }
  return out;
}

export interface Filters {
  severities: Set<Severity>;
  source: "all" | "rule" | "ai";
}

export const allFilters = (): Filters => ({ severities: new Set(SEVERITIES), source: "all" });

export function filterIssues(issues: Issue[], f: Filters): Issue[] {
  return issues.filter((i) => f.severities.has(i.severity) && (f.source === "all" || i.source === f.source));
}
