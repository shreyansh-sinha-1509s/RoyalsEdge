# RR PERFORMANCE LAB — REST API Specification (Stage 1)

**Base URL (Local Dev):** `http://localhost:5000/api`  
**Format:** JSON (`{ "success": true, "data": ..., "meta": ... }`)  
**Errors:** Consistent JSON envelope (`{ "success": false, "error": { "code": "...", "message": "...", "details": [...] } }`)

---

## 1. Security, Validation & Query Standards

- **Input Validation:** Every query param, path param, and request body validated via `zod`. Invalid `playerId` / `matchId` or out-of-range page limits return `400 Bad Request`.
- **Safe Sorting:** Sort columns restricted to explicit per-endpoint allowlists to prevent injection or unindexed table scans.
- **Pagination:** Default `page=1`, `limit=20` (max `100`). Returns `meta: { page, limit, total, totalPages }`.
- **Rate Limiting:** General public API (`300 req / 15 min` per IP); Admin login (`10 req / 15 min` per IP).
- **Security Headers & CORS:** `helmet()`, strict `CORS_ORIGIN` allowlist, `compression()`, `express.json({ limit: '1mb' })`.
- **Caching:** Short-lived in-memory read cache for static/aggregated endpoints, invalidatable from the Admin Panel (`POST /api/admin/cache/refresh`).

---

## 2. Public Read-Only Analytics Endpoints

| Method | Endpoint | Query Params | Purpose & Response Data |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | — | Service status, DB connectivity ping (`SELECT 1`), last successful import timestamp, uptime |
| `GET` | `/api/overview` | — | Homepage & About snapshot: exact verified counts (`193,988` deliveries, `837` ball matches / `853` eligible matches, `1,652` innings, `824` batters, `596` bowlers, `173`/`165` eligible), Top 10 preview cards, Model C validation highlights, 6-stage pipeline metadata |
| `GET` | `/api/pressure/summary` | `format`, `season`, `pressureLevel`, `innings`, `phase`, `framework` | Server-aggregated Chase / First-Innings / Bowling pressure KPIs: mean pressure index, RRR, CRR, runs remaining, balls remaining, wickets lost/in hand, current score, balls elapsed, HIGH+EXTREME share, and explicit `UNAVAILABLE` count (`1,551` total) |
| `GET` | `/api/pressure/distribution` | `format`, `season`, `pressureLevel`, `innings`, `phase`, `framework` | 20-bin `0–100` pressure score histograms + `LOW`/`MODERATE`/`HIGH`/`EXTREME`/`UNAVAILABLE` tier counts & exposure percentages + phase/season breakdown |
| `GET` | `/api/pressure/models` | `framework` | Exact comparison table of **Model A**, **Model B**, and **Model C (Primary)** (`mean`, `std`, `iqr`, `iplMean`, `t20iMean`, `iplMinusT20i`, Spearman/Pearson vs C, Top-30 agreement), plus component weights & threshold rules |
| `GET` | `/api/batting/summary` | `format`, `season`, `pressureLevel`, `role`, `innings`, `phase`, `playerId` | Batting KPI cards (analyzed, eligible, total pressure runs, BF, median pressure SR, HIGH+EXTREME exposures), SR/Avg/Dot%/Boundary% by pressure tier, pressure vs non-pressure comparison, Performance vs Reliability scatter points (`173` eligible + optional low-evidence toggle), seasonal trends |
| `GET` | `/api/batting/rankings` | `top10Only`, `search`, `role`, `competition`, `stabilityTier`, `evidenceTier`, `sortBy`, `sortOrder`, `page`, `limit` | Verified Phase 6 batting rankings (`173` eligible; `top10Only=true` returns exact ordered Top 10 matching `submission/RR_Performance_Lab_Top_10_Batters.csv`), including scores, EB impact, SR, Avg, Reliability, Evidence, Exposure, 95% CIs, MC Top-10 %, stability |
| `GET` | `/api/bowling/summary` | `format`, `season`, `pressureLevel`, `role`, `innings`, `phase`, `playerId` | Bowling KPI cards (analyzed, eligible, pressure LB, wickets, median pressure economy, HIGH+EXTREME exposures), Economy/WktFreq/Dot%/Boundary% by pressure tier, pressure vs non-pressure comparison, Performance vs Reliability scatter (`165` eligible), seasonal consistency |
| `GET` | `/api/bowling/rankings` | `top10Only`, `search`, `role`, `paceOrSpin`, `competition`, `stabilityTier`, `evidenceTier`, `sortBy`, `sortOrder`, `page`, `limit` | Verified Phase 6 bowling rankings (`165` eligible; `top10Only=true` returns exact ordered Top 10 matching `submission/RR_Performance_Lab_Top_10_Bowlers.csv`) |
| `GET` | `/api/players` | `discipline` (`all`\|`batting`\|`bowling`), `search`, `role`, `competition`, `evidenceTier`, `eligibleOnly`, `sortBy`, `sortOrder`, `page`, `limit` | Searchable paginated directory across all `1,217` players (with `playerId`, `sharesNameWithOtherId`, team context, eligibility, headline batting/bowling pressure metrics & ranks) |
| `GET` | `/api/players/:playerId` | — | Complete player profile overview: identity, roles, teams, competition exposure, seasons, ranking status (if eligible/Top 10), and **deterministic data-backed explanation** built solely from actual DB fields (explicitly flags missing/insufficient evidence) |
| `GET` | `/api/players/:playerId/performance` | `discipline` | Raw vs EB-shrunk performance, overall/pressure/non-pressure metrics, `LOW`/`MODERATE`/`HIGH`/`EXTREME` breakdown, IPL vs T20I, Inn 1 vs Chase, and Powerplay/Middle/Death splits |
| `GET` | `/api/players/:playerId/reliability` | `discipline` | Reliability score (`NULL` if insufficient evidence — never `0`), 4 sub-components, Evidence Strength score, matches/innings/balls, match-clustered 95% CI, MC rank interval & Top-10 probability |
| `GET` | `/api/players/:playerId/trends` | `discipline` | Season-by-season (`2022–2026`) pressure performance, innings split, phase split, and EXTREME-tier execution |
| `GET` | `/api/compare` | `discipline` (`batting`\|`bowling`, required), `playerIds` (`2`–`4` comma-separated IDs) | Side-by-side same-discipline comparison (rejects cross-discipline comparisons with `400`). Returns aligned metrics, tier breakdowns, seasonal trajectories, CIs, rankings, and an automatic `sampleSizeWarning` flag whenever one player has `< 50%` of the cohort leader's pressure balls |
| `GET` | `/api/matches` | `search`, `format`, `season`, `completionType`, `minPressure`, `sortBy`, `sortOrder`, `page`, `limit` | Server-paginated historical matches archive (`853` eligible matches) with pressure summary metadata |
| `GET` | `/api/matches/:matchId` | — | Match detail with full innings summaries (`innings` 1 & 2), scores, wickets, DLS/reduced-overs flags, and pressure exposure profiles |
| `GET` | `/api/methodology` | — | All 20 parsed methodology sections, formulas, model comparison tables, ranking method comparison (`Balanced` vs `Perf-Dom` vs `Rel-Dom`), robustness tests (`14` rows), threshold sensitivity (`10` rows), and narrow-miss audit (`Ranks 11–15`) |
| `GET` | `/api/reports` | — | Catalog of verified downloadable files from `submission/` and curated `outputs/` CSVs with title, description, file type, byte size, and actual filesystem `mtime` |
| `GET` | `/api/reports/:reportId/download` | — | Allowlisted streaming file download (`Content-Disposition: attachment`) resolving strictly to existing files in `submission/` or curated `outputs/` (blocks path traversal) |

