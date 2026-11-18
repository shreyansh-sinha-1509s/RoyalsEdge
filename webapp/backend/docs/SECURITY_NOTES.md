# Backend Security Notes — RR PERFORMANCE LAB

## 1. Secret & Credential Hygiene
- All secrets (`DATABASE_URL`, `DIRECT_URL`, `JWT_SECRET`, `ADMIN_BOOTSTRAP_EMAIL`) live strictly in local `webapp/backend/.env` or hosting provider secret managers.
- Both `SupeRR_Selector/.gitignore` and `webapp/backend/.gitignore` exclude `.env` and `.env.*` (while keeping `.env.example` tracked with placeholders only).
- `src/config/env.js` rejects placeholder values (`YOUR_*`, `REPLACE_WITH_*`) and short JWT secrets (`<32` chars) at startup without printing any secret values.
- Error handler (`src/middleware/errorHandler.js`) strips internal stack traces and database connection details from all HTTP responses.

## 2. Administrator Authentication & Authorization
- **Zero Public Registration:** No endpoint exists to register accounts or create admins over HTTP.
- **Interactive CLI Bootstrap:** `scripts/bootstrapAdmin.js` reads `ADMIN_BOOTSTRAP_EMAIL` from `.env`, prompts for a masked password (minimum 12 characters, never passed as CLI arguments so it never enters PowerShell history), and stores only the `bcryptjs` (cost 12) hash.
- **Session Transport:** Signed JWT issued inside an `HttpOnly` cookie (`rr_admin_session`) with `SameSite=Strict` + `Secure` in production (`SameSite=Lax` in local HTTP dev).
- **Brute-Force Protection:** `POST /api/admin/auth/login` is protected by a dedicated rate limiter (`10 attempts / 15 min / IP`) and records both failed and successful attempts in `admin_audit_logs`.
- **Analytical Integrity:** No endpoint allows administrators to manually edit ranking scores, player statistics, or Top 10 lists. Updates happen strictly via validated CSV re-imports (`POST /api/admin/imports/run`) followed by automatic reconciliation.

## 3. Input Validation & Query Hardening
- Every route validates query parameters, path parameters, and JSON bodies with `zod`.
- Dynamic sorting uses explicit per-endpoint allowlists (`BATTING_RANK_SORTS`, `BOWLING_RANK_SORTS`, `PLAYER_SORTS`, `MATCH_SORTS`), blocking arbitrary column sorting.
- All database queries use parameterized Prisma queries (immune to SQL injection).
- Request payloads are capped at `1mb`; HTTP headers are hardened via `helmet()`; CORS restricts browser access to `FRONTEND_ORIGIN`.

## 4. Allowlisted Report Downloads
- `GET /api/reports/:reportId/download` accepts only alphanumeric hyphenated allowlisted IDs defined in `src/utils/reportsCatalog.js`.
- Each target path is resolved with `path.resolve` and verified to remain strictly inside `submission/` or `outputs/`.
- Directory traversal (`../`), `.env`, raw data (`data/raw/`), and source code downloads are explicitly blocked (`404`).

