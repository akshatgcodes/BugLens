import { describe, expect, it } from "vitest";
import type { Issue } from "../types";
import { countIssues, filterIssues, initialReview, reviewReducer, sortIssues, worstByLine, type ReviewState } from "./review";

const issue = (over: Partial<Issue>): Issue => ({
  id: "r1",
  source: "rule",
  rule_id: "x",
  severity: "warning",
  category: "bug",
  line: 1,
  end_line: 1,
  title: "t",
  explanation: "",
  suggestion: "",
  snippet: "",
  fixable: false,
  patch: null,
  ...over,
});

function play(events: [string, unknown][]): ReviewState {
  let s = reviewReducer(initialReview, { type: "start", code: "x = 1\n" });
  for (const [event, data] of events) s = reviewReducer(s, { type: "event", event, data });
  return s;
}

describe("reviewReducer", () => {
  it("builds the review from the event stream", () => {
    const patch = { before: "a", after: "b" };
    const s = play([
      ["meta", { id: "abc", language: "python", model: "m" }],
      ["static", { issues: [issue({ id: "r1" }), issue({ id: "r2", line: 3 })], fixed: "rules", ms: 2 }],
      ["ai_start", {}],
      ["issue", issue({ id: "a1", source: "ai", severity: "critical" })],
      ["static_fix", { id: "r2", patch }],
      ["notice", { message: "heads up" }],
    ]);
    expect(s.phase).toBe("running");
    expect(s.aiRunning).toBe(true);
    expect(s.issues.map((i) => i.id)).toEqual(["r1", "r2", "a1"]);
    expect(s.issues[1]).toMatchObject({ fixable: true, patch });
    expect(s.aiFixes).toBe(1);
    expect(s.fixed).toBe("rules");
    expect(s.notices).toEqual(["heads up"]);

    const done = reviewReducer(
      reviewReducer(s, { type: "event", event: "fixed", data: { code: "model", source: "model" } }),
      { type: "event", event: "done", data: { status: "complete", ms: 900 } },
    );
    expect(done).toMatchObject({ phase: "done", aiRunning: false, fixed: "model", fixedSource: "model", totalMs: 900 });
  });

  it("starting again clears the previous review", () => {
    const s = reviewReducer(play([["notice", { message: "x" }]]), { type: "start", code: "y" });
    expect(s).toEqual({ ...initialReview, phase: "running", code: "y" });
  });
});

describe("helpers", () => {
  const list = [
    issue({ id: "a", severity: "info", line: 1 }),
    issue({ id: "b", severity: "critical", line: 9, source: "ai" }),
    issue({ id: "c", severity: "warning", line: 2, end_line: 4 }),
    issue({ id: "d", severity: "critical", line: 3 }),
  ];

  it("sorts by severity, then line", () => {
    expect(sortIssues(list).map((i) => i.id)).toEqual(["d", "b", "c", "a"]);
  });

  it("counts, filters and finds the worst issue per line", () => {
    expect(countIssues(list)).toEqual({ critical: 2, warning: 1, info: 1 });
    expect(filterIssues(list, { severities: new Set(["critical"]), source: "rule" }).map((i) => i.id)).toEqual(["d"]);
    expect([...worstByLine(list)]).toEqual([
      [1, "info"],
      [9, "critical"],
      [2, "warning"],
      [3, "critical"],
      [4, "warning"],
    ]);
  });
});