---

## 3. Protected Admin Endpoints (`/api/admin/*`)

All routes except `/api/admin/auth/login` require valid `HttpOnly` JWT admin cookie verified by `requireAdmin` middleware (`401 Unauthorized` / `403 Forbidden` otherwise).

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/admin/auth/login` | Validates email + password against `admin_users` (`bcrypt.compare`), issues `HttpOnly` JWT cookie, logs audit event |
| `POST` | `/api/admin/auth/logout` | Clears auth cookie |
| `GET` | `/api/admin/auth/me` | Returns authenticated admin profile (never returns password hash) |
| `GET` | `/api/admin/health` | Detailed DB table row counts, memory usage, uptime, cache stats, source CSV directory status |
| `GET` | `/api/admin/imports` | Paginated history of `data_import_logs` including errors & duration |
| `POST` | `/api/admin/imports/run` | Executes validated transactional re-import from verified `data/processed/`, `outputs/`, and `submission/` CSVs (serialized lock prevents concurrent imports) |
| `POST` | `/api/admin/reconcile` | Runs `verifyConsistency` comparing DB `batting_rankings` / `bowling_rankings` Top 10 & table counts against `submission/*.csv` |
| `POST` | `/api/admin/cache/refresh` | Flushes server-side read cache and records audit entry |
| `GET` | `/api/admin/audit-logs` | Returns paginated admin action & import audit trail |

> **Governance Rule:** No `PUT` or `PATCH` endpoint exists to manually mutate ranking scores or player metrics. All analytical data changes strictly via validated CSV re-import from the Python pipeline.

