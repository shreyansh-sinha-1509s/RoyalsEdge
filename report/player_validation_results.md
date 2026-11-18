# Phase 5 Player Validation, Robustness & Temporal Analysis Report

**Validation Script:** `src/10_player_validation.py`  
**Automated Test Suite (`pytest tests -v`):** **28 / 28 PASSED** (`15.96s`) — including 7 new Phase 5 tests in `tests/test_player_performance.py`  
**Validation Artifacts:** `outputs/player_validation_results.csv`, `outputs/player_model_robustness.csv`, `outputs/player_temporal_validation.csv`, and 10 charts (`outputs/charts/10_*.png` through `19_*.png`).

---

## 1. Automated Integrity & Anti-Leakage Checks (`12 / 12 PASS`)

| Check | Status | Verified Value | Details |
| :--- | :---: | :--- | :--- |
| `01_player_ids_map_to_player_master` | **PASS** | `bat=824, bowl=596` | 100% of analyzed `player_id`s map cleanly to `player_master.csv` |
| `02_no_shared_name_merging` | **PASS** | `True` | `Abdul Samad` (`6922`/`7446`), `Haider Ali` (`7338`/`28756`), `Rashid Khan` (`4722`) kept strictly separate |
| `03_no_excluded_competitions` | **PASS** | `True` | `0` deliveries from `comp_id` `2670` or `3289` |
| `04_no_super_over_deliveries` | **PASS** | `True` | `0` Super Over rows (`innings >= 3`) |
| `05_no_invalid_player_ball_assignments` | **PASS** | `True` | `0` rows with `striker_id == non_striker_id` or `striker_id == bowler_id` |
| `06_batting_balls_faced_conservation_no_wides` | **PASS** | `185,040 == 185,040` | Exact conservation across `player_batting_performance`, breakdown table, and source (no wides, no duplicates) |
| `07_bowling_legal_balls_conservation` | **PASS** | `184,222 == 184,222` | Exact conservation across `player_bowling_performance`, breakdown table, and source |
| `08_bowler_wicket_attribution_exact` | **PASS** | `9,802 == 9,802` | Strictly bowler-credited dismissals only (`0` run-outs or retired outs) |
| `09_unavailable_not_treated_as_low_pressure` | **PASS** | `unavail=1,551` | All `1,551` UNAVAILABLE deliveries excluded from LOW/MOD/HIGH/EXTREME slices |
| `10_reliability_bounds_and_non_volume_independence` | **PASS** | `bat=-0.136, bowl=+0.058` | All reliability scores strictly in `[0, 100]` with near-zero volume correlation |
| `11_insufficient_evidence_never_fabricated` | **PASS** | `bat=511, bowl=343` | 100% of `INSUFFICIENT_EVIDENCE` players have `NaN` reliability |
| `12_temporal_out_of_time_validation_completed` | **PASS** | `qual_bat=94, qual_bowl=96` | Out-of-time Early (`2022–23`) vs. Late (`2024–26`) validation completed |

---

## 2. Cross-Model & Threshold Robustness (`outputs/player_model_robustness.csv`)

| Discipline | Robustness Comparison | Metric | Players | Spearman $r$ | Pearson $r$ | MAD | Top-20 Cohort Overlap |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| **Batting** | Model A Top-30% vs. Model C | Pressure SR | 173 | **0.9619** | 0.9680 | 3.65 | 75.0% |
| **Batting** | Model B Top-30% vs. Model C | Pressure SR | 173 | **0.9469** | 0.9611 | 4.13 | 85.0% |
| **Batting** | Threshold −3 pts vs. Model C | Pressure SR | 173 | **0.9587** | 0.9693 | 3.37 | 95.0% |
| **Batting** | Threshold +3 pts vs. Model C | Pressure SR | 173 | **0.9572** | 0.9650 | 3.99 | 90.0% |
| **Batting** | Raw vs. EB-Shrunk Impact | Net Impact / 100b | 173 | **0.9959** | 0.9933 | 8.69 | 75.0% |
| **Bowling** | Model A Top-30% vs. Model C | Pressure Economy | 165 | **0.8860** | 0.8845 | 0.44 | 65.0% |
| **Bowling** | Model B Top-30% vs. Model C | Pressure Economy | 165 | **0.7976** | 0.7854 | 0.58 | 55.0% |
| **Bowling** | Threshold −3 pts vs. Model C | Pressure Economy | 165 | **0.9472** | 0.9309 | 0.35 | 80.0% |
| **Bowling** | Threshold +3 pts vs. Model C | Pressure Economy | 165 | **0.8797** | 0.8935 | 0.56 | 80.0% |
| **Bowling** | Raw vs. EB-Shrunk Impact | Net Impact / 24b | 165 | **0.9873** | 0.9702 | 3.00 | 75.0% |

**Why Model B Diverges More for Bowling (`r = 0.7976`, `55%` Top-20 overlap):** As established in Phase 4, pooled-ECDF Model B ignores the `+0.78 RPO` IPL vs. T20I scoring gap, shifting which IPL vs. T20I spells enter the top-30% pressure slice. Model C's format-specific LOMO baselines align batting fairly while preserving IPL's true bowling difficulty — explaining why Model C vs. threshold shifts stays highly stable (`r = 0.88–0.96`, `80–95%` Top-20 overlap).

---

## 3. Out-of-Time Temporal Validation (`outputs/player_temporal_validation.csv`)

Comparing **Early Era (`2022–2023`)** against **Late Era (`2024–2026`)** using strictly historical early-era deliveries (`>= 40` pressure balls and `>= 5` pressure matches in *both* eras required):

| Discipline | Qualifying Multi-Era Players | Insufficient Seasonal Coverage | Stable Across Eras | Materially Changed | Early Era Mean | Late Era Mean | Cross-Era Spearman $r$ | Era MAD |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Batting** *(Pressure SR; ±20 tol)* | **94** | 730 | **54** (57.4%) | 40 (42.6%) | 137.62 | 137.03 | **0.3729** | 19.34 |
| **Bowling** *(Pressure Econ; ±1.25 tol)* | **96** | 500 | **37** (38.5%) | 59 (61.5%) | 9.04 | 10.27 | **0.2023** | 1.76 |

**Key Takeaway:** Cross-era persistence is modest for batting (`r = 0.37`) and low for raw bowling economy (`r = 0.20`, heavily impacted by the **`+1.23 RPO`** league-wide scoring inflation between 2022–23 and 2024–26). This confirms why **Empirical Bayes shrinkage, match-clustered confidence intervals, and multi-season exposure checks** are indispensable before Phase 6 final rankings.

