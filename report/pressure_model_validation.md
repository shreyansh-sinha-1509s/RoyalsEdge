# Phase 4 Pressure Model Validation Report — RR PERFORMANCE LAB

**Validation Script:** `src/06_pressure_validation.py`  
**Automated Test Suite:** `tests/test_pressure_framework.py` (+ Phase 3 test suite: **21 / 21 PASSED**)  
**Validation Artifacts:** `outputs/pressure_validation_results.csv`, `outputs/pressure_leakage_checks.csv`, `outputs/pressure_model_comparison.csv`, `outputs/pressure_threshold_analysis.csv`, `outputs/pressure_sensitivity_analysis.csv`, `outputs/pressure_exposure_summary.csv`, and 9 charts in `outputs/charts/`.

---

## 1. Executive Validation Scorecard

| Validation Pillar | Checks Run | Passed | Failed | Key Verified Evidence |
| :--- | :---: | :---: | :---: | :--- |
| **A. Face Validity & Distinctness** | 4 | **4** | 0 | Hard chase `82.77` vs Easy chase `14.41`; Batting–Bowling corr `-0.866` (Inn 1) / `-0.596` (Inn 2) |
| **B. Distribution Bounds** | 1 | **1** | 0 | All 3 primary indices & all 9 alternative model columns strictly within `[0, 100]` |
| **C. IPL vs. T20I Comparison** | 1 | **1** | 0 | Batting calibrated (`-1.18` Chase, `-0.66` Inn 1); Bowling reflects IPL hazard (`+4.82`) |
| **D. Weight & Threshold Sensitivity** | 1 | **1** | 0 | Minimum Spearman rank correlation across all weight perturbations = **`0.9729`** |
| **E. Boundary Tests (All 10 Required)** | 10 | **10** | 0 | 0 wkts `29.13`, 9 wkts `93.60`, RRR≥18 `84.68`, RRR≤5 `13.99`, 0 Super Overs |
| **F. Leakage & Ordering Checks** | 6 | **6** | 0 | 1,652/1,652 monotonic innings, Ball-1 outcome invariance diff `0.010`, 0 result cols used |
| **G. Temporal Stability (2022–2026)** | 1 | **1** | 0 | Max yearly mean spread `5.26` pts (Chase `2.16`, Bowling `2.01`, Inn 1 `5.26` reflecting T20 scoring inflation) |
| **Total Automated Validation** | **24** | **24** | **0** | **100% PASS** |

---

## 2. Face Validity & Boundary Test Results (Actual Values)

| Scenario / Boundary Test | Observed Value | Verdict | Interpretation |
| :--- | :--- | :---: | :--- |
| Hard chase (`RRR >= 14`, `>= 5 wkts down`) | Mean **`82.77`** | PASS | Firmly inside `EXTREME PRESSURE` (`>= 74`) |
| Easy chase (`RRR <= 6`, `<= 2 wkts down`) | Mean **`14.41`** | PASS | Firmly inside `LOW PRESSURE` (`< 32`) |
| Inn 1 Powerplay collapse (`>= 3 wkts down`) | Mean **`53.43`** | PASS | Inside `HIGH PRESSURE` (`>= 45`) vs cruising **`20.92`** (`+32.51` separation) |
| Bowling tight Death chase (`RRR 8–13`, `>= 5` wkts left) | Mean **`70.34`** | PASS | Inside `EXTREME PRESSURE` (`>= 68`) vs dead chase **`19.44`** (`+50.90` separation) |
| Zero wickets lost (Chase) | Mean **`29.13`** | PASS | `LOW PRESSURE` |
| Nine wickets lost (Chase, `n = 1,488`) | Mean **`93.60`** | PASS | Peak `EXTREME PRESSURE`, bounded `<= 100` |
| Very high RRR (`>= 18 RPO`) | Mean **`84.68`** | PASS | Smooth logistic saturation prevents tail blow-up |
| Very low RRR (`<= 5 RPO`) | Mean **`13.99`** | PASS | Firm `LOW PRESSURE` |
| Few balls remaining (`<= 12` legal balls) | Mean **`67.15`** | PASS | `+34.04` pts above opening overs (`>= 100` balls: **`33.11`**) |
| First delivery of innings (`innings_ball_num == 1`) | Inn 1 **`24.65`**, Inn 2 **`30.86`** | PASS | Starts calmly in `LOW PRESSURE` without false panic |
| Missing target / DLS missing `revised_overs` | **`1,551`** rows `UNAVAILABLE` | PASS | `1,539` missing-revised-overs + `12` corrupted-target (`48610`) never fabricated |
| Verified revised-overs DLS chases | **`1,629`** valid rows | PASS | Properly scaled to exact `revised_balls` and `revised_target` |
| Super Overs in primary dataset | **`0`** rows | PASS | Strictly separated into `data/processed/super_over_deliveries.csv` |

---

## 3. Model Comparison (Model A vs. Model B vs. Model C)

