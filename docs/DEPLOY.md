# Deploy

BugLens is **not deployed yet**. This is the intended setup.

| Part | Platform |
|---|---|
| Frontend | Vercel (`frontend/`, build `npm run build`, output `dist`, SPA rewrite to `index.html`) |
| API | Any Python host (e.g. Render), `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Database | Postgres (e.g. Neon) through `DATABASE_URL`, so reports survive restarts on hosts without a persistent disk |
| Model | Groq |

The API is light: there's no local model. A local run sat at about 116 MB of memory after several reviews.

Streaming needs the proxy in front of the API not to buffer responses. The API sets `Cache-Control: no-cache` and `X-Accel-Buffering: no`; if events arrive all at once at the end, buffering is the cause.

## Environment

On the API:

- `APP_PASSWORD` (strong) and `SESSION_SECRET` (long random)
- `LLM_PROVIDER=groq`, `LLM_API_KEY`
- `DATABASE_URL=postgresql+psycopg://…`
- `FRONTEND_URL=https://<frontend-host>`, `CROSS_SITE_COOKIES=true`

On the frontend: `VITE_API_URL=https://<api-host>`.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
