import { SEVERITY_LABEL, type Issue } from "../types";
import DiffView from "./DiffView";

interface Props {
  issues: Issue[];
  selected: Issue | null;
  onSelect: (issue: Issue) => void;
}

export function SeverityBadge({ severity }: { severity: Issue["severity"] }) {
  return <span className={`sev sev-${severity}`}>{SEVERITY_LABEL[severity]}</span>;
}

export default function IssueList({ issues, selected, onSelect }: Props) {
  if (!issues.length) return null;
  return (
    <ul className="issues">
      {issues.map((i) => {
        const open = selected?.id === i.id;
        return (
          <li key={i.id} className={`issue ${open ? "open" : ""} ${i.source === "ai" ? "from-ai" : ""}`}>
            <button className="issue-head" aria-expanded={open} onClick={() => onSelect(i)}>
              <SeverityBadge severity={i.severity} />
              <span className="issue-title">{i.title}</span>
              <span className="issue-line mono">
                L{i.line}
                {i.end_line > i.line ? `–${i.end_line}` : ""}
              </span>
            </button>
            <div className="issue-meta small">
              <span className={`source source-${i.source}`}>{i.source === "ai" ? "AI" : "Rule"}</span>
              {i.rule_id && <code>{i.rule_id}</code>}
              <span className="muted">{i.category}</span>
              {i.fixable && <span className="fix-tag">fix in diff</span>}
            </div>
            {open && (
              <div className="issue-body">
                {i.explanation && <p>{i.explanation}</p>}
                {i.suggestion && (
                  <p className="suggestion">
                    <strong>Fix:</strong> {i.suggestion}
                  </p>
                )}
                {i.patch ? (
                  <DiffView before={i.patch.before} after={i.patch.after} layout="unified" context={0} numbered={false} />
                ) : (
                  i.snippet && <pre className="snippet mono">{i.snippet}</pre>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
