"""
SupeRR Selector Season 2 - Phase 6 Final Submission Package Generator (RR PERFORMANCE LAB).

Reads validated Phase 4, 5, and 6 datasets and outputs to build all competition
deliverables inside submission/:
  1. RR_Performance_Lab_Top_10_Batters.csv
  2. RR_Performance_Lab_Top_10_Bowlers.csv
  3. RR_Performance_Lab_Final_Rankings.xlsx
  4. RR_Performance_Lab_Methodology_Report.md
  5. RR_Performance_Lab_Methodology_Report.pdf
  6. RR_Performance_Lab_Executive_Summary.pdf
  7. README_SUBMISSION.md

Never alters original raw data. Never submits externally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
CHART_DIR = OUT_DIR / "charts"
SUB_DIR = ROOT / "submission"
SUB_DIR.mkdir(parents=True, exist_ok=True)

# RR PERFORMANCE LAB visual tokens (dashboard/DESIGN_SYSTEM.md)
HEX_PLUM = "24172C"
HEX_PLUM2 = "392940"
HEX_PINK = "E83E80"
HEX_GOLD = "D8B45A"
HEX_LIGHT = "F5F1F5"
HEX_LAV = "B8A6C2"

RL_PLUM = colors.HexColor("#24172C")
RL_PLUM2 = colors.HexColor("#392940")
RL_PINK = colors.HexColor("#E83E80")
RL_GOLD = colors.HexColor("#D8B45A")
RL_LIGHT = colors.HexColor("#F5F1F5")
RL_LAV = colors.HexColor("#B8A6C2")
RL_DARK_TXT = colors.HexColor("#1E1424")
RL_MUTED_TXT = colors.HexColor("#5B4C66")


def build_submission_top10_tables(
    bat_ranked: pd.DataFrame,
    bowl_ranked: pd.DataFrame,
    ov_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assemble clean, audited Top 10 Batters and Top 10 Bowlers submission tables."""
    ov_bat = ov_df[ov_df["discipline"] == "batting"][["player_id", "methods_in_top10_out_of_8", "stability_classification"]]
    ov_bowl = ov_df[ov_df["discipline"] == "bowling"][["player_id", "methods_in_top10_out_of_8", "stability_classification"]]

    bat10 = bat_ranked.head(10).merge(ov_bat, on="player_id", how="left")
    bowl10 = bowl_ranked.head(10).merge(ov_bowl, on="player_id", how="left")

    bat_out = pd.DataFrame({
        "rank": bat10["rank"].astype(int),
        "player_id": bat10["player_id"].astype(int),
        "player_name": bat10["player_name"],
        "role": bat10["batting_role"],
        "team_context": bat10["team_names"],
        "competition_context": bat10["competition_context"],
        "final_ranking_score": bat10["final_ranking_score"].round(2),
        "performance_score": bat10["performance_score"].round(2),
        "reliability_score": bat10["reliability_score"].round(2),
        "evidence_score": bat10["evidence_strength_score"].round(2),
        "eb_pressure_impact_per_100b": bat10["eb_pressure_impact"].round(2),
        "raw_pressure_impact_per_100b": bat10["raw_pressure_impact"].round(2),
        "pressure_runs": bat10["pressure_runs"].astype(int),
        "pressure_balls_faced": bat10["pressure_balls_faced"].astype(int),
        "pressure_strike_rate": bat10["pressure_strike_rate"].round(2),
        "pressure_average": bat10["pressure_average"].round(2),
        "pressure_boundary_pct": bat10["pressure_boundary_pct"].round(2),
        "pressure_dot_ball_pct": bat10["pressure_dot_ball_pct"].round(2),
        "pressure_innings": bat10["pressure_innings"].astype(int),
        "unique_matches": bat10["pressure_matches"].astype(int),
        "seasons_count": bat10["pressure_seasons"].astype(int),
        "seasons_represented": bat10["season_years_represented"],
        "impact_ci95_low": bat10["impact_ci95_low"].round(2),
        "impact_ci95_high": bat10["impact_ci95_high"].round(2),
        "mc_rank_p05": bat10["mc_rank_p05"],
        "mc_rank_p95": bat10["mc_rank_p95"],
        "mc_prob_top10_pct": bat10["mc_prob_top10_pct"],
        "methods_in_top10_out_of_8": bat10["methods_in_top10_out_of_8"].astype(int),
        "stability_tier": bat10["stability_classification"],
        "key_strengths": bat10["key_strengths"],
        "main_limitation": bat10["main_limitation"],
        "confidence": bat10["confidence_description"],
    })

    bowl_out = pd.DataFrame({
        "rank": bowl10["rank"].astype(int),
        "player_id": bowl10["player_id"].astype(int),
        "player_name": bowl10["player_name"],
        "role": bowl10["bowling_role"],
        "team_context": bowl10["team_names"],
        "competition_context": bowl10["competition_context"],
        "final_ranking_score": bowl10["final_ranking_score"].round(2),
        "performance_score": bowl10["performance_score"].round(2),
        "reliability_score": bowl10["reliability_score"].round(2),
        "evidence_score": bowl10["evidence_strength_score"].round(2),
        "eb_pressure_impact_per_24b": bowl10["eb_pressure_impact"].round(2),
        "raw_pressure_impact_per_24b": bowl10["raw_pressure_impact"].round(2),
        "pressure_legal_balls": bowl10["pressure_legal_balls"].astype(int),
        "pressure_runs_conceded": bowl10["pressure_runs_conceded"].astype(int),
        "pressure_wickets": bowl10["pressure_wickets"].astype(int),
        "pressure_economy": bowl10["pressure_economy"].round(2),
        "pressure_bowling_average": bowl10["pressure_bowling_average"].round(2),
        "pressure_bowling_strike_rate": bowl10["pressure_bowling_strike_rate"].round(2),
        "pressure_dot_ball_pct": bowl10["pressure_dot_ball_pct"].round(2),
        "pressure_boundary_conceded_pct": bowl10["pressure_boundary_conceded_pct"].round(2),
        "pressure_rsae_per_over": bowl10["pressure_rsae_per_over"].round(2),
        "pressure_innings": bowl10["pressure_innings"].astype(int),
        "unique_matches": bowl10["pressure_matches"].astype(int),
        "seasons_count": bowl10["pressure_seasons"].astype(int),
        "seasons_represented": bowl10["season_years_represented"],
        "impact_ci95_low": bowl10["impact_ci95_low"].round(2),
        "impact_ci95_high": bowl10["impact_ci95_high"].round(2),
        "mc_rank_p05": bowl10["mc_rank_p05"],
        "mc_rank_p95": bowl10["mc_rank_p95"],
        "mc_prob_top10_pct": bowl10["mc_prob_top10_pct"],
        "methods_in_top10_out_of_8": bowl10["methods_in_top10_out_of_8"].astype(int),
        "stability_tier": bowl10["stability_classification"],
        "key_strengths": bowl10["key_strengths"],
        "main_limitation": bowl10["main_limitation"],
        "confidence": bowl10["confidence_description"],
    })

    bat_out.to_csv(SUB_DIR / "RR_Performance_Lab_Top_10_Batters.csv", index=False)
    bowl_out.to_csv(SUB_DIR / "RR_Performance_Lab_Top_10_Bowlers.csv", index=False)
    return bat_out, bowl_out


