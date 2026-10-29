# Architecture

```
 React app                                   FastAPI
 ─────────                                   ───────
 Review page ── POST /api/analyze ─────────▶ analyze()
   │  (fetch + ReadableStream,                 │
   │   own SSE parser)                         ├─ languages.detect   file name → content signals
   │                                           ├─ lexer.scan         raw · code · comment views
   │◀── event: meta ───────────────────────────┤
   │◀── event: static  (rule issues, ─────────┤─ rules.find         31 regex rules, < 1 ms
   │                   rule-fixed code)        ├─ rules.apply_fixes  line-local fixes
   │                                           ├─ rules.insert_imports (+ line Shift)
   │◀── event: ai_start ───────────────────────┤
   │◀── event: issue / static_fix (streamed) ──┤─ review.run         ChatOpenAI.stream()
   │◀── event: notice (cut off / failed) ──────┤    ObjectScanner → validate → apply_patch
   │◀── event: fixed   (final code) ───────────┤
   │◀── event: done    (report id, counts) ────┤─ Report saved (also if the client leaves)
   │
   ├─ CodeView    lines marked by worst severity
   ├─ IssueList   filters, per-issue before/after
   └─ DiffView    LCS line diff, word highlights, folding
```

## Backend modules

| Module | Role |
|---|---|
| `languages.py` | Language from the extension, else weighted regex signals (e.g. `^package \w+` for Go, `self.` for Python). TypeScript wins over JavaScript only when there are type signals. |
| `lexer.py` | One pass over the source per language syntax (line and block comments, quote kinds, which quotes span lines, which have no escapes). Produces three equal-length views: `raw`, `code` (strings masked, comments blanked), `comment`. |
| `rules.py` | `Rule` = id, severity, category, pattern, view, optional `when(match, views)` and `fix(match, span, language)`. `find()` returns findings (capped at 25 per rule); `apply_fixes()` applies non-overlapping fixes, which never change line count; `insert_imports()` adds what fixes need (Python) and returns a `Shift`. |
| `review.py` | Prompt, streaming call, `ObjectScanner` (complete `{...}` objects out of streamed text, string-aware), `ReviewStream` (validation, de-duplication, fix application), `apply_patch()`. |
| `routers/analyze.py` | The SSE endpoint, saved reports, rule catalogue, samples. |

## Review pipeline

1. Normalise line endings; reject empty input (422) or more than `MAX_CHARS` (413)
2. Detect the language; run the rules; apply their fixes; insert imports
3. Send `static` with the rule issues and the rule-fixed code
4. If AI is on and configured: send the model the rule-fixed code (numbered) and the list of rule findings, each marked *fixed* or *needs a fix*
5. For every complete object the model streams:
   - `fix_for` a rule finding → apply its find/replace → `static_fix`
   - an issue on a rule finding's lines with the same category → treated as that finding's fix (models repeat findings)
   - otherwise validate (line within the code, title present, severity and category mapped to known values), map its line numbers back through the `Shift`, apply its fix if it matches → `issue`
6. `finish_reason == "length"` → a notice and status `partial`
7. `fixed` with the model-fixed code if any model fix applied, else the rule-fixed code
8. Save the report in a `finally` block, so a review the browser abandons is still kept

## API

All under `/api`, all need the owner session except login.

| Method | Path | |
|---|---|---|
| POST | `/auth/login` · `/auth/logout` | |
| GET | `/auth/me` | |
| POST | `/analyze` | body `{code, language?, filename?, ai}` → `text/event-stream` |
| GET | `/reports` | newest 100, without code |
| GET · DELETE | `/reports/{id}` | |
| GET | `/rules` | rule catalogue and languages |
| GET | `/samples` | demo programs |

Events: `meta`, `static`, `ai_start`, `issue`, `static_fix`, `notice`, `fixed`, `done`.

## Data model

One table, `reports`: id (12 hex chars), title (file name or "Python snippet, 45 lines"), language, code, issues (JSON list of rule and AI issues, each with its patch), fixed code, fixed_source (`rules` / `model`), model, status (`complete` / `partial` / `static`), ai_error, created_at.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
