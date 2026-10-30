import type { Site } from "./types";

export const site: Site = {
  name: "BugLens",
  letter: "B",
  title: "BugLens — rules first, model second",
  description:
    "Paste code and get a review: static rules flag secrets, injection and common bugs in under a millisecond, then an AI pass streams in what the rules can't see, with every fix shown as a diff.",
  meta: ["live", "Python · JS · TS · Java · Go · PHP", "GPLv3"],
  headline: ["Code review,", "rules first, model second."],
  intro:
    "Paste code and press Review. 31 static rules flag secrets, injection and common bugs in under a millisecond. Then an AI review streams in, issue by issue, looking for what the rules can't see, and every fix is shown as a diff.",
  primary: { label: "Open BugLens", href: "/app/" },
  repo: "https://github.com/akshatgcodes/BugLens",
  note: "Demo password: `demo1234`. Pick one of the samples (each has planted bugs) and press Review.",
  xfactor: {
    title: "Two passes, each doing what it's good at.",
    intro:
      "Rules are instant, free and give the same answer every time. A model can follow logic. BugLens runs both, and tells the model what the rules already found.",
    features: [
      {
        icon: "⚡",
        title: "Static rules, instantly",
        body: "Hardcoded secrets, SQL and shell injection, `eval`, unsafe YAML and pickle, disabled TLS checks, `==` in JavaScript. Where the fix is mechanical (`== None` → `is None`), the rule makes it.",
      },
      {
        icon: "≋",
        title: "AI review, streamed",
        body: "Issues arrive one by one over Server-Sent Events: logic errors, edge cases, missing error handling, and the fixes rules can't make, like a parameterised query.",
      },
      {
        icon: "±",
        title: "Fixes as diffs",
        body: "Each fix is a find/replace that's applied only if it matches exactly one place. The result is shown side by side or unified, with changed words highlighted.",
      },
    ],
  },
  preview: {
    intro:
      "A finished review with the annotated code and issue list, one issue opened with its own before and after, and the full suggested diff.",
    shots: [
      { src: "/shots/review.png", alt: "A finished review: annotated code on the left, issues by severity on the right", caption: "Review" },
      { src: "/shots/issue.png", alt: "An issue card opened, showing the explanation and its fix", caption: "One issue" },
      { src: "/shots/diff.png", alt: "Side-by-side diff of the original and suggested code", caption: "Suggested diff" },
    ],
  },
  stack: ["React 19", "TypeScript", "Vite", "FastAPI", "SSE", "SQLAlchemy", "LangChain", "Groq", "gpt-oss-120b", "PostgreSQL", "pytest", "Vitest"],
  concepts: [
    { title: "Masked scanning", body: "Rules match against a copy of the code with strings and comments blanked out, same length, so `eval(` in a docstring isn't flagged and line numbers still match." },
    { title: "Find/replace fixes", body: "Asked for the whole corrected file, the model reformatted everything. Now each issue carries `find` and `replace`, and a fix that doesn't match is dropped instead of guessed." },
    { title: "Repeats become fixes", body: "When the model re-reports a rule finding anyway, it's merged into that finding as its fix instead of showing up twice." },
    { title: "Own diff and SSE parser", body: "An LCS line and word diff and a small SSE reader over `fetch`, so the review can be POSTed and streamed." },
    { title: "Works without a key", body: "With no LLM key, or the AI box unticked, you still get the rules and their fixes." },
    { title: "Any OpenAI-compatible model", body: "Groq by default, or OpenAI, or a local Ollama, through one LangChain `ChatOpenAI` client." },
  ],
  run: {
    title: "Run your own",
    intro: "A Groq key is free; without one, BugLens still runs the static rules.",
    blocks: [
      {
        title: "API",
        steps: [
          { text: "Install, then set `APP_PASSWORD` and `LLM_API_KEY` in `.env`:", cmd: "cd backend && uv sync\ncp .env.example .env" },
          { text: "Start it on port 8000:", cmd: "uv run uvicorn app.main:app --reload" },
        ],
      },
      {
        title: "App",
        steps: [
          { text: "Install and start Vite:", cmd: "cd frontend && npm install\nnpm run dev" },
          { text: "Open it, pick a sample and press Review:", cmd: "http://localhost:5173" },
        ],
      },
    ],
  },
  tagline: "static rules plus an AI review, with diffs.",
};
