# Backend API & Verification Test Report — Stage 2

**Date:** 2026-11-18  
**Runtime:** Node.js `v22.16.0` · npm `10.9.2` · Prisma `v6.19.3` · Vitest `v3.2.7` + Supertest `v7.0.0`

---

## 1. Automated Verification Summary

| Suite / Command | Target | Status | Observed Result |
| :--- | :--- | :---: | :--- |
| `npx prisma validate` | `prisma/schema.prisma` (19 PostgreSQL models) | **PASS** | `The schema at prisma\schema.prisma is valid` |
| `npx prisma generate` | `@prisma/client` v6.19.3 | **PASS** | Generated in `413ms` |
| `npx prisma migrate diff` | `prisma/migrations/20261118000000_init/migration.sql` | **PASS** | Initial PostgreSQL DDL generated cleanly |
| `npm test` (Vitest + Supertest) | All 3 test files (`17` integration & import tests) | **PASS** | **`3 passed (3)` files · `17 passed (17)` tests in `21.40s`** |
| `pytest SupeRR_Selector/tests -q` | Existing Python analytics test suite | **PASS** | **`33 passed`** (raw CSVs & submission deliverables untouched) |
| Live Neon DB Connection & Import | Real Neon PostgreSQL instance | **PENDING USER `.env`** | Awaiting manual entry of Neon `DATABASE_URL` / `DIRECT_URL` in local `webapp/backend/.env` (never requested in chat) |

---

## 2. Detailed Test Coverage Matrix (`npm test` — 17/17 PASSED)

### A. CSV Import, Idempotency & Reconciliation (`tests/importAndReconcile.test.js` — 2/2 PASSED)
1. **Header & Source Validation:** Verified all 30 source files across `data/processed/`, `outputs/`, and `submission/` exist with all required headers.
2. **Full Real-Data Import, Idempotency & Reconciliation (`19.62s`):**
   - Imported all verified Phase 2–6 datasets (`1,217` players, `824` batting perf/rel, `596` bowling perf/rel, `1,420` pressure exposures, `4,276` tier breakdowns, `3,008` seasonal rows, `173` batting rankings, `165` bowling rankings, `853` matches, `1,652` innings, `82` pressure summaries, `65` robustness audits, `20` methodology sections, `912` OLAP cube buckets aggregating all `193,988` regular deliveries).
   - Verified exact Top 10 Batters (`#1 Matthew Wade 796` through `#10 Romario Shepherd 6726`) and Top 10 Bowlers (`#1 Nasum Ahmed 4658` through `#10 Matheesha Pathirana 8661`) match `submission/RR_Performance_Lab_Top_10_*.csv` on rank, `player_id`, `player_name`, composite score, EB impact, and reliability.
   - Re-ran the full import a second time and verified zero duplicates across all tables (`data_import_logs` count = `2`).

### B. Public REST API (`tests/publicApi.test.js` — 11/11 PASSED)
1. `GET /api/health` — DB ping & last successful reconciled import metadata.
2. `GET /api/overview` — Exact verified counts (`193,988` deliveries, `837` matches with ball data, `1,652` innings, `824` batters, `596` bowlers) + Top 10 lists.
3. `GET /api/batting/rankings` — Exact ordered Top 10 + full `173`-player pagination (`page=2&limit=15` starts at `#16`).
4. `GET /api/bowling/rankings` — Exact ordered Top 10 + full `165`-player cohort count.
5. `GET /api/players` & `GET /api/players/:playerId` — Verified shared-name disambiguation (`Rashid Khan`: `player_id=4722` ranked `#4` vs `player_id=20172` unranked; never merged).
6. `GET /api/players/:playerId/reliability` — Confirmed `INSUFFICIENT_EVIDENCE` players return `reliabilityScore: null` (never `0`).
7. `GET /api/pressure/summary` & `/distribution` — Confirmed `1,551` `UNAVAILABLE` pressure deliveries preserved separately with `meanPressureIndex: null` (never collapsed into `LOW PRESSURE`).
8. `GET /api/pressure/models` — Confirmed Model C flagged `isPrimaryFramework: true` across Chase, First Innings, and Bowling.
9. `GET /api/compare` — Confirmed same-discipline comparison works with automatic `sampleSizeWarning` (`172b` vs `550b`), and cross-discipline comparison (`796` Matthew Wade in bowling mode) is rejected with `400 DISCIPLINE_MISMATCH`.
10. Invalid query validation — Negative page/oversized limit (`page=-5&limit=999`) and non-integer `playerId` return `400 VALIDATION_ERROR` with zero stack trace leakage.
11. `GET /api/matches`, `/api/matches/:matchId`, `/api/methodology`, `/api/batting/summary`, `/api/bowling/summary` — Verified pagination, match detail, 20 methodology sections, and format-filtered pressure splits.

### C. Admin Auth, Protected Operations & Report Allowlisting (`tests/adminAndSecurity.test.js` — 4/4 PASSED)
1. Unauthenticated requests to all 6 protected admin routes return `401 UNAUTHORIZED`.
2. Invalid password on `POST /api/admin/auth/login` returns `401 INVALID_CREDENTIALS`.
3. Valid admin login sets `HttpOnly` JWT cookie, returns sanitized admin profile (no `passwordHash`), grants access to `/api/admin/health`, `/api/admin/reconcile` (`passed: true`), `/api/admin/cache/refresh`, `/api/admin/audit-logs`, and invalidates session on `POST /api/admin/auth/logout`.
4. `GET /api/reports` lists all verified files; `GET /api/reports/top-10-batters-csv/download` streams the official CSV; traversal attempts (`..%2F.env`, `.env`, `ball_by_ball.csv`, unknown IDs) return `404`.