def write_styled_excel_workbook(sheets: dict[str, pd.DataFrame], out_path: Path) -> None:
    """Create RR PERFORMANCE LAB styled Excel workbook with consistent formatting."""
    wb = Workbook()
    wb.remove(wb.active)

    hdr_fill = PatternFill(start_color=HEX_PLUM, end_color=HEX_PLUM, fill_type="solid")
    alt_fill = PatternFill(start_color=HEX_LIGHT, end_color=HEX_LIGHT, fill_type="solid")
    hdr_font = Font(name="Calibri", size=10, bold=True, color=HEX_LIGHT)
    body_font = Font(name="Calibri", size=10, color="1E1424")
    thin_side = Side(style="thin", color=HEX_LAV)
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    for sheet_name, df in sheets.items():
        ws = wb.create_sheet(title=sheet_name[:31])
        ws.freeze_panes = "A2"
        cols = list(df.columns)
        for ci, col_name in enumerate(cols, start=1):
            cell = ws.cell(row=1, column=ci, value=col_name)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border
        ws.row_dimensions[1].height = 24

        for ri, row in enumerate(df.itertuples(index=False), start=2):
            for ci, val in enumerate(row, start=1):
                clean_val = None if (isinstance(val, float) and np.isnan(val)) else val
                cell = ws.cell(row=ri, column=ci, value=clean_val)
                cell.font = body_font
                cell.border = border
                if ri % 2 == 1:
                    cell.fill = alt_fill
                if isinstance(clean_val, (int, float, np.integer, np.floating)):
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)

        for ci, col_name in enumerate(cols, start=1):
            max_len = max([len(str(col_name))] + [min(len(str(v)), 48) for v in df[col_name].head(30).tolist()])
            ws.column_dimensions[get_column_letter(ci)].width = min(max(max_len + 3, 11), 46)

    wb.save(out_path)


def build_player_narrative_markdown(df10: pd.DataFrame, is_bat: bool) -> str:
    """Create structured 5-point analytical justifications for every Top 10 player."""
    blocks = []
    for r in df10.itertuples():
        if is_bat:
            blocks.append(
                f"#### #{r.rank}. {r.player_name} (`player_id={r.player_id}` | {r.role} | {r.competition_context})\n"
                f"- **Composite Score:** `{r.final_ranking_score:.2f}` (Performance `{r.performance_score:.1f}`, Reliability `{r.reliability_score:.1f}`, Evidence `{r.evidence_score:.1f}`; in Top 10 under **{r.methods_in_top10_out_of_8}/8** tested specifications; `{r.mc_prob_top10_pct:.1f}%` MC Top-10 probability).\n"
                f"- **1. Why included:** Combines high context-adjusted pressure scoring (`EB {r.eb_pressure_impact_per_100b:+.2f}` runs/100b) with above-cohort cross-innings stability (`Rel {r.reliability_score:.1f}`) across `{r.pressure_balls_faced}` HIGH+EXTREME balls (`{r.pressure_innings}` innings, `{r.unique_matches}` matches, seasons `{r.seasons_represented}`).\n"
                f"- **2. Pressure effectiveness:** {r.key_strengths}.\n"
                f"- **3. Consistency:** Reliability score `{r.reliability_score:.1f}/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).\n"
                f"- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ {r.impact_ci95_low:+.1f}, {r.impact_ci95_high:+.1f} ]` runs/100b; 90% MC rank band `#{r.mc_rank_p05:.0f}–#{r.mc_rank_p95:.0f}` ({r.confidence}).\n"
                f"- **5. Main limitation / risk:** {r.main_limitation}.\n"
            )
        else:
            blocks.append(
                f"#### #{r.rank}. {r.player_name} (`player_id={r.player_id}` | {r.role} | {r.competition_context})\n"
                f"- **Composite Score:** `{r.final_ranking_score:.2f}` (Performance `{r.performance_score:.1f}`, Reliability `{r.reliability_score:.1f}`, Evidence `{r.evidence_score:.1f}`; in Top 10 under **{r.methods_in_top10_out_of_8}/8** tested specifications; `{r.mc_prob_top10_pct:.1f}%` MC Top-10 probability).\n"
                f"- **1. Why included:** Combines elite context-adjusted run prevention and wicket-taking (`EB {r.eb_pressure_impact_per_24b:+.2f}` runs/24b) with repeatable spell consistency (`Rel {r.reliability_score:.1f}`) across `{r.pressure_legal_balls}` HIGH+EXTREME legal balls (`{r.pressure_innings}` innings, `{r.unique_matches}` matches, seasons `{r.seasons_represented}`).\n"
                f"- **2. Pressure effectiveness:** {r.key_strengths}.\n"
                f"- **3. Consistency:** Reliability score `{r.reliability_score:.1f}/100` (volume-free variance-stabilized spell consistency across innings, conditions, and seasons).\n"
                f"- **4. Statistical evidence:** Match-clustered 95% CI on raw net impact `[ {r.impact_ci95_low:+.1f}, {r.impact_ci95_high:+.1f} ]` runs/24b; 90% MC rank band `#{r.mc_rank_p05:.0f}–#{r.mc_rank_p95:.0f}` ({r.confidence}).\n"
                f"- **5. Main limitation / risk:** {r.main_limitation}.\n"
            )
    return "\n".join(blocks)


