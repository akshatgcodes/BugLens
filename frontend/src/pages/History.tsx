import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { SeverityBadge } from "../components/IssueList";
import TopBar from "../components/TopBar";
import { LANGUAGES, SEVERITIES, type ReportSummary } from "../types";

const STATUS: Record<ReportSummary["status"], string> = { complete: "", partial: "AI review incomplete", static: "rules only" };

export default function History() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.reports().then(setReports).catch((e) => setError(e.message));
  }, []);

  const remove = async (r: ReportSummary) => {
    if (!confirm(`Delete the review of ${r.title}?`)) return;
    await api.removeReport(r.id);
    setReports((list) => list?.filter((x) => x.id !== r.id) ?? null);
  };

  return (
    <div className="shell">
      <TopBar />
      <main className="page">
        <h1>History</h1>
        <p className="muted">Every review is saved with its code, issues and suggested fix.</p>
        {error && <p className="error">{error}</p>}
        {reports?.length === 0 && (
          <p className="empty">
            No reviews yet. <Link to="/">Review some code</Link>.
          </p>
        )}
        <ul className="report-list">
          {reports?.map((r) => (
            <li key={r.id} className="panel report-row">
              <Link to={`/r/${r.id}`} className="report-link">
                <span className="report-title">{r.title}</span>
                <span className="muted small">
                  {LANGUAGES[r.language] ?? r.language} · {new Date(r.created_at).toLocaleString()}
                  {STATUS[r.status] && ` · ${STATUS[r.status]}`}
                </span>
              </Link>
              <span className="report-counts">
                {SEVERITIES.filter((s) => r.counts[s]).map((s) => (
                  <span key={s} className="count-badge">
                    <SeverityBadge severity={s} /> {r.counts[s]}
                  </span>
                ))}
                {SEVERITIES.every((s) => !r.counts[s]) && <span className="muted small">clean</span>}
              </span>
              <button className="icon-btn" aria-label={`Delete ${r.title}`} onClick={() => remove(r)}>
                ✕
              </button>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
