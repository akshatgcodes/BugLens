# Setup

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node 20.19+ or 22.12+ (what Vite 8 needs)
- An API key for an OpenAI-compatible provider ([Groq](https://console.groq.com/keys) has a free tier). Optional: without one, only the static rules run.

## Backend

```bash
cd backend
uv sync
cp .env.example .env      # set APP_PASSWORD, SESSION_SECRET and LLM_API_KEY
uv run uvicorn main:app --reload        # or: uv run uvicorn app.main:app --reload
```

API on http://localhost:8000, interactive docs at `/docs`. SQLite lives in `./data` and the table is created on start.

| Variable | Default | Purpose |
|---|---|---|
| `APP_PASSWORD` | empty | login password; login is refused until it's set |
| `SESSION_SECRET` | dev value | signs the session cookie; set a long random string |
| `FRONTEND_URL` | `http://localhost:5173` | allowed CORS origin |
| `CROSS_SITE_COOKIES` | `false` | `true` when frontend and API are on different sites (HTTPS) |
| `LLM_PROVIDER` | `groq` | `groq`, `openai` or `ollama` |
| `LLM_API_KEY` / `GROQ_API_KEY` | empty | provider key; empty = static rules only |
| `LLM_MODEL` | per provider | groq `openai/gpt-oss-120b` · openai `gpt-4o-mini` · ollama `llama3.2` |
| `LLM_BASE_URL` | per provider | any other OpenAI-compatible endpoint |
| `LLM_MAX_TOKENS` | `16000` | output budget per review, reasoning included |
| `LLM_REASONING_EFFORT` | empty | `low` / `medium` / `high`, reasoning models only |
| `MAX_CHARS` | `40000` | largest submission |
| `MAX_AI_ISSUES` | `15` | cap on model-reported issues |
| `DATA_DIR` | `./data` | SQLite location |
| `DATABASE_URL` | SQLite in `DATA_DIR` | e.g. `postgresql+psycopg://…` |

Groq has been tested end to end. The OpenAI and Ollama presets use the same client but haven't been run against those services yet.

## Frontend

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173, proxies /api to :8000
```

Point the proxy elsewhere with `VITE_API_PROXY=http://localhost:8004 npm run dev`. For a build served separately from the API, set `VITE_API_URL`.

## Checks

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run typecheck && npm test && npm run build
```

Backend tests use a fake streaming model and need no API key.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
