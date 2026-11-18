# Phase 4 Pressure Framework Methodology — RR PERFORMANCE LAB

**Project:** SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Analytics  
**Implementation:** `src/05_pressure_framework.py`  
**Analytical Scope:** `193,988` primary regular deliveries (`837` matches, `1,652` innings) across eligible **IPL (2022–2026)** and **T20I (2022–2026)** competitions. Super Overs (`38` deliveries) and excluded non-IPL T20 competitions (`comp_id` `2670`, `3289`; `6,985` deliveries) remain separated.

---

## 1. Foundational Conceptual Separation

To prevent circularity and ensure methodological transparency per the official Round 1 Problem Statement, this project strictly separates three distinct quantities:

1. **Pressure (Phase 4 — This Document):** The objective difficulty of the match situation *strictly before* the delivery is bowled.
2. **Performance (Phase 5 — Upcoming):** The batter's or bowler's realized delivery-level response relative to baseline expectations.
3. **Reliability (Phase 5 — Upcoming):** The cross-match and cross-innings consistency of a player's response under sustained pressure exposure.

**Strict Anti-Leakage Principle:** No current-delivery runs, current-delivery wickets, final innings totals (for the current innings), future player outcomes, or completed match results (`win_team_id`, `result`) ever enter any pressure index.

---

## 2. Empirical Motivation: Why Separate IPL & T20I Baselines Are Mandatory

Pre-modeling empirical analysis on `data/processed/clean_deliveries.csv` established a substantial structural scoring gap between IPL and T20I:

| Competition | Inn 1 Powerplay RPO | Inn 1 Middle RPO | Inn 1 Death RPO | Median Inn 1 Score (After 15 Ov) | Median Inn 2 RRR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **IPL (2022–2026)** | 9.08 | 8.65 | 11.04 | 132 (3.81 wkts) | 10.08 |
| **T20I (2022–2026)** | 8.20 | 8.10 | 10.26 | 119 (4.22 wkts) | 9.33 |
| **IPL − T20I Gap** | **+0.88** | **+0.55** | **+0.78** | **+13 runs** | **+0.75** |

Treating IPL and T20I with a single global par rate artificially deflates IPL first-innings batting pressure by **5.0–6.8 points** (confirmed empirically in Model A and Model B). Therefore, the recommended primary model (**Model C**) constructs **Leave-One-Match-Out (LOMO) competition-specific baselines** separately for `IPL` and `T20I` at every normalized progress bin (`progress_bin = floor(legal_balls_before / scheduled_legal_balls * 20)`). Because every match is excluded from its own baseline denominator, zero within-match leakage occurs.

---

## 3. Recommended Primary Model (Model C): Three Distinct Frameworks (0–100 Scale)

All continuous sub-components are mapped smoothly onto `[0, 1]` using logistic scaling $\sigma(z) = \frac{1}{1 + e^{-z}}$ (with robust IQR-derived spread $\hat{\sigma} = \max(0.7413 \cdot \text{IQR}, 8.0)$) or bounded convex resource curves, then combined linearly and scaled to `[0, 100]`.

### A. Second-Innings Chase Pressure (`chase_pressure_index`, Innings 2 Only)

Measures batting difficulty for the chasing team strictly before each delivery:

$$\text{Chase Pressure} = 100 \times \bigl(0.34\,C_{\text{RRR}} + 0.24\,C_{\text{Wkt}} + 0.14\,C_{\text{Accel}} + 0.12\,C_{\text{Urg}} + 0.16\,C_{\text{Int}}\bigr)$$

- **$C_{\text{RRR}}$ (Weight `0.34`, $r = 0.912$):** Format-and-stage-adjusted Required Run Rate demand:
  $$0.65\,\sigma\!\left(\frac{\text{RRR} - \text{ExpRemRPO}_{\text{LOMO}}}{2.75}\right) + 0.35\,\sigma\!\left(\frac{\text{RRR} - \text{FormatParRPO}_{\text{LOMO}}}{3.0}\right)$$
