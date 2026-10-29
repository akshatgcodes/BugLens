import { useEffect, useReducer, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import CodeView from "../components/CodeView";
import Results from "../components/Results";
import TopBar from "../components/TopBar";
import { initialReview, reviewReducer, sortIssues } from "../lib/review";
import { LANGUAGES, type Issue, type Report } from "../types";

export default function ReportPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [state, dispatch] = useReducer(reviewReducer, initialReview);
  const [selected, setSelected] = useState<Issue | null>(null);

  useEffect(() => {
    api
      .report(id)
      .then((r) => {
        setReport(r);
        dispatch({ type: "load", report: r });
      })
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? "This report doesn't exist (any more)." : String(e.message)));
  }, [id]);

  const remove = async () => {
    if (!report || !confirm(`Delete the review of ${report.title}?`)) return;
    await api.removeReport(report.id);
    navigate("/history");
  };

  const selectLine = (line: number) => {
    const hit = sortIssues(state.issues).find((i) => line >= i.line && line <= Math.max(i.line, i.end_line));
    if (hit) setSelected(hit);
  };

  return (
    <div className="shell">
      <TopBar />
      {error && <p className="center error">{error}</p>}
      {!error && !report && <p className="center muted">Loading…</p>}
      {report && (
        <main className="workspace">
          <section className="pane code-pane" aria-label="Code">
            <div className="pane-head">
              <span className="pane-title">
                {report.title}
                <span className="lang-tag">{LANGUAGES[report.language] ?? report.language}</span>
              </span>
              <button
                className="btn btn-sm"
                onClick={() => navigate("/", { state: { code: report.code, filename: report.title.includes(" snippet, ") ? null : report.title, language: report.language } })}
              >
                Open in editor
              </button>
              <button className="icon-btn" aria-label="Delete report" title="Delete report" onClick={remove}>
                ✕
              </button>
            </div>
            <CodeView code={state.code} issues={state.issues} selected={selected} onSelectLine={selectLine} />
          </section>
          <section className="pane results-pane">
            <p className="muted small saved">Reviewed {new Date(report.created_at).toLocaleString()}</p>
            <Results state={state} selected={selected} onSelect={(i) => setSelected(selected?.id === i.id ? null : i)} />
          </section>
        </main>
      )}
    </div>
  );
}
