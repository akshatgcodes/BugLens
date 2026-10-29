import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { SeverityBadge } from "../components/IssueList";
import TopBar from "../components/TopBar";
import { LANGUAGES, type Category, type RuleInfo } from "../types";

const CATEGORY: Record<Category, string> = { security: "Security", bug: "Bugs", smell: "Code smells", performance: "Performance" };

export default function Rules() {
  const [rules, setRules] = useState<RuleInfo[] | null>(null);
  const [lang, setLang] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.rules().then((r) => setRules(r.rules)).catch((e) => setError(e.message));
  }, []);

  const groups = useMemo(() => {
    const shown = (rules ?? []).filter((r) => lang === "all" || r.languages.length === 0 || r.languages.includes(lang));
    return (Object.keys(CATEGORY) as Category[]).map((c) => [c, shown.filter((r) => r.category === c)] as const).filter(([, list]) => list.length);
  }, [rules, lang]);

  return (
    <div className="shell">
      <TopBar />
      <main className="page">
        <div className="page-head">
          <div>
            <h1>Static rules</h1>
            <p className="muted">
              These run before the AI, in milliseconds and for free. Strings and comments are masked first, so <code>"eval("</code> in a string doesn't count.
              Rules marked <span className="fix-tag">auto-fix</span> change the code themselves; the AI suggests fixes for the rest.
            </p>
          </div>
          <select className="select-sm" aria-label="Language" value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="all">All languages</option>
            {Object.entries(LANGUAGES)
              .filter(([k]) => k !== "other")
              .map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
          </select>
        </div>
        {error && <p className="error">{error}</p>}
        {groups.map(([cat, list]) => (
          <section key={cat} className="rule-group">
            <h2>
              {CATEGORY[cat]} <span className="count">{list.length}</span>
            </h2>
            <ul className="rule-list">
              {list.map((r) => (
                <li key={r.id} className="panel rule">
                  <div className="rule-head">
                    <SeverityBadge severity={r.severity} />
                    <strong>{r.title}</strong>
                    <code className="small">{r.id}</code>
                    {r.fixable && <span className="fix-tag">auto-fix</span>}
                  </div>
                  <p>{r.explanation}</p>
                  {r.suggestion && (
                    <p className="suggestion small">
                      <strong>Fix:</strong> {r.suggestion}
                    </p>
                  )}
                  <p className="muted small">{r.languages.length ? r.languages.map((l) => LANGUAGES[l] ?? l).join(", ") : "Every language"}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </main>
    </div>
  );
}
