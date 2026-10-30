# Deploy

Live at **https://buglens.akshatgcodes.in**: one Vercel project, connected to this repo, so every push to `main` deploys (Dependabot branches are skipped by `ignoreCommand`).

| Path | Served by |
|---|---|
| `/` | the landing page (`landing/`, a Next.js static export) |
| `/app/` | the React app (`frontend/`, built with `VITE_BASE=/app/`) |
| `/api/…`, `/health` | FastAPI as a Python function (`index.py` imports `backend/app/main.py`) |

`vercel.json` holds the builds and routes. Vercel's Python runtime installs from `requirements.txt` at the root, which is exported from `backend/uv.lock`:

```bash
cd backend && uv export --no-dev --no-hashes --no-emit-project -o ../requirements.txt
```

The database is Neon Postgres (free tier, Singapore). The app and API share one origin, so the session cookie needs no cross-site settings.

## Environment

Set in the Vercel project, production:

- `DATABASE_URL`: Neon connection string (`postgresql+psycopg://…`, pooled), so reports survive between function instances
- `SESSION_SECRET`: long random value
- `APP_PASSWORD`: `demo1234` on the public demo
- `LLM_PROVIDER=groq`, `LLM_API_KEY`: without a key the static rules still run
- `DATA_DIR=/tmp/buglens`: the function's filesystem is read-only except `/tmp`
- `FRONTEND_URL=https://buglens.akshatgcodes.in`, `CROSS_SITE_COOKIES=false`

`maxDuration` is 300 seconds in `vercel.json`, because an AI review streams for up to a minute or two.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
