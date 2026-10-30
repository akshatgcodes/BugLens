import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const api = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  // "/app/" on Vercel, where the landing page owns "/" (see vercel.json)
  base: process.env.VITE_BASE ?? "/",
  server: {
    port: 5173,
    // Same-origin in dev: the session cookie just works, no CORS preflights
    proxy: { "/api": api },
  },
});
