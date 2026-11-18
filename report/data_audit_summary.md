# Phase 2 Data Audit Summary — SupeRR Selector Season 2

**Audit Scope:** Read-only inspection and validation of all six competition CSVs inside `data/raw/Data Pack/` and the official Round 1 Problem Statement PDF (`Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf`).  
**Reproducible Scripts:** `src/01_dataset_audit.py` and `src/02_dataset_audit.py`  
**Audit Outputs Directory:** `outputs/` (8 structured Phase 2 CSV reports + 12 starter audit CSVs)  
**Raw Data Integrity:** Verified untouched (no raw files modified, overwritten, or renamed).

---

## 1. Overall Dataset Assessment

The supplied competition dataset is **structurally sound, well-keyed, and analytically usable**, spanning **2022-01-22 through 2026-11-01** across **141 competitions**, **883 scheduled/recorded matches**, **867 matches with delivery data**, and **200,999 ball-by-ball records**.

Key structural strengths:
- **Zero exact duplicate rows** across all six CSVs.
- **100% referential integrity** for `comp_id` across `matches`, `teams`, and `competition_team_player_mapping`, and for `match_id` between `ball_by_ball` and `matches`.
- **100% player coverage** from `ball_by_ball` and `playing_eleven` into `competition_team_player_mapping` (`0` unmapped player IDs; `0` unmapped `(comp_id, team_id, player_id)` triples).
- **Clean delivery natural key:** `0` duplicates on `(match_id, innings, innings_ball_num)` and `0` duplicates on `(match_id, innings, overid, over_ball_num)`.

However, the audit uncovered **critical domain, schema, and edge-case nuances** that would materially distort downstream pressure modeling if overlooked — most notably:
1. Two **non-IPL T20 competitions** (30 matches, 6,985 deliveries) mixed into `competitions.csv`.
2. Non-standard extras coding where **`extras_type == 'other'` (264 rows)** is empirically a **non-legal no-ball**, and **`extras_type == 'None'` (189,167 rows)** is parsed as `NaN` by default `pandas.read_csv()`.
3. `over_ball_num` and `innings_ball_num` count **all deliveries (including wides/no-balls)** rather than legal deliveries.
4. Minor feed anomalies (e.g., 12 retired-hurt rows with `is_wicket=False` & populated `dismissed_player_id`, 1 `Retire Out` with missing `dismissed_player_id`, 1 `striker_id == non_striker_id` row, 1 7-legal-ball over, 7 shared player names across 14 `player_id`s, and heavy zero-sentinels + 10x decimal-shift typos in `bowl_speed`).

---

## 2. File-Level Inventory & Schema Summary

| File | Rows | Columns | Memory (MB) | Natural Key | Exact Dups | Key Dups | Raw Blank Cells | Pandas Default NA Cells |
| :--- | ---: | ---: | ---: | :--- | ---: | ---: | ---: | ---: |
| `ball_by_ball.csv` | 200,999 | 33 | 169.196 | `match_id + innings + innings_ball_num` | 0 | 0 | 570,769 | 766,466 |
| `matches.csv` | 883 | 22 | 0.462 | `match_id` | 0 | 0 | 2,736 | 2,736 |
| `competitions.csv` | 141 | 4 | 0.027 | `comp_id` | 0 | 0 | 0 | 0 |
| `teams.csv` | 353 | 3 | 0.026 | `comp_id + team_id` | 0 | 0 | 0 | 0 |
| `playing_eleven.csv` | 28,381 | 9 | 3.209 | `match_id + team_id + player_id` | 0 | **40** | 26,012 | 26,012 |
| `competition_team_player_mapping.csv` | 6,413 | 6 | 1.388 | `comp_id + team_id + player_id` | 0 | 0 | 0 | 0 |

*Note on `playing_eleven.csv` (40 key duplicates):* Verified across **75 rows in exactly 3 Super Over matches** (`match_id` `13613`, `21176`, `28962`). Players who batted in both the regulation innings and the Super Over appear twice with different `batting_order` values.

