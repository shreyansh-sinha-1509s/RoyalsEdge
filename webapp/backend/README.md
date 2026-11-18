# RoyalsEdge — Backend API & Database Layer

**Subtitle:** IPL 2027 Performance & Auction Intelligence Platform  
**Tagline:** *Beyond the Numbers. Inside the Pressure.*  
**Stack:** Node.js 22 (ES Modules) · Express.js · Prisma 6 ORM · Neon Managed PostgreSQL · Zod · Vitest + Supertest

---

## Overview

This backend serves the verified Phase 2–6 cricket analytics datasets produced by the Python pipeline (`SupeRR_Selector/data/processed/`, `outputs/`, `submission/`). It **never recalculates** Phase 6 player rankings in JavaScript and **never modifies** any file outside `webapp/backend/`.

### Key Safeguards
- **Strict Identity:** All player entities are keyed on integer `player_id` (preserving distinct shared-name players such as `Rashid Khan` `4722`/`20172`, `Abdul Samad` `6922`/`7446`, `Haider Ali` `7338`/`28756`).
- **Statistical Honesty:** `INSUFFICIENT_EVIDENCE` reliability scores are stored as SQL `NULL` (never `0`), and `1,551` missing-DLS / corrupted-target pressure deliveries remain explicitly labeled `'UNAVAILABLE'` (never `'LOW PRESSURE'`).
- **Verified Rankings Authority:** Post-import reconciliation checks DB Top 10 Batters and Top 10 Bowlers row-by-row against `submission/RR_Performance_Lab_Top_10_*.csv`.
- **Secure Admin Only:** No public registration; bcrypt-hashed admin credentials (`cost 12`) bootstrapped interactively via CLI; `HttpOnly` JWT cookies; zero manual ranking-editing endpoints.

---

## Quick Start (Windows PowerShell)

```powershell
# 1. Navigate to backend directory
cd "C:\Users\lenovo\OneDrive\Desktop\SupeRR Selector Season 2\SupeRR_Selector\webapp\backend"

# 2. Install dependencies
npm install

# 3. Create your local .env from template (NEVER commit .env)
Copy-Item .env.example .env

# 4. Generate a strong JWT secret (paste output into JWT_SECRET in .env)
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"

# 5. Open .env in your editor and paste your Neon pooled DATABASE_URL, direct DIRECT_URL,
#    JWT_SECRET, and ADMIN_BOOTSTRAP_EMAIL

# 6. Generate Prisma client & apply PostgreSQL schema migrations to Neon
npm run prisma:generate
npm run prisma:migrate:deploy

# 7. Import all verified Phase 2–6 analytics datasets + run automatic Top-10 reconciliation
npm run import:data

# 8. Bootstrap your initial admin user (interactive hidden password prompt)
npm run bootstrap:admin

# 9. Start the API server
npm run dev
```

---

## npm Scripts

| Script | Purpose |
| :--- | :--- |
| `npm run dev` | Start Express API with Nodemon auto-reload (`http://localhost:5000`) |
| `npm start` | Start Express API in standard Node mode |
| `npm run prisma:validate` | Validate `prisma/schema.prisma` syntax & relations |
| `npm run prisma:generate` | Generate Prisma Client |
| `npm run prisma:migrate` | Create/apply development migration (`prisma migrate dev`) |
| `npm run prisma:migrate:deploy` | Apply committed migrations cleanly to Neon PostgreSQL |
| `npm run import:data` | Transactional, idempotent CSV import + post-import Top-10 reconciliation |
| `npm run reconcile:data` | Standalone DB vs. `submission/*.csv` consistency verification |
| `npm run bootstrap:admin` | Interactive masked-password CLI admin creation/update |
| `npm test` | Run full Vitest + Supertest suite (in-memory harness; safe, non-destructive) |

---

## Documentation

- [Setup Guide (Neon & PowerShell)](docs/SETUP_GUIDE.md)
- [Analytics Data Import & Reconciliation Guide](docs/IMPORT_GUIDE.md)
- [Security Architecture & Secret Hygiene](docs/SECURITY_NOTES.md)
- [API Test & Verification Report](docs/API_TEST_REPORT.md)
- [System Architecture](../../docs/APPLICATION_ARCHITECTURE.md)
- [Database Schema](../../docs/DATABASE_SCHEMA.md)
- [REST API Contract](../../docs/API_DOCUMENTATION.md)

