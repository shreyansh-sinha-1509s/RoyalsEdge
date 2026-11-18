# Setup Guide — Neon PostgreSQL & Local Backend (Windows PowerShell)

This guide explains step-by-step how to connect **RR PERFORMANCE LAB** to your **Neon managed PostgreSQL** database without ever exposing credentials in chat, logs, or Git.

---

## 1. Prerequisites

- **Node.js 22+** (`node -v` → verified `v22.16.0`)
- **npm 10+** (`npm -v` → verified `10.9.2`)
- A **Neon** PostgreSQL project ([https://console.neon.tech](https://console.neon.tech))

---

## 2. Obtain Your Two Neon Connection Strings

In the **Neon Console → Your Project → Connection Details**:

1. Select **PostgreSQL 16** (or 17) and your database (`neondb`).
2. **Pooled connection string** (check *Connection pooling* — hostname contains `-pooler`):
   - Copy this into `DATABASE_URL` inside `webapp/backend/.env`.
   - Ensure `?sslmode=require` is present (Neon includes it by default).
3. **Direct connection string** (uncheck *Connection pooling* — no `-pooler` in hostname):
   - Copy this into `DIRECT_URL` inside `webapp/backend/.env`.
   - Prisma uses `DIRECT_URL` automatically for schema migrations (`prisma migrate deploy` / `prisma migrate dev`) so DDL locks do not conflict with PgBouncer pooling.

---

## 3. Configure `webapp/backend/.env` Locally

```powershell
cd "C:\Users\lenovo\OneDrive\Desktop\SupeRR Selector Season 2\SupeRR_Selector\webapp\backend"
Copy-Item .env.example .env
```

Generate a cryptographically secure `JWT_SECRET` (96 hex chars):

```powershell
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
```

Edit `webapp/backend/.env` in VS Code / Notepad and populate:
- `DATABASE_URL` = your Neon **pooled** URL
- `DIRECT_URL` = your Neon **direct** URL
- `JWT_SECRET` = the 96-char random string generated above
- `ADMIN_BOOTSTRAP_EMAIL` = your administrator email address (e.g., `yourname@yourdomain.com`)

> **NEVER commit `.env`** (protected by both root `.gitignore` and `webapp/backend/.gitignore`) and **NEVER paste real connection strings or passwords into chat.**

---

## 4. Apply Prisma Migrations to Neon

```powershell
npm run prisma:generate
npm run prisma:migrate:deploy
```

*Note:* If you later modify `prisma/schema.prisma`, create a new migration using `npm run prisma:migrate`.

---

## 5. Import All Verified Phase 2–6 Analytics Datasets

```powershell
npm run import:data
```

This single command:
1. Validates all 30 source files and mandatory CSV headers.
2. Streams `pressure_deliveries.csv` (`193,988` deliveries) into the compact `pressure_analytics_cube` OLAP table.
3. Imports all 16 analytical tables inside a single Prisma transaction.
4. Automatically verifies DB counts and exact Top 10 Batters & Bowlers against `submission/RR_Performance_Lab_Top_10_*.csv`.
5. Logs the batch summary to `data_import_logs`.

Re-verify reconciliation anytime:

```powershell
npm run reconcile:data
```

---

## 6. Create the Administrator Account

```powershell
npm run bootstrap:admin
```

- Reads `ADMIN_BOOTSTRAP_EMAIL` from `.env`.
- Prompts interactively with hidden input (nothing echoed to terminal or shell history).
- Enforces a minimum 12-character password and stores only the `bcrypt` (cost 12) hash.

---

## 7. Run & Smoke-Test the Backend API

```powershell
npm run dev
```

In a second PowerShell terminal:

```powershell
Invoke-RestMethod http://localhost:5000/api/health
Invoke-RestMethod "http://localhost:5000/api/batting/rankings?top10Only=true"
Invoke-RestMethod "http://localhost:5000/api/bowling/rankings?top10Only=true"
Invoke-RestMethod "http://localhost:5000/api/pressure/summary"
```