| Framework | Model | Mean | SD | IPL Mean | T20I Mean | IPL − T20I | Spearman vs. C | Top-30% Agreement w/ C | Yearly Spread (2022–26) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Chase (Inn 2)** | Model A (Rule-Based) | 29.75 | 24.95 | 30.26 | 29.31 | +0.94 | 0.9810 | 96.86% | 2.19 |
| **Chase (Inn 2)** | Model B (Percentile) | 46.79 | 23.85 | 47.55 | 46.14 | +1.41 | 0.9610 | 96.67% | 2.83 |
| **Chase (Inn 2)** | **Model C (Primary)** | **42.68** | **20.37** | **42.04** | **43.22** | **−1.18** | **1.0000** | **100.00%** | **2.16** |
| **First Inn (Inn 1)** | Model A (Rule-Based) | 21.75 | 18.42 | 18.99 | 24.00 | **−5.01** | 0.9362 | 93.77% | 3.03 |
| **First Inn (Inn 1)** | Model B (Percentile) | 46.80 | 21.37 | 43.04 | 49.87 | **−6.83** | 0.9207 | 92.85% | 4.25 |
| **First Inn (Inn 1)** | **Model C (Primary)** | **37.90** | **15.93** | **37.54** | **38.19** | **−0.66** | **1.0000** | **100.00%** | **5.26** |
| **Bowling (Inn 1+2)** | Model A (Rule-Based) | 52.02 | 16.22 | 54.24 | 50.17 | +4.07 | 0.9261 | 88.56% | 3.22 |
| **Bowling (Inn 1+2)** | Model B (Percentile) | 46.57 | 15.44 | 48.71 | 44.80 | +3.91 | 0.8597 | 83.61% | 2.26 |
| **Bowling (Inn 1+2)** | **Model C (Primary)** | **51.46** | **13.63** | **54.10** | **49.28** | **+4.82** | **1.0000** | **100.00%** | **2.01** |

**Why Model C Wins:** Models A and B exhibit severe `-5.01` to `-6.83` pt structural bias against IPL in the 1st innings because they ignore IPL's `+0.78 to +0.88` RPO higher par environment. Model C reduces that format distortion by ~10× (`-0.66` pts) while preserving high rank-order agreement with Model A (`0.926–0.981`) and reflecting the true higher bowling difficulty in IPL (`+4.82` pts).

---

## 4. Sensitivity Analysis Summary

Across all 3 frameworks (`outputs/pressure_sensitivity_analysis.csv`):
- **Chase:** Weight perturbations (`+10%` RRR, `+10%` Wickets, No Interaction, Equal 20%) retain **`Spearman = 0.9938 – 0.9993`**, MAD `1.43 – 3.99` pts, and `92.65% – 97.78%` High+Extreme agreement. Shifting thresholds `±3` pts keeps `95.74% – 96.27%` agreement.
- **First Innings:** Weight perturbations retain **`Spearman = 0.9893 – 0.9995`**, MAD `1.19 – 3.82` pts, and `92.25% – 97.67%` High+Extreme agreement. Threshold shifts `±3` pts keep `94.39% – 94.81%` agreement.
- **Bowling:** Weight perturbations retain **`Spearman = 0.9729 – 0.9906`**, MAD `2.23 – 3.47` pts, and `87.00% – 91.27%` High+Extreme agreement.

---

## 5. Leakage Testing & Intra-Innings Autocorrelation Findings

1. **Chronological & Monotonic Invariants:** Verified across all `1,652` primary innings (`PASS`).
2. **Ball-1 Zero Pre-State:** All `1,652` innings start at `0` runs, `0` wickets, `0` legal balls (`PASS`).
3. **Current-Ball Outcome Invariance:** On IPL Inn 1 Ball 1, mean pressure before a dot ball (`24.6748`) vs. before a boundary (`24.6645`) differs by only `0.0103` pts (pure LOMO match sampling noise — confirming zero current-ball outcome leakage).
4. **Source Code Guard:** Neither `win_team_id` nor `match_completion_classification` appears in `src/05_pressure_framework.py`.
5. **Intra-Innings Delivery Correlation (`bat_ac1 = 0.950`, `bowl_ac1 = 0.862`):** Consecutive balls in the same innings are strongly correlated (averaging `25.7` EXTREME batting balls per exposed innings and `23.0` EXTREME bowling balls per exposed innings). **Critical Phase 5 Design Implication:** Player eligibility and reliability testing in Phase 5 MUST enforce minimum **unique innings / unique matches** under pressure (and cluster/innings-level consistency metrics), never raw ball counts alone.

---

## 6. Temporal Validation (2022–2026)

| Season Year | Chase Mean | First-Innings Mean | Bowling Mean | Observation |
| :---: | ---: | ---: | ---: | :--- |
| **2022** | 43.74 | 39.97 | 50.74 | Baseline post-2022 scoring era |
| **2023** | 42.92 | 38.43 | 51.79 | Impact Player introduced in IPL 2023 |
| **2024** | 43.00 | 38.40 | 51.04 | Stable chase & bowling distributions |
| **2025** | 41.58 | 37.48 | 51.35 | Slightly higher 1st-innings scoring |
| **2026** | 42.09 | 34.70 | 52.75 | Continued T20 scoring inflation lowers Inn 1 par-deficit and raises Bowling difficulty |

