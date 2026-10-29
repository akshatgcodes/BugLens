# Decisions

Timings and counts below come from local runs against Groq's `openai/gpt-oss-120b` on 2026-10-30, using the five built-in samples. Model output varies from run to run, so treat them as observations, not benchmarks.

### 1. Rules first, model second
**Decision:** Static rules run and are sent to the browser before the model is called. The model is told what they found.
**Why:** The rules are free and instant (under a millisecond on the 45-line Flask sample) and never miss the pattern they know. The model is slow (4.5 to 21 seconds per sample in the final run) and varies between runs, so it's best spent on what patterns can't express: logic errors, edge cases, missing error handling, indirect injection.
**Trade-off:** Two engines to maintain, and their findings have to be merged (see 6).

### 2. Rules match a masked copy of the code
**Decision:** A small per-language scanner produces three same-length views: raw, code with string contents masked and comments blanked, and comments only. Each rule picks a view.
**Why:** On raw text, `eval(` in a docstring or `password = "x"` in a comment would be flagged. Equal length keeps offsets and line numbers identical across views. Rules about strings (secrets, SQL) match the raw view and then check that the match isn't in a comment or inside a larger string.
**Trade-off:** It's a scanner, not a parser: JavaScript regex literals and PHP heredocs aren't understood. No data flow either, so `q = request.args["q"]` on one line and `execute(q)` on another isn't connected; the model covers that.

### 3. Rule fixes never change the line count
**Decision:** A rule fix replaces text within its own line. Imports a fix needs (`import os` for an environment variable) are inserted afterwards in one block, and the insertion is recorded as a `Shift(at, k)`.
**Why:** Rule findings, model issues and the code view all talk in line numbers. With line-local fixes plus one known shift, model line numbers (which refer to the code it was shown) map back to the code the user pasted.

### 4. Fixes as search/replace pairs, not a rewritten file
**Context:** The first version asked the model for the whole corrected file after a marker line. The 31-line Express sample came back as 72 lines; blank lines were dropped and comments added, so the diff was mostly noise. In two of three runs the corrected file couldn't be found at all (in the one inspected, the model had written `===` instead of `===FIXED===`).
**Decision:** Each issue may carry `find` (lines copied from the code) and `replace`. A fix is applied only if `find` matches exactly one place: exactly, then ignoring trailing spaces, then ignoring indentation (re-indenting the replacement). Copied line-number prefixes are stripped. Ambiguous or unmatched fixes are dropped, not guessed.
**Why:** Diffs contain only real changes, every issue gets its own before/after, and a fix for a line the model misread simply doesn't apply.

### 5. One JSON object per issue, read with a brace scanner
**Decision:** The model streams one object per issue; the server extracts each complete top-level `{...}` (tracking strings and escapes) as soon as its closing brace arrives.
**Why:** A single JSON document (JSON mode) can only be parsed at the end, which defeats streaming. Line-by-line parsing broke when the model pretty-printed objects or wrapped them in an array or code fences; the scanner copes with all of those and with a stray closing brace. Each object is validated on its own, so one bad object costs one issue, not the review.

### 6. Repeated findings become fixes
**Decision:** If the model reports an issue whose line range covers a rule finding of the same category, it's not shown as a new issue. If it carries a fix and the rule couldn't fix that finding, the fix is attached to the rule finding.
**Why:** Despite the prompt, the model repeatedly re-reported rule findings, typically the SQL injection, and usually with exactly the parameterised-query fix the rule can't make. Dropping those lost the fix; showing them duplicated the issue.

### 7. A 16k output budget; default reasoning effort
**Context:** gpt-oss reasons before answering, and the reasoning counts against the output limit. Before the change, two of five runs on the Express sample stopped with `finish_reason: length` after only 353 and 817 characters of answer.
**Decision:** `LLM_MAX_TOKENS=16000`; a cut-off reply shows a notice and marks the report partial, instead of looking like "no issues". `LLM_REASONING_EFFORT` is configurable but left at the provider default.
**Why the default:** One run each on three samples with effort `low` took 6.6–10.6 s and found 0–2 AI issues; `medium` took 13.8–19.1 s and found 4 each, including the XSS in the Express sample and the `findIndex` returning -1 bug in the TypeScript sample, which `low` missed.

### 8. Server-Sent Events over a POST, read with fetch
**Decision:** `POST /api/analyze` returns `text/event-stream`; the browser reads it with `fetch` and a small parser instead of `EventSource`.
**Why:** `EventSource` only does GET, and the code doesn't fit in a URL. SSE over a normal HTTP response works through the Vite proxy and typical reverse proxies (`X-Accel-Buffering: no` is set for nginx), with no WebSocket server.

### 9. Save the report even if the browser leaves
**Decision:** The report is written in a `finally` block of the streaming generator.
**Why:** Closing the tab mid-review stops the generator. Whatever arrived (at least the rule results) is still in History, marked partial.

### 10. Own diff instead of a library
**Decision:** LCS line diff (after trimming the common prefix and suffix), pairing of replaced lines, word-level highlights only when a pair is at least half the same, folding of unchanged runs.
**Why:** It's under 200 lines, unit-tested, and does exactly the views needed (split, unified, and the per-issue patch). Word highlights on unrelated lines that happen to be paired were noise, hence the similarity check.

### 11. Owner password, like the other projects
**Decision:** One `APP_PASSWORD`, a signed session cookie, every API route behind it.
**Why:** The AI review spends a paid or rate-limited API key. A public page would let anyone use it up.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