def write_methodology_markdown(
    bat10: pd.DataFrame,
    bowl10: pd.DataFrame,
    mc_df: pd.DataFrame,
    rob_df: pd.DataFrame,
    elig_df: pd.DataFrame,
    alts_df: pd.DataFrame,
) -> Path:
    """Write the complete 20-section reproducible Methodology Report Markdown."""
    bat_tbl_lines = ["| Rank | Player ID | Player Name | Role | Comp | Score | EB Impact/100b | Press SR | Press Avg | Rel | Evid | Balls / Matches | 95% CI | Stability |",
                     "| :---: | ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :--- |"]
    for r in bat10.itertuples():
        avg_s = f"{r.pressure_average:.1f}" if pd.notna(r.pressure_average) else "N/A"
        bat_tbl_lines.append(
            f"| {r.rank} | {r.player_id} | **{r.player_name}** | {r.role} | {r.competition_context} | {r.final_ranking_score:.2f} | {r.eb_pressure_impact_per_100b:+.2f} | {r.pressure_strike_rate:.1f} | {avg_s} | {r.reliability_score:.1f} | {r.evidence_score:.1f} | {r.pressure_balls_faced}b / {r.unique_matches}m | [{r.impact_ci95_low:+.1f}, {r.impact_ci95_high:+.1f}] | {r.methods_in_top10_out_of_8}/8 |"
        )

    bowl_tbl_lines = ["| Rank | Player ID | Player Name | Role | Comp | Score | EB Impact/24b | Press Econ | Press Wkts | Rel | Evid | Balls / Matches | 95% CI | Stability |",
                      "| :---: | ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :--- |"]
    for r in bowl10.itertuples():
        bowl_tbl_lines.append(
            f"| {r.rank} | {r.player_id} | **{r.player_name}** | {r.role} | {r.competition_context} | {r.final_ranking_score:.2f} | {r.eb_pressure_impact_per_24b:+.2f} | {r.pressure_economy:.2f} | {r.pressure_wickets} | {r.reliability_score:.1f} | {r.evidence_score:.1f} | {r.pressure_legal_balls}b / {r.unique_matches}m | [{r.impact_ci95_low:+.1f}, {r.impact_ci95_high:+.1f}] | {r.methods_in_top10_out_of_8}/8 |"
        )

    rob_lines = ["| Discipline | Robustness Test | Spearman vs. Primary | Top-10 Overlap | Top-15 Mean Rank Shift |",
                 "| :--- | :--- | ---: | ---: | ---: |"]
    for r in rob_df.itertuples():
        rob_lines.append(f"| {r.discipline.title()} | {r.robustness_test} | {r.spearman_corr_vs_primary:.4f} | {r.top10_overlap_count}/10 ({r.top10_overlap_pct:.0f}%) | {r.mean_abs_rank_shift_top15:.2f} |")

    nm_lines = ["| Discipline | Primary Rank | Player Name | Role | Score | EB Impact | Rel | Pressure Balls / Matches | Notes |",
                "| :--- | :---: | :--- | :--- | ---: | ---: | ---: | :---: | :--- |"]
    for r in alts_df[alts_df["audit_group"] == "narrow_miss_ranks_11_to_15"].itertuples():
        nm_lines.append(f"| {r.discipline.title()} | #{int(r.primary_rank)} | {r.player_name} | {r.role} | {r.final_ranking_score:.2f} | {r.eb_pressure_impact:+.2f} | {r.reliability_score:.1f} | {int(r.pressure_balls)}b / {int(r.pressure_matches)}m | {r.note} |")

    content = f"""# SupeRR Selector Season 2 — Methodology Report (RR PERFORMANCE LAB)

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
{chr(10).join(rob_lines)}

### Narrow Misses (Ranks 11–15, `outputs/shortlist_alternatives.csv`)
{chr(10).join(nm_lines)}

## 16. Validation Results
- **Phase 3–6 Automated Test Suite (`pytest tests -v`):** All unit, cricket-rule, integrity, leakage, pressure, reliability, and final-ranking tests verified passing.
- **Ranking Validation (`outputs/ranking_validation_results.csv`):** `8 / 8 PASS` (zero duplicate IDs, exact descending score order, strict eligibility enforcement, zero missing reliability imputed as zero, composite scores strictly within `[0, 100]`, volume correlation kept low, uncertainty intervals preserved).

## 17. Final Ordered Top 10 Batters Under Pressure
{chr(10).join(bat_tbl_lines)}

### Batter-by-Batter Analytical Justification
{build_player_narrative_markdown(bat10, True)}

## 18. Final Ordered Top 10 Bowlers Under Pressure
{chr(10).join(bowl_tbl_lines)}

### Bowler-by-Bowler Analytical Justification
{build_player_narrative_markdown(bowl10, False)}

## 19. Important Limitations
1. **Overlapping Confidence Intervals:** Adjacent ranks (especially `#4–#10` in both lists) have overlapping match-clustered 95% CIs and Monte Carlo rank bands; small composite-score gaps (`< 1.5` pts) represent statistical near-ties rather than definitive separation.
2. **Moderate-Sample Qualifiers in Bowling:** `#1 Nasum Ahmed` (`93` legal balls, `14` matches), `#3 Mark Wood` (`100` balls, `11` matches), and `#8 Joshua Little` (`115` balls, `18` matches) satisfy the primary `90b / 10m` rule cleanly (and are NOT excluded merely for smaller volume), but carry wider CIs and drop out if the cutoff is tightened to `120–180` balls (`outputs/ranking_threshold_sensitivity.csv`).
3. **Observational, Non-Causal & Non-Predictive Scope:** Historical pressure metrics reflect past performance in observed deployment roles across 2022–2026 and do **not** guarantee future IPL 2027 outcomes (out-of-time cross-era Spearman persistence is `0.37` batting / `0.20` bowling due to T20 scoring inflation).
4. **Excluded Contexts & Venue Granularity:** `1,551` missing-DLS/corrupted-target deliveries, `38` Super Over deliveries, and `6,985` non-IPL T20 deliveries are excluded; baselines adjust for IPL vs. T20I × innings × phase × pressure tier rather than individual ground dimensions.
5. **Unstop Dropdown Verification Required Before Upload:** Exact player spelling/availability in the Unstop Round 1 dropdowns must be verified manually by the user prior to submitting.

## 20. Reproducibility Instructions
From `SupeRR_Selector/` in Windows PowerShell with `.venv` active:
```powershell
.\\.venv\\Scripts\\Activate.ps1
python src\\02_dataset_audit.py
python src\\03_data_cleaning.py
python src\\04_feature_engineering.py
python src\\05_pressure_framework.py
python src\\06_pressure_validation.py
python src\\07_batting_performance.py
python src\\08_bowling_performance.py
python src\\09_player_reliability.py
python src\\10_player_validation.py
python src\\11_final_ranking_model.py
python src\\12_ranking_robustness.py
python src\\13_submission_package.py
pytest tests -v
```
"""
    out_path = SUB_DIR / "RR_Performance_Lab_Methodology_Report.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def make_pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "banner_title": ParagraphStyle("banner_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=RL_LIGHT, alignment=TA_LEFT, spaceAfter=4),
        "banner_sub": ParagraphStyle("banner_sub", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=RL_GOLD, alignment=TA_LEFT),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=RL_PLUM, spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=RL_PINK, spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=8.8, leading=12.5, textColor=RL_DARK_TXT, spaceAfter=4),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica", fontSize=7.4, leading=9.8, textColor=RL_MUTED_TXT, spaceAfter=2),
        "note": ParagraphStyle("note", parent=base["Normal"], fontName="Helvetica", fontSize=6.9, leading=8.8, textColor=RL_MUTED_TXT, spaceAfter=1.8),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontName="Helvetica", fontSize=8.3, leading=11.4, leftIndent=12, bulletIndent=4, textColor=RL_DARK_TXT, spaceAfter=2.0),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontName="Helvetica", fontSize=7.4, leading=9.2, textColor=RL_DARK_TXT),
        "cell_hdr": ParagraphStyle("cell_hdr", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.4, leading=9.2, textColor=RL_LIGHT),
    }


