import { useEffect, useReducer, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api";
import CodeEditor from "../components/CodeEditor";
import CodeView from "../components/CodeView";
import Results from "../components/Results";
import TopBar from "../components/TopBar";
import { initialReview, reviewReducer, sortIssues } from "../lib/review";
import { LANGUAGES, type Issue, type Sample } from "../types";

const DRAFT_KEY = "buglens.draft";
const MAX_FILE = 200_000;

interface Draft {
  code: string;
  filename: string | null;
  language: string;
}

function loadDraft(): Draft | null {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_KEY) ?? "null");
  } catch {
    return null;
  }
}

export default function Review() {
  const location = useLocation();
  // "Open in editor" from a saved report hands its code over through router state
  const handed = (location.state as Draft | null) ?? null;
  const initial = handed ?? loadDraft();
  const [code, setCode] = useState(initial?.code ?? "");
  const [filename, setFilename] = useState<string | null>(initial?.filename ?? null);
  const [language, setLanguage] = useState(initial?.language ?? "auto");
  const [ai, setAi] = useState(true);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [state, dispatch] = useReducer(reviewReducer, initialReview);
  const [selected, setSelected] = useState<Issue | null>(null);
  const [editing, setEditing] = useState(true);
  const [fileError, setFileError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    api.samples().then(setSamples).catch(() => {});
    return () => abort.current?.abort();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify({ code, filename, language }));
      } catch {
        // Storage can be full or blocked; the draft is only a convenience
      }
    }, 400);
    return () => clearTimeout(t);
  }, [code, filename, language]);

  const running = state.phase === "running";

  const run = async () => {
    if (!code.trim() || running) return;
    const ctl = new AbortController();
    abort.current = ctl;
    dispatch({ type: "start", code: code.replace(/\r\n/g, "\n") });
    setSelected(null);
    setEditing(false);
    try {
      await api.analyze({ code, language, filename, ai }, (event, data) => dispatch({ type: "event", event, data }), ctl.signal);
    } catch (e) {
      if (ctl.signal.aborted) return;
      dispatch({ type: "error", message: e instanceof Error ? e.message : "The review failed" });
      setEditing(true);
    }
  };

  const stop = () => {
    abort.current?.abort();
    dispatch({ type: "error", message: "Stopped. What arrived so far is kept in History." });
  };

  const openFile = async (file: File | undefined) => {
    setFileError(null);
    if (!file) return;
    if (file.size > MAX_FILE) {
      setFileError(`${file.name} is ${Math.round(file.size / 1000)} KB; the limit is ${MAX_FILE / 1000} KB.`);
      return;
    }
    setCode(await file.text());
    setFilename(file.name);
    setLanguage("auto");
    setEditing(true);
  };

  const pickSample = (id: string) => {
    const s = samples.find((x) => x.id === id);
    if (!s) return;
    setCode(s.code);
    setFilename(s.filename);
    setLanguage(s.language);
    setEditing(true);
  };

  const selectLine = (line: number) => {
    const hit = sortIssues(state.issues).find((i) => line >= i.line && line <= Math.max(i.line, i.end_line));
    if (hit) setSelected(hit);
  };

  const stale = state.phase !== "idle" && code.replace(/\r\n/g, "\n") !== state.code;

  return (
    <div className="shell">
      <TopBar />
      <main className={`workspace ${state.phase === "idle" ? "solo" : ""}`}>
        <section className="pane code-pane" aria-label="Code">
          {editing ? (
            <>
              <div className="pane-head wrap">
                <select className="select-sm" aria-label="Language" value={language} onChange={(e) => setLanguage(e.target.value)}>
                  <option value="auto">Auto-detect</option>
                  {Object.entries(LANGUAGES).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
                <select className="select-sm" aria-label="Load a sample" value="" onChange={(e) => pickSample(e.target.value)}>
                  <option value="">Try a sample…</option>
                  {samples.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
                <label className="btn btn-sm file-btn">
                  Open file
                  <input type="file" accept=".py,.js,.mjs,.cjs,.jsx,.ts,.tsx,.java,.go,.php,.txt" onChange={(e) => openFile(e.target.files?.[0])} />
                </label>
                {filename && (
                  <span className="filename mono small" title={filename}>
                    {filename}
                    <button className="icon-btn tiny" aria-label="Forget file name" onClick={() => setFilename(null)}>
                      ✕
                    </button>
                  </span>
                )}
              </div>
              {fileError && <p className="notice notice-error">{fileError}</p>}
              <CodeEditor
                value={code}
                onChange={(v) => {
                  setCode(v);
                }}
                onSubmit={run}
              />
              <div className="pane-foot">
                <label className="check small">
                  <input type="checkbox" checked={ai} onChange={(e) => setAi(e.target.checked)} /> AI review
                </label>
                <span className="muted small hide-narrow">
                  <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Enter</kbd>
                </span>
                <button className="btn btn-primary" onClick={run} disabled={!code.trim() || running}>
                  {running ? "Reviewing…" : "Review code"}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="pane-head">
                <span className="pane-title">
                  {filename ?? "Snippet"}
                  {state.language && <span className="lang-tag">{LANGUAGES[state.language] ?? state.language}</span>}
                </span>
                {running ? (
                  <button className="btn btn-sm" onClick={stop}>
                    Stop
                  </button>
                ) : (
                  <button className="btn btn-sm" onClick={() => setEditing(true)}>
                    Edit code
                  </button>
                )}
              </div>
              <CodeView code={state.code} issues={state.issues} selected={selected} onSelectLine={selectLine} />
            </>
          )}
        </section>

        {state.phase !== "idle" && (
          <section className="pane results-pane">
            {stale && editing && (
              <p className="notice">
                The code has changed since this review.{" "}
                <button className="link-btn accent" onClick={run}>
                  Review again
                </button>
              </p>
            )}
            <Results state={state} selected={selected} onSelect={(i) => setSelected(selected?.id === i.id ? null : i)} />
            {state.phase === "done" && state.id && (
              <p className="muted small saved">
                Saved to <Link to={`/r/${state.id}`}>History</Link>.
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