- **$C_{\text{Wkt}}$ (Weight `0.24`, $r = 0.790$):** Convex absolute wicket scarcity + excess wickets lost vs. stage baseline:
  $$0.60\left(\frac{\text{wickets\_before}}{9}\right)^{1.30} + 0.40\,\sigma\!\left(\frac{\text{wickets\_before} - \text{ExpWkts}_{\text{LOMO}}}{1.50}\right)$$
- **$C_{\text{Accel}}$ (Weight `0.14`, $r = 0.845$):** Acceleration gap $\sigma\bigl((\text{RRR} - \text{CRR} - 0.5)/3.0\bigr)$ (falls back to $C_{\text{RRR}}$ on ball 1 when CRR is undefined).
- **$C_{\text{Urg}}$ (Weight `0.12`, $r = 0.819$):** Endgame time urgency $\text{progress} \times \sigma\bigl((\text{RRR} - \text{FormatParRPO}_{\text{LOMO}} + 1.5)/2.5\bigr)$ — rises late in tight/demanding chases, not in easy strolls.
- **$C_{\text{Int}}$ (Weight `0.16`, $r = 0.941$):** Non-linear interaction $C_{\text{RRR}} \times C_{\text{Wkt}}$, capturing compounding risk when high RRR coincides with depleted wickets.

### B. First-Innings Batting Pressure (`first_innings_pressure_index`, Innings 1 Only)

Because no target exists in a 1st innings, difficulty is evaluated against competition-specific LOMO scoring and wicket trajectories:

$$\text{First-Innings Pressure} = 100 \times \bigl(0.30\,F_{\text{Def}} + 0.30\,F_{\text{Wkt}} + 0.15\,F_{\text{CRR}} + 0.10\,F_{\text{Stage}} + 0.15\,F_{\text{Int}}\bigr)$$

- **$F_{\text{Def}}$ (Weight `0.30`, $r = 0.875$):** Progress-weighted score deficit behind format LOMO par trajectory (damped in the first 3 overs via `progress_weight = clip(legal_balls_before / 18, 0.20, 1.0)` to avoid false panic after 1 dot ball).
- **$F_{\text{Wkt}}$ (Weight `0.30`, $r = 0.814$):** Early collapse severity ($0.55$ excess wickets vs. LOMO trajectory + $0.45$ convex absolute wicket depletion).
- **$F_{\text{CRR}}$ (Weight `0.15`, $r = 0.856$):** Progress-weighted current run-rate lag below format-and-stage expected CRR.
- **$F_{\text{Stage}}$ (Weight `0.10`, $r = 0.441$):** Late-innings urgency (overs 12–20) modulated by score deficit.
- **$F_{\text{Int}}$ (Weight `0.15`, $r = 0.959$):** Interaction $F_{\text{Def}} \times F_{\text{Wkt}}$ (behind par *and* losing wickets simultaneously).

### C. Bowling Pressure (`bowling_pressure_index`, Innings 1 & 2)

Evaluates difficulty for the **bowler** strictly from pre-delivery context — intentionally carrying **opposite wicket polarity** to batting pressure (more batting wickets in hand = higher bowling pressure; correlation with batting pressure is `-0.866` in Inn 1 and `-0.596` in Inn 2):

- **Second Innings (Defending a Target):**
  $$\text{Bowl}_{\text{Inn2}} = 100 \times \bigl(0.30\,B_{\text{Close}} + 0.22\,B_{\text{WktHand}} + 0.18\,B_{\text{Phase}} + 0.15\,B_{\text{Threat}} + 0.15\,B_{\text{End}}\bigr)$$
  - $B_{\text{Close}} = \exp\!\bigl(-0.5\,[(\text{RRR} - \text{ExpRemRPO}_{\text{LOMO}})/3.8]^2\bigr)$: peaks when the chase sits on a knife-edge around par RPO, and decays cleanly when the chase is mathematically dead (e.g., `RRR > 22`, bowler cruising).
  - $B_{\text{WktHand}} = (\text{wickets\_in\_hand\_before} / 10)^{1.15}$.
  - $B_{\text{Phase}}$: empirically anchored to LOMO format × innings × phase RPO (`Death > Powerplay > Middle`).
  - $B_{\text{Threat}}$: strictly pre-delivery striker threat based on `batter_runs_before` and confidence-weighted pre-delivery strike rate in the *current innings only*.
  - $B_{\text{End}} = \text{progress} \times B_{\text{Close}}$ (late-over close-chase leverage).