def pdf_page_decorator(title_label: str):
    def _draw(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        w, h = A4
        # Top thin accent bar
        canvas.setFillColor(RL_PLUM)
        canvas.rect(0, h - 0.55 * cm, w, 0.55 * cm, fill=1, stroke=0)
        canvas.setFillColor(RL_PINK)
        canvas.rect(0, h - 0.62 * cm, w, 0.07 * cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(RL_LIGHT)
        canvas.drawString(1.5 * cm, h - 0.39 * cm, f"RR PERFORMANCE LAB  |  {title_label}")
        # Footer with page number
        canvas.setStrokeColor(RL_LAV)
        canvas.setLineWidth(0.5)
        canvas.line(1.5 * cm, 1.25 * cm, w - 1.5 * cm, 1.25 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(RL_MUTED_TXT)
        canvas.drawString(1.5 * cm, 0.85 * cm, "SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Analytics")
        canvas.drawRightString(w - 1.5 * cm, 0.85 * cm, f"Page {doc.page}")
        canvas.restoreState()
    return _draw


def styled_pdf_table(headers: list[str], rows: list[list[Any]], col_widths: list[float], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[Paragraph(str(h), styles["cell_hdr"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(v), styles["cell"]) for v in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RL_PLUM),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, RL_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.35, RL_LAV),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def add_banner(story: list[Any], title: str, subtitle: str, styles: dict[str, ParagraphStyle]) -> None:
    banner = Table(
        [[Paragraph(title, styles["banner_title"])], [Paragraph(subtitle, styles["banner_sub"])]],
        colWidths=[18.0 * cm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RL_PLUM),
        ("LINEBELOW", (0, -1), (-1, -1), 2.5, RL_PINK),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.35 * cm))


def embed_chart(story: list[Any], chart_name: str, width_cm: float, caption: str, styles: dict[str, ParagraphStyle]) -> None:
    cp = CHART_DIR / chart_name
    if cp.is_file():
        img = RLImage(str(cp), width=width_cm * cm, height=width_cm * 0.48 * cm, kind="proportional")
        story.append(img)
        story.append(Paragraph(caption, styles["small"]))
        story.append(Spacer(1, 0.12 * cm))


def build_methodology_pdf(
    bat10: pd.DataFrame,
    bowl10: pd.DataFrame,
    rob_df: pd.DataFrame,
    alts_df: pd.DataFrame,
) -> Path:
    """Build polished multi-page RR_Performance_Lab_Methodology_Report.pdf."""
    out_path = SUB_DIR / "RR_Performance_Lab_Methodology_Report.pdf"
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.35 * cm, bottomMargin=1.6 * cm,
    )
    styles = make_pdf_styles()
    story: list[Any] = []

    add_banner(
        story,
        "RR PERFORMANCE LAB — Methodology Report",
        "SupeRR Selector Season 2 | Identifying the Most Reliable Batters & Bowlers Under Pressure (IPL + T20I, 2022–2026)",
        styles,
    )

    # Section 1-4 Overview
    story.append(Paragraph("1. Competition Objective, Data Scope & Quality Controls", styles["h1"]))
    story.append(Paragraph(
        "This report documents a transparent, fully reproducible analytical pipeline built for Rajasthan Royals' SupeRR Selector Season 2 Round 1 challenge. "
        "Per the official Round 1 Problem Statement, we produce two ordered Top 10 lists (Batters Ranks 1–10 and Bowlers Ranks 1–10) using historical IPL (2022–2026) and T20 International (T20I, 2022–2026) data.",
        styles["body"],
    ))
    for b in [
        "<b>Measured Dataset Scope:</b> 200,999 raw deliveries across 883 matches (141 competitions) and 1,217 unique player_ids. Primary eligible cohort = <b>193,988 regular-innings deliveries</b> (87,673 IPL across 5 seasons; 106,315 T20I across 134 series; 837 matches with ball data).",
        "<b>Explicit Exclusions:</b> 2 non-IPL T20 competitions (comp_id 2670 & 3289; 6,985 deliveries), 38 Super Over deliveries, and 1,551 UNAVAILABLE pressure deliveries (missing DLS revised-overs metadata + Match 48610 corrupted revised_target).",
        "<b>Cricket-Law Validation:</b> Zero reconciliation diffs across 1,652 primary innings for total_runs, bowler_conceded_runs, legal_deliveries (excluding wide, Overstep, and empirically verified non-overstep 'other' no-balls), and bowler wickets. Batting dismissals strictly use dismissed_player_id (capturing 261 non-striker run-outs); 11 primary Retired Hurt events are excluded from wickets. Players are keyed strictly on player_id (never merged by shared name).",
    ]:
        story.append(Paragraph(f"• {b}", styles["bullet"]))

    # Section 5-6 Pressure Framework
    story.append(Paragraph("2. Pre-Delivery Pressure Framework (Model C — Context-Normalized LOMO)", styles["h1"]))
    story.append(Paragraph(
        "<b>Conceptual Separation:</b> Pressure measures pre-delivery match difficulty only (zero current-ball runs/wickets or match results). "
        "Because IPL averages +0.55 to +0.88 RPO higher than T20I across every phase, Model C computes Leave-One-Match-Out (LOMO) IPL vs. T20I baselines across 21 normalized progress bins, reducing Inn 1 format bias ~10x versus fixed-par Model A (-5.01 pts) and pooled-ECDF Model B (-6.83 pts).",
        styles["body"],
    ))
    p_rows = [
        ["Chase (Inn 2)", "0.34 RRR Demand + 0.24 Wkts + 0.14 Accel + 0.12 Urgency + 0.16 RRR×Wkt", "32 / 50 / 74", "30.18% HIGH+EXT", "91,149 valid (785 unavail)"],
        ["First Innings (Inn 1)", "0.30 Par Deficit + 0.30 Wkt Collapse + 0.15 CRR Lag + 0.10 Stage + 0.15 Int", "30 / 45 / 61", "30.84% HIGH+EXT", "101,288 valid (766 unavail)"],
        ["Bowling (Inn 1+2)", "Opposite wicket polarity: Close Chase/Opp Surge + Wkts in Hand + Phase + Threat", "47 / 60 / 68", "29.88% HIGH+EXT", "192,437 valid (1,551 unavail)"],
    ]
    story.append(styled_pdf_table(["Framework", "Model C Pre-Delivery Structure (0–100)", "Thresholds", "High+Ext Share", "Coverage"], p_rows, [2.7*cm, 6.7*cm, 2.1*cm, 2.7*cm, 3.8*cm], styles))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<b>Non-Circular Empirical Validation:</b> Without using outcomes to build pressure, aggregate batting SR drops monotonically across LOW→MOD→HIGH→EXTREME (145.25 → 139.86 → 136.62 → 128.07; dismissal rate doubles 4.79% → 8.45%), while bowling economy climbs monotonically (8.07 → 8.61 → 9.12 → 10.95). All 6 leakage checks and 18 validation checks PASSED.",
        styles["body"],
    ))

    # Section 7-13 Performance, Reliability, EB, Bootstrap & Ranking Formula
    story.append(Paragraph("3. Performance, Empirical Bayes Shrinkage, Reliability & Final Composite Formula", styles["h1"]))
    for b in [
        "<b>Format-Adjusted Performance:</b> Every delivery is benchmarked against LOMO (format × innings × phase × pressure_level) par runs and wickets. Batting: net_impact_per_100b = 100 × (RVAE + 12 × survival_above_exp) / balls_faced. Bowling: net_impact_per_24b = 24 × (RSAE + 12 × wickets_above_exp) / legal_balls (higher = better for both).",
        "<b>Empirical Bayes Shrinkage:</b> Ball-weighted match-level variance decomposition estimates prior k = 8.65 matches (batting) and k = 30.00 matches (bowling), automatically shrinking noisier small-sample spells toward context par.",
        "<b>Volume-Free Reliability (0–100):</b> Computed on variance-stabilized spell residuals (net_impact_runs / sqrt(balls)) across >=5 pressure innings: 40% Innings Stability (inverse IQR) + 30% Floor Consistency + 20% Cross-Condition Stability + 10% Seasonal Stability. Near-zero volume correlation (+0.100 batting, +0.165 bowling).",
        "<b>Match-Clustered Uncertainty & Eligibility:</b> Whole-match bootstrap (B=500) preserves intra-innings autocorrelation (0.950 bat / 0.862 bowl). Primary eligibility requires >=80 pressure BF & >=10 inn/matches (173 of 824 batters) and >=90 pressure LB & >=10 inn/matches (165 of 596 bowlers).",
        "<b>Balanced Primary Composite (0–100):</b> Final Score = 0.50 × Calibrated EB Performance + 0.25 × Calibrated Reliability + 0.15 × Extreme-Pressure & Pressure-vs-Non-Pressure Lift + 0.10 × Evidence Strength. Selected over Performance-Dominant (65/20/10/5) and Reliability-Dominant (30/50/10/10) to honor both effectiveness and consistency.",
    ]:
        story.append(Paragraph(f"• {b}", styles["bullet"]))

    # Page 2: Top 10 Batters
    story.append(PageBreak())
    story.append(Paragraph("4. Final Ordered Top 10 Batters Under Pressure", styles["h1"]))
    bat_rows = []
    for r in bat10.itertuples():
        avg_s = f"{r.pressure_average:.1f}" if pd.notna(r.pressure_average) else "N/A"
        bat_rows.append([
            f"#{r.rank}", f"<b>{r.player_name}</b><br/>ID {r.player_id}", r.role, r.competition_context,
            f"<b>{r.final_ranking_score:.2f}</b>", f"{r.eb_pressure_impact_per_100b:+.1f}",
            f"{r.pressure_strike_rate:.1f} / {avg_s}", f"{r.reliability_score:.1f}",
            f"{r.pressure_balls_faced}b / {r.unique_matches}m", f"[{r.impact_ci95_low:+.0f}, {r.impact_ci95_high:+.0f}]", f"{r.methods_in_top10_out_of_8}/8",
        ])
    story.append(styled_pdf_table(
        ["Rk", "Batter", "Role", "Comp", "Score", "EB/100b", "SR / Avg", "Rel", "Exp", "95% CI", "Stab"],
        bat_rows, [0.9*cm, 3.0*cm, 2.5*cm, 1.5*cm, 1.3*cm, 1.4*cm, 1.8*cm, 1.1*cm, 1.7*cm, 1.8*cm, 1.0*cm], styles,
    ))
    story.append(Spacer(1, 0.12 * cm))
    embed_chart(story, "20_final_batting_rankings.png", 12.4, "Figure 1: Top 10 Batters — Composite Pillar Decomposition & Monte Carlo Top-10 Inclusion Probability.", styles)

    story.append(Paragraph("Top 10 Batters — Concise Analytical Notes & Key Risks", styles["h2"]))
    for r in bat10.itertuples():
        story.append(Paragraph(
            f"<b>#{r.rank} {r.player_name}:</b> {r.key_strengths}. <i>Limitation:</i> {r.main_limitation}.",
            styles["note"],
        ))

    # Page 3: Top 10 Bowlers
    story.append(PageBreak())
    story.append(Paragraph("5. Final Ordered Top 10 Bowlers Under Pressure", styles["h1"]))
    bowl_rows = []
    for r in bowl10.itertuples():
        bowl_rows.append([
            f"#{r.rank}", f"<b>{r.player_name}</b><br/>ID {r.player_id}", r.role, r.competition_context,
            f"<b>{r.final_ranking_score:.2f}</b>", f"{r.eb_pressure_impact_per_24b:+.2f}",
            f"{r.pressure_economy:.2f} / {r.pressure_wickets}w", f"{r.reliability_score:.1f}",
            f"{r.pressure_legal_balls}b / {r.unique_matches}m", f"[{r.impact_ci95_low:+.1f}, {r.impact_ci95_high:+.1f}]", f"{r.methods_in_top10_out_of_8}/8",
        ])
    story.append(styled_pdf_table(
        ["Rk", "Bowler", "Role", "Comp", "Score", "EB/24b", "Econ / Wkts", "Rel", "Exp", "95% CI", "Stab"],
        bowl_rows, [0.9*cm, 3.0*cm, 2.6*cm, 1.5*cm, 1.3*cm, 1.3*cm, 1.8*cm, 1.1*cm, 1.7*cm, 1.8*cm, 1.0*cm], styles,
    ))
    story.append(Spacer(1, 0.12 * cm))
    embed_chart(story, "21_final_bowling_rankings.png", 12.2, "Figure 2: Top 10 Bowlers — Composite Pillar Decomposition & Monte Carlo Top-10 Inclusion Probability.", styles)

    story.append(Paragraph("Top 10 Bowlers — Concise Analytical Notes & Key Risks", styles["h2"]))
    for r in bowl10.itertuples():
        story.append(Paragraph(
            f"<b>#{r.rank} {r.player_name}:</b> {r.key_strengths}. <i>Limitation:</i> {r.main_limitation}.",
            styles["note"],
        ))

    # Page 4: Uncertainty, Robustness & Limitations
    story.append(PageBreak())
    story.append(Paragraph("6. Uncertainty Intervals, Robustness & Unselected Candidates", styles["h1"]))
    embed_chart(story, "24_shortlist_confidence_intervals.png", 13.4, "Figure 3: Match-Clustered Bootstrap 95% CIs (Raw vs. EB-Shrunk Impact) — Overlapping Intervals Reflect True Ordering Uncertainty.", styles)
    embed_chart(story, "25_top10_overlap_methods.png", 11.8, "Figure 4: Top 10 Overlap Across Pressure Models (A, B, C±3pts), Raw vs. EB Shrinkage, and Alternative Ranking Philosophies.", styles)

    rob_rows = [[r.discipline.title(), r.robustness_test, f"{r.spearman_corr_vs_primary:.4f}", f"{r.top10_overlap_count}/10 ({r.top10_overlap_pct:.0f}%)", f"{r.mean_abs_rank_shift_top15:.2f}"] for r in rob_df.itertuples()]
    story.append(styled_pdf_table(["Discipline", "Robustness Specification", "Spearman r", "Top-10 Overlap", "Top-15 Mean Shift"], rob_rows, [2.4*cm, 6.6*cm, 2.8*cm, 3.2*cm, 3.0*cm], styles))
    story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("7. Key Limitations & Reproducibility", styles["h1"]))
    for b in [
        "<b>Statistical Uncertainty:</b> Adjacent shortlisted ranks (#4–#10) carry overlapping 95% CIs and MC rank intervals; composite gaps under ~1.5 points should be read as statistical near-ties.",
        "<b>Moderate-Sample Bowling Caveats:</b> #1 Nasum Ahmed (93b/14m), #3 Mark Wood (100b/11m), and #8 Joshua Little (115b/18m) meet the validated 90b/10m cutoff cleanly, but have wider CIs than high-exposure anchors like Axar Patel (749b), Rashid Khan (810b), and R. Ashwin (560b).",
        "<b>Non-Causal & Historical Scope:</b> Observational comparisons reflect 2022–2026 historical performance and do not guarantee IPL 2027 outcomes (out-of-time cross-era Spearman r = 0.37 batting, 0.20 bowling due to +1.23 RPO scoring inflation).",
        "<b>Full Reproducibility:</b> Re-run scripts src/02 through src/13 and pytest tests -v from SupeRR_Selector/ using .venv (all raw CSVs verified byte-for-byte unchanged).",
    ]:
        story.append(Paragraph(f"• {b}", styles["bullet"]))

    doc.build(story, onFirstPage=pdf_page_decorator("METHODOLOGY REPORT"), onLaterPages=pdf_page_decorator("METHODOLOGY REPORT"))
    return out_path