---

## 3. Important Findings

### A. Competition Eligibility & Format Separation
The official Round 1 PDF states the dataset covers **historical IPL and T20 International (T20I) data from 2022 onwards**. Auditing `competitions.csv` reveals three distinct groups:

| Eligibility Category | Competitions | Matches (Metadata) | Matches (Ball Data) | Total Deliveries | Legal Deliveries | Date Span |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **IPL** (`IPL 2022`–`IPL 2026`) | 5 | 371 | 367 | 87,687 | 83,755 | 2022-03-26 to 2026-05-31 |
| **T20I** | 134 | 482 | 470 | 106,327 | 101,960 | 2022-01-22 to 2026-11-01 |
| **Non-IPL T20** *(Flagged)* | 2 | 30 | 30 | 6,985 | 6,730 | 2024-10-18 to 2025-11-23 |
| **Total** | **141** | **883** | **867** | **200,999** | **192,445** | **2022-01-22 to 2026-11-01** |

- **Non-IPL T20 Competitions explicitly separated:**
  - `comp_id=2670`: `Mens T20 Emerging Teams Asia Cup 2024` (`T20`, `2024`, 15 matches, 3,519 deliveries)
  - `comp_id=3289`: `Asia Cup Rising Stars 2025` (`T20`, `2025`, 15 matches, 3,466 deliveries)
- **IPL season counts:** `IPL 2022` (74/74), `IPL 2023` (74/74), `IPL 2024` (74 meta / 71 ball — 3 abandoned without a ball bowled), `IPL 2025` (75 meta / 74 ball — 1 abandoned without a ball bowled), `IPL 2026` (74/74).
- **3 T20I competitions with 0 matches in `matches.csv`:**
  - `2940`: `India in Bangladesh T20I Series 2025` (2 teams, 0 players in mapping)
  - `3405`: `Afghanistan v Sri Lanka T20I Series 2026` (2 teams, 15 players in mapping)
  - `3473`: `United Arab Emirates in Nepal T20I Series 2026` (2 teams, 35 players in mapping)
- **Unknown/unmatched `comp_id`s:** `0` across `matches`, `teams`, and `player_mapping`.

### B. Match Reconciliation
- **883 matches in `matches.csv` vs. 867 in `ball_by_ball.csv`:**
  - **All 16 matches absent from `ball_by_ball.csv` are empirically verified as `result = "Match Abandoned"`** (zero balls bowled).
  - **0** matches exist in `ball_by_ball.csv` without metadata in `matches.csv`.
- **Abandoned & No-Result matches:**
  - **19** abandoned matches in metadata: 16 with 0 deliveries + **3 with partial ball data** (`15410` [22 balls], `20226` [118 balls], `21406` [118 balls]).
  - **21** no-result matches in metadata: all 21 have partial ball data.
  - **22** matches have only Innings 1 recorded in `ball_by_ball.csv`.
- **Playing XI coverage:** 880 of 883 matches appear in `playing_eleven.csv`; the 3 missing matches (`36210`, `41503`, `48513`) are all `Match Abandoned` with 0 deliveries.
- **Tied & Super Over matches (10 distinct matches identified):**
  - **6 matches** have Super Over ball-by-ball records (`innings` 3 & 4: 25 + 13 = 38 deliveries): `34429`, `40725` (DC vs RR, IPL 2025), `45512`, `48027`, `48029`, `50359` (LSG vs KKR, IPL 2026).
  - **3 Super Over matches lack innings 3/4 ball data** despite result text confirming a Super Over: `13613` ("one over Eliminator"), `21176` ("super over"), `28962` ("Super Over").
  - **1 rain-shortened tie without a Super Over:** `18532` (NZ vs IND, 2022-11-22, `Match Tied` on DLS after 9 overs in 2nd innings).