- **First Innings (Containing & Taking Wickets):**
  $$\text{Bowl}_{\text{Inn1}} = 100 \times \bigl(0.28\,B_{\text{OppMom}} + 0.22\,B_{\text{WktHand}} + 0.20\,B_{\text{Phase}} + 0.15\,B_{\text{Threat}} + 0.15\,(B_{\text{OppMom}} \cdot B_{\text{WktHand}})\bigr)$$
  - $B_{\text{OppMom}}$ measures opponent surge *ahead* of format LOMO expected score.

---

## 4. Missing & Corrupted Context Guardrails

No pressure index is ever fabricated when context is missing or corrupted (`1,551` deliveries = `0.80%` marked `UNAVAILABLE` / `NaN`):
1. **`1,539` deliveries (`766` Inn 1, `773` Inn 2)** across 10 DLS/rain-shortened matches lacking `revised_overs` or `revised_target` metadata in `matches.csv`.
2. **`12` deliveries in Match `48610` (Inn 2, overs 14–15)** where `cum_score_before >= revised_target_num` (`115`), empirically identifying a corrupted `revised_target` entry in raw metadata (`chase_target_integrity_ok = False`).

---

## 5. Pressure Category Thresholds & Justification

Empirical comparison across four schemes (`outputs/pressure_threshold_analysis.csv`) demonstrated why naive shared boundaries fail:
- **Equal-Interval (`25/50/75`):** Classifies `57.20%` of Bowling balls as HIGH+EXTREME vs. only `22.36%` of First Innings (and only `1.83%` EXTREME in Inn 1).
- **Shared Fixed (`35/55/72`):** Still severely skewed (`44.51%` Bowling HIGH+EXTREME vs. `15.69%` First Innings).
- **Quartile (`p25/p50/p75`):** Classifies `50.0%` of all balls as HIGH+EXTREME, diluting genuine pressure situations.
- **Selected Empirically Calibrated Framework-Specific Tiers (Anchored to `~p35 / p70 / p90`, rounded to clean integers):**

| Framework | LOW PRESSURE | MODERATE PRESSURE | HIGH PRESSURE | EXTREME PRESSURE | Empirical HIGH + EXTREME Share |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Chase (`chase_pressure_index`)** | `< 32` | `32 – < 50` | `50 – < 74` | `>= 74` | **30.18%** (`20.14%` HIGH, `10.04%` EXTREME) |
| **First Innings (`first_innings_pressure_index`)** | `< 30` | `30 – < 45` | `45 – < 61` | `>= 61` | **30.84%** (`21.21%` HIGH, `9.63%` EXTREME) |
| **Bowling (`bowling_pressure_index`)** | `< 47` | `47 – < 60` | `60 – < 68` | `>= 68` | **29.88%** (`20.36%` HIGH, `9.52%` EXTREME) |

This preserves the unmodified continuous `0–100` score for every delivery while isolating the top **~30% pressure situations** (and top **~10% extreme crunch/crisis situations**) consistently across all three frameworks, without forcing IPL and T20I to share identical category percentages.

---

## 6. Alternative Models Retained for Robustness Testing

- **Model A (`model_a_*`):** Transparent rule-based weighted index using fixed cricket domain bounds (no format baselines). Retained for simplicity comparison.
- **Model B (`model_b_*`):** Empirical percentile (ECDF) rank-scaled index pooled across IPL + T20I. Retained as a non-parametric check.
- **Model C (`model_c_*` — Recommended Primary):** Context-normalized LOMO IPL/T20I model with smooth logistic scaling. Selected because it eliminates the `5.0–6.8` pt cross-format batting bias found in Models A & B, preserves authentic IPL bowling difficulty (`+4.82` pts), avoids hard-clipping plateaus, and remains highly robust across weight perturbations (`Spearman >= 0.9729`).

