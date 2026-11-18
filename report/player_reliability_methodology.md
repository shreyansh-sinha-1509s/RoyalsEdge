# Phase 5 Player Reliability, Uncertainty & Eligibility Methodology — RR PERFORMANCE LAB

**Script:** `src/09_player_reliability.py`  
**Core Outputs:** `data/processed/player_batting_reliability.csv`, `data/processed/player_bowling_reliability.csv`, `data/processed/player_pressure_exposure.csv`, `data/processed/player_pressure_vs_nonpressure.csv`, `outputs/player_bootstrap_uncertainty.csv`, `outputs/minimum_exposure_sensitivity.csv`

---

## 1. Strict Three-Pillar Separation

To prevent conflating a hot 25-ball cameo with proven dependability — and to avoid rewarding raw career volume as "reliability" — Phase 5 evaluates three independent pillars:

| Pillar | What It Measures | Key Outputs | Volume Dependence |
| :--- | :--- | :--- | :--- |
| **1. Performance** | Format-adjusted effectiveness under HIGH+EXTREME pressure | `raw_pressure_impact`, `eb_pressure_impact`, `performance_score` (`0–100`) | Small-sample players shrunk toward context par via Empirical Bayes |
| **2. Reliability** | Repeatability & stability across pressure innings, conditions, and seasons | `reliability_score` (`0–100`) + 4 explicit stability sub-components | **Volume-free** (`corr(reliability, balls) = -0.136` batting, `+0.058` bowling) |
| **3. Evidence Strength** | Statistical confidence & exposure sufficiency | `evidence_tier`, `evidence_strength_score` (`0–100`), Match-Clustered Bootstrap 95% CIs | Directly tracks matches, balls, seasons, and CI width |

---

## 2. Empirical Exposure Distribution & Minimum Eligibility Rules

Examining `outputs/minimum_exposure_sensitivity.csv` across 6 candidate thresholds per discipline guided our tiered eligibility framework:

| Evidence Tier | Batting Rule (HIGH+EXTREME) | Batters (`n`) | Bowling Rule (HIGH+EXTREME) | Bowlers (`n`) | Analytical Treatment |
| :--- | :--- | ---: | :--- | ---: | :--- |
| **HIGH_CONFIDENCE** | `>= 150` BF, `>= 18` inn/matches, `>= 2` seasons | **87** | `>= 180` LB (30 ov), `>= 18` inn/matches, `>= 2` seasons | **96** | Highest statistical precision (median CI width `84.0` bat / `18.3` bowl) |
| **MODERATE_CONFIDENCE** *(Primary Cutoff)* | `>= 80` BF, `>= 10` inn/matches | **86** *(173 cumulative)* | `>= 90` LB (15 ov), `>= 10` inn/matches | **69** *(165 cumulative)* | Meets primary eligibility (`21.0%` of batters, `27.7%` of bowlers) |
| **LOW_EVIDENCE** | `>= 30` BF, `>= 5` inn/matches | **140** | `>= 36` LB (6 ov), `>= 5` inn/matches | **88** | Diagnostic reliability & CIs computed; explicitly flagged as low confidence |
| **INSUFFICIENT_EVIDENCE** | `< 30` BF or `< 5` inn/matches | **511** | `< 36` LB or `< 5` inn/matches | **343** | `reliability_score = NaN`, bootstrap CIs = `NaN` (never fabricated) |

**Sensitivity Trade-Off:** Tightening from `60 BF / 8 inn` (`215` batters, median CI width `120.7`) to **`80 BF / 10 inn`** (`173` batters, median CI width `111.9`) cuts extreme small-sample noise while preserving a rich multi-role pool (and `90 LB / 10 inn` gives `165` bowlers with median CI width `21.5`).

---

## 3. Empirical Bayes Shrinkage (Ball-Weighted, Match-Level Variance Decomposition)

Rather than choosing an arbitrary shrinkage constant, the prior strength $k = \hat{\sigma}^2_{\text{within}} / \hat{\tau}^2_{\text{between}}$ (in match units) is estimated directly via ball-weighted method-of-moments variance decomposition across match-level spells (using the delta method to project match-level `net_impact_runs` variance onto rate scale, avoiding 1-ball duck denominator explosions):

$$\hat{\theta}_{i}^{\text{EB}} = \frac{m_i}{m_i + k}\,\hat{\theta}_{i}^{\text{raw}} + \frac{k}{m_i + k}\,\mu_0$$