def build_executive_summary_pdf(bat10: pd.DataFrame, bowl10: pd.DataFrame) -> Path:
    """Build concise, decision-maker-ready RR_Performance_Lab_Executive_Summary.pdf."""
    out_path = SUB_DIR / "RR_Performance_Lab_Executive_Summary.pdf"
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.35 * cm, bottomMargin=1.6 * cm,
    )
    styles = make_pdf_styles()
    story: list[Any] = []

    add_banner(
        story,
        "RR PERFORMANCE LAB — Executive Summary",
        "Rajasthan Royals IPL 2027 Auction Analytics | Reliable Performers Under Pressure (2022–2026 IPL + T20I)",
        styles,
    )

    story.append(Paragraph("Decision Question & Analytical Framework", styles["h1"]))
    story.append(Paragraph(
        "Which batters and bowlers consistently deliver above-par impact when T20 matches are on the line — and how strongly does the data back those calls? "
        "Across <b>193,988 verified regular deliveries</b> (837 IPL & T20I matches, 2022–2026), we strictly separate three concepts that scouting analyses frequently blur:",
        styles["body"],
    ))
    for b in [
        "<b>1. Match Pressure (Pre-Delivery Only):</b> Model C scores every ball 0–100 using only pre-delivery state relative to separate IPL vs. T20I historical par trajectories (eliminating the +0.78 RPO IPL scoring distortion). HIGH + EXTREME pressure isolates the toughest ~30% of balls.",
        "<b>2. Performance Effectiveness (Context-Adjusted & Shrunk):</b> Measures runs/wickets above expected for each player's exact format, innings, phase, and pressure tier, shrunk via Empirical Bayes (k = 8.65 matches batting; k = 30.0 matches bowling) so short hot streaks cannot hijack the list.",
        "<b>3. Reliability & Evidence Strength:</b> Consistency across pressure innings, conditions, and seasons (0–100, decoupled from raw volume) paired with match-clustered bootstrap 95% confidence intervals.",
    ]:
        story.append(Paragraph(f"• {b}", styles["bullet"]))

    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph("Final Shortlist — Top 10 Batters Under Pressure (173 Eligible / 824 Analyzed)", styles["h2"]))
    b_rows = [
        [f"#{r.rank}", f"<b>{r.player_name}</b>", r.role, f"{r.final_ranking_score:.1f}", f"{r.eb_pressure_impact_per_100b:+.1f}", f"{r.pressure_strike_rate:.1f}", f"{r.reliability_score:.1f}", f"{r.pressure_balls_faced}b / {r.unique_matches}m", f"{r.mc_prob_top10_pct:.0f}%"]
        for r in bat10.itertuples()
    ]
    story.append(styled_pdf_table(
        ["Rk", "Batter", "Role", "Score", "EB/100b", "Press SR", "Rel", "Exposure", "MC Top10"],
        b_rows, [1.0*cm, 3.6*cm, 3.1*cm, 1.4*cm, 1.7*cm, 1.7*cm, 1.3*cm, 2.4*cm, 1.8*cm], styles,
    ))

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("Final Shortlist — Top 10 Bowlers Under Pressure (165 Eligible / 596 Analyzed)", styles["h2"]))
    w_rows = [
        [f"#{r.rank}", f"<b>{r.player_name}</b>", r.role, f"{r.final_ranking_score:.1f}", f"{r.eb_pressure_impact_per_24b:+.2f}", f"{r.pressure_economy:.2f} ({r.pressure_wickets}w)", f"{r.reliability_score:.1f}", f"{r.pressure_legal_balls}b / {r.unique_matches}m", f"{r.mc_prob_top10_pct:.0f}%"]
        for r in bowl10.itertuples()
    ]
    story.append(styled_pdf_table(
        ["Rk", "Bowler", "Role", "Score", "EB/24b", "Econ (Wkts)", "Rel", "Exposure", "MC Top10"],
        w_rows, [1.0*cm, 3.6*cm, 3.1*cm, 1.4*cm, 1.7*cm, 1.9*cm, 1.3*cm, 2.2*cm, 1.8*cm], styles,
    ))

    # Page 2: Visual Evidence & Strategic Risks
    story.append(PageBreak())
    story.append(Paragraph("Performance vs. Reliability Separation & Uncertainty", styles["h1"]))
    embed_chart(story, "22_final_perf_vs_reliability.png", 17.8, "Top 10 Batters and Bowlers occupy the upper-right high-effectiveness, high-consistency zone without relying on raw volume.", styles)
    embed_chart(story, "24_shortlist_confidence_intervals.png", 17.8, "Match-clustered 95% confidence intervals highlight where high-exposure anchors (Jadeja, Klaasen, Axar, Rashid, Ashwin) carry tighter certainty than moderate-sample qualifiers.", styles)

    story.append(Paragraph("Strongest Evidence & Key Decision Risks", styles["h1"]))
    for b in [
        "<b>High-Confidence Franchise Pillars:</b> Among batters, Ravindra Jadeja (550b/39m), Heinrich Klaasen (532b/34m), Ayush Badoni (497b/33m), Tim David (509b/43m), and Romario Shepherd (495b/47m) bring multi-season high-volume proof alongside explosive finishers Naman Dhir (225b, SR 182.2) and Matthew Wade (172b, EB +68.9). Among bowlers, Axar Patel (749b/86m), Rashid Khan (810b/68m), R. Ashwin (560b/42m), Wanindu Hasaranga (545b/52m), and Matheesha Pathirana (270b/31m) deliver verified multi-season reliability.",
        "<b>Moderate-Sample Caveats (Not Hidden):</b> Bowlers Nasum Ahmed (93b/14m), Mark Wood (100b/11m), and Joshua Little (115b/18m) legitimately qualify under the primary 90b/10m threshold on exceptional per-ball impact, but carry wider CIs and drop out under stricter 120–180b filters.",
        "<b>Ordering Precision & Non-Causal Scope:</b> Overlapping 95% CIs mean adjacent ranks (#4–#10) should be treated as a closely matched elite tier rather than rigid separation, and historical 2022–2026 reliability informs — rather than guarantees — IPL 2027 outcomes.",
    ]:
        story.append(Paragraph(f"• {b}", styles["bullet"]))

    doc.build(story, onFirstPage=pdf_page_decorator("EXECUTIVE SUMMARY"), onLaterPages=pdf_page_decorator("EXECUTIVE SUMMARY"))
    return out_path


