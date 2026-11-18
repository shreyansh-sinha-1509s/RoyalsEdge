# Phase 3 Data Cleaning & Feature Engineering Methodology

**Project:** SupeRR Selector Season 2 — RR PERFORMANCE LAB  
**Pipeline Scripts:** `src/03_data_cleaning.py` → `src/04_feature_engineering.py`  
**Automated Test Suite:** `tests/test_cricket_rules.py`, `tests/test_data_integrity.py`, `tests/test_feature_engineering.py`  
**Raw Data Policy:** Read-only ingestion from `data/raw/Data Pack/` (`keep_default_na=False, na_values=['']` so literal `'None'` tokens are never silently mangled into `NaN`). Original columns are preserved verbatim in processed tables; all transformations live in explicitly named derived columns.

---

## 1. Competition Eligibility & Separation Rules

Grounded in `report/official_problem_statement_requirements.md` (*"historical IPL and T20 International (T20I) data from 2022 onwards"*), competition eligibility is validated against both `competitions.csv` and `matches.csv` using `comp_id`, `match_format`, and parsed `season_start_year` (never competition name alone):

- **Primary Eligible Competitions (139 total):**
  - **IPL (5 competitions):** `comp_id` ∈ `{1358, 1715, 2193, 2725, 3298}` (`IPL 2022`–`IPL 2026`, `match_format='T20'`, 371 matches in metadata, 367 with ball data).
  - **T20I (134 competitions):** `match_format='T20I'` and `season_start_year >= 2022` (482 matches in metadata, 470 with ball data; includes 3 zero-match series `2940`, `3405`, `3473`).
- **Excluded Non-IPL T20 Competitions (2 total):**
  - `comp_id=2670`: `Mens T20 Emerging Teams Asia Cup 2024` (15 matches, 3,519 deliveries).
  - `comp_id=3289`: `Asia Cup Rising Stars 2025` (15 matches, 3,466 deliveries, including 12 Super Over deliveries).
  - Preserved intact in `data/processed/excluded_competition_deliveries.csv` (6,985 rows) with explicit `exclusion_reason` and logged in `outputs/excluded_records.csv`.

---

## 2. Super Over Separation & Incomplete Super Over Coverage

- Every delivery is tagged with `innings_type`: `regular_first` (`innings == 1`), `regular_second` (`innings == 2`), or `super_over` (`innings >= 3`).
- All **38 Super Over deliveries** (`26` from 4 primary IPL/T20I matches `34429`, `40725`, `45512`, `50359`; `12` from 2 excluded competition matches `48027`, `48029`) are separated into `data/processed/super_over_deliveries.csv` and never mixed with regulation innings in `data/processed/clean_deliveries.csv`.
- **Three earlier T20I Super Over matches lack innings 3–4 ball data** despite result text confirming a Super Over and duplicate Super Over `batting_order` rows in `playing_eleven.csv`:
  - `13613` (AUS vs SL, 2022-02-13, *"Australia Won the one over Eliminator"*)
  - `21176` (NZ vs SL, 2023-04-02, *"Sri Lanka won the super over"*)
  - `28962` (IND vs AFG, 2024-01-17, *"India Won Super Over By 10 Runs"*)
- These matches are classified as `tied_super_over_missing_ball_data` in `data/processed/clean_matches.csv`. Their regulation innings (1–2) remain intact in `clean_deliveries.csv`, and missing Super Over balls are **never reconstructed**.

---

## 3. Cricket Scoring & Delivery-Level Rules

All 33 source columns of `ball_by_ball.csv` are preserved unmodified. Derived analytical fields enforce official T20 scoring laws:

| Metric / Rule | Formula / Definition | Cricket-Law Justification |
| :--- | :--- | :--- |
| `total_runs` | `runs + extras1_runs + extras_2_runs` | Raw CSV has no `total_runs` column; reconciles with 0 diff across all 1,652 primary regular innings and matches 387/388 non-DLS run-margin results exactly (sole exception: `14130`, documented as `ANOM_14`). |
| `is_wide` | `extras_type == 'wide'` | Wide ball (non-legal, not faced by batter). |
| `is_noball` | `extras_type in {'Overstep', 'other'}` | Phase 2 proved `'other'` (264 rows) behaves identically to `'Overstep'` (576 rows) with `extras1_runs=1` and 6 remaining legal balls per over. |
| `is_legal_delivery` | `~(is_wide \| is_noball)` | Excludes `wide`, `Overstep`, `other`; includes `None`, `byes`, `legbyes`, and legal `Penalty` (`16753`). |
| `is_batter_ball_faced` | `~is_wide` | Under ICC/T20 scoring laws, no-balls count as balls faced by the striker; wides do not. |
| `batter_runs` | `runs` | Strictly runs off the bat (verified `0` on all wides and byes). |
| `bowler_conceded_runs` | `wide`: `extras1_runs + extras_2_runs`; `noball`: `runs + extras1_runs`; `byes`/`legbyes`/`Penalty`: `0`; `None`: `runs` | Excludes byes, leg-byes, penalty runs, and byes/leg-byes off no-balls (`extras_2_runs`). Satisfies exact accounting identity `bowler_conceded_runs + non_bowler_extras_runs == total_runs` on 100% of rows. |
| `is_wicket_event` | `is_wicket == True` | Team wickets fallen. Excludes the 12 verified Retired Hurt events where `is_wicket == False`. |
| `is_retired_hurt` | `(~is_wicket) & dismissed_player_id.notna()` | Verified via next-ball crease inspection across all 12 rows (11 primary, 1 excluded): injured batter departs immediately without losing a team wicket and never returns. |
| `dismissal_type_std` | Normalizes `'Obstracting the field'` → `'Obstructing the field'` | Preserves raw `dismissal_type` untouched. |
| `is_bowler_wicket` | `is_wicket_event & dismissal_type_std in {'Caught', 'Bowled', 'LBW', 'Stump', 'Hit Wicket'}` | Explicitly excludes `RunOut`, `Retire Out`, `Obstructing the field`, and `Retired Hurt`. |
| `bowl_speed_clean` | Validated speed in `[50, 165]` km/h; else `NaN` | Preserves raw `bowl_speed`; flags `0.0` (`zero_unrecorded`), `<0` (`negative_invalid`), `(0,50)` (`below_50_outlier`), and `>165` (`above_165_outlier`, including 10× decimal shifts up to `1456.1`). |

