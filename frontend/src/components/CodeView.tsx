import { useEffect, useMemo, useRef } from "react";
import { splitLines } from "../lib/diff";
import { worstByLine } from "../lib/review";
import type { Issue } from "../types";

interface Props {
  code: string;
  issues: Issue[];
  selected: Issue | null;
  onSelectLine: (line: number) => void;
}

/** The reviewed code, read-only, with each issue's lines marked by severity. */
export default function CodeView({ code, issues, selected, onSelectLine }: Props) {
  const lines = useMemo(() => splitLines(code), [code]);
  const marks = useMemo(() => worstByLine(issues), [issues]);
  const titles = useMemo(() => {
    const m = new Map<number, string[]>();
    for (const i of issues) m.set(i.line, [...(m.get(i.line) ?? []), i.title]);
    return m;
  }, [issues]);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!selected || !box.current) return;
    const row = box.current.querySelector<HTMLElement>(`[data-line="${selected.line}"]`);
    // Scroll this pane only; scrollIntoView would also move the page
    if (row) box.current.scrollTo({ top: row.offsetTop - box.current.clientHeight / 3, behavior: "smooth" });
  }, [selected]);

  const inSelection = (n: number) => selected !== null && n >= selected.line && n <= Math.max(selected.line, selected.end_line);

  return (
    <div className="codeview mono" ref={box} role="region" aria-label="Reviewed code">
      {lines.map((text, i) => {
        const n = i + 1;
        const sev = marks.get(n);
        const t = titles.get(n);
        return (
          <div key={n} data-line={n} className={`cv-row ${sev ? `sev-bg-${sev}` : ""} ${inSelection(n) ? "cv-selected" : ""}`}>
            <span className="cv-num">{n}</span>
            {t ? (
              <button className={`cv-mark sev-dot-${sev}`} title={t.join("\n")} aria-label={`Line ${n}: ${t.join("; ")}`} onClick={() => onSelectLine(n)} />
            ) : (
              <span className="cv-mark" />
            )}
            <span className="cv-text">{text || " "}</span>
          </div>
        );
      })}
    </div>
  );
}