- **Batting Empirical Prior:** **$k = 8.65$ pressure matches** (mean EB shrinkage weight `0.695` among primary-eligible batters; `Spearman(raw, EB) = 0.9959`, MAD `8.69` runs/100b).
- **Bowling Empirical Prior:** **$k = 30.00$ pressure matches** (mean EB shrinkage weight `0.446` among primary-eligible bowlers; `Spearman(raw, EB) = 0.9873`, MAD `3.00` runs/24b).
- **Domain Interpretation:** T20 pressure bowling has substantially higher match-to-match variance relative to between-player skill than batting, so Empirical Bayes automatically applies stronger regression to the mean for small-sample bowlers.

---

## 4. Volume-Free Reliability Score (`0–100`)

Computed strictly for players with `>= 5` pressure innings using match/innings-level `net_impact_runs` (zero raw delivery-count terms):

$$\text{Reliability} = 100 \times \bigl(0.40\,R_{\text{Stab}} + 0.30\,R_{\text{Floor}} + 0.20\,R_{\text{Cross}} + 0.10\,R_{\text{Seas}}\bigr)$$

1. **$R_{\text{Stab}}$ (0.40) — Innings-to-Innings Stability:** $1 - \text{clip}(\text{IQR}_{\text{net\_impact\_runs}} / \text{Cohort } P_{90}\text{ IQR},\, 0,\, 1)$. Rewards repeatable innings outputs over volatile boom-or-bust swings.
2. **$R_{\text{Floor}}$ (0.30) — Floor Delivery Consistency:** Fraction of pressure innings achieving `net_impact_runs >= -2.0` (avoiding frequent collapses / expensive blow-ups).
3. **$R_{\text{Cross}}$ (0.20) — Cross-Condition Stability:** Stability between `HIGH` vs. `EXTREME` pressure tiers (`>= 15` balls each) and `Inn 1` vs. `Inn 2` (`>= 3` innings each); neutral `0.50` if exposed to only one condition.
4. **$R_{\text{Seas}}$ (0.10) — Cross-Season Stability:** Low inter-season standard deviation across seasons with `>= 3` pressure innings; neutral `0.50` if fewer than 2 qualifying seasons.

**Observed Reliability Distributions (Primary-Eligible Cohorts):**
- **Batting (`n = 173`):** Mean **`36.26`**, SD `10.06`, IQR `29.50–43.09`, `corr(reliability, balls) = -0.1365`, `corr(reliability, performance) = +0.1339`.
- **Bowling (`n = 165`):** Mean **`36.05`**, SD `10.30`, IQR `28.67–42.42`, `corr(reliability, balls) = +0.0577`, `corr(reliability, performance) = +0.2036`.

---

## 5. Match-Clustered Bootstrap Uncertainty & Observational Pressure vs. Non-Pressure Comparisons

Because Phase 4 confirmed high intra-innings delivery autocorrelation (`0.950` batting, `0.862` bowling), delivery-level resampling would severely understate uncertainty. All 95% confidence intervals in `outputs/player_bootstrap_uncertainty.csv` and `data/processed/player_pressure_vs_nonpressure.csv` use **match-clustered ratio bootstrap (`B = 500`, deterministic seed `42`, resampling whole `match_id` spells with replacement)**.

- **Bootstrap Convergence Check (`B = 500` vs. `B = 1000`):** CI width correlation = **`0.9742`** (batting, MAD `1.96` SR pts) and **`0.9778`** (bowling, MAD `0.12` econ pts).
- **Observational Pressure vs. Non-Pressure Summary (`outputs/pressure_vs_nonpressure_summary.csv`):**
  - *Batting (`119` players meeting primary eligibility on BOTH sides):* Mean pressure SR `143.30` vs. non-pressure SR `141.73` (`+1.57` raw diff; context-adjusted impact diff `+20.20` because surviving batters in the primary cohort outperform the tougher pressure baseline). Only **`13` of `119` (`10.92%`)** have a match-clustered 95% CI excluding `0` — highlighting how noisy raw pressure splits are without uncertainty quantification!
  - *Bowling (`165` players meeting primary eligibility on BOTH sides):* Mean pressure economy `9.83` vs. non-pressure economy `8.52` (`+1.31` RPO higher raw economy under pressure, while context-adjusted diff averages `-0.28` runs/24b). Only **`11` of `165` (`6.67%`)** have a 95% CI excluding `0`.
  - *Interpretation Note:* All comparisons are strictly **observational**, not causal estimates of psychological pressure effects (selection effects — such as death-over specialists bowling disproportionately under high pressure — also contribute).

