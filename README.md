# RoyalsEdge

### **IPL 2027 Performance & Auction Intelligence Platform**
> ***Beyond the Numbers. Inside the Pressure.***

**RoyalsEdge** is a full-stack T20 cricket analytics and auction intelligence platform built for **SupeRR Selector Season 2**. It uncovers which batters and bowlers consistently deliver above-par impact when T20 matches are on the line across verified **IPL and T20I seasons (2022–2026)** — strictly separating **pre-delivery match pressure**, **context-adjusted performance**, **volume-free reliability**, and **evidence strength**.

> *Independent research and analytics project. Not affiliated with or officially endorsed by Rajasthan Royals or the IPL.*

---

## Key Capabilities & Features

- **Cinematic 3D Night Stadium Entrance (`/`):** Procedural Three.js / React Three Fiber night stadium with volumetric floodlights, 22-yard cricket pitch, rotating gold-stitched crimson cricket ball, and drifting atmospheric particles — code-split strictly to `/` with an automatic CSS fallback for mobile and `prefers-reduced-motion`.
- **Overview Dashboard (`/overview`):** Live verified dataset snapshot (`193,988` deliveries · `837` ball-data matches · `1,652` innings · `824` batters · `596` bowlers) and official Phase 6 Top 10 Batters & Bowlers visual summaries.
- **Pre-Delivery Pressure Intelligence (`/pressure`):** Dedicated Chase (Inn 2), First-Innings (Inn 1), and Bowling (Inn 1+2) pressure frameworks powered by **Model C (Context-Normalized LOMO)**, interactive cross-filters, 20-bin score histograms, Model A/B/C comparison, and explicit preservation of `1,551` `UNAVAILABLE` DLS/corrupted-target deliveries.
- **Official Batting & Bowling Rankings (`/batting`, `/bowling`):** Ordered Top 10 shortlists + full eligible cohorts (`173` batters, `165` bowlers) with search, multi-column sorting, role/format/stability filters, Performance vs. Reliability scatter plots, seasonal trends, and match-clustered 95% confidence intervals.
- **Player Explorer & Profiles (`/players`, `/players/:playerId`):** Strict integer `player_id` identity across all `1,217` players (preserving shared-name pairs such as `Rashid Khan` `4722`/`20172`, `Abdul Samad` `6922`/`7446`, `Haider Ali` `7338`/`28756`), deterministic data-backed analytical summaries, and explicit `NULL` reliability notices for `INSUFFICIENT_EVIDENCE` profiles.
- **Same-Discipline Player Comparison (`/compare`):** Side-by-side 2–4 player analysis (Batter vs. Batter or Bowler vs. Bowler) with automatic sample-size discrepancy warnings.
- **Historical Match Explorer (`/matches`, `/matches/:matchId`):** Server-paginated archive of `853` eligible matches and `1,652` reconciled innings with Model C pressure summaries.
- **Transparent Methodology & Official Reports (`/methodology`, `/reports`):** Interactive 20-section methodology reader, robustness tables, narrow-miss audit (`Ranks #11–#15`), and allowlisted downloads of official CSV, Excel, and PDF deliverables.
- **Protected Admin Console (`/admin`):** `bcryptjs` + `HttpOnly` JWT cookie authentication (zero public registration; zero manual ranking-editing forms) for DB health, import monitoring, Top-10 reconciliation verification, cache refresh, and audit logs.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Analytical Pipeline** | Python 3.15 · Pandas · NumPy · DuckDB · Matplotlib · OpenPyXL · ReportLab · Pytest (`33` tests) |
| **Frontend** | React 18 · Vite 6 · Tailwind CSS 3.4 · React Router 7 · Recharts · Framer Motion · Three.js / React Three Fiber · Vitest + RTL (`8` tests) |
| **Backend & Serverless API** | Node.js 22 (ESM) · Express.js · Zod · Helmet · CORS · `express-rate-limit` · `bcryptjs` · JWT `HttpOnly` Cookies · Vitest + Supertest (`17` tests) |
| **Database & ORM** | **Neon Managed PostgreSQL** (pooled runtime + direct migration URLs) · **Prisma 6 ORM** (`19` relational models) |
| **Deployment** | **Vercel** (Static Vite SPA + Serverless Express Function `/api/index.js` + Neon PostgreSQL) |

