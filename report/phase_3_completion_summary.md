# Phase 3 Completion Summary — Data Cleaning, Cricket Rule Validation & Feature Engineering

**Project:** SupeRR Selector Season 2 — RR PERFORMANCE LAB  
**Phase Status:** **PASS**  
**Pipeline Scripts:** `src/03_data_cleaning.py` → `src/04_feature_engineering.py`  
**Automated Test Suite:** `tests/test_cricket_rules.py`, `tests/test_data_integrity.py`, `tests/test_feature_engineering.py` (**14 / 14 PASSED**)  
**Raw Data Immutability:** Verified byte-for-byte unchanged across all 6 source CSVs and Round 1 PDF.

---

## 1. Original vs. Processed Row Counts

| Layer | File | Rows | Columns | Notes |
| :--- | :--- | ---: | ---: | :--- |
| **Raw** | `data/raw/Data Pack/ball_by_ball.csv` | 200,999 | 33 | Untouched read-only source |
| **Raw** | `data/raw/Data Pack/matches.csv` | 883 | 22 | Untouched read-only source |
| **Raw** | `data/raw/Data Pack/competitions.csv` | 141 | 4 | Untouched read-only source |
| **Raw** | `data/raw/Data Pack/teams.csv` | 353 | 3 | Untouched read-only source |
| **Raw** | `data/raw/Data Pack/playing_eleven.csv` | 28,381 | 9 | Untouched read-only source |
| **Raw** | `data/raw/Data Pack/competition_team_player_mapping.csv` | 6,413 | 6 | Untouched read-only source |
| **Processed** | `data/processed/clean_deliveries.csv` | **193,988** | **96** | Primary IPL + T20I regular innings (1 & 2) with all 33 raw cols + derived rules + 29 pre-delivery features |
| **Processed** | `data/processed/clean_matches.csv` | **853** | **56** | Eligible IPL (371) + T20I (482) matches with unit-clarified revised balls & completion classifications |
| **Processed** | `data/processed/player_master.csv` | **1,217** | **23** | Canonical player master keyed strictly on `player_id` |
| **Processed** | `data/processed/competition_master.csv` | **141** | **15** | Full competition register with explicit eligibility flags & exclusion reasons |
| **Processed** | `data/processed/innings_summary.csv` | **1,652** | **44** | Reconciled innings totals across 837 primary eligible matches with ball data |
| **Processed** | `data/processed/super_over_deliveries.csv` | **38** | **67** | Separated Super Over innings (3 & 4): 26 primary IPL/T20I + 12 excluded comp 3289 |
| **Processed** | `data/processed/excluded_competition_deliveries.csv` | **6,985** | **68** | Preserved non-IPL T20 deliveries (`comp_id` 2670 & 3289; includes 12 Super Over deliveries) |

**Exact Row Conservation Check:** `193,988` (primary regular) + `26` (primary Super Over) + `6,985` (excluded competitions) = **`200,999`** raw deliveries (**0 rows lost or duplicated**).

---

## 2. Competition Breakdown & Excluded Records

| Category | Competitions | Matches (Meta) | Matches (Ball) | Regular Deliveries | Legal Deliveries | Batter Balls Faced | Total Runs | Wickets | Bowler Wickets |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **IPL (Primary)** — Inn 1 | 5 | 371 | 367 | 45,588 | 43,509 | 43,708 | 67,902 | 2,288 | 2,147 |
| **IPL (Primary)** — Inn 2 | — | — | 363 | 42,085 | 40,233 | 40,413 | 62,101 | 2,166 | 2,054 |
| **T20I (Primary)** — Inn 1 | 134 | 482 | 470 | 56,466 | 54,127 | 54,371 | 78,195 | 3,126 | 2,923 |
| **T20I (Primary)** — Inn 2 | — | — | 452 | 49,849 | 47,823 | 48,024 | 67,137 | 2,898 | 2,775 |
| **Primary Subtotal (Regular)** | **139** | **853** | **837** | **193,988** | **185,692** | **186,516** | **275,335** | **10,478** | **9,899** |
| **Excluded Non-IPL T20** (`2670`, `3289`) | 2 | 30 | 30 | 6,973 (+12 SO) | 6,730 (all) | — | — | — | — |

- **Excluded Competitions (Preserved in `data/processed/excluded_competition_deliveries.csv`):**
  - `comp_id=2670`: `Mens T20 Emerging Teams Asia Cup 2024` (15 matches, 3,519 deliveries).
  - `comp_id=3289`: `Asia Cup Rising Stars 2025` (15 matches, 3,466 deliveries including 12 Super Over balls).
- **Abandoned Zero-Ball Matches (Preserved in `clean_matches.csv`):** 16 eligible IPL/T20I matches with `result = "Match Abandoned"` and 0 deliveries.

---

## 3. Regular vs. Super Over Records & Match Completion Breakdown

- **Regular Innings (Primary):** `193,988` deliveries (`102,054` Innings 1 + `91,934` Innings 2) across `837` matches (`1,652` innings).
- **Super Over Innings (Separated):** `38` deliveries across 6 matches (`26` from 4 primary matches `34429`, `40725`, `45512`, `50359`; `12` from 2 excluded matches `48027`, `48029`).
- **3 Earlier Super Over Matches Missing Innings 3–4 Ball Data:** `13613` (AUS vs SL 2022), `21176` (NZ vs SL 2023), `28962` (IND vs AFG 2024) — preserved as `tied_super_over_missing_ball_data` without reconstructing missing deliveries.
- **Eligible Match Completion Distribution (`853` matches):**
  - `completed_regular`: 774
  - `completed_dls_revised`: 26
  - `no_result_partial_play`: 21
  - `abandoned_no_play`: 16
  - `completed_reduced_overs_no_dls`: 5
  - `tied_super_over_with_ball_data`: 4
  - `tied_super_over_missing_ball_data`: 3
  - `abandoned_partial_play`: 3
  - `tied_no_super_over_dls`: 1

