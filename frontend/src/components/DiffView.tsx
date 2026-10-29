import { Fragment, useMemo, useState } from "react";
import { fold, splitRows, stats, unifiedRows, type Row, type Side, type Span } from "../lib/diff";

interface Props {
  before: string;
  after: string;
  layout: "split" | "unified";
  context?: number;
  numbered?: boolean;
}

function Text({ side }: { side?: Side }) {
  if (!side) return null;
  if (!side.spans) return <>{side.text || " "}</>;
  return (
    <>
      {side.spans.map((s: Span, i) =>
        s.changed ? (
          <mark key={i} className="word">
            {s.text}
          </mark>
        ) : (
          <Fragment key={i}>{s.text}</Fragment>
        ),
      )}
    </>
  );
}

function SplitRow({ r }: { r: Row }) {
  const leftKind = r.kind === "equal" ? "" : r.left ? "del" : "empty";
  const rightKind = r.kind === "equal" ? "" : r.right ? "add" : "empty";
  return (
    <tr>
      <td className={`dn ${leftKind}`}>{r.left?.n}</td>
      <td className={`dc ${leftKind}`}>
        <Text side={r.left} />
      </td>
      <td className={`dn ${rightKind}`}>{r.right?.n}</td>
      <td className={`dc ${rightKind}`}>
        <Text side={r.right} />
      </td>
    </tr>
  );
}

function UnifiedRow({ r }: { r: Row }) {
  const kind = r.kind === "equal" ? "" : r.kind;
  const side = r.kind === "add" ? r.right : r.left;
  return (
    <tr>
      <td className={`dn ${kind}`}>{r.left?.n}</td>
      <td className={`dn ${kind}`}>{r.right?.n}</td>
      <td className={`dc ${kind}`}>
        <span className="sign" aria-hidden>
          {r.kind === "add" ? "+" : r.kind === "del" ? "−" : " "}
        </span>
        <Text side={side} />
      </td>
    </tr>
  );
}

export default function DiffView({ before, after, layout, context = 3, numbered = true }: Props) {
  const rows = useMemo(() => (layout === "split" ? splitRows(before, after) : unifiedRows(before, after)), [before, after, layout]);
  const blocks = useMemo(() => fold(rows, context), [rows, context]);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const cols = layout === "split" ? 4 : 3;
  const Row = layout === "split" ? SplitRow : UnifiedRow;

  if (!stats(rows).added && !stats(rows).removed) return <p className="muted small diff-empty">No changes.</p>;

  return (
    <div className="diff mono">
      <table className={`diff-table diff-${layout} ${numbered ? "" : "no-numbers"}`}>
        <tbody>
          {blocks.map((b, bi) =>
            b.type === "rows" || open.has(bi) ? (
              b.rows.map((r, ri) => <Row key={`${bi}-${ri}`} r={r} />)
            ) : (
              <tr key={bi}>
                <td colSpan={cols} className="gap">
                  <button className="link-btn small" onClick={() => setOpen(new Set(open).add(bi))}>
                    ⋯ {b.rows.length} unchanged lines
                  </button>
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  );
}

export function useDiffStats(before: string, after: string) {
  return useMemo(() => stats(splitRows(before, after)), [before, after]);
}