---

## Architecture & Repository Layout

```text
SupeRR_Selector/
├── api/
│   └── index.js                 # Vercel serverless Express entrypoint (no app.listen, no cold-start migrations)
├── vercel.json                  # Full-stack Vercel build, SPA rewrites, /api routing & includeFiles
├── package.json                 # Root workspace metadata
├── src/                         # Verified Phase 1–6 Python analytical pipeline (01–13)
├── tests/                       # 33 automated Python cricket-law, pressure, reliability & ranking tests
├── submission/                  # Official Phase 6 Top 10 CSVs, Excel workbook & PDF/MD reports
├── outputs/                     # Curated aggregate robustness & model comparison CSVs
├── report/                      # Phase 2–5 audit, cleaning, pressure & reliability reports
├── notebooks/                   # Reproducible exploratory notebooks (02–05)
└── webapp/
    ├── docs/                    # Architecture, Database Schema & REST API specifications
    ├── backend/                 # Express REST API, Prisma 6 schema/migrations, CSV importer & reconciler
    └── frontend/                # React + Vite + Tailwind + Three.js + Recharts application
```

---

## Data & Methodology Integrity Rules

1. **Python Pipeline Authority:** Rankings, Empirical Bayes estimates, pressure scores, and reliability metrics are never recalculated in JavaScript and never manually edited via UI forms.
2. **Strict `player_id` Identity:** Players are keyed exclusively on integer `player_id` — duplicate names are never merged.
3. **No Fabricated Zeros or Demo Data:** `INSUFFICIENT_EVIDENCE` reliability scores (`511` batters, `343` bowlers) are stored and displayed as `NULL` (never `0`). Missing DLS / corrupted-target deliveries (`1,551`) remain explicitly labeled `UNAVAILABLE` (never `LOW PRESSURE`).
4. **Verified Top-10 Reconciliation:** Automated reconciliation confirms live Neon PostgreSQL Top 10 Batters & Bowlers match `submission/RR_Performance_Lab_Top_10_*.csv` exactly on rank, `player_id`, name, composite score, EB impact, and reliability.
5. **Secret Protection:** Raw competition data (`data/raw/`), processed data (`data/processed/`), and all `.env` files are strictly gitignored and never committed.

---

## Local Development (Windows PowerShell)

### 1. Backend API (`http://localhost:5000`)
```powershell
cd webapp\backend
npm install
Copy-Item .env.example .env
# Populate DATABASE_URL (Neon pooled), DIRECT_URL (Neon direct), JWT_SECRET, ADMIN_BOOTSTRAP_EMAIL locally

npm run prisma:generate
npm run prisma:migrate:deploy
npm run import:data
npm run reconcile:data
npm run bootstrap:admin
npm run dev
```

### 2. Frontend App (`http://localhost:5173`)
```powershell
cd webapp\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

### 3. Run All Automated Test Suites
```powershell
# Backend Vitest + Supertest (17 tests)
cd webapp\backend; npm test

# Frontend Vitest + React Testing Library (8 tests)
cd webapp\frontend; npm test

# Python Pipeline Pytest (33 tests)
.\.venv\Scripts\python.exe -m pytest tests -q
```

---

## Production Deployment (Vercel + Neon PostgreSQL)

RoyalsEdge deploys as a unified full-stack project on **Vercel** (`royalsedge`):
- **Frontend:** Built from `webapp/frontend` into `webapp/frontend/dist` with SPA fallback routing.
- **Backend API:** Served at `/api/*` via `api/index.js` wrapping `webapp/backend/src/app.js` with Prisma Linux query engine (`rhel-openssl-3.0.x`) and bundled `submission/` download files.
- **Database:** Connected to the existing initialized & reconciled **Neon PostgreSQL** database via Vercel Production environment variables (`DATABASE_URL`, `DIRECT_URL`, `JWT_SECRET`, `JWT_EXPIRES_IN`, `FRONTEND_ORIGIN`, `ADMIN_BOOTSTRAP_EMAIL`).