def write_submission_readme(bat10: pd.DataFrame, bowl10: pd.DataFrame) -> Path:
    bat_list = "\n".join(f"{r.rank}. **{r.player_name}** (`player_id={r.player_id}`, Score `{r.final_ranking_score:.2f}`)" for r in bat10.itertuples())
    bowl_list = "\n".join(f"{r.rank}. **{r.player_name}** (`player_id={r.player_id}`, Score `{r.final_ranking_score:.2f}`)" for r in bowl10.itertuples())
    txt = f"""# SupeRR Selector Season 2 — Round 1 Submission Package (`RR PERFORMANCE LAB`)

> **HOLD FOR REVIEW:** Nothing has been submitted to Unstop or any external platform. Review every file below and verify exact player names in the Unstop dropdowns before uploading.

## Official Round 1 Submission Checklist (Per Supplied Problem Statement PDF)

1. **Component 01 — Ordered Player Rankings (Unstop Dropdowns):**
   - Two separate ordered Top-10 lists (Rank 1 = highest-rated, zero duplicates within a list).
   - Must **exactly match** the uploaded Methodology Report.
2. **Component 02 — Methodology Report Upload:**
   - Upload `RR_Performance_Lab_Methodology_Report.pdf` (with `RR_Performance_Lab_Executive_Summary.pdf` and `RR_Performance_Lab_Final_Rankings.xlsx` available as companion review materials).

---

## Ordered Top 10 Batters (For Unstop Dropdown Entry)

{bat_list}

## Ordered Top 10 Bowlers (For Unstop Dropdown Entry)

{bowl_list}

---

## Files Inside `submission/`

| File | Purpose |
| :--- | :--- |
| `RR_Performance_Lab_Top_10_Batters.csv` | Audited Top 10 Batters table with IDs, roles, scores, exposure, 95% CIs, strengths & limitations |
| `RR_Performance_Lab_Top_10_Bowlers.csv` | Audited Top 10 Bowlers table with IDs, roles, scores, exposure, 95% CIs, strengths & limitations |
| `RR_Performance_Lab_Final_Rankings.xlsx` | Multi-sheet RR PERFORMANCE LAB workbook (Top 10 Batters, Top 10 Bowlers, Method Comparison, Robustness, Overlap, Alternatives, Eligibility) |
| `RR_Performance_Lab_Methodology_Report.pdf` | Polished multi-page competition Methodology Report (for Unstop upload) |
| `RR_Performance_Lab_Methodology_Report.md` | Full 20-section Markdown source of the Methodology Report |
| `RR_Performance_Lab_Executive_Summary.pdf` | Concise 2-page franchise decision-maker Executive Summary |
| `README_SUBMISSION.md` | This submission guide & pre-upload checklist |

## Data Governance & Integrity Verification

- Original competition CSVs in `data/raw/Data Pack/` remain **100% unmodified** and private (excluded via `.gitignore`).
- Primary analysis strictly covers eligible **IPL (2022–2026)** and **T20I (2022–2026)** regular innings (`0` Super Overs, `0` excluded non-IPL T20 competitions).
- All CSV, Excel, Markdown, and PDF files are programmatically generated from the exact same `data/processed/final_batting_rankings.csv` and `data/processed/final_bowling_rankings.csv` tables and verified by `pytest tests -v`.
"""
    p = SUB_DIR / "README_SUBMISSION.md"
    p.write_text(txt, encoding="utf-8")
    return p


