# SupeRR Selector Season 2 — Methodology Report (RR PERFORMANCE LAB)

**Challenge:** Identify the Most Reliable Players Under Pressure (Rajasthan Royals — IPL 2027 Auction Strategy)  
**Submission Alignment:** Matches Official Round 1 Problem Statement PDF (`01 Player Rankings`: two ordered Top-10 lists — Top 10 Batters & Top 10 Bowlers; `02 Methodology Report`).  
**Epistemic Labeling Convention:** Throughout this report, *Measured Facts* denote raw observed counts/rates, *Calculated Metrics* denote cricket-law-derived quantities, *Model-Derived Scores* denote LOMO/Empirical-Bayes/composite outputs, and *Interpretations / Limitations* identify scope boundaries and sampling uncertainty.

---

## 1. Competition Objective
Build a transparent, reproducible, data-driven system that measures how batters and bowlers perform in high-pressure T20 match situations compared with their usual baseline performance, separates effectiveness from cross-match reliability and sample-size evidence, and outputs two ordered Top 10 lists (Batters Ranks 1–10 and Bowlers Ranks 1–10) backed strictly by analysis of the supplied competition data.

## 2. Dataset Description & Source Files
**Measured Facts (Verified Phase 2 Audit):** Six unmodified CSV files inside `data/raw/Data Pack/` spanning `2022-01-22` through `2026-11-01`:
- `ball_by_ball.csv`: `200,999` deliveries × `33` columns (`0` exact duplicates; natural key `match_id + innings + innings_ball_num`).
- `matches.csv`: `883` matches × `22` columns (`867` with ball data; all `16` absent matches verified as `Match Abandoned`).
- `competitions.csv`: `141` competitions (`5` IPL, `134` T20I, `2` non-IPL T20).
- `teams.csv`: `353` `(comp_id, team_id)` entries.
- `playing_eleven.csv`: `28,381` rows (`40` duplicate keys verified across `3` Super Over matches).
- `competition_team_player_mapping.csv`: `6,413` rows (`1,217` unique `player_id`s; `1,210` unique names).

## 3. Data Cleaning & Quality Controls
**Calculated Metrics & Engineering Controls (Phase 3):**
- **Literal `'None'` Preservation:** All CSVs read with `keep_default_na=False, na_values=['']` so `189,167` rows of `extras_type='None'` are never silently parsed as `NaN`.
- **Cricket Scoring Laws:** Verified `total_runs = runs + extras1_runs + extras_2_runs` (`0` diffs across all `1,652` primary innings; `387/388` non-DLS run-margin matches reconcile to the exact run, with sole exception `match_id=14130` missing 1 ball per innings documented as `ANOM_14`). Empirically verified `extras_type='other'` (`264` rows) are non-overstep no-balls (`is_legal_delivery` excludes `wide`, `Overstep`, `other`; `is_batter_ball_faced` excludes `wide` only). Bowler-conceded runs exclude byes, leg-byes, penalty runs, and `extras_2_runs` (`0` reconciliation diffs).
- **Dismissal Integrity:** Strictly attributed batting dismissals via `dismissed_player_id` (accurately assigning `261` non-striker run-outs), excluded `11` primary Retired Hurt events (`is_wicket=False` with `dismissed_player_id` populated), normalized `'Obstracting the field'` → `'Obstructing the field'` in `dismissal_type_std`, and restricted bowler wickets to `Caught`, `Bowled`, `LBW`, `Stump`, and `Hit Wicket`.
- **Unit & Identity Integrity:** Verified `first_inn_revised_overs` / `second_inn_revised_overs` are stored in **legal balls** (multiples of 6). Keyed all players strictly on integer `player_id` so shared-name individuals (`Rashid Khan` `4722`/`20172`, `Abdul Samad` `6922`/`7446`, `Haider Ali` `7338`/`28756`) are never merged.

