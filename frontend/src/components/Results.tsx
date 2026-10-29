import { useMemo, useState } from "react";
import { allFilters, countIssues, filterIssues, sortIssues, type Filters, type ReviewState } from "../lib/review";
import { useMedia } from "../lib/useMedia";
import { SEVERITIES, SEVERITY_LABEL, type Issue } from "../types";
import DiffView, { useDiffStats } from "./DiffView";
import IssueList from "./IssueList";

interface Props {
  state: ReviewState;
  selected: Issue | null;
  onSelect: (issue: Issue) => void;
}

function shortModel(model?: string) {
  return model ? model.split("/").pop() : "";
}

export default function Results({ state, selected, onSelect }: Props) {
  const [tab, setTab] = useState<"issues" | "diff">("issues");
  const [filters, setFilters] = useState<Filters>(allFilters);
  const narrow = useMedia("(max-width: 760px)");
  const [layout, setLayout] = useState<"split" | "unified" | null>(null);
  const [copied, setCopied] = useState(false);

  const counts = useMemo(() => countIssues(state.issues), [state.issues]);
  const shown = useMemo(() => sortIssues(filterIssues(state.issues, filters)), [state.issues, filters]);
  const fixed = state.fixed ?? state.code;
  const diff = useDiffStats(state.code, fixed);
  const ruleCount = state.issues.filter((i) => i.source === "rule").length;
  const aiCount = state.issues.length - ruleCount;
  const done = state.phase === "done";
  const aiOff = state.status === "static";

  const toggle = (sev: Issue["severity"]) => {
    const next = new Set(filters.severities);
    if (next.has(sev) && next.size > 1) next.delete(sev);
    else next.add(sev);
    setFilters({ ...filters, severities: next });
  };

  const copy = async () => {
    await navigator.clipboard.writeText(fixed);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="results" aria-label="Review results" aria-busy={state.phase === "running"}>
      <div className="stages">
        <div className="stage">
          <span className="stage-icon" aria-hidden>
            ⚡
          </span>
          <span>
            <strong>Static rules</strong>{" "}
            <span className="muted">
              {state.staticMs === undefined && !done ? "running…" : `${ruleCount} found${state.staticMs !== undefined ? ` in ${state.staticMs} ms` : ""}`}
            </span>
          </span>
        </div>
        <div className="stage">
          <span className={`stage-icon ${state.aiRunning ? "spin" : ""}`} aria-hidden>
            {state.aiRunning ? "◌" : "✦"}
          </span>
          <span>
            <strong>AI review</strong>{" "}
            <span className="muted">
              {aiOff
                ? "off"
                : state.aiRunning
                  ? `reading the code… ${aiCount ? `${aiCount} so far` : ""}`
                  : done
                    ? `${aiCount} found${state.aiFixes ? `, fixed ${state.aiFixes} rule finding${state.aiFixes > 1 ? "s" : ""}` : ""}${state.model ? ` · ${shortModel(state.model)}` : ""}`
                    : "waiting"}
            </span>
          </span>
        </div>
      </div>

      {state.error && (
        <p className="notice notice-error" role="alert">
          {state.error}
        </p>
      )}
      {state.notices.map((n, i) => (
        <p key={i} className="notice">
          {n}
        </p>
      ))}

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "issues"} className={`tab ${tab === "issues" ? "active" : ""}`} onClick={() => setTab("issues")}>
          Issues <span className="count">{state.issues.length}</span>
        </button>
        <button role="tab" aria-selected={tab === "diff"} className={`tab ${tab === "diff" ? "active" : ""}`} onClick={() => setTab("diff")}>
          Suggested fix{" "}
          {(diff.added > 0 || diff.removed > 0) && (
            <span className="count">
              <span className="plus">+{diff.added}</span> <span className="minus">−{diff.removed}</span>
            </span>
          )}
        </button>
      </div>

      {tab === "issues" ? (
        <>
          <div className="filters">
            {SEVERITIES.map((s) => (
              <button key={s} className={`chip chip-${s} ${filters.severities.has(s) ? "on" : ""}`} aria-pressed={filters.severities.has(s)} onClick={() => toggle(s)}>
                {SEVERITY_LABEL[s]} <span className="chip-n">{counts[s]}</span>
              </button>
            ))}
            <select className="select-sm" aria-label="Source" value={filters.source} onChange={(e) => setFilters({ ...filters, source: e.target.value as Filters["source"] })}>
              <option value="all">Rules + AI</option>
              <option value="rule">Rules only</option>
              <option value="ai">AI only</option>
            </select>
          </div>
          <IssueList issues={shown} selected={selected} onSelect={onSelect} />
          {done && state.issues.length === 0 && <p className="empty">No issues found. Nice.</p>}
          {done && state.issues.length > 0 && shown.length === 0 && <p className="empty muted">Nothing matches these filters.</p>}
        </>
      ) : (
        <div className="diff-pane">
          <div className="diff-tools">
            <span className="muted small">
              {state.fixedSource === "model" ? "Rule fixes and AI fixes" : "Rule fixes only"}
              {!done && " · may still change"}
            </span>
            <div className="seg" role="group" aria-label="Diff layout">
              {(["split", "unified"] as const).map((l) => (
                <button key={l} className={(layout ?? (narrow ? "unified" : "split")) === l ? "on" : ""} onClick={() => setLayout(l)}>
                  {l === "split" ? "Side by side" : "Unified"}
                </button>
              ))}
            </div>
            <button className="btn btn-sm" onClick={copy}>
              {copied ? "Copied" : "Copy fixed code"}
            </button>
          </div>
          <DiffView before={state.code} after={fixed} layout={layout ?? (narrow ? "unified" : "split")} />
        </div>
      )}
    </section>
  );
}