- **DLS / Revised-Overs inconsistencies:**
  - 34 matches have `first_inn_revised_overs` or `second_inn_revised_overs` populated (23 have `revised_target`).
  - However, **8 rain-reduced/DLS matches have `revised_overs = NaN` in `matches.csv`** even though their innings ended early or result text states `D/L` / `DLS` (e.g., `15795`, `16754`, `21070`, `23674`, `28046`, `29984`, `31278` [IPL 2024 16-over match], `48514`).
- **Unusual innings numbering:** `0` rows outside `{1, 2, 3, 4}`.
- **Team ID integrity:** `0` missing `comp_id`/`home_team_id`/`away_team_id`/`batting_team_id`/`bowling_team_id`; `0` team mismatches between `ball_by_ball` and `matches`; `0` mid-innings team ID switches.

### C. Delivery-Level Validation
- **Total vs. Legal Deliveries:**
  - **Total deliveries:** `200,999`
  - **Legal deliveries:** `192,445` (`extras_type` not in `{'wide', 'Overstep', 'other'}`)
  - **Non-legal deliveries:** `8,554` (`wide`: 7,714; `Overstep`: 576; `other`: 264)
  - *Empirical verification of `'other'` (264 rows):* Every single row has `extras1_runs = 1`, batter `runs` in `{0, 1, 2, 3, 4, 6}`, `extras_2_runs` in `{0, 1, 4}`, and in 243/254 overs containing `'other'`, `total_deliveries - wide - Overstep - other == 6` (the remaining 11 are partial end-of-innings overs). This proves `'other'` represents **non-overstep no-balls** (e.g., waist-high full tosses, fielding restriction no-balls).
  - **`Penalty` (1 row):** `match_id=16753, innings=2, over=6, ball=4` (`extras1_runs=5`, legal delivery within a 6-ball over).
- **Runs & Extras Reconciliation:**
  - No `total_runs` column exists in `ball_by_ball.csv`; total runs per delivery must be derived as `runs + extras1_runs + extras_2_runs` (0 negative values; max batter runs = 6; max derived total runs on one ball = 7).
  - **2 rows** have `extras_type = 'None'` with non-zero extras: `match_id=17555` (`innings=1, over=5, ball=4`, `extras_2_runs=1`) and `match_id=36097` (`innings=2, over=8, ball=6`, `extras1_runs=1`).
  - **1 row** has `extras_type = 'legbyes'` with `extras1_runs=0, runs=1`: `match_id=37099` (`innings=1, over=14, ball=1`).
  - **0** wides or byes have non-zero batter `runs`.
- **Boundary Flags:**
  - `is_four=True` always has `runs=4` (0 violations); 20 rows have `runs=4, is_four=False` (all-run 4s / overthrows).
  - `is_six=True` always has `runs=6` (0 violations); **3 rows** have `runs=6, is_six=False` (`match_id` `17396`, `31277`, `40766` — likely overthrow 6s or unflagged sixes).
- **Over & Ball Numbering:**
  - `overid` strictly within `1..20` (`overid = 1` for all Super Overs).
  - `over_ball_num` and `innings_ball_num` are sequential **delivery** indices (including wides/no-balls), **not** legal-ball counters.
  - **1 over** contains 7 legal deliveries: `(match_id=41509, innings=1, overid=12)` bowled by Aaron Hardie (7 consecutive `'None'` deliveries).
  - **2 IPL 2022 innings** (`14130` inn 1 & 2, `14164` inn 1) have 119 legal deliveries instead of 120 without revised overs (likely 1 missed delivery in feed or 5-ball over).
