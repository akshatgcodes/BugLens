// Line diff for the review's "original vs suggested" view, plus word-level highlights
// inside changed lines. LCS over lines after trimming the common prefix and suffix:
// fixes touch a few lines, so the part that needs the quadratic table is small.

export type Op = { type: "equal" | "del" | "add"; a?: number; b?: number };

const MAX_CELLS = 4_000_000;

function lcs<T>(a: T[], b: T[]): Op[] {
  let start = 0;
  while (start < a.length && start < b.length && a[start] === b[start]) start++;
  let endA = a.length;
  let endB = b.length;
  while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
    endA--;
    endB--;
  }
  const ops: Op[] = [];
  for (let i = 0; i < start; i++) ops.push({ type: "equal", a: i, b: i });

  const n = endA - start;
  const m = endB - start;
  if (n * m > MAX_CELLS) {
    // Too big to align: show it as replaced wholesale rather than freeze the tab
    for (let i = 0; i < n; i++) ops.push({ type: "del", a: start + i });
    for (let j = 0; j < m; j++) ops.push({ type: "add", b: start + j });
  } else {
    // table[i][j] = LCS length of a[start+i..endA) and b[start+j..endB)
    const w = m + 1;
    const table = new Uint32Array((n + 1) * w);
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        table[i * w + j] =
          a[start + i] === b[start + j] ? table[(i + 1) * w + j + 1] + 1 : Math.max(table[(i + 1) * w + j], table[i * w + j + 1]);
      }
    }
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
      if (a[start + i] === b[start + j]) {
        ops.push({ type: "equal", a: start + i, b: start + j });
        i++;
        j++;
      } else if (table[(i + 1) * w + j] >= table[i * w + j + 1]) {
        ops.push({ type: "del", a: start + i++ });
      } else {
        ops.push({ type: "add", b: start + j++ });
      }
    }
    while (i < n) ops.push({ type: "del", a: start + i++ });
    while (j < m) ops.push({ type: "add", b: start + j++ });
  }
  for (let k = 0; k < a.length - endA; k++) ops.push({ type: "equal", a: endA + k, b: endB + k });
  return ops;
}

export function splitLines(text: string): string[] {
  const lines = text.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

export const diffLines = (a: string, b: string) => lcs(splitLines(a), splitLines(b));

// --- word highlights -------------------------------------------------------------------

export type Span = { text: string; changed: boolean };

const TOKEN = /\s+|\w+|[^\w\s]/g;

/** Splits a changed line pair into spans, marking the tokens that differ. */
export function wordDiff(before: string, after: string): { left: Span[]; right: Span[] } {
  const a = before.match(TOKEN) ?? [];
  const b = after.match(TOKEN) ?? [];
  const left: Span[] = [];
  const right: Span[] = [];
  const push = (list: Span[], text: string, changed: boolean) => {
    const last = list[list.length - 1];
    if (last && last.changed === changed) last.text += text;
    else list.push({ text, changed });
  };
  for (const op of lcs(a, b)) {
    if (op.type === "equal") {
      push(left, a[op.a!], false);
      push(right, b[op.b!], false);
    } else if (op.type === "del") push(left, a[op.a!], true);
    else push(right, b[op.b!], true);
  }
  return { left, right };
}

/** Share of non-space characters the two sides have in common, 0..1. */
export function sameShare(left: Span[], right: Span[]): number {
  const size = (spans: Span[], changed?: boolean) =>
    spans.filter((s) => changed === undefined || s.changed === changed).reduce((n, s) => n + s.text.replace(/\s/g, "").length, 0);
  const total = size(left) + size(right);
  return total ? (size(left, false) + size(right, false)) / total : 1;
}

// --- rows for the views ----------------------------------------------------------------

export type Side = { n: number; text: string; spans?: Span[] };
export type Row = { kind: "equal" | "change" | "del" | "add"; left?: Side; right?: Side };

/** Side-by-side rows: runs of deletions and additions are paired up line by line. */
export function splitRows(a: string, b: string): Row[] {
  const al = splitLines(a);
  const bl = splitLines(b);
  const rows: Row[] = [];
  let dels: number[] = [];
  let adds: number[] = [];
  const flush = () => {
    const k = Math.max(dels.length, adds.length);
    for (let i = 0; i < k; i++) {
      const d = dels[i];
      const ad = adds[i];
      if (d !== undefined && ad !== undefined) {
        const { left, right } = wordDiff(al[d], bl[ad]);
        // Word highlights only help when the two lines are versions of each other
        const similar = sameShare(left, right) >= 0.5;
        rows.push({
          kind: "change",
          left: { n: d + 1, text: al[d], spans: similar ? left : undefined },
          right: { n: ad + 1, text: bl[ad], spans: similar ? right : undefined },
        });
      } else if (d !== undefined) rows.push({ kind: "del", left: { n: d + 1, text: al[d] } });
      else rows.push({ kind: "add", right: { n: ad + 1, text: bl[ad] } });
    }
    dels = [];
    adds = [];
  };
  for (const op of lcs(al, bl)) {
    if (op.type === "del") dels.push(op.a!);
    else if (op.type === "add") adds.push(op.b!);
    else {
      flush();
      rows.push({ kind: "equal", left: { n: op.a! + 1, text: al[op.a!] }, right: { n: op.b! + 1, text: bl[op.b!] } });
    }
  }
  flush();
  return rows;
}

/** Unified rows: each change shows its old lines, then its new lines. */
export function unifiedRows(a: string, b: string): Row[] {
  return splitRows(a, b).flatMap((r): Row[] =>
    r.kind === "change" ? [{ kind: "del", left: r.left }, { kind: "add", right: r.right }] : [r],
  );
}

export type Block = { type: "rows"; rows: Row[] } | { type: "gap"; rows: Row[] };

/** Keeps `context` unchanged rows around each change and folds the rest into gaps. */
export function fold(rows: Row[], context = 3): Block[] {
  const keep = rows.map(() => false);
  rows.forEach((r, i) => {
    if (r.kind === "equal") return;
    for (let k = Math.max(0, i - context); k <= Math.min(rows.length - 1, i + context); k++) keep[k] = true;
  });
  const blocks: Block[] = [];
  rows.forEach((r, i) => {
    const type = keep[i] ? "rows" : "gap";
    const last = blocks[blocks.length - 1];
    if (last && last.type === type) last.rows.push(r);
    else blocks.push({ type, rows: [r] });
  });
  // A gap of one or two lines isn't worth a click
  return blocks.flatMap((b) => (b.type === "gap" && b.rows.length <= 2 ? [{ type: "rows" as const, rows: b.rows }] : [b]));
}

export function stats(rows: Row[]): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  for (const r of rows) {
    if (r.kind === "add" || r.kind === "change") added++;
    if (r.kind === "del" || r.kind === "change") removed++;
  }
  return { added, removed };
}
