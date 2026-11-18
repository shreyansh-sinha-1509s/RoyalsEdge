# Phase 4 Completion Summary — Pressure Framework, Validation & Exposure Analysis

**Project:** SupeRR Selector Season 2 — RR PERFORMANCE LAB  
**Phase Status:** **PASS**  
**Scripts Executed:** `src/05_pressure_framework.py`, `src/06_pressure_validation.py`  
**Automated Test Suite (`pytest tests -v`):** **21 / 21 PASSED** (`13.79s`) — 14 Phase 3 tests + 7 Phase 4 tests  
**Scope Guardrail:** Strictly measures **match-situation difficulty before each delivery**. Zero player performance ratings, reliability scores, rankings, or dashboard pages have been created.

---

## 1. Final Pressure Framework Architecture

Three conceptually and mathematically distinct pre-delivery pressure indices (`0–100` scale) were built on the `193,988` primary regular deliveries (`837` matches, `1,652` innings; eligible IPL 2022–2026 + T20I 2022–2026; `0` Super Over rows; `0` excluded competition rows):

1. **`chase_pressure_index`** *(Innings 2 batting difficulty — `91,149` valid, `785` unavailable)*
2. **`first_innings_pressure_index`** *(Innings 1 batting difficulty vs. format baseline — `101,288` valid, `766` unavailable)*
3. **`bowling_pressure_index`** *(Innings 1 & 2 bowling difficulty — `192,437` valid, `1,551` unavailable)*

*(Full mathematical specification in `report/pressure_framework_methodology.md`.)*

---

## 2. Formula & Component Definitions (Recommended Primary: Model C)

- **Chase (`chase_pressure_index`):** `0.34` Format-and-Stage RRR Demand + `0.24` Wicket Scarcity (convex absolute + excess vs. LOMO stage baseline) + `0.14` Acceleration Gap (`RRR - CRR`) + `0.12` Endgame Urgency + `0.16` Interaction (`RRR × Wickets`).
- **First Innings (`first_innings_pressure_index`):** `0.30` Progress-Weighted Score Deficit vs. LOMO Par + `0.30` Wicket Collapse Severity + `0.15` CRR Lag + `0.10` Late-Innings Stage Urgency + `0.15` Interaction (`Deficit × Wickets`).
- **Bowling (`bowling_pressure_index`):**
  - *Innings 2 (Defending):* `0.30` Chase Closeness (Gaussian peak around format/stage par RPO) + `0.22` Batting Wickets in Hand + `0.18` Empirical Phase Scoring Hazard + `0.15` Pre-Delivery Striker Threat + `0.15` Endgame Leverage.
  - *Innings 1 (Containing):* `0.28` Opponent Ahead-of-Par Surge + `0.22` Batting Wickets in Hand + `0.20` Empirical Phase Scoring Hazard + `0.15` Pre-Delivery Striker Threat + `0.15` Interaction (`Surge × Wickets in Hand`).

---

## 3. Normalization Methodology

- **Leave-One-Match-Out (LOMO) Format-Specific Baselines:** Computed separately for `IPL` and `T20I` across 21 normalized innings-progress bins, excluding the current match from every denominator.
- **Robust Logistic Scaling:** Standardized deviations using IQR-derived spread ($\hat{\sigma} = \max(0.7413 \cdot \text{IQR}, 8.0)$) passed through smooth sigmoid functions $\sigma(z)$ to prevent extreme tail distortions (e.g., `RRR > 36` in dead chases) while retaining smooth monotonicity.

---

## 4. Pressure Category Thresholds

Empirically calibrated against `~p35 / p70 / p90` (after proving equal-interval `25/50/75`, shared fixed `35/55/72`, and quartile `p25/p50/p75` distort cross-framework balance):

- **Chase:** `< 32` LOW | `32 – < 50` MODERATE | `50 – < 74` HIGH | `>= 74` EXTREME
- **First Innings:** `< 30` LOW | `30 – < 45` MODERATE | `45 – < 61` HIGH | `>= 61` EXTREME
- **Bowling:** `< 47` LOW | `47 – < 60` MODERATE | `60 – < 68` HIGH | `>= 68` EXTREME

Continuous `0–100` scores are retained alongside all categorical labels.

---

## 5. Actual Pressure Distribution & Exposure (`outputs/pressure_level_summary.csv`)

| Framework | Valid Balls | Mean (SD) | LOW (%) | MODERATE (%) | HIGH (%) | EXTREME (%) | EXTREME Unique Innings / Matches | UNAVAILABLE |
| :--- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: |
| **Chase (Inn 2)** | 91,149 | 42.68 (20.37) | 31,178 (34.21%) | 32,469 (35.62%) | 18,353 (20.14%) | 9,149 (10.04%) | 410 inn / 410 matches | 785 |
| **First Innings (Inn 1)** | 101,288 | 37.90 (15.93) | 36,948 (36.48%) | 33,103 (32.68%) | 21,485 (21.21%) | 9,752 (9.63%) | 326 inn / 326 matches | 766 |
| **Batting Combined** | 192,437 | 40.16 (18.32) | 68,126 (35.40%) | 65,572 (34.07%) | 39,838 (20.70%) | 18,901 (9.82%) | 736 inn / 650 matches | 1,551 |
| **Bowling (Inn 1+2)** | 192,437 | 51.46 (13.63) | 67,590 (35.12%) | 67,338 (34.99%) | 39,183 (20.36%) | 18,326 (9.52%) | 797 inn / 593 matches | 1,551 |

*Exposure correlation note:* High lag-1 autocorrelation (`0.950` batting, `0.862` bowling) confirms deliveries within an innings are not independent (`22.3–29.9` extreme balls per exposed innings). Phase 5 will evaluate reliability at both delivery and innings/match granularity.