---

## 4. Data-Quality Corrections & Derived Rules

- **Literal `'None'` Preservation:** Loaded all CSVs with `keep_default_na=False, na_values=['']` so `extras_type='None'` is preserved and never silently parsed as `NaN`.
- **Unit Clarification on `revised_overs`:** Verified `first_inn_revised_overs` and `second_inn_revised_overs` in `matches.csv` are stored in **legal balls** (e.g., `90.0` = 15 overs in IPL 2023 Final `21586`); added explicit `*_revised_balls` and `*_revised_overs_exact` columns.
- **Cricket Scoring Rules:** Implemented exact `total_runs`, `is_legal_delivery` (excluding `wide`, `Overstep`, `other`), `is_batter_ball_faced` (`~is_wide`), `bowler_conceded_runs` (excluding byes, leg-byes, penalty runs, and `extras_2_runs`), and `is_bowler_wicket` (excluding `RunOut`, `Retire Out`, `Obstructing the field`, and `Retired Hurt`).
- **Dismissal Normalization:** Normalized `'Obstracting the field'` → `'Obstructing the field'` in `dismissal_type_std` while retaining raw `dismissal_type`.
- **Retired Hurt Separation:** Confirmed all 12 `is_wicket=False` & `dismissed_player_id.notna()` rows (11 primary, 1 excluded) are Retired Hurt events and excluded them from team wickets and bowler wickets.
- **Bowling Speed Cleaning (`bowl_speed_clean`):** In primary regular deliveries: `123,075` valid (`50–165 km/h`), `70,870` `zero_unrecorded` → `NaN`, `22` `below_50_outlier` → `NaN`, `20` `above_165_outlier` → `NaN`, `1` `negative_invalid` → `NaN`. Raw `bowl_speed` preserved untouched.
- **Pre-Delivery Match State & Phase Distribution (`193,988` primary deliveries):**
  - `Middle`: `88,468` | `Powerplay`: `60,510` | `Death`: `43,471` | `Unavailable` (missing revised-overs metadata): `1,539`.
  - 2nd-innings chase context available (`chase_context_available == True`): `91,161 / 91,934` (`99.16%`; `773` deliveries in missing-revised-overs/target DLS or reduced chases properly marked unavailable).

---

## 5. Remaining Anomalies & Known Limitations

All **14 investigated anomalies** are documented in `outputs/anomaly_investigation.csv` without silent deletion or fabrication:
1. **Unclassified extras on `'None'` (`17555`, `36097`):** 2 primary deliveries have 1 extra run with `extras_type='None'` — included in `total_runs` (matching official margins), excluded from `bowler_conceded_runs`, and flagged.
2. **7-legal-ball over (`41509`, inn 1, over 12):** Sole exception to the 6-legal-ball over rule across all 193,988 primary deliveries; preserved and flagged.
3. **1-ball missing per innings in `14130` (IPL 2022 LSG vs MI):** Sole run-margin mismatch across 388 non-DLS matches won by runs (`387 / 388` match official margin to the exact run; `14130` computes 37 vs official 36 runs due to 119 legal balls recorded per innings).
4. **Missing `dismissed_player_id` on `Retire Out` (`40709`, IPL 2025):** Raw `NaN` preserved; empirically verified from ball 19.6 as Tilak Varma (`7897`).
5. **Excluded-competition source defects (`37086`, `37099`, `36153`, `39444`):** Confined to excluded `comp_id=2670` (`excluded_competition_deliveries.csv`) with zero impact on primary IPL/T20I analysis.
6. **DLS / reduced-overs metadata gaps:** `1,539` primary deliveries (across 10 matches) lack defensible scheduled-overs metadata; their `legal_balls_remaining_before`, `required_run_rate_before`, and `match_phase` are explicitly `NaN` / `'Unavailable'`.
7. **Shared player names (`player_alias_report.csv`):** 3 distinct individuals sharing names (`Rashid Khan`, `Abdul Samad`, `Haider Ali`) and 4 suspected split IDs (`Basil Hameed`, `Bashir Ahmad`, `Mohammad Ali`, `Muhammad Farooq`) remain strictly keyed by `player_id` and are never merged by name.

---

## 6. Automated Validation & Test Results

- **`outputs/reconciliation_checks.csv`:** `12 PASS`, `1 WARN` (`14130` sole run-margin mismatch across 388 matches), `1 INFO` (`41509` 7-legal-ball over), **`0 FAIL`**.
- **Pytest Suite (`pytest tests -v`):** **`14 passed, 0 failed`** in `14.87s`:
  - `tests/test_cricket_rules.py`: 5 / 5 PASSED
  - `tests/test_data_integrity.py`: 5 / 5 PASSED
  - `tests/test_feature_engineering.py`: 4 / 4 PASSED
- **Notebook Verification:** All code cells in `notebooks/03_data_cleaning.ipynb` executed cleanly headlessly with zero errors.
- **Audit Outputs Generated (`outputs/`):** `cleaning_log.csv`, `excluded_records.csv`, `reconciliation_checks.csv`, `feature_dictionary.csv`, `player_alias_report.csv`, `anomaly_investigation.csv`, `innings_reconciliation.csv`.

---

## 7. Phase 3 Assessment: **PASS**

The cleaned, cricket-law-validated, leak-free analytical dataset in `data/processed/` is complete, verified, and ready for your review prior to **Phase 4 (Pressure Framework Definition & Modeling)**.

