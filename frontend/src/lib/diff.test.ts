import { describe, expect, it } from "vitest";
import { diffLines, fold, splitRows, stats, unifiedRows, wordDiff } from "./diff";
import { SSEParser } from "./sse";

const A = "a\nb\nc\nd\ne\n";

describe("diffLines", () => {
  it("finds the minimal edit", () => {
    const ops = diffLines(A, "a\nB\nc\nd\ne\nf\n").map((o) => o.type[0]).join("");
    expect(ops).toBe("edaeeea");
  });

  it("ignores a final newline and handles empty input", () => {
    expect(diffLines("x\n", "x").every((o) => o.type === "equal")).toBe(true);
    expect(diffLines("", "x\ny").map((o) => o.type)).toEqual(["del", "add", "add"]);
  });
});

describe("splitRows", () => {
  it("pairs replaced lines into change rows with word highlights", () => {
    const rows = splitRows("if x == None:\n    pass\n", "if x is None:\n    pass\n");
    expect(rows.map((r) => r.kind)).toEqual(["change", "equal"]);
    const changed = (spans = rows[0].left!.spans!) => spans.filter((s) => s.changed).map((s) => s.text);
    expect(changed()).toEqual(["=="]);
    expect(changed(rows[0].right!.spans!)).toEqual(["is"]);
  });

  it("doesn't highlight words when the paired lines are unrelated", () => {
    const [row] = splitRows("    db = get_db()\n", "    if not user_id:\n");
    expect(row.kind).toBe("change");
    expect(row.left!.spans).toBeUndefined();
    expect(row.right!.spans).toBeUndefined();
  });

  it("keeps extra lines as plain adds, numbered on their own side", () => {
    const rows = splitRows("a\nb\n", "a\nb1\nb2\nb3\n");
    expect(rows.map((r) => [r.kind, r.left?.n, r.right?.n])).toEqual([
      ["equal", 1, 1],
      ["change", 2, 2],
      ["add", undefined, 3],
      ["add", undefined, 4],
    ]);
    expect(stats(rows)).toEqual({ added: 3, removed: 1 });
  });

  it("unified view lists old lines before new ones", () => {
    expect(unifiedRows("a\nb\n", "a\nc\n").map((r) => r.kind)).toEqual(["equal", "del", "add"]);
  });
});

describe("fold", () => {
  it("keeps context around changes and folds long unchanged runs", () => {
    const old = Array.from({ length: 30 }, (_, i) => `l${i}`).join("\n");
    const rows = splitRows(old, old.replace("l15", "L15"));
    const blocks = fold(rows, 3);
    expect(blocks.map((b) => [b.type, b.rows.length])).toEqual([
      ["gap", 12],
      ["rows", 7],
      ["gap", 11],
    ]);
  });

  it("doesn't fold tiny gaps", () => {
    const rows = splitRows("a\nb\nc\nd\ne\n", "A\nb\nc\nd\nE\n");
    expect(fold(rows, 1).every((b) => b.type === "rows")).toBe(true);
  });
});

describe("wordDiff", () => {
  it("merges neighbouring tokens", () => {
    const { left, right } = wordDiff("x = eval(s)", "x = ast.literal_eval(s)");
    expect(left).toEqual([{ text: "x = ", changed: false }, { text: "eval", changed: true }, { text: "(s)", changed: false }]);
    expect(right.filter((s) => s.changed).map((s) => s.text)).toEqual(["ast.literal_eval"]);
  });
});

describe("SSEParser", () => {
  const stream = 'event: static\ndata: {"a":1}\n\n: keep-alive\n\nevent: issue\ndata: {"b":\ndata: 2}\n\n';

  it.each([1, 3, 7, 1000])("parses frames split into %i-character chunks", (size) => {
    const p = new SSEParser();
    const out = [];
    for (let i = 0; i < stream.length; i += size) out.push(...p.feed(stream.slice(i, i + size)));
    expect(out).toEqual([
      { event: "static", data: '{"a":1}' },
      { event: "issue", data: '{"b":\n2}' },
    ]);
  });

  it("accepts CRLF line endings", () => {
    expect(new SSEParser().feed("event: done\r\ndata: {}\r\n\r\n")).toEqual([{ event: "done", data: "{}" }]);
  });
});