---

## 6. IPL vs. T20I Differences

- **Raw Scoring Environment:** IPL averages `+0.55` to `+0.88` RPO higher than T20I across all phases (`11.04` vs `10.26` in Inn 1 Death; `9.08` vs `8.20` in Inn 1 Powerplay).
- **Model C Batting Calibration:** Chase mean `42.04` (IPL) vs `43.22` (T20I); First-Innings mean `37.54` (IPL) vs `38.19` (T20I) — cleanly aligned across formats (HIGH+EXTREME share: Chase `28.79%` IPL vs `31.35%` T20I; Inn 1 `30.45%` IPL vs `31.16%` T20I).
- **Bowling Environment Reality:** IPL bowling pressure averages **`54.10`** vs T20I **`49.28`** (`+4.82` pts; `38.18%` vs `22.99%` HIGH+EXTREME), genuinely reflecting IPL's flatter tracks, deeper Impact Player batting lineups, and higher Death/Powerplay scoring hazards.

---

## 7. First Innings vs. Chase Differences

- Chase pressure has a higher mean (`42.68` vs `37.90`), wider variance (`SD 20.37` vs `15.93`), and heavier upper tail (`p90 = 74.07` vs `60.65`) driven by explicit target/RRR escalation in overs 15–20.
- First-innings pressure rises primarily on early Powerplay collapses (`>=3` wkts down: mean `53.43`) and sustained scoring deficits relative to format par.
- Calibrated framework-specific thresholds ensure both innings contribute balanced `~30%` HIGH+EXTREME shares without letting 2nd-innings chases drown out 1st-innings rescue knocks.

---

## 8. Model Comparison Results (`outputs/pressure_model_comparison.csv`)

- **Model A (Rule-Based Fixed):** High rank correlation with Model C (`0.981` Chase, `0.936` Inn 1, `0.926` Bowling), but suffers `-5.01` pt IPL bias in Inn 1 due to fixed 8.5 RPO par and hard clipping plateaus.
- **Model B (Empirical Percentile ECDF):** Good rank alignment (`0.961` Chase, `0.921` Inn 1, `0.860` Bowling), but introduces `-6.83` pt IPL bias in Inn 1 (pooled ranks ignore format scoring gap) and compresses tail extremes.
- **Model C (Context-Normalized LOMO):** Eliminates cross-format batting bias (`-0.66` pt Inn 1 gap), retains smooth monotonic behavior, preserves true IPL bowling difficulty, and achieves `2.01–2.16` yearly spread on Chase & Bowling.

---

## 9. Sensitivity Analysis (`outputs/pressure_sensitivity_analysis.csv`)

- Across all weight perturbations (`+10%` Primary, `+10%` Wickets, No Interaction, Equal 20% weights), Spearman rank correlation against Baseline Model C stays **`0.9938–0.9993`** (Chase), **`0.9893–0.9995`** (First Innings), and **`0.9729–0.9906`** (Bowling).
- Threshold shifts of `±3` points retain `95.7%–96.3%` (Chase), `94.4%–94.8%` (First Innings), and `89.5%–91.3%` (Bowling) High+Extreme agreement.

---

## 10. Leakage Testing Results (`outputs/pressure_leakage_checks.csv`)

All **6 / 6** anti-leakage checks **PASSED**: chronological & monotonic pre-delivery state across all `1,652` innings; Ball-1 zero pre-state (`1,652/1,652`); Ball-1 outcome invariance (`diff = 0.0103` pts); zero match-result columns in `05_pressure_framework.py`; all `1,551` missing-DLS / corrupted-target (`48610`) deliveries marked `UNAVAILABLE`; intra-innings autocorrelation audited (`0.950` bat, `0.862` bowl).

---

## 11. Known Limitations

1. **Multi-Season Scoring Drift (2022–2026):** Using pooled 2022–2026 format baselines causes 1st-innings mean pressure to drift gently downward from `39.97` (2022) to `34.70` (2026) as T20 scoring rates inflate over time (season-specific baselines can be tested as a Phase 5 robustness check).
2. **Venue & Pitch Effects Absent:** `matches.csv` provides `venue_id` and `venue_country` without pitch/boundary metadata; par trajectories are format-level (`IPL` vs `T20I`) rather than venue-adjusted (small per-venue sample sizes prevent reliable LOMO per-venue trajectory estimation for most T20I grounds).
3. **Unavailable Contexts (`0.80%`):** `1,539` missing-revised-overs deliveries and `12` corrupted-target deliveries (`48610`) cannot receive pressure scores without fabricating metadata.
4. **Match Importance / Knockout Multiplier Deferred:** Tournament stage (`knock_out`, `Final`, `Playoff`) is preserved in `clean_matches.csv` for Phase 5 sensitivity/context weighting rather than conflated into ball-level match-state difficulty.

---

## 12. Recommended Primary Model

**Model C (Context-Normalized LOMO IPL/T20I Model)** is recommended as the primary pressure framework for Phase 5 player evaluation, with **Model A** and **Model B** retained in `data/processed/pressure_deliveries.csv` for Phase 5 ranking robustness checks.

---

## 13. Phase 4 Assessment: **PASS**

All required processed datasets (`3`), audit/validation CSVs (`9`), analytical charts (`9`, `RR PERFORMANCE LAB` styled), notebook (`notebooks/04_pressure_analysis.ipynb`), methodology/validation reports (`3`), and automated tests (`21/21 PASSED`) are complete and verified. Ready for review before **Phase 5 (Player Performance & Reliability Modeling)**.