---

## 4. Match Metadata & DLS / Revised-Overs Unit Discovery

- **Critical Unit Verification:** Inspection of `matches.csv` proved that `first_inn_revised_overs` and `second_inn_revised_overs` are stored in **legal balls** (multiples of 6: e.g., `90.0` for the 15-over IPL 2023 Final `21586`, `84.0` for the 14-over IPL 2025 match `40727`, `30.0` for 5-over match `54711`). `clean_matches.csv` preserves the raw columns and adds unit-explicit `first_inn_revised_balls`, `second_inn_revised_balls`, `first_inn_revised_overs_exact`, and `second_inn_revised_overs_exact`.
- **No Invented Scheduled Overs:** For DLS matches lacking `revised_overs` or `revised_target` (`20182`, `23674`, `24822`, `28334`), unflagged rain-shortened matches (`15795`, `18532`, `31278`, `48514`), and asymmetric revised-overs entries (`16753`, `19959` inn 2 where `second_inn_revised_overs` is blank), `scheduled_legal_balls`, `legal_balls_remaining_before`, and `required_run_rate_before` are set to **`NaN`** and `match_phase` to **`'Unavailable'`** rather than assuming 20 overs. Those matches remain preserved in `clean_deliveries.csv` for non-RRR batting/bowling analysis.
- **Sentinel Cleaning:** `man_of_the_match == 0` (119 raw rows) is mapped to `NaN` in derived `man_of_the_match_clean` while preserving raw `man_of_the_match`.

---

## 5. Player Master & Alias Policy

- `data/processed/player_master.csv` (`1,217` unique rows) is keyed strictly by integer `player_id`. Players are **never joined or grouped by name alone**.
- **Cross-table name variant (`4458`):** Standardized display name set to `'Aneurin Donald'` (from `ball_by_ball.csv`) while preserving `'AHT Donald'` in `mapping_source_names`.
- **Shared names across distinct `player_id`s (7 groups, 14 IDs):** Documented in `outputs/player_alias_report.csv` and kept strictly separate:
  - *Distinct individuals:* `Rashid Khan` (`4722` AFG/GT vs `20172` Nepal), `Abdul Samad` (`6922` PAK vs `7446` IPL), `Haider Ali` (`7338` PAK vs `28756` UAE).
  - *Suspected split IDs (not auto-merged):* `Basil Hameed` (`8638`, `39444`), `Bashir Ahmad` (`29833`, `39479`), `Mohammad Ali` (`3083`, `20229`), `Muhammad Farooq` (`27373`, `28978`).
- **Playing XI Super Over duplicates (40 keys across matches `13613`, `21176`, `28962`)** and **2 excluded-competition delivery players absent from `playing_eleven.csv` (`36153`, `39444` in `comp_id=2670`)** are documented in `outputs/player_alias_report.csv`.

---

## 6. Pre-Delivery Feature Engineering & Anti-Leakage Guarantees

Every state feature in `src/04_feature_engineering.py` is computed **strictly before the current delivery** using cumulative sums minus the current ball (`cumsum() - current_value`), sorted deterministically by `(match_id, innings, innings_ball_num)`:

- **Innings Pre-Delivery State:** `cum_score_before`, `wickets_before`, `wickets_in_hand_before`, `legal_balls_before`, `overs_completed_before`, `current_run_rate_before` (`NaN` when `legal_balls_before == 0`).
- **Match Phase (`match_phase`):**
  - Standard 20-over innings (`scheduled_legal_balls == 120`): `Powerplay` (`legal_balls_before < 36`, overs 1–6), `Middle` (`36 <= legal_balls_before < 90`, overs 7–15), `Death` (`>= 90`, overs 16–20).
  - Known reduced-over innings (`scheduled_legal_balls < 120`): Powerplay scaled per official ICC T20 Clause 28.7.3 (`5–8 ov → 2`, `9–11 → 3`, `12–14 → 4`, `15–18 → 5`, `19–20 → 6`); Death = final `ceil(0.25 * scheduled_overs)` overs.
  - Missing revised-overs DLS/reduced innings: `match_phase = 'Unavailable'`.
- **Chase Context (`innings == 2` only; always `NaN` in `innings == 1`):** `target_runs` (`revised_target` when available, else `inn1_total_runs + 1` for non-DLS — strictly known before ball 1 of innings 2), `runs_remaining_before`, `legal_balls_remaining_before`, `required_run_rate_before`, and boolean `chase_context_available`.
- **Individual Pre-Delivery State:** `batter_runs_before`, `batter_balls_faced_before`, `bowler_legal_balls_before`, `bowler_runs_conceded_before`, `bowler_wickets_before`.
- **Zero Future-Outcome Leakage:** Completed match results (`result`, `win_team_id`) are never used to compute per-ball match state, target runs, or scheduled balls.

