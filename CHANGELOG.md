# Changelog

All notable changes to **BugLens** are documented here.

---

## [Unreleased]

### ✨ Added
- Product page at `/` and the app at `/app/`, served together from one host
- Deployed on Vercel: the landing page and app as static builds, the API as a Python function, Neon Postgres

---

## [0.1.0] — 2026-10-30

### ✨ Added
- 31 static rules for Python, JavaScript, TypeScript, Java, Go, PHP and any language (secrets, SQL and shell injection, eval, unsafe deserialisation, TLS, weak hashes, insecure random, XSS sinks, common bugs and smells), matched on code with strings and comments masked
- Line-local automatic fixes for the mechanical cases, with the imports they need
- Streamed AI review (Groq, OpenAI or Ollama) that skips what the rules found and adds search/replace fixes, including for rule findings the rules can't fix
- Review page: editor with samples and file open, instant rule results, live AI issues, annotated code, severity and source filters, per-issue before/after, side-by-side and unified diff of the suggested code
- Saved reports (History), rule catalogue page, owner password login

### 🧪 Tests
- Scanner, a case that must fire for every rule plus cases that must not, fixes, the review stream (chunking, layouts, validation, fix matching) and the API with a fake streaming model
- Line diff, word highlights, folding, SSE parsing and the review state reducer

---

[Unreleased]: https://github.com/akshatgcodes/BugLens/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/akshatgcodes/BugLens/releases/tag/v0.1.0

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