- **Wickets & Dismissals (`10,881` flagged wickets):**
  - Breakdown: `Caught` (7,557), `Bowled` (1,775), `LBW` (709), `RunOut` (600), `Stump` (214), `Hit Wicket` (17), `Retire Out` (6), `Obstracting the field` (2 — typo), `Obstructing the field` (1).
  - **1 row** has `is_wicket=True` with `dismissed_player_id=NaN`: `match_id=40709, innings=2, over=19, ball=5` (`Retire Out`, striker Hardik Pandya).
  - **12 rows** have `is_wicket=False` and `dismissal_type=NaN` yet `dismissed_player_id` populated (verified as **Retired Hurt** events such as Rahul Tripathi, Rohit Sharma, Shikhar Dhawan, Kane Williamson, Pathum Nissanka).
  - **1 row** has `striker_id == non_striker_id`: `match_id=37086, innings=1, over=18, ball=6` (`3550`, Sharafuddin Ashraf — in non-IPL T20 `comp_id=2670`).
- **Bowling Speed (`bowl_speed`):**
  - `77,861` rows (**38.74%**) equal `0.0` (unrecorded radar speed sentinel).
  - `123,095` rows (**61.24%**) fall in plausible range `50–165 km/h` (min `61.4`, median `123.8`, max `157.4`).
  - `43` non-zero anomalous speeds: `1` negative (`-1.0`, `match_id=14108`), `22` in `(0, 50)`, and `20` above `165 km/h` (e.g., `1456.1`, `1339.6`, `1305.0`, `967.0` — 10x decimal-shift errors).

### D. Player Mapping Validation
- **Coverage:** 959 unique `player_id`s in `ball_by_ball`, 1,082 in `playing_eleven`, 1,217 in `competition_team_player_mapping` (`0` players in `ball_by_ball` or `playing_eleven` missing from mapping; 258 squad/bench/abandoned-match players in mapping with 0 deliveries).
- **2 players in deliveries absent from `playing_eleven.csv`:** `36153` (Syed Haider) and `39444` (Basil Hameed), both in UAE matches `37087, 37092, 37095` inside non-IPL T20 `comp_id=2670`.
- **1 cross-table name mismatch for the same `player_id`:** `player_id=4458` appears as `'Aneurin Donald'` in `ball_by_ball` vs. `'AHT Donald'` in `player_mapping`.
- **7 player names shared across multiple `player_id`s** (1,217 unique `player_id`s vs. 1,210 unique `player_name`s):
  - **3 genuinely distinct individuals (never merge by name!):**
    - `Rashid Khan`: `4722` (Afghanistan / Gujarat Titans) vs. `20172` (Nepal)
    - `Abdul Samad`: `6922` (Pakistan / Pakistan A) vs. `7446` (SRH / LSG IPL)
    - `Haider Ali`: `7338` (Pakistan / Pakistan A) vs. `28756` (UAE)
  - **4 likely duplicate/split IDs for the same person (require explicit verification before any ID merge):**
    - `Basil Hameed`: `8638` (UAE, 5 comps) vs. `39444` (UAE, Emerging Asia Cup `2670`)
    - `Bashir Ahmad`: `29833` (Afghanistan) vs. `39479` (Afghanistan A)
    - `Mohammad Ali`: `3083` (Pakistan) vs. `20229` (Pakistan)
    - `Muhammad Farooq`: `27373` (UAE) vs. `28978` (UAE)

---

## 4. Data Limitations & Missing Information

