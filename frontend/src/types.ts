export type Severity = "critical" | "warning" | "info";
export type Category = "security" | "bug" | "smell" | "performance";

export const SEVERITIES: Severity[] = ["critical", "warning", "info"];
export const SEVERITY_LABEL: Record<Severity, string> = { critical: "Critical", warning: "Warning", info: "Info" };

export const LANGUAGES: Record<string, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  java: "Java",
  go: "Go",
  php: "PHP",
  other: "Other",
};

export interface Patch {
  before: string;
  after: string;
}

export interface Issue {
  id: string;
  source: "rule" | "ai";
  rule_id: string | null;
  severity: Severity;
  category: Category;
  line: number;
  end_line: number;
  title: string;
  explanation: string;
  suggestion: string;
  snippet: string;
  fixable: boolean;
  patch: Patch | null;
}

export type Counts = Record<Severity, number>;
export type Status = "complete" | "partial" | "static";

export interface ReportSummary {
  id: string;
  title: string;
  language: string;
  status: Status;
  counts: Counts;
  created_at: string;
}

export interface Report extends ReportSummary {
  code: string;
  issues: Issue[];
  fixed: string;
  fixed_source: "model" | "rules";
  model: string;
  ai_error: string;
}

export interface Sample {
  id: string;
  title: string;
  language: string;
  filename: string;
  code: string;
}

export interface RuleInfo {
  id: string;
  title: string;
  severity: Severity;
  category: Category;
  languages: string[];
  explanation: string;
  suggestion: string;
  fixable: boolean;
}
