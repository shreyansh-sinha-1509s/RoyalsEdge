# Phase 5 Player Performance Methodology — RR PERFORMANCE LAB

**Project:** SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Analytics  
**Scripts:** `src/07_batting_performance.py`, `src/08_bowling_performance.py`  
**Primary Pressure Framework:** Model C (Context-Normalized Leave-One-Match-Out, IPL + T20I 2022–2026)  
**Primary Identity Key:** Integer `player_id` (validated against `data/processed/player_master.csv`; players are **never** merged by name).

---

## 1. Scope & Strict Exclusions

- **Included:** Eligible IPL (`2022–2026`) and T20I (`2022–2026`) regular-innings deliveries with valid Model C pressure scores (`192,437` valid deliveries: `185,040` valid batter balls faced across `824` batters; `184,222` valid legal balls bowled across `596` bowlers).
- **Excluded from Primary Player Analysis:**
  - Non-IPL T20 competitions (`comp_id` `2670` and `3289`, `6,985` deliveries).
  - Super Over deliveries (`innings >= 3`, `38` deliveries).
  - Unavailable pressure contexts (`1,551` deliveries from missing-revised-overs DLS/reduced matches and Match `48610`'s corrupted target) — **never silently merged into `LOW PRESSURE`**.
- **Analytical Guardrail:** Performance is modeled strictly separately from Reliability (consistency) and Evidence Strength (sample sufficiency). No final Top 10 rankings are created in Phase 5.

---

## 2. Batting Performance Under Pressure (`src/07_batting_performance.py`)

### Exact Cricket-Law Definitions
- **Balls Faced (`balls_faced`):** `sum(is_batter_ball_faced)` — strictly excludes wides, includes legal deliveries and no-balls per official ICC/T20 scoring laws.
- **Runs (`runs`):** `sum(batter_runs)` — runs off the bat only.
- **Dismissals (`dismissals`):** Counted strictly via **`dismissed_player_id`** where `is_wicket_event == True` (NOT `striker_id`), accurately attributing all `261` non-striker run-outs to the dismissed batter and excluding all `11` primary Retired Hurt events. The single `Retire Out` lacking `dismissed_player_id` (`match_id=40709`) is left unattributed rather than fabricated.
- **Rates (set to `NaN` whenever denominator is `0`):**
  - `strike_rate = runs / balls_faced * 100`
  - `batting_average = runs_per_dismissal = runs / dismissals`
  - `boundary_pct = sum(is_four | is_six) / balls_faced * 100`
  - `dot_ball_pct = sum(batter_runs == 0) / balls_faced * 100`
  - `dismissal_rate_pct = dismissals / balls_faced * 100`
  - `pressure_contribution_pct`: mean across player's pressure innings of `(player_innings_runs / team_innings_total_runs) * 100`.

### Format- & Context-Adjusted Batting Value (Addressing IPL vs. T20I Scoring Gap)
Because IPL averages `+0.55` to `+0.88` RPO higher than T20I, raw strike rates cannot be compared across formats without context adjustment. For every delivery faced, leave-one-match-out (LOMO) expected batter runs (`exp_bat_runs_per_ball`) and expected dismissal probability (`exp_bat_wkt_per_ball`) are estimated by `(eligibility_category, innings, match_phase, batting_pressure_level)`:
- **Run Value Above Expected (`rvae_per_100b`):** $100 \times \frac{\sum(\text{runs} - \text{exp\_runs})}{\text{balls\_faced}}$
- **Survival Above Expected (`survival_above_exp`):** $\sum \text{exp\_dismissals} - \text{dismissals}$
- **Net Context-Adjusted Impact (`net_impact_per_100b`):** $100 \times \frac{\text{RVAE} + 12.0 \times \text{survival\_above\_exp}}{\text{balls\_faced}}$ (higher = better).

### Data-Driven Batting Role Classification
Assigned strictly from observed primary data (`>= 30` total primary balls faced and `>= 5` innings; otherwise **`UNKNOWN / INSUFFICIENT EVIDENCE`**, `379` of `824` batters):
- `Opener` (`94`): median `batter_position <= 2.5` or `opener_innings_share >= 50%`
- `Top-Order` (`46`): median position `(2.5, 3.5]`
- `Middle-Order` (`101`): median position `(3.5, 5.5]`
- `Finisher / Lower-Middle` (`93`): median position `(5.5, 7.5]`
- `Lower-Order / Tail` (`111`): median position `> 7.5`
- Wicketkeepers (`ever_wk`) and dual-discipline all-rounders (`>= 60` BF and `>= 60` LB) are flagged explicitly while keeping batting and bowling evaluations strictly separate.

---

## 3. Bowling Performance Under Pressure (`src/08_bowling_performance.py`)

### Exact Cricket-Law Definitions & Explicit Metric Directions
- **Legal Balls (`legal_balls`) & Overs (`overs = legal_balls / 6`):** Excludes `wide`, `Overstep`, and `other` no-balls.
- **Runs Conceded (`runs_conceded`):** `sum(bowler_conceded_runs)` — includes batter runs + wides + no-ball penalties; strictly excludes byes, leg-byes, penalty runs, and `extras_2_runs`.
- **Bowler Wickets (`bowler_wickets`):** Strictly `is_bowler_wicket` (`Caught`, `Bowled`, `LBW`, `Stump`, `Hit Wicket`); excludes `RunOut`, `Retire Out`, `Obstructing the field`, and `Retired Hurt`.
- **Rates & Explicit Directions:**
  - `economy_rate = runs_conceded / overs` (**lower = better**)
  - `bowling_average = runs_conceded / bowler_wickets` (**lower = better**; `NaN` if 0 wickets)
  - `bowling_strike_rate = legal_balls / bowler_wickets` (**lower = better**; `NaN` if 0 wickets)
  - `boundary_conceded_pct = sum(is_four | is_six) / legal_balls * 100` (includes boundaries hit off no-balls; **lower = better**)
  - `dot_ball_pct = sum(is_legal_delivery & bowler_conceded_runs == 0) / legal_balls * 100` (**higher = better**)
  - `wicket_frequency = bowler_wickets / legal_balls` (**higher = better**)

### Format- & Context-Adjusted Bowling Value
LOMO expected conceded runs and bowler wickets per legal ball are computed by `(eligibility_category, innings, match_phase, bowling_pressure_level)`:
- **Runs Saved Above Expected per Over (`rsae_per_over`):** $\frac{\sum \text{exp\_runs\_conceded} - \text{runs\_conceded}}{\text{overs}}$ (**higher = better**)
- **Wickets Above Expected (`wickets_above_exp`):** $\text{bowler\_wickets} - \sum \text{exp\_bowler\_wickets}$ (**higher = better**)
- **Net Context-Adjusted Bowling Impact (`net_impact_per_24b`):** $24 \times \frac{\text{RSAE} + 12.0 \times \text{wickets\_above\_exp}}{\text{legal\_balls}}$ (**higher = better**, representing expected runs saved + wicket value per 4-over spell).

### Data-Driven Bowling Role Classification
Requires `>= 36` total primary legal balls and `>= 5` innings (otherwise **`UNKNOWN / INSUFFICIENT EVIDENCE`**, `247` of `596` bowlers); combines observed `pace_or_spin` with phase usage:
- `Death Specialist` (`>= 35%` Death overs): `41` Pace, `2` Spin
- `Powerplay Specialist` (`>= 40%` Powerplay overs): `97` Pace, `14` Spin
- `Middle-Overs Enforcer` (`>= 55%` Middle overs): `30` Pace, `118` Spin
- `All-Phase` (balanced): `42` Pace, `5` Spin

---

## 4. Cohort Benchmarks Across Model C Pressure Tiers (Actual Results)

### Batting (`outputs/batting_metric_summary.csv`)
| Tier | Balls Faced | Runs | Dismissals | Strike Rate | Average | Boundary % | Dot % | Dismissal Rate % |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **LOW PRESSURE** | 65,497 | 95,133 | 3,140 | **145.25** | 30.30 | 20.40% | 36.66% | **4.79%** |
| **MODERATE PRESSURE** | 63,154 | 88,330 | 3,314 | **139.86** | 26.65 | 18.88% | 36.81% | **5.25%** |
| **HIGH PRESSURE** | 38,350 | 52,392 | 2,396 | **136.62** | 21.87 | 17.06% | 35.59% | **6.25%** |
| **EXTREME PRESSURE** | 18,039 | 23,102 | 1,524 | **128.07** | 15.16 | 16.20% | 41.55% | **8.45%** |
| *HIGH+EXTREME (IPL)* | 24,761 | 35,060 | 1,633 | 141.59 | 21.47 | 18.40% | 35.82% | 6.60% |
| *HIGH+EXTREME (T20I)* | 31,628 | 40,434 | 2,287 | 127.84 | 17.68 | 15.52% | 38.81% | 7.23% |

### Bowling (`outputs/bowling_metric_summary.csv`)
| Tier | Legal Balls | Runs Conceded | Bowler Wkts | Economy | Avg | Strike Rate | Dot % | Boundary Conc. % |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **LOW PRESSURE** | 64,855 | 87,276 | 3,746 | **8.07** | 23.30 | 17.31 | **39.15%** | **16.42%** |
| **MODERATE PRESSURE** | 64,473 | 92,541 | 3,165 | **8.61** | 29.24 | 20.37 | **37.81%** | **18.67%** |
| **HIGH PRESSURE** | 37,555 | 57,103 | 1,929 | **9.12** | 29.60 | 19.47 | **35.61%** | **20.40%** |
| **EXTREME PRESSURE** | 17,339 | 31,655 | 962 | **10.95** | 32.91 | 18.02 | **28.24%** | **25.39%** |
| *HIGH+EXTREME (IPL)* | 31,870 | 52,049 | 1,595 | 9.80 | 32.63 | 19.98 | 32.96% | 22.67% |
| *HIGH+EXTREME (T20I)* | 23,024 | 36,709 | 1,296 | 9.57 | 28.32 | 17.77 | 33.74% | 21.01% |