1. **No standalone `players.csv`:** Despite the Round 1 PDF mentioning "players" alongside mappings, no separate player biographical table (DOB, role, nationality, Unstop dropdown IDs) is supplied.
2. **Missing radar speed on 38.74% of deliveries** (`bowl_speed == 0`), plus 43 corrupted non-zero speeds; pace/speed features cannot be required for every ball.
3. **Incomplete DLS metadata:** `first_inn_revised_overs`, `second_inn_revised_overs`, and `revised_target` are blank (`NaN`) for at least 8 rain-reduced/DLS matches, meaning naive `120 - legal_balls` balls-remaining calculations will misstate pressure in those matches unless DLS/shortened innings are handled explicitly.
4. **Incomplete Super Over ball coverage:** Only 6 of 9 Super Over matches have `innings` 3 & 4 ball-by-ball rows; 3 earlier Super Over matches (`13613`, `21176`, `28962`) have no Super Over deliveries.
5. **No venue name or pitch/boundary dimensions:** `matches.csv` provides `venue_id` and `venue_country`, not venue name or ground size.
6. **Sentinel zeros in `matches.man_of_the_match`:** 119 rows contain `0` instead of null.
7. **Missing `playing_eleven` flags on ~30.5% of rows:** `batting_order` (8,678), `is_captain` (8,667), and `is_wk` (8,667) are blank primarily for non-playing squad/bench entries (`is_played=False`).
8. **Missing `delivery_ist_time` precision:** Sample timestamps show midnight UTC (`00:00:00 UTC`), indicating date-level rather than exact ball-by-ball wall-clock timestamps.

---

## 5. Potential Analytical Risks (If Unaddressed in Phase 3)

| Risk | Impact on Pressure Analysis & Rankings |
| :--- | :--- |
| **Default `pd.read_csv()` NA parsing** | Silently turns `extras_type='None'` (189,167 rows), `stroke='None'` (6,146), and `delivery_style='None'` (384) into `NaN`, breaking string equality filters. |
| **Treating `extras_type='other'` as legal** | Miscounts legal balls, strike rates, economy rates, and balls remaining across 254 overs (264 no-balls). |
| **Using `innings_ball_num` as legal balls bowled** | Overstates balls bowled (and understates balls remaining / inflates RRR) in every innings with wides or no-balls. |
| **Silently including Non-IPL T20 (`2670`, `3289`)** | Violates the official brief ("IPL and T20I data from 2022 onwards") and mixes India A / Pakistan A / Emerging players into senior IPL/T20I rankings. |
| **Joining or grouping by `player_name`** | Merges distinct players (`Rashid Khan` AFG/GT + `Rashid Khan` Nepal; `Abdul Samad` IPL + `Abdul Samad` PAK; `Haider Ali` PAK + UAE). |
| **Crediting non-bowler dismissals to bowlers** | Crediting `RunOut` (600), `Retire Out` (6), and `Obstructing/Obstracting the field` (3) as bowler wickets corrupts bowling pressure metrics. |
| **Treating `is_wicket=False` with `dismissed_player_id` as dismissals** | Misclassifies 12 Retired Hurt events as outs. |
| **Including Super Over rows (`innings >= 3`) in regulation chase/RRR logic** | Super Overs have a 6-ball cap and 2-wicket cap; mixing them with 20-over formulas distorts RRR and wickets-in-hand calculations. |
| **Unfiltered `bowl_speed` averages** | Zeros (`38.74%`) and 10x typos (`1456.1 km/h`) severely bias mean/std speed features. |

---

## 6. Recommended Cleaning Decisions for Phase 3 (Not Yet Applied)

1. **Standardized Ingestion Loader:** Read all CSVs with `keep_default_na=False, na_values=['']` (preserving literal `'None'`), and explicitly cast numeric/boolean columns.
2. **Primary Analytical Cohort Filter:** Separate into explicit competition flags (`is_ipl`, `is_t20i`, `is_non_ipl_t20`). Restrict core Round 1 modeling to **IPL (`comp_id` in `{1358, 1715, 2193, 2725, 3298}`) + T20I (`match_format == 'T20I'`)**, explicitly excluding the 2 Non-IPL T20 Emerging/Rising Stars tournaments (`2670`, `3289`) while keeping them documented and traceable.
3. **Canonical Delivery Flags (Derived Columns in `data/processed/`):**
   - `is_wide = (extras_type == 'wide')`
   - `is_noball = extras_type.isin(['Overstep', 'other'])`
   - `is_legal_ball = ~(is_wide | is_noball)`
   - `is_batter_ball_faced = ~is_wide` *(no-balls count as balls faced by the batter under cricket scoring laws)*
   - `total_runs = runs + extras1_runs + extras2_runs`
   - `bowler_runs_conceded`: `runs + extras1_runs` for `wide`/`Overstep`/`other`, `runs` only for `None`, `0` for `byes`/`legbyes`/`Penalty` (and `extras_2_runs` excluded from bowler runs as byes/legbyes off a no-ball).
   - `is_bowler_wicket = is_wicket & dismissal_type.isin(['Caught', 'Bowled', 'LBW', 'Stump', 'Hit Wicket'])`
   - Standardize `dismissal_type`: normalize `'Obstracting the field'` → `'Obstructing the field'` in the processed layer only.
