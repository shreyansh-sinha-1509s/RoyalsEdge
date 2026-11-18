# RR PERFORMANCE LAB — Frontend Application

**Stack:** React 18 · Vite 6 · Tailwind CSS 3.4 · React Router 7 · Recharts · Framer Motion · Three.js / React Three Fiber · Vitest + React Testing Library

## Local Development (Windows PowerShell)

```powershell
cd "C:\Users\lenovo\OneDrive\Desktop\SupeRR Selector Season 2\SupeRR_Selector\webapp\frontend"

# 1. Install dependencies
npm install

# 2. Optional: copy .env.example to .env if overriding default http://localhost:5000 backend
Copy-Item .env.example .env

# 3. Run Vite development server (http://localhost:5173)
npm run dev

# 4. Run frontend unit & route tests
npm test

# 5. Run production bundle build
npm run build
```

## Notes
- Connects exclusively to the Express REST API configured via `VITE_API_BASE_URL` (default `http://localhost:5000`) with `credentials: 'include'` for `HttpOnly` admin cookies.
- Never fabricates fallback player stats or rankings when the backend is unavailable.
- The 3D night-stadium scene (`StadiumScene3D.jsx`) is code-split exclusively to `/` and automatically falls back to a lightweight CSS night-stadium scene on mobile, `prefers-reduced-motion`, or non-WebGL browsers.

