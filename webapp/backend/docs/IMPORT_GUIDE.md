# Analytics Data Import & Reconciliation Guide

## Authority & Non-Recalculation Policy

The Python pipeline (`SupeRR_Selector/src/01` through `13`) is the sole analytical authority.  
`webapp/backend/scripts/importAnalyticsData.js` imports verified CSV and Markdown outputs directly into Neon PostgreSQL without recalculating pressure scores, Empirical Bayes estimates, reliability scores, or final rankings.

---

## Imported Sources & Expected Counts

| Database Table | Source File(s) | Expected Rows |
| :--- | :--- | ---: |
| `players` | `data/processed/player_master.csv` | `1,217` |
| `player_batting_performance` | `data/processed/player_batting_performance.csv` | `824` |
| `player_bowling_performance` | `data/processed/player_bowling_performance.csv` | `596` |
| `player_batting_reliability` | `data/processed/player_batting_reliability.csv` + `player_pressure_vs_nonpressure.csv` | `824` |
| `player_bowling_reliability` | `data/processed/player_bowling_reliability.csv` + `player_pressure_vs_nonpressure.csv` | `596` |
| `player_pressure_exposure` | `data/processed/player_pressure_exposure.csv` | `1,420` |
| `player_pressure_breakdowns` | `data/processed/player_batting_pressure_breakdown.csv` + `player_bowling_pressure_breakdown.csv` | `4,276` |
| `player_season_performance` | `data/processed/player_season_performance.csv` | `3,008` |
| `batting_rankings` | `data/processed/final_batting_rankings.csv` + `outputs/top10_overlap_analysis.csv` | `173` |
| `bowling_rankings` | `data/processed/final_bowling_rankings.csv` + `outputs/top10_overlap_analysis.csv` | `165` |
| `matches` | `data/processed/clean_matches.csv` + `data/processed/pressure_match_summary.csv` | `853` |
| `innings` | `data/processed/innings_summary.csv` + `data/processed/pressure_innings_summary.csv` | `1,652` |
| `pressure_summaries` | `outputs/pressure_*.csv` (5 files) | `82` |
| `pressure_analytics_cube` | Streamed from `data/processed/pressure_deliveries.csv` (`193,988` deliveries) | `~500–900` |
| `methodology_sections` | `submission/RR_Performance_Lab_Methodology_Report.md` | `20` |
| `ranking_robustness_audits` | `outputs/ranking_*.csv` + `shortlist_alternatives.csv` (4 files) | `65` |

---

## Transactional Safety & Idempotency

1. **Upfront Validation:** All 30 files and required CSV headers are validated before any database write begins. If any file or column is missing, the script aborts cleanly with zero database changes.
2. **Atomic Replacement:** All analytical tables are refreshed inside a single Prisma `$transaction` (preserving `admin_users`, `admin_audit_logs`, and `data_import_logs`). If any insert fails, PostgreSQL rolls back completely.
3. **Repeatable Runs:** Running `npm run import:data` twice produces identical row counts with zero duplicates and appends a new audit row to `data_import_logs`.
4. **CSV Hygiene:** Preserves literal `'None'` strings; converts empty cells and `NaN` to SQL `NULL`; keeps integer `player_id` keys intact.

---

## Post-Import Reconciliation Strategy

`scripts/reconcileData.js` (also invoked automatically at the end of every import) validates:
- **Exact Pool Counts:** `173` eligible batters, `165` eligible bowlers, `1,217` players, `853` matches, `1,652` innings, `193,988` deliveries aggregated in `pressure_analytics_cube`.
- **Exact Top 10 Submission Match:** Compares DB `rank 1..10` rows for both batting and bowling against `submission/RR_Performance_Lab_Top_10_Batters.csv` and `submission/RR_Performance_Lab_Top_10_Bowlers.csv` on:
  - Exact integer `rank` (`1..10`)
  - Exact integer `player_id`
  - Exact `player_name`
  - `final_ranking_score` within `±0.015` (accounts strictly for 2-decimal formatting in submission CSV vs 3-decimal precision in `final_*_rankings.csv`)
  - `eb_pressure_impact` within `±0.025`
  - `reliability_score` within `±0.055`
- **NULL Reliability Rule:** Confirms `0` `INSUFFICIENT_EVIDENCE` rows have a non-null `reliability_score`.
- **Shared-Name Integrity:** Confirms distinct `player_id`s (`4722`/`20172`, `6922`/`7446`, `7338`/`28756`) exist separately.