4. **Canonical Entity Keying:** Always group and join on `player_id` (integer), attaching one canonical display name per `player_id` (resolving `4458` `'Aneurin Donald'`/`'AHT Donald'` consistently).
5. **Super Overs & DLS Handling:**
   - Separate `innings in {1, 2}` (regulation) from `innings in {3, 4}` (Super Overs) so Super Over deliveries never enter 20-over RRR calculations (optionally analyze Super Overs as a separate clutch indicator or exclude consistently with documentation).
   - Flag all DLS / rain-shortened / abandoned / no-result innings explicitly (`is_dls_or_reduced`, `is_abandoned_or_nr`) so chase target and balls-remaining features handle revised overs accurately or exclude ambiguous missing-`revised_overs` chases from RRR calculations.
6. **Edge-Case Audit Log:** Keep the 3 minor extras anomalies (`17555`, `36097`, `37099`), the 1 missing `dismissed_player_id` on `Retire Out` (`40709`), the 1 `striker_id == non_striker_id` row (`37086`, already outside IPL+T20I), and the 7-legal-ball over (`41509`) logged in a transparent cleaning log; treat `bowl_speed == 0` or outside `[50, 165]` as `NaN` in processed tables.
7. **Deduplicate `playing_eleven` View:** When using `playing_eleven.csv` for match participation/roles, separate regulation-innings rows from the 40 Super Over duplicate rows in matches `13613`, `21176`, and `28962`.

---

## 7. Unresolved Questions for Alignment Before Phase 3

1. **Non-IPL T20 Tournaments (`2670`, `3289`):** Confirm exclusion of `Mens T20 Emerging Teams Asia Cup 2024` and `Asia Cup Rising Stars 2025` to strictly match the official PDF ("IPL and T20I data from 2022 onwards").
2. **IPL 2026 & Full-Period Coverage:** Note that the supplied dataset runs through `2026-11-01` and includes all 5 full IPL seasons (`2022`–`2026`, 74–75 matches each) plus T20Is through Nov 2026. Confirm whether all seasons 2022–2026 should receive equal weight or recency weighting.
3. **Unstop Dropdown Eligibility Pool:** Confirm whether the Unstop submission dropdown restricts choices to a specific player list (e.g., IPL-active or senior T20I players) and verify exact name matching against `player_id`.
4. **Super Overs (`innings` 3–4):** Because only 6 of 9 Super Over matches contain delivery data (and 2 of those 6 are in non-IPL T20 `comp_id=3289`), decide whether to exclude Super Over deliveries from the core pressure model for fairness or track them only as supplementary context.
5. **Rain-Reduced / DLS Matches Missing `revised_overs`:** Decide whether to exclude the 8 rain-shortened matches that lack `revised_overs`/`revised_target` metadata from RRR-based chase pressure features, or backfill revised targets only if explicitly authorized.
6. **Suspected Split IDs in Associate/A-Team Feeds:** Confirm whether any of the 4 suspected split IDs (`Basil Hameed`, `Bashir Ahmad`, `Mohammad Ali`, `Muhammad Farooq`) affect eligible IPL/T20I players after excluding non-IPL T20 competitions (`2670`, `3289`).