## 4. Competition Eligibility
Strictly matching the official brief (*"historical IPL and T20I data from 2022 onwards"*):
- **Primary Analytical Dataset:** `193,988` regular-innings (`innings` 1 & 2) deliveries across `139` eligible competitions (`5` IPL seasons 2022–2026: `87,673` deliveries; `134` T20I series: `106,315` deliveries; `837` matches with ball data; `1,652` innings).
- **Explicit Exclusions (Preserved Separately):** `2` non-IPL T20 competitions (`comp_id=2670` Men's T20 Emerging Teams Asia Cup 2024 and `comp_id=3289` Asia Cup Rising Stars 2025; `6,985` deliveries) and all `38` Super Over deliveries (`26` primary + `12` excluded).

## 5. Pressure Framework & Model C Selection
**Model-Derived Pre-Delivery Framework (Phase 4):** Strictly separates **Pressure** (pre-delivery match difficulty) from **Performance** and **Reliability**. Zero current-delivery runs/wickets, final innings totals, or match results enter any pressure score.
- Because IPL scores `+0.55` to `+0.88` RPO higher than T20I across every phase (`11.04` vs `10.26` Inn 1 Death; `9.08` vs `8.20` Powerplay), **Model C (Context-Normalized Leave-One-Match-Out IPL/T20I Model)** was selected over Model A (fixed domain bounds, `-5.01` pt Inn 1 IPL bias) and Model B (pooled ECDF, `-6.83` pt Inn 1 IPL bias).
- Three distinct `0–100` pre-delivery indices:
  1. **Chase Pressure (`chase_pressure_index`, Inn 2):** `0.34` Format-and-Stage RRR Demand + `0.24` Wicket Scarcity + `0.14` Acceleration Gap (`RRR - CRR`) + `0.12` Endgame Urgency + `0.16` Interaction (`RRR × Wickets`).
  2. **First-Innings Pressure (`first_innings_pressure_index`, Inn 1):** `0.30` Score Deficit vs. LOMO Par + `0.30` Wicket Collapse Severity + `0.15` CRR Lag + `0.10` Late-Innings Urgency + `0.15` Interaction (`Deficit × Wickets`).
  3. **Bowling Pressure (`bowling_pressure_index`, Inn 1 & 2):** Opposite wicket polarity (`corr = -0.866` Inn 1, `-0.596` Inn 2 with batting pressure). Defending chases peak in the tight battle zone around format par RPO (`7–13 RPO`) with batting wickets in hand, high phase hazard, set pre-delivery striker threat, and endgame leverage.
- **Missing/Corrupted Context Guard:** `1,551` deliveries (`1,539` missing revised-overs DLS/reduced matches + `12` corrupted-target deliveries in Match `48610`) are marked `UNAVAILABLE` (`NaN`) and never silently folded into `LOW PRESSURE`.

## 6. Pressure Threshold Calibration
Empirically calibrated against `~p35 / p70 / p90` (after testing equal-interval `25/50/75`, shared fixed `35/55/72`, and quartile `p25/p50/p75`):
- **Chase:** `< 32` LOW | `32–<50` MODERATE | `50–<74` HIGH | `>= 74` EXTREME (`30.18%` HIGH+EXTREME)
- **First Innings:** `< 30` LOW | `30–<45` MODERATE | `45–<61` HIGH | `>= 61` EXTREME (`30.84%` HIGH+EXTREME)
- **Bowling:** `< 47` LOW | `47–<60` MODERATE | `60–<68` HIGH | `>= 68` EXTREME (`29.88%` HIGH+EXTREME)
- **Non-Circular Validation:** Aggregate batting SR drops monotonically **`145.25 → 139.86 → 136.62 → 128.07`** (dismissal rate rises **`4.79% → 8.45%`**) and aggregate bowling economy climbs **`8.07 → 8.61 → 9.12 → 10.95`** across LOW → MODERATE → HIGH → EXTREME.

## 7. Batting Performance Methodology
For each batter (`824` analyzed), LOMO context expectations (`exp_bat_runs_per_ball`, `exp_bat_wkt_per_ball`) by `(format, innings, match_phase, batting_pressure_level)` isolate format-adjusted **Run Value Above Expected (`RVAE`)** and **Survival Above Expected (`exp_dismissals - dismissals`)**, combined into `net_impact_per_100b = 100 * (RVAE + 12.0 * survival_above_exp) / balls_faced` (higher = better), alongside raw SR, average, boundary %, dot %, and dismissal rate.

## 8. Bowling Performance Methodology
For each bowler (`596` analyzed), LOMO context expectations (`exp_bowl_runs_per_lb`, `exp_bowl_wkt_per_lb`) isolate **Runs Saved Above Expected (`RSAE`)** and **Wickets Above Expected**, combined into `net_impact_per_24b = 24 * (RSAE + 12.0 * wickets_above_exp) / legal_balls` (higher = better; explicit direction: lower economy & boundary-conceded % = better, higher dot % & wicket frequency = better).

## 9. Empirical Bayes Shrinkage
To prevent small-sample spikes from dominating rankings, ball-weighted method-of-moments variance decomposition across match-level spells (using delta-method rate-variance projection to prevent 1-ball duck explosions) empirically estimates prior strength `k = sigma_within^2 / tau_between^2`:

`theta_EB = (m_i / (m_i + k)) * theta_raw + (k / (m_i + k)) * mu_0`

- **Batting:** `k = 8.65` pressure matches.
- **Bowling:** `k = 30.00` pressure matches (higher match-to-match noise in T20 bowling automatically invokes stronger shrinkage).

## 10. Reliability & Evidence Scoring
Strictly decoupled from performance effectiveness and volume:
- **Reliability Score (`0–100`, Volume-Free Consistency):** Computed across `>= 5` pressure innings using **variance-stabilized spell residuals** (`z_spell = net_impact_runs / sqrt(L_balls)` — invariant to spell length so neither 1-ball ducks blow up nor workhorse players are penalized): `0.40` Innings Stability (inverse IQR) + `0.30` Floor Consistency (`z_spell >= -0.60`) + `0.20` Cross-Condition Stability (HIGH vs EXTREME and Inn 1 vs Inn 2) + `0.10` Cross-Season Stability. Verified near-zero correlation with raw ball volume (`r = +0.100` batting, `+0.165` bowling).
- **Evidence Strength Score (`0–100`):** Separately quantifies confidence from pressure balls (`0.30`), unique pressure matches (`0.30`), seasons represented (`0.20`), and inverse 95% bootstrap CI width (`0.20`). Players in `INSUFFICIENT_EVIDENCE` keep `reliability_score = NaN` (never imputed as `0`).

## 11. Uncertainty Estimation & Match-Clustered Bootstrap
Because Phase 4 documented high intra-innings delivery autocorrelation (`0.950` batting, `0.862` bowling), all 95% CIs resample **whole `match_id` clusters (`B = 500`, seed `42`)**. Additionally, Phase 6 runs **1,000 Monte Carlo rank simulations** perturbing each player's EB-shrunk impact by its match-clustered bootstrap SE to quantify 90% rank intervals (`mc_rank_p05`–`mc_rank_p95`) and Top-10 inclusion probabilities (`mc_prob_top10_pct`).

## 12. Player Eligibility
Validated Phase 5 primary cutoffs (`data/processed/ranking_eligibility_audit.csv`):
- **Batting:** `>= 80` HIGH+EXTREME balls faced, `>= 10` pressure innings, `>= 10` unique matches, non-null reliability → **`173` eligible** (`87` `HIGH_CONFIDENCE`), **`651` excluded**.
- **Bowling:** `>= 90` HIGH+EXTREME legal balls (15 overs), `>= 10` pressure innings, `>= 10` unique matches, non-null reliability → **`165` eligible** (`96` `HIGH_CONFIDENCE`), **`431` excluded**.

## 13. Ranking Model & Composite Score Formula
Each of four non-redundant pillars is calibrated onto a common `0–100` scale over the eligible cohort via robust logistic scaling (median & IQR) so nominal weights match actual variance shares without letting volume dominate. We compared three philosophies (`outputs/ranking_method_comparison.csv`):
1. **Performance-Dominant (`65/20/10/5`):** Maximizes raw/EB impact but lets boom-or-bust volatility slip into Top 10.
2. **Reliability-Dominant (`30/50/10/10`):** Rewards low-variance steadiness even when scoring/economy impact is mediocre.
3. **Balanced Primary (`50/25/15/10` — Selected):** Best aligns with the competition objective (*"perform well and deliver most consistently when it matters"*):

`Final Ranking Score = 0.50 * S_Perf(EB) + 0.25 * S_Reliability + 0.15 * S_Extreme+Lift + 0.10 * S_Evidence`

where `S_Extreme+Lift` combines `0.60` EB-shrunk EXTREME-tier execution (`k = 40` balls) and `0.40` shrunk observational pressure-vs-non-pressure context lift. Evidence weight is intentionally capped at `10%` because EB shrinkage inside `S_Perf(EB)` already accounts for sample size.

## 14. Role & Opportunity Considerations
Data-driven roles (`Opener`, `Top-Order`, `Middle-Order`, `Finisher / Lower-Middle`, `Powerplay Specialist`, `Middle-Overs Enforcer`, `Death Specialist`, `All-Phase`, plus `UNKNOWN / INSUFFICIENT EVIDENCE` for sparse players) confirm that context-adjusted `RVAE` and `RSAE` level the playing field across roles: finishers (`Matthew Wade`, `Naman Dhir`, `Ravindra Jadeja`, `Ayush Badoni`, `Tim David`, `Romario Shepherd`), top-order/openers (`Ibrahim Zadran`, `Shai Hope`, `Ruturaj Gaikwad`), and middle-order (`Heinrich Klaasen`) all compete fairly, as do death pacers (`Mark Adair`, `Matheesha Pathirana`), all-phase pacers (`Mark Wood`, `Eshan Malinga`, `Joshua Little`), and spinners (`Nasum Ahmed`, `Axar Patel`, `Rashid Khan`, `R. Ashwin`, `Wanindu Hasaranga`).

## 15. Ranking Robustness & Unselected Candidate Audit
| Discipline | Robustness Test | Spearman vs. Primary | Top-10 Overlap | Top-15 Mean Rank Shift |
| :--- | :--- | ---: | ---: | ---: |
| Batting | Model_A_Pressure | 0.9786 | 8/10 (80%) | 3.27 |
| Batting | Model_B_Pressure | 0.9732 | 7/10 (70%) | 4.20 |
| Batting | Model_C_Thresh_Minus3pts | 0.9755 | 8/10 (80%) | 4.27 |
| Batting | Model_C_Thresh_Plus3pts | 0.9759 | 7/10 (70%) | 3.40 |
| Batting | Raw_No_EB_Shrinkage | 0.9986 | 8/10 (80%) | 2.13 |
| Batting | Approach_Performance_Dominant | 0.9959 | 8/10 (80%) | 1.73 |
| Batting | Approach_Reliability_Dominant | 0.9291 | 7/10 (70%) | 4.87 |
| Bowling | Model_A_Pressure | 0.9396 | 5/10 (50%) | 5.13 |
| Bowling | Model_B_Pressure | 0.8838 | 7/10 (70%) | 6.47 |
| Bowling | Model_C_Thresh_Minus3pts | 0.9511 | 8/10 (80%) | 3.87 |
| Bowling | Model_C_Thresh_Plus3pts | 0.9126 | 8/10 (80%) | 6.07 |
| Bowling | Raw_No_EB_Shrinkage | 0.9927 | 8/10 (80%) | 3.13 |
| Bowling | Approach_Performance_Dominant | 0.9894 | 9/10 (90%) | 1.27 |
| Bowling | Approach_Reliability_Dominant | 0.8807 | 7/10 (70%) | 5.60 |

### Narrow Misses (Ranks 11–15, `outputs/shortlist_alternatives.csv`)
| Discipline | Primary Rank | Player Name | Role | Score | EB Impact | Rel | Pressure Balls / Matches | Notes |
| :--- | :---: | :--- | :--- | ---: | ---: | ---: | :---: | :--- |
| Batting | #11 | David Miller | Middle-Order | 71.36 | +40.32 | 46.2 | 631b / 49m | Rank #11 (score 71.36); Perf-Dom #8, Rel-Dom #17; MC Top-10 prob 41.4% |
| Batting | #12 | Dinesh Karthik | Finisher / Lower-Middle | 70.50 | +44.52 | 37.4 | 391b / 32m | Rank #12 (score 70.50); Perf-Dom #9, Rel-Dom #22; MC Top-10 prob 29.8% |
| Batting | #13 | Liton Das | Top-Order | 69.77 | +30.03 | 62.1 | 126b / 10m | Rank #13 (score 69.77); Perf-Dom #14, Rel-Dom #7; MC Top-10 prob 26.8% |
| Batting | #14 | Suryakumar Yadav | Middle-Order | 69.75 | +33.22 | 49.9 | 622b / 44m | Rank #14 (score 69.75); Perf-Dom #15, Rel-Dom #15; MC Top-10 prob 26.2% |
| Batting | #15 | Rahmanullah Gurbaz | Opener | 69.63 | +38.75 | 51.7 | 91b / 10m | Rank #15 (score 69.63); Perf-Dom #12, Rel-Dom #16; MC Top-10 prob 29.2% |
| Bowling | #11 | Corbin Bosch | All-Phase (Pace) | 68.07 | +4.17 | 49.1 | 105b / 12m | Rank #11 (score 68.07); Perf-Dom #9, Rel-Dom #10; MC Top-10 prob 39.4% |
| Bowling | #12 | Nathan Ellis | Death Specialist (Pace) | 68.02 | +3.12 | 46.1 | 295b / 24m | Rank #12 (score 68.02); Perf-Dom #14, Rel-Dom #11; MC Top-10 prob 30.9% |
| Bowling | #13 | Mohammad Nawaz | Middle-Overs Enforcer (Spin) | 67.36 | +4.16 | 41.3 | 245b / 24m | Rank #13 (score 67.36); Perf-Dom #12, Rel-Dom #18; MC Top-10 prob 31.1% |
| Bowling | #14 | Sunil Narine | Middle-Overs Enforcer (Spin) | 67.06 | +2.72 | 49.8 | 530b / 43m | Rank #14 (score 67.06); Perf-Dom #17, Rel-Dom #8; MC Top-10 prob 28.9% |
| Bowling | #15 | Digvesh Rathi | Middle-Overs Enforcer (Spin) | 66.38 | +3.23 | 41.4 | 295b / 19m | Rank #15 (score 66.38); Perf-Dom #16, Rel-Dom #20; MC Top-10 prob 19.7% |

## 16. Validation Results
- **Phase 3–6 Automated Test Suite (`pytest tests -v`):** All unit, cricket-rule, integrity, leakage, pressure, reliability, and final-ranking tests verified passing.
- **Ranking Validation (`outputs/ranking_validation_results.csv`):** `8 / 8 PASS` (zero duplicate IDs, exact descending score order, strict eligibility enforcement, zero missing reliability imputed as zero, composite scores strictly within `[0, 100]`, volume correlation kept low, uncertainty intervals preserved).

## 17. Final Ordered Top 10 Batters Under Pressure
| Rank | Player ID | Player Name | Role | Comp | Score | EB Impact/100b | Press SR | Press Avg | Rel | Evid | Balls / Matches | 95% CI | Stability |
| :---: | ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :--- |
| 1 | 796 | **Matthew Wade** | Finisher / Lower-Middle | IPL + T20I | 80.51 | +68.88 | 169.2 | 58.2 | 50.1 | 57.7 | 172b / 16m | [+51.5, +132.6] | 8/8 |
| 2 | 37052 | **Naman Dhir** | Finisher / Lower-Middle | IPL + T20I | 77.83 | +48.92 | 182.2 | 37.3 | 55.7 | 67.5 | 225b / 20m | [+21.1, +110.0] | 8/8 |
| 3 | 6448 | **Ibrahim Zadran** | Top-Order | T20I Only | 76.54 | +48.79 | 141.2 | 59.0 | 48.7 | 70.2 | 209b / 19m | [+19.1, +103.5] | 7/8 |
| 4 | 152 | **Ravindra Jadeja** | Finisher / Lower-Middle | IPL + T20I | 74.66 | +36.06 | 140.2 | 40.6 | 51.7 | 89.1 | 550b / 39m | [+14.6, +63.8] | 8/8 |
| 5 | 4369 | **Shai Hope** | Top-Order | IPL + T20I | 73.68 | +53.66 | 182.9 | 44.5 | 48.7 | 57.2 | 146b / 16m | [-2.2, +144.1] | 5/8 |
| 6 | 6460 | **Ayush Badoni** | Finisher / Lower-Middle | IPL Only | 73.24 | +31.15 | 152.5 | 33.0 | 50.4 | 88.4 | 497b / 33m | [+9.8, +61.9] | 8/8 |
| 7 | 6059 | **Ruturaj Gaikwad** | Opener | IPL + T20I | 72.96 | +35.93 | 155.7 | 49.2 | 61.3 | 57.7 | 158b / 15m | [-6.1, +88.9] | 4/8 |
| 8 | 6396 | **Tim David** | Finisher / Lower-Middle | IPL + T20I | 72.95 | +66.86 | 181.5 | 40.2 | 29.4 | 84.9 | 509b / 43m | [+43.2, +111.1] | 6/8 |
| 9 | 4260 | **Heinrich Klaasen** | Middle-Order | IPL + T20I | 72.47 | +31.46 | 156.8 | 33.4 | 64.7 | 90.1 | 532b / 34m | [+14.9, +59.4] | 7/8 |
| 10 | 6726 | **Romario Shepherd** | Finisher / Lower-Middle | IPL + T20I | 71.40 | +35.56 | 143.2 | 26.3 | 49.3 | 87.6 | 495b / 47m | [+11.0, +66.6] | 2/8 |

### Batter-by-Batter Analytical Justification
#### #1. Matthew Wade (`player_id=796` | Finisher / Lower-Middle | IPL + T20I)
- **Composite Score:** `80.51` (Performance `88.2`, Reliability `50.1`, Evidence `57.7`; in Top 10 under **8/8** tested specifications; `98.7%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +68.88` runs/100b) with above-cohort cross-innings stability (`Rel 50.1`) across `172` HIGH+EXTREME balls (`16` innings, `16` matches, seasons `2022, 2023, 2024`).
- **2. Pressure effectiveness:** EB pressure impact +68.9 runs/100b (raw +102.0); Pressure SR 169.2, avg 58.2; Boundary 22.1%, dot 26.7%; Extreme pressure: 52b @ SR 165.4.
- **3. Consistency:** Reliability score `50.1/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +51.5, +132.6 ]` runs/100b; 90% MC rank band `#1–#5` (Moderate Confidence (16 matches, 3 seasons; 99% MC Top-10 prob)).
- **5. Main limitation / risk:** Moderate sample (172 pressure balls across 16 matches).

#### #2. Naman Dhir (`player_id=37052` | Finisher / Lower-Middle | IPL + T20I)
- **Composite Score:** `77.83` (Performance `79.7`, Reliability `55.7`, Evidence `67.5`; in Top 10 under **8/8** tested specifications; `83.3%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +48.92` runs/100b) with above-cohort cross-innings stability (`Rel 55.7`) across `225` HIGH+EXTREME balls (`20` innings, `20` matches, seasons `2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +48.9 runs/100b (raw +66.8); Pressure SR 182.2, avg 37.3; Boundary 25.3%, dot 28.0%; Extreme pressure: 82b @ SR 192.7.
- **3. Consistency:** Reliability score `55.7/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +21.1, +110.0 ]` runs/100b; 90% MC rank band `#1–#21` (High Confidence (20 matches, 3 seasons; 83% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #1-#21 (90% MC interval).

#### #3. Ibrahim Zadran (`player_id=6448` | Top-Order | T20I Only)
- **Composite Score:** `76.54` (Performance `79.6`, Reliability `48.7`, Evidence `70.2`; in Top 10 under **7/8** tested specifications; `83.2%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +48.79` runs/100b) with above-cohort cross-innings stability (`Rel 48.7`) across `209` HIGH+EXTREME balls (`19` innings, `19` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +48.8 runs/100b (raw +67.6); Pressure SR 141.1, avg 59.0; Boundary 18.2%, dot 34.9%; Extreme pressure: 53b @ SR 147.2.
- **3. Consistency:** Reliability score `48.7/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +19.1, +103.5 ]` runs/100b; 90% MC rank band `#1–#20` (High Confidence (19 matches, 5 seasons; 83% MC Top-10 prob)).
- **5. Main limitation / risk:** T20I-only exposure (no IPL pressure data).

#### #4. Ravindra Jadeja (`player_id=152` | Finisher / Lower-Middle | IPL + T20I)
- **Composite Score:** `74.66` (Performance `72.0`, Reliability `51.7`, Evidence `89.1`; in Top 10 under **8/8** tested specifications; `74.5%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +36.06` runs/100b) with above-cohort cross-innings stability (`Rel 51.7`) across `550` HIGH+EXTREME balls (`39` innings, `39` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +36.1 runs/100b (raw +42.4); Pressure SR 140.2, avg 40.6; Boundary 14.9%, dot 26.2%; Extreme pressure: 188b @ SR 162.8.
- **3. Consistency:** Reliability score `51.7/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +14.6, +63.8 ]` runs/100b; 90% MC rank band `#2–#20` (High Confidence (39 matches, 5 seasons; 74% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #2-#20 (90% MC interval).

#### #5. Shai Hope (`player_id=4369` | Top-Order | IPL + T20I)
- **Composite Score:** `73.68` (Performance `82.0`, Reliability `48.7`, Evidence `57.2`; in Top 10 under **5/8** tested specifications; `56.9%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +53.66` runs/100b) with above-cohort cross-innings stability (`Rel 48.7`) across `146` HIGH+EXTREME balls (`16` innings, `16` matches, seasons `2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +53.7 runs/100b (raw +78.6); Pressure SR 182.9, avg 44.5; Boundary 26.0%, dot 26.0%.
- **3. Consistency:** Reliability score `48.7/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -2.2, +144.1 ]` runs/100b; 90% MC rank band `#2–#52` (Moderate Confidence (16 matches, 4 seasons; 57% MC Top-10 prob)).
- **5. Main limitation / risk:** Moderate sample (146 pressure balls across 16 matches); Wide 95% CI (-2.2 to +144.1 runs/100b); Limited EXTREME-tier exposure (0 balls).

#### #6. Ayush Badoni (`player_id=6460` | Finisher / Lower-Middle | IPL Only)
- **Composite Score:** `73.24` (Performance `68.7`, Reliability `50.4`, Evidence `88.4`; in Top 10 under **8/8** tested specifications; `61.2%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +31.15` runs/100b) with above-cohort cross-innings stability (`Rel 50.4`) across `497` HIGH+EXTREME balls (`33` innings, `33` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +31.1 runs/100b (raw +37.3); Pressure SR 152.5, avg 33.0; Boundary 19.1%, dot 29.0%; Extreme pressure: 131b @ SR 162.6.
- **3. Consistency:** Reliability score `50.4/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +9.8, +61.9 ]` runs/100b; 90% MC rank band `#2–#26` (High Exposure / Borderline Order (33 matches; 61% MC Top-10 prob)).
- **5. Main limitation / risk:** IPL-only exposure (no T20I pressure data).

#### #7. Ruturaj Gaikwad (`player_id=6059` | Opener | IPL + T20I)
- **Composite Score:** `72.96` (Performance `72.0`, Reliability `61.3`, Evidence `57.7`; in Top 10 under **4/8** tested specifications; `53.0%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +35.93` runs/100b) with above-cohort cross-innings stability (`Rel 61.3`) across `158` HIGH+EXTREME balls (`15` innings, `15` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +35.9 runs/100b (raw +52.3); Pressure SR 155.7, avg 49.2; Boundary 20.9%, dot 33.5%; Extreme pressure: 53b @ SR 118.9.
- **3. Consistency:** Reliability score `61.3/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -6.1, +88.9 ]` runs/100b; 90% MC rank band `#2–#35` (Moderate Confidence (15 matches, 5 seasons; 53% MC Top-10 prob)).
- **5. Main limitation / risk:** Moderate sample (158 pressure balls across 15 matches); Wide 95% CI (-6.1 to +88.9 runs/100b).

#### #8. Tim David (`player_id=6396` | Finisher / Lower-Middle | IPL + T20I)
- **Composite Score:** `72.95` (Performance `87.5`, Reliability `29.4`, Evidence `84.9`; in Top 10 under **6/8** tested specifications; `55.0%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +66.86` runs/100b) with above-cohort cross-innings stability (`Rel 29.4`) across `509` HIGH+EXTREME balls (`43` innings, `43` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +66.9 runs/100b (raw +78.8); Pressure SR 181.5, avg 40.2; Boundary 25.1%, dot 31.4%; Extreme pressure: 162b @ SR 161.1.
- **3. Consistency:** Reliability score `29.4/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +43.2, +111.1 ]` runs/100b; 90% MC rank band `#4–#22` (High Exposure / Borderline Order (43 matches; 55% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #4-#22 (90% MC interval).

#### #9. Heinrich Klaasen (`player_id=4260` | Middle-Order | IPL + T20I)
- **Composite Score:** `72.47` (Performance `68.9`, Reliability `64.7`, Evidence `90.1`; in Top 10 under **7/8** tested specifications; `52.3%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +31.46` runs/100b) with above-cohort cross-innings stability (`Rel 64.7`) across `532` HIGH+EXTREME balls (`34` innings, `34` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +31.5 runs/100b (raw +37.5); Pressure SR 156.8, avg 33.4; Boundary 19.7%, dot 26.9%; Extreme pressure: 118b @ SR 149.2.
- **3. Consistency:** Reliability score `64.7/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +14.9, +59.4 ]` runs/100b; 90% MC rank band `#3–#26` (High Exposure / Borderline Order (34 matches; 52% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #3-#26 (90% MC interval).

#### #10. Romario Shepherd (`player_id=6726` | Finisher / Lower-Middle | IPL + T20I)
- **Composite Score:** `71.40` (Performance `71.7`, Reliability `49.3`, Evidence `87.6`; in Top 10 under **2/8** tested specifications; `37.4%` MC Top-10 probability).
- **1. Why included:** Combines high context-adjusted pressure scoring (`EB +35.56` runs/100b) with above-cohort cross-innings stability (`Rel 49.3`) across `495` HIGH+EXTREME balls (`47` innings, `47` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +35.6 runs/100b (raw +40.7); Pressure SR 143.2, avg 26.3; Boundary 19.0%, dot 40.4%; Extreme pressure: 228b @ SR 162.7.
- **3. Consistency:** Reliability score `49.3/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +11.0, +66.6 ]` runs/100b; 90% MC rank band `#3–#38` (High Exposure / Borderline Order (47 matches; 37% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #3-#38 (90% MC interval).


## 18. Final Ordered Top 10 Bowlers Under Pressure
| Rank | Player ID | Player Name | Role | Comp | Score | EB Impact/24b | Press Econ | Press Wkts | Rel | Evid | Balls / Matches | 95% CI | Stability |
| :---: | ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :--- |
| 1 | 4658 | **Nasum Ahmed** | Powerplay Specialist (Spin) | T20I Only | 76.11 | +5.34 | 7.68 | 8 | 55.9 | 45.9 | 93b / 14m | [+2.5, +27.0] | 8/8 |
| 2 | 2876 | **Axar Patel** | Middle-Overs Enforcer (Spin) | IPL + T20I | 75.92 | +4.38 | 8.29 | 39 | 60.1 | 88.0 | 749b / 86m | [-0.6, +12.7] | 8/8 |
| 3 | 2985 | **Mark Wood** | All-Phase (Pace) | IPL + T20I | 74.10 | +4.59 | 9.12 | 10 | 62.1 | 43.3 | 100b / 11m | [+3.4, +31.8] | 8/8 |
| 4 | 4722 | **Rashid Khan** | Middle-Overs Enforcer (Spin) | IPL + T20I | 73.14 | +3.98 | 8.04 | 41 | 59.0 | 92.4 | 810b / 68m | [+1.8, +10.1] | 8/8 |
| 5 | 5379 | **Mark Adair** | Death Specialist (Pace) | T20I Only | 71.79 | +4.07 | 8.60 | 15 | 47.5 | 70.4 | 203b / 21m | [+1.4, +18.5] | 7/8 |
| 6 | 39657 | **Eshan Malinga** | All-Phase (Pace) | IPL + T20I | 71.12 | +3.42 | 9.38 | 20 | 54.6 | 73.4 | 311b / 30m | [-2.4, +15.9] | 7/8 |
| 7 | 305 | **Ravichandran Ashwin** | Middle-Overs Enforcer (Spin) | IPL + T20I | 70.13 | +3.72 | 7.94 | 27 | 46.0 | 88.0 | 560b / 42m | [-0.4, +12.8] | 4/8 |
| 8 | 4807 | **Joshua Little** | All-Phase (Pace) | IPL + T20I | 69.29 | +6.30 | 9.18 | 12 | 33.3 | 52.8 | 115b / 18m | [-2.9, +38.0] | 4/8 |
| 9 | 4900 | **Wanindu Hasaranga** | Middle-Overs Enforcer (Spin) | IPL + T20I | 68.61 | +5.16 | 8.59 | 37 | 35.7 | 85.8 | 545b / 52m | [+1.4, +17.0] | 3/8 |
| 10 | 8661 | **Matheesha Pathirana** | Death Specialist (Pace) | IPL + T20I | 68.33 | +4.81 | 9.62 | 23 | 35.4 | 82.4 | 270b / 31m | [-0.4, +18.9] | 5/8 |

### Bowler-by-Bowler Analytical Justification
#### #1. Nasum Ahmed (`player_id=4658` | Powerplay Specialist (Spin) | T20I Only)
- **Composite Score:** `76.11` (Performance `78.2`, Reliability `55.9`, Evidence `45.9`; in Top 10 under **8/8** tested specifications; `88.8%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +5.34` runs/24b) with repeatable spell consistency (`Rel 55.9`) across `93` HIGH+EXTREME legal balls (`14` innings, `14` matches, seasons `2022, 2023, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +5.34 runs/24b (raw +15.85); Pressure econ 7.68, 8 wkts (SR 11.6); RSAE +1.73/ov, dot 44.1%.
- **3. Consistency:** Reliability score `55.9/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +2.5, +27.0 ]` runs/24b; 90% MC rank band `#1–#15` (Moderate Confidence (14 matches, 4 seasons; 89% MC Top-10 prob)).
- **5. Main limitation / risk:** Moderate sample (93 pressure legal balls across 14 matches); Wide 95% CI (+2.5 to +27.0 runs/24b); Limited EXTREME-tier exposure (17 legal balls); T20I-only exposure (no IPL pressure data).

#### #2. Axar Patel (`player_id=2876` | Middle-Overs Enforcer (Spin) | IPL + T20I)
- **Composite Score:** `75.92` (Performance `73.8`, Reliability `60.1`, Evidence `88.0`; in Top 10 under **8/8** tested specifications; `79.0%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +4.38` runs/24b) with repeatable spell consistency (`Rel 60.1`) across `749` HIGH+EXTREME legal balls (`86` innings, `86` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +4.38 runs/24b (raw +5.76); Pressure econ 8.29, 39 wkts (SR 19.2); RSAE +1.29/ov, dot 31.8%; Extreme pressure: 254b @ econ 9.24.
- **3. Consistency:** Reliability score `60.1/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -0.6, +12.7 ]` runs/24b; 90% MC rank band `#1–#28` (High Confidence (86 matches, 5 seasons; 79% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #1-#28 (90% MC interval).

#### #3. Mark Wood (`player_id=2985` | All-Phase (Pace) | IPL + T20I)
- **Composite Score:** `74.10` (Performance `74.8`, Reliability `62.1`, Evidence `43.3`; in Top 10 under **8/8** tested specifications; `78.1%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +4.59` runs/24b) with repeatable spell consistency (`Rel 62.1`) across `100` HIGH+EXTREME legal balls (`11` innings, `11` matches, seasons `2022, 2023, 2024, 2025`).
- **2. Pressure effectiveness:** EB pressure impact +4.59 runs/24b (raw +15.95); Pressure econ 9.12, 10 wkts (SR 10.0); RSAE +0.75/ov, dot 47.0%; Extreme pressure: 34b @ econ 10.77.
- **3. Consistency:** Reliability score `62.1/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +3.4, +31.8 ]` runs/24b; 90% MC rank band `#1–#27` (Moderate Confidence (11 matches, 4 seasons; 78% MC Top-10 prob)).
- **5. Main limitation / risk:** Moderate sample (100 pressure legal balls across 11 matches); Wide 95% CI (+3.4 to +31.8 runs/24b).

#### #4. Rashid Khan (`player_id=4722` | Middle-Overs Enforcer (Spin) | IPL + T20I)
- **Composite Score:** `73.14` (Performance `71.8`, Reliability `59.0`, Evidence `92.4`; in Top 10 under **8/8** tested specifications; `75.2%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +3.98` runs/24b) with repeatable spell consistency (`Rel 59.0`) across `810` HIGH+EXTREME legal balls (`68` innings, `68` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +3.98 runs/24b (raw +5.55); Pressure econ 8.04, 41 wkts (SR 19.8); RSAE +1.45/ov, dot 32.0%; Extreme pressure: 263b @ econ 9.35.
- **3. Consistency:** Reliability score `59.0/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +1.8, +10.1 ]` runs/24b; 90% MC rank band `#1–#21` (High Confidence (68 matches, 5 seasons; 75% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #1-#21 (90% MC interval).

#### #5. Mark Adair (`player_id=5379` | Death Specialist (Pace) | T20I Only)
- **Composite Score:** `71.79` (Performance `72.2`, Reliability `47.5`, Evidence `70.4`; in Top 10 under **7/8** tested specifications; `63.2%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +4.07` runs/24b) with repeatable spell consistency (`Rel 47.5`) across `203` HIGH+EXTREME legal balls (`21` innings, `21` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +4.07 runs/24b (raw +9.27); Pressure econ 8.60, 15 wkts (SR 13.5); RSAE +1.35/ov, dot 38.4%; Extreme pressure: 59b @ econ 10.58.
- **3. Consistency:** Reliability score `47.5/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +1.4, +18.5 ]` runs/24b; 90% MC rank band `#2–#30` (High Exposure / Borderline Order (21 matches; 63% MC Top-10 prob)).
- **5. Main limitation / risk:** T20I-only exposure (no IPL pressure data).

#### #6. Eshan Malinga (`player_id=39657` | All-Phase (Pace) | IPL + T20I)
- **Composite Score:** `71.12` (Performance `68.8`, Reliability `54.6`, Evidence `73.4`; in Top 10 under **7/8** tested specifications; `54.7%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +3.42` runs/24b) with repeatable spell consistency (`Rel 54.6`) across `311` HIGH+EXTREME legal balls (`30` innings, `30` matches, seasons `2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +3.42 runs/24b (raw +6.42); Pressure econ 9.38, 20 wkts (SR 15.6); RSAE +0.88/ov, dot 35.7%; Extreme pressure: 141b @ econ 10.13.
- **3. Consistency:** Reliability score `54.6/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -2.4, +15.9 ]` runs/24b; 90% MC rank band `#1–#46` (High Exposure / Borderline Order (30 matches; 55% MC Top-10 prob)).
- **5. Main limitation / risk:** Only 2 season(s) represented.

#### #7. Ravichandran Ashwin (`player_id=305` | Middle-Overs Enforcer (Spin) | IPL + T20I)
- **Composite Score:** `70.13` (Performance `70.4`, Reliability `46.0`, Evidence `88.0`; in Top 10 under **4/8** tested specifications; `49.8%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +3.72` runs/24b) with repeatable spell consistency (`Rel 46.0`) across `560` HIGH+EXTREME legal balls (`42` innings, `42` matches, seasons `2022, 2023, 2024, 2025`).
- **2. Pressure effectiveness:** EB pressure impact +3.71 runs/24b (raw +6.06); Pressure econ 7.94, 27 wkts (SR 20.7); RSAE +1.41/ov, dot 30.7%; Extreme pressure: 165b @ econ 8.47.
- **3. Consistency:** Reliability score `46.0/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -0.4, +12.8 ]` runs/24b; 90% MC rank band `#2–#40` (High Exposure / Borderline Order (42 matches; 50% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #2-#40 (90% MC interval).

#### #8. Joshua Little (`player_id=4807` | All-Phase (Pace) | IPL + T20I)
- **Composite Score:** `69.29` (Performance `82.0`, Reliability `33.3`, Evidence `52.8`; in Top 10 under **4/8** tested specifications; `46.3%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +6.30` runs/24b) with repeatable spell consistency (`Rel 33.3`) across `115` HIGH+EXTREME legal balls (`18` innings, `18` matches, seasons `2022, 2023, 2024, 2025`).
- **2. Pressure effectiveness:** EB pressure impact +6.30 runs/24b (raw +16.08); Pressure econ 9.18, 12 wkts (SR 9.6); RSAE +0.44/ov, dot 35.7%; Extreme pressure: 32b @ econ 10.88.
- **3. Consistency:** Reliability score `33.3/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -2.9, +38.0 ]` runs/24b; 90% MC rank band `#3–#78` (Moderate Confidence (18 matches, 4 seasons; 46% MC Top-10 prob)).
- **5. Main limitation / risk:** Moderate sample (115 pressure legal balls across 18 matches); Wide 95% CI (-2.9 to +38.0 runs/24b).

#### #9. Wanindu Hasaranga (`player_id=4900` | Middle-Overs Enforcer (Spin) | IPL + T20I)
- **Composite Score:** `68.61` (Performance `77.4`, Reliability `35.7`, Evidence `85.8`; in Top 10 under **3/8** tested specifications; `37.8%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +5.16` runs/24b) with repeatable spell consistency (`Rel 35.7`) across `545` HIGH+EXTREME legal balls (`52` innings, `52` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +5.16 runs/24b (raw +7.89); Pressure econ 8.59, 37 wkts (SR 14.7); RSAE +0.74/ov, dot 31.2%; Extreme pressure: 186b @ econ 9.42.
- **3. Consistency:** Reliability score `35.7/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ +1.4, +17.0 ]` runs/24b; 90% MC rank band `#3–#61` (High Exposure / Borderline Order (52 matches; 38% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #3-#61 (90% MC interval).

#### #10. Matheesha Pathirana (`player_id=8661` | Death Specialist (Pace) | IPL + T20I)
- **Composite Score:** `68.33` (Performance `75.8`, Reliability `35.4`, Evidence `82.4`; in Top 10 under **5/8** tested specifications; `36.0%` MC Top-10 probability).
- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB +4.81` runs/24b) with repeatable spell consistency (`Rel 35.4`) across `270` HIGH+EXTREME legal balls (`31` innings, `31` matches, seasons `2022, 2023, 2024, 2025, 2026`).
- **2. Pressure effectiveness:** EB pressure impact +4.81 runs/24b (raw +9.05); Pressure econ 9.62, 23 wkts (SR 11.7); RSAE +0.31/ov, dot 35.9%; Extreme pressure: 114b @ econ 10.63.
- **3. Consistency:** Reliability score `35.4/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).
- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ -0.4, +18.9 ]` runs/24b; 90% MC rank band `#3–#62` (High Exposure / Borderline Order (31 matches; 36% MC Top-10 prob)).
- **5. Main limitation / risk:** Rank uncertainty spans #3-#62 (90% MC interval).


## 19. Important Limitations
1. **Overlapping Confidence Intervals:** Adjacent ranks (especially `#4–#10` in both lists) have overlapping match-clustered 95% CIs and Monte Carlo rank bands; small composite-score gaps (`< 1.5` pts) represent statistical near-ties rather than definitive separation.
2. **Moderate-Sample Qualifiers in Bowling:** `#1 Nasum Ahmed` (`93` legal balls, `14` matches), `#3 Mark Wood` (`100` balls, `11` matches), and `#8 Joshua Little` (`115` balls, `18` matches) satisfy the primary `90b / 10m` rule cleanly (and are NOT excluded merely for smaller volume), but carry wider CIs and drop out if the cutoff is tightened to `120–180` balls (`outputs/ranking_threshold_sensitivity.csv`).
3. **Observational, Non-Causal & Non-Predictive Scope:** Historical pressure metrics reflect past performance in observed deployment roles across 2022–2026 and do **not** guarantee future IPL 2027 outcomes (out-of-time cross-era Spearman persistence is `0.37` batting / `0.20` bowling due to T20 scoring inflation).
4. **Excluded Contexts & Venue Granularity:** `1,551` missing-DLS/corrupted-target deliveries, `38` Super Over deliveries, and `6,985` non-IPL T20 deliveries are excluded; baselines adjust for IPL vs. T20I × innings × phase × pressure tier rather than individual ground dimensions.
5. **Unstop Dropdown Verification Required Before Upload:** Exact player spelling/availability in the Unstop Round 1 dropdowns must be verified manually by the user prior to submitting.

## 20. Reproducibility Instructions
From `SupeRR_Selector/` in Windows PowerShell with `.venv` active:
```powershell
.\.venv\Scripts\Activate.ps1
python src\02_dataset_audit.py
python src\03_data_cleaning.py
python src\04_feature_engineering.py
python src\05_pressure_framework.py
python src\06_pressure_validation.py
python src\07_batting_performance.py
python src\08_bowling_performance.py
python src\09_player_reliability.py
python src\10_player_validation.py
python src\11_final_ranking_model.py
python src\12_ranking_robustness.py
python src\13_submission_package.py
pytest tests -v
```
