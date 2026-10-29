<p align="center">
  <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"
       fill="none" stroke="#6d28d9" stroke-width="1.5"
       stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="7"/>
    <path d="m21 21-4.3-4.3"/>
    <path d="M11 8v3"/>
    <path d="M11 14h.01"/>
  </svg>
</p>

<h1 align="center">BugLens</h1>

<p align="center">
  <strong>Paste code and get a review: static rules flag secrets, injection and common bugs in under a millisecond, then an AI pass streams in what the rules can't see, with every fix shown as a diff.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/Groq-F55036?style=flat-square" alt="Groq">
  <img src="https://img.shields.io/badge/license-GPL--3.0-6d28d9?style=flat-square" alt="License">
</p>

---

## What is BugLens?

A code reviewer built the way real review tools are: **rules first, model second.**

1. **Static rules** (31 of them, for Python, JavaScript, TypeScript, Java, Go and PHP) run as soon as you press Review. Hardcoded secrets, SQL and shell injection, `eval`, unsafe YAML and pickle, disabled TLS checks, weak hashes, bare `except`, `==` in JavaScript and more. On the 45-line Flask sample they take under a millisecond, cost nothing, and give the same answer every time. Where the fix is mechanical (`== None` → `is None`, a secret → `os.environ[...]`), the rule makes it.
2. **The AI review** streams in next, issue by issue. It's told what the rules already found, so it spends its effort on logic errors, edge cases, missing error handling and injection through indirect paths. It also writes the fixes the rules couldn't make, like turning an f-string query into a parameterised one.
3. **The diff view** shows the original against the suggested code, side by side or unified, with changed words highlighted. Each issue card also shows its own before/after.

Reviews are saved, so you can come back to them in History.

---

## What you get

- **Paste, open a file, or pick a sample** (Flask, Express, TypeScript, Java, Go, each with planted bugs). Language is detected from the file name or the code.
- **Instant static results**, then AI issues appearing as they're written (Server-Sent Events)
- **Annotated code**: lines marked by severity; click a marker or an issue to jump between them
- **Severity filters** (Critical / Warning / Info) and a Rules / AI filter; every issue says where it came from, and rule issues name their rule
- **Suggested fix diff** with folded unchanged regions, word-level highlights and a copy button
- **Rule catalogue** page listing what the static checks look for, per language
- **Works without a key**: with no LLM key (or the AI box unticked) you still get the rules and their fixes
- **Any OpenAI-compatible model**: Groq by default, or OpenAI, or a local Ollama

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19 · TypeScript · Vite · React Router; own LCS line/word diff and SSE parser |
| Backend | FastAPI (StreamingResponse for SSE) · SQLAlchemy |
| Static analysis | a small scanner that masks strings and comments, plus per-language regex rules with line-local fixes |
| AI review | LangChain `ChatOpenAI` streaming against Groq (`openai/gpt-oss-120b`), OpenAI or Ollama |
| Storage | SQLite (or Postgres) for saved reports |
| Tooling | uv · pytest · Vitest · ruff · GitHub Actions |

---

## Run it

```bash
# API → http://localhost:8000/docs
cd backend && uv sync && cp .env.example .env    # set APP_PASSWORD, SESSION_SECRET and LLM_API_KEY
uv run uvicorn main:app --reload

# App → http://localhost:5173
cd frontend && npm install && npm run dev
```

More in [docs/SETUP.md](docs/SETUP.md).

---

## Engineering Decisions

**Why do the rules mask strings and comments first?**
A regex over raw source flags `eval(` in a docstring and `password = "x"` in a comment. The scanner produces a copy of the code with string contents and comments blanked out, same length so line numbers still match, and most rules match against that. The rules that are *about* strings (secrets, SQL) match the raw text and then check the match isn't inside a comment or a larger string.

**Why search/replace fixes instead of asking for the corrected file?**
That was the first version. Asked for the whole file, the model also reformatted it: the 31-line Express sample came back as 72 lines, blank lines were dropped and comments added, so the diff was mostly noise. In two of three runs the corrected file couldn't even be found (in the one inspected, the model had written `===` instead of the agreed `===FIXED===` marker). Now each issue carries `find` (lines copied from the code) and `replace`. BugLens applies a fix only if `find` matches exactly one place, falling back to ignoring trailing spaces or indentation. A fix that doesn't match is dropped instead of guessed.

**Why does the model repeat findings, and what happens then?**
Told not to, it still re-reports rule findings, often with the fix the rule couldn't make. So a repeat that lands on a rule finding's lines, in the same category, is turned into that finding's fix instead of a duplicate issue.

**What would you do differently in v2?**
Use a real parser (tree-sitter) for the rules instead of masked regex, so rules can follow data flow from a request to a query. And run the fixed code through the language's own parser before showing it, to catch fixes that don't compile.

More in [docs/DECISIONS.md](docs/DECISIONS.md).

---

## Docs

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Product requirements: goals, user stories, non-goals |
| [Architecture](docs/ARCHITECTURE.md) | Pipeline, event stream, API |
| [Decisions](docs/DECISIONS.md) | Every major technical decision and why |
| [Setup](docs/SETUP.md) | Local dev setup and env vars |
| [Deploy](docs/DEPLOY.md) | Deployment notes |
| [Contributing](CONTRIBUTING.md) | How to propose changes |
| [Changelog](CHANGELOG.md) | What changed in each release |
| [Security](SECURITY.md) | How to report a vulnerability |

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