def main() -> None:
    bat_ranked = pd.read_csv(PROCESSED_DIR / "final_batting_rankings.csv", low_memory=False)
    bowl_ranked = pd.read_csv(PROCESSED_DIR / "final_bowling_rankings.csv", low_memory=False)
    elig_df = pd.read_csv(PROCESSED_DIR / "ranking_eligibility_audit.csv", low_memory=False)
    mc_df = pd.read_csv(OUT_DIR / "ranking_method_comparison.csv", low_memory=False)
    rob_df = pd.read_csv(OUT_DIR / "ranking_robustness.csv", low_memory=False)
    ov_df = pd.read_csv(OUT_DIR / "top10_overlap_analysis.csv", low_memory=False)
    alts_df = pd.read_csv(OUT_DIR / "shortlist_alternatives.csv", low_memory=False)

    bat10, bowl10 = build_submission_top10_tables(bat_ranked, bowl_ranked, ov_df)

    write_styled_excel_workbook(
        {
            "Top_10_Batters": bat10,
            "Top_10_Bowlers": bowl10,
            "Method_Comparison": mc_df,
            "Robustness_Summary": rob_df,
            "Top10_Overlap": ov_df,
            "Shortlist_Alternatives": alts_df,
            "Eligibility_Audit": elig_df,
        },
        SUB_DIR / "RR_Performance_Lab_Final_Rankings.xlsx",
    )

    md_path = write_methodology_markdown(bat10, bowl10, mc_df, rob_df, elig_df, alts_df)
    pdf_meth = build_methodology_pdf(bat10, bowl10, rob_df, alts_df)
    pdf_exec = build_executive_summary_pdf(bat10, bowl10)
    readme_p = write_submission_readme(bat10, bowl10)

    print("\n=== PHASE 6 SUBMISSION PACKAGE GENERATED ===")
    for p in sorted(SUB_DIR.iterdir()):
        print(f"  {p.name:48s} {p.stat().st_size:>10,} bytes")


if __name__ == "__main__":
    main()
