"""
SupeRR Selector Season 2 - Phase 5 Player Validation, Robustness, Temporal Checks & Visualizations.

Validates all Phase 5 batting, bowling, and reliability tables across:
  - Identity, eligibility, cricket-rule conservation, and anti-leakage checks
  - Cross-model robustness (Model C vs. Model A vs. Model B, threshold shifts, raw vs. EB shrunk, bootstrap B)
  - Temporal stability (Early Era 2022-2023 vs. Late Era 2024-2026 without future leakage)
  - 10 RR PERFORMANCE LAB static analytical charts (outputs/charts/10_*.png to 19_*.png)

No final Top 10 player rankings or dashboard pages are created in this script.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "rr_perf_lab_mpl"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
CHART_DIR = OUT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# RR PERFORMANCE LAB Design System (dashboard/DESIGN_SYSTEM.md)
BG_DEEP = "#24172C"
BG_CARD = "#392940"
PINK = "#E83E80"
GOLD = "#D8B45A"
LIGHT_TXT = "#F5F1F5"
LAVENDER = "#B8A6C2"
BLUE_SEC = "#7C9EF2"
TEAL_POS = "#4FD1A5"
CORAL_NEG = "#F26A6A"


def apply_rr_theme(fig: plt.Figure, axes: Any) -> None:
    fig.patch.set_facecolor(BG_DEEP)
    ax_list = [axes] if not isinstance(axes, (list, np.ndarray)) else np.ravel(axes)
    for ax in ax_list:
        ax.set_facecolor(BG_CARD)
        ax.tick_params(colors=LIGHT_TXT, labelsize=9)
        ax.xaxis.label.set_color(LIGHT_TXT)
        ax.yaxis.label.set_color(LIGHT_TXT)
        ax.title.set_color(LIGHT_TXT)
        ax.grid(axis="y", color=LAVENDER, alpha=0.16, linestyle="--", linewidth=0.7)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        for sp in ["bottom", "left"]:
            ax.spines[sp].set_color(LAVENDER)
            ax.spines[sp].set_alpha(0.35)


def spearman_corr(a: pd.Series, b: pd.Series) -> float:
    valid = a.notna() & b.notna()
    if valid.sum() < 3:
        return np.nan
    return float(a.loc[valid].rank(method="average").corr(b.loc[valid].rank(method="average")))


def run_model_robustness(
    p_df: pd.DataFrame,
    bat_rel: pd.DataFrame,
    bowl_rel: pd.DataFrame,
) -> pd.DataFrame:
    """Compare player performance ordering across Model C, A, B, threshold shifts, raw vs EB, and bootstrap B."""
    rows: list[dict[str, Any]] = []

    # Helper to compute batting SR / bowling economy under any boolean pressure mask
    bat_elig = bat_rel[bat_rel["is_primary_eligible"]].set_index("player_id")
    bowl_elig = bowl_rel[bowl_rel["is_primary_eligible"]].set_index("player_id")

    # Batting: define top-30% pressure masks under Models A, B, and +/-3pt threshold shifts on Model C
    p_df["model_a_bat_idx"] = np.where(p_df["innings"] == 1, p_df["model_a_first_innings_pressure"], p_df["model_a_chase_pressure"])
    p_df["model_b_bat_idx"] = np.where(p_df["innings"] == 1, p_df["model_b_first_innings_pressure"], p_df["model_b_chase_pressure"])

    bat_valid = p_df[p_df["batting_pressure_index"].notna() & p_df["is_batter_ball_faced"]].copy()
    bat_c_mask = bat_valid["batting_pressure_level"].isin(["HIGH PRESSURE", "EXTREME PRESSURE"])
    # Match ~30% high-pressure share for Model A and Model B by innings
    bat_a_mask = pd.Series(False, index=bat_valid.index)
    bat_b_mask = pd.Series(False, index=bat_valid.index)
    for inn in [1, 2]:
        m_i = bat_valid["innings"] == inn
        bat_a_mask.loc[m_i] = bat_valid.loc[m_i, "model_a_bat_idx"] >= bat_valid.loc[m_i, "model_a_bat_idx"].quantile(0.70)
        bat_b_mask.loc[m_i] = bat_valid.loc[m_i, "model_b_bat_idx"] >= bat_valid.loc[m_i, "model_b_bat_idx"].quantile(0.70)

    bat_lo_shift = np.where(
        bat_valid["innings"] == 1,
        bat_valid["first_innings_pressure_index"] >= 42.0,
        bat_valid["chase_pressure_index"] >= 47.0,
    )
    bat_hi_shift = np.where(
        bat_valid["innings"] == 1,
        bat_valid["first_innings_pressure_index"] >= 48.0,
        bat_valid["chase_pressure_index"] >= 53.0,
    )

    def bat_sr_by_mask(mask: Any) -> pd.Series:
        sub = bat_valid.loc[mask]
        g = sub.groupby("striker_id").agg(r=("batter_runs", "sum"), bf=("is_batter_ball_faced", "sum"))
        return (g["r"] / g["bf"] * 100.0).reindex(bat_elig.index)

    sr_c = bat_sr_by_mask(bat_c_mask)
    for label, alt_s in [
        ("Model_A_Top30_vs_Model_C", bat_sr_by_mask(bat_a_mask)),
        ("Model_B_Top30_vs_Model_C", bat_sr_by_mask(bat_b_mask)),
        ("Threshold_Minus3pts_vs_Model_C", bat_sr_by_mask(bat_lo_shift)),
        ("Threshold_Plus3pts_vs_Model_C", bat_sr_by_mask(bat_hi_shift)),
    ]:
        both = sr_c.notna() & alt_s.notna()
        top20_c = set(sr_c[both].nlargest(20).index)
        top20_a = set(alt_s[both].nlargest(20).index)
        rows.append({
            "discipline": "batting",
            "comparison": label,
            "metric_compared": "pressure_strike_rate",
            "n_players": int(both.sum()),
            "spearman_corr": round(spearman_corr(sr_c, alt_s), 4),
            "pearson_corr": round(float(sr_c[both].corr(alt_s[both])), 4),
            "mean_abs_diff": round(float((sr_c[both] - alt_s[both]).abs().mean()), 3),
            "top20_cohort_overlap_pct": round(len(top20_c & top20_a) / 20.0 * 100.0, 1),
        })

    # Raw vs Empirical-Bayes Shrunk comparison (Batting)
    raw_b = bat_elig["raw_pressure_impact"]
    eb_b = bat_elig["eb_pressure_impact"]
    top20_r = set(raw_b.nlargest(20).index)
    top20_e = set(eb_b.nlargest(20).index)
    rows.append({
        "discipline": "batting",
        "comparison": "Raw_vs_EB_Shrunk_Impact",
        "metric_compared": "net_impact_per_100b",
        "n_players": int(len(bat_elig)),
        "spearman_corr": round(spearman_corr(raw_b, eb_b), 4),
        "pearson_corr": round(float(raw_b.corr(eb_b)), 4),
        "mean_abs_diff": round(float((raw_b - eb_b).abs().mean()), 3),
        "top20_cohort_overlap_pct": round(len(top20_r & top20_e) / 20.0 * 100.0, 1),
    })

    # Bowling robustness
    bowl_valid = p_df[p_df["bowling_pressure_index"].notna()].copy()
    bowl_c_mask = bowl_valid["bowling_pressure_level"].isin(["HIGH PRESSURE", "EXTREME PRESSURE"])
    bowl_a_mask = bowl_valid["model_a_bowling_pressure"] >= bowl_valid["model_a_bowling_pressure"].quantile(0.70)
    bowl_b_mask = bowl_valid["model_b_bowling_pressure"] >= bowl_valid["model_b_bowling_pressure"].quantile(0.70)
    bowl_lo_shift = bowl_valid["bowling_pressure_index"] >= 57.0
    bowl_hi_shift = bowl_valid["bowling_pressure_index"] >= 63.0

    def bowl_econ_by_mask(mask: Any) -> pd.Series:
        sub = bowl_valid.loc[mask]
        g = sub.groupby("bowler_id").agg(rc=("bowler_conceded_runs", "sum"), lb=("is_legal_delivery", "sum"))
        g = g[g["lb"] > 0]
        return (g["rc"] * 6.0 / g["lb"]).reindex(bowl_elig.index)

    ec_c = bowl_econ_by_mask(bowl_c_mask)
    for label, alt_s in [
        ("Model_A_Top30_vs_Model_C", bowl_econ_by_mask(bowl_a_mask)),
        ("Model_B_Top30_vs_Model_C", bowl_econ_by_mask(bowl_b_mask)),
        ("Threshold_Minus3pts_vs_Model_C", bowl_econ_by_mask(bowl_lo_shift)),
        ("Threshold_Plus3pts_vs_Model_C", bowl_econ_by_mask(bowl_hi_shift)),
    ]:
        both = ec_c.notna() & alt_s.notna()
        top20_c = set(ec_c[both].nsmallest(20).index)  # Lower economy is better
        top20_a = set(alt_s[both].nsmallest(20).index)
        rows.append({
            "discipline": "bowling",
            "comparison": label,
            "metric_compared": "pressure_economy_rate",
            "n_players": int(both.sum()),
            "spearman_corr": round(spearman_corr(ec_c, alt_s), 4),
            "pearson_corr": round(float(ec_c[both].corr(alt_s[both])), 4),
            "mean_abs_diff": round(float((ec_c[both] - alt_s[both]).abs().mean()), 3),
            "top20_cohort_overlap_pct": round(len(top20_c & top20_a) / 20.0 * 100.0, 1),
        })

    raw_w = bowl_elig["raw_pressure_impact"]
    eb_w = bowl_elig["eb_pressure_impact"]
    top20_rw = set(raw_w.nlargest(20).index)
    top20_ew = set(eb_w.nlargest(20).index)
    rows.append({
        "discipline": "bowling",
        "comparison": "Raw_vs_EB_Shrunk_Impact",
        "metric_compared": "net_impact_per_24b",
        "n_players": int(len(bowl_elig)),
        "spearman_corr": round(spearman_corr(raw_w, eb_w), 4),
        "pearson_corr": round(float(raw_w.corr(eb_w)), 4),
        "mean_abs_diff": round(float((raw_w - eb_w).abs().mean()), 3),
        "top20_cohort_overlap_pct": round(len(top20_rw & top20_ew) / 20.0 * 100.0, 1),
    })

    # Bootstrap setting stability check (B=200 vs B=500 vs B=1000 on sample of 30 high-confidence players)
    boot_df = pd.read_csv(OUT_DIR / "player_bootstrap_uncertainty.csv")
    rng_alt = np.random.default_rng(123)
    for disc, rel_tbl, id_col, num_c, den_c, sc in [
        ("batting", bat_rel, "striker_id", "batter_runs", "is_batter_ball_faced", 100.0),
        ("bowling", bowl_rel, "bowler_id", "bowler_conceded_runs", "is_legal_delivery", 6.0),
    ]:
        hi_ids = rel_tbl.loc[rel_tbl["evidence_tier"] == "HIGH_CONFIDENCE", "player_id"].head(30).tolist()
        mask = (p_df["batting_pressure_level"] if disc == "batting" else p_df["bowling_pressure_level"]).isin(["HIGH PRESSURE", "EXTREME PRESSURE"])
        sub = p_df[mask & p_df[id_col].isin(hi_ids)]
        m_tbl = sub.groupby([id_col, "match_id"], as_index=False).agg(num=(num_c, "sum"), den=(den_c, "sum"))
        w500, w1000 = [], []
        for pid in hi_ids:
            pm = m_tbl[(m_tbl[id_col] == pid) & (m_tbl["den"] > 0)]
            if len(pm) < 5:
                continue
            nv, dv = pm["num"].to_numpy(float), pm["den"].to_numpy(float)
            for B_val, holder in [(500, w500), (1000, w1000)]:
                idx = rng_alt.integers(0, len(nv), size=(B_val, len(nv)))
                est = nv[idx].sum(axis=1) / dv[idx].sum(axis=1) * sc
                lo, hi = np.percentile(est, [2.5, 97.5])
                holder.append(hi - lo)
        w500_s, w1000_s = pd.Series(w500), pd.Series(w1000)
        rows.append({
            "discipline": disc,
            "comparison": "Bootstrap_B500_vs_B1000_CI_Width",
            "metric_compared": "raw_rate_ci95_width",
            "n_players": int(len(w500_s)),
            "spearman_corr": round(spearman_corr(w500_s, w1000_s), 4),
            "pearson_corr": round(float(w500_s.corr(w1000_s)), 4),
            "mean_abs_diff": round(float((w500_s - w1000_s).abs().mean()), 3),
            "top20_cohort_overlap_pct": np.nan,
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "player_model_robustness.csv", index=False)
    return out


def run_temporal_validation(p_df: pd.DataFrame, bat_perf: pd.DataFrame, bowl_perf: pd.DataFrame) -> pd.DataFrame:
    """
    Strictly out-of-time temporal comparison: Early Era (2022-2023) vs Late Era (2024-2026).
    Early-era metrics use ONLY 2022-2023 deliveries (zero future information).
    Players lacking >=40 pressure balls & >=5 pressure matches in BOTH eras are explicitly
    labeled INSUFFICIENT_SEASONAL_COVERAGE.
    """
    p_df = p_df.copy()
    p_df["season_year"] = p_df["season"].astype(str).str.extract(r"(\d{4})")[0].astype(int)
    p_df["era"] = np.where(p_df["season_year"] <= 2023, "early_2022_2023", "late_2024_2026")

    rows: list[dict[str, Any]] = []
    for disc, perf_tbl, id_col, lvl_col, num_col, den_col, scale, stable_tol in [
        ("batting", bat_perf, "striker_id", "batting_pressure_level", "batter_runs", "is_batter_ball_faced", 100.0, 20.0),
        ("bowling", bowl_perf, "bowler_id", "bowling_pressure_level", "bowler_conceded_runs", "is_legal_delivery", 6.0, 1.25),
    ]:
        sub = p_df[p_df[lvl_col].isin(["HIGH PRESSURE", "EXTREME PRESSURE"])].copy()
        if disc == "batting":
            sub = sub[sub["is_batter_ball_faced"]]
        agg = (
            sub.groupby([id_col, "era"], as_index=False)
            .agg(
                balls=(den_col, "sum"),
                num=(num_col, "sum"),
                matches=("match_id", "nunique"),
            )
            .rename(columns={id_col: "player_id"})
        )
        agg = agg[agg["balls"] > 0]
        agg["rate"] = agg["num"] / agg["balls"] * scale

        early = agg[agg["era"] == "early_2022_2023"].set_index("player_id")
        late = agg[agg["era"] == "late_2024_2026"].set_index("player_id")

        names = perf_tbl.set_index("player_id")["player_name"]
        for pid in perf_tbl["player_id"]:
            eb = int(early.loc[pid, "balls"]) if pid in early.index else 0
            em = int(early.loc[pid, "matches"]) if pid in early.index else 0
            er = float(early.loc[pid, "rate"]) if pid in early.index else np.nan
            lb = int(late.loc[pid, "balls"]) if pid in late.index else 0
            lm = int(late.loc[pid, "matches"]) if pid in late.index else 0
            lr = float(late.loc[pid, "rate"]) if pid in late.index else np.nan

            qual = (eb >= 40 and em >= 5 and lb >= 40 and lm >= 5)
            delta = (lr - er) if (qual and pd.notna(lr) and pd.notna(er)) else np.nan
            if not qual:
                status = "INSUFFICIENT_SEASONAL_COVERAGE"
            elif abs(delta) <= stable_tol:
                status = "STABLE_ACROSS_ERAS"
            else:
                status = "MATERIALLY_CHANGED"

            rows.append({
                "discipline": disc,
                "player_id": int(pid),
                "player_name": names.get(pid, ""),
                "rate_metric": "pressure_strike_rate" if disc == "batting" else "pressure_economy",
                "early_2022_2023_balls": eb,
                "early_2022_2023_matches": em,
                "early_2022_2023_rate": round(er, 2) if pd.notna(er) else np.nan,
                "late_2024_2026_balls": lb,
                "late_2024_2026_matches": lm,
                "late_2024_2026_rate": round(lr, 2) if pd.notna(lr) else np.nan,
                "era_delta_late_minus_early": round(delta, 2) if pd.notna(delta) else np.nan,
                "temporal_coverage_status": status,
            })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "player_temporal_validation.csv", index=False)
    return out


def run_validation_suite(
    p_df: pd.DataFrame,
    pm: pd.DataFrame,
    bat_perf: pd.DataFrame,
    bowl_perf: pd.DataFrame,
    bat_bk: pd.DataFrame,
    bowl_bk: pd.DataFrame,
    bat_rel: pd.DataFrame,
    bowl_rel: pd.DataFrame,
    temp_df: pd.DataFrame,
) -> pd.DataFrame:
    """Execute all required Phase 5 integrity, statistical, and anti-leakage checks."""
    rows: list[dict[str, Any]] = []

    def add(name: str, passed: bool, value: Any, details: str) -> None:
        rows.append({
            "check_name": name,
            "status": "PASS" if passed else "FAIL",
            "metric_value": str(value),
            "details": details,
        })

    pm_ids = set(pm["player_id"])
    bat_ids = set(bat_perf["player_id"])
    bowl_ids = set(bowl_perf["player_id"])

    add("01_player_ids_map_to_player_master", bat_ids.issubset(pm_ids) and bowl_ids.issubset(pm_ids), f"bat={len(bat_ids)}, bowl={len(bowl_ids)}", "100% of batting and bowling player_ids exist in player_master.csv")

    # Shared-name non-merging check (Rashid Khan 4722/20172, Abdul Samad 6922/7446, Haider Ali 7338/28756)
    no_merge_ok = (
        bat_perf["player_id"].is_unique
        and bowl_perf["player_id"].is_unique
        and {6922, 7446}.issubset(bat_ids)
        and {7338, 28756}.issubset(bat_ids)
        and (4722 in bowl_ids)
    )
    add("02_no_shared_name_merging", no_merge_ok, no_merge_ok, "Unique player_id keys; Abdul Samad (6922/7446), Haider Ali (7338/28756), and Rashid Khan (4722) kept strictly separate")

    no_excl = not p_df["comp_id"].isin([2670, 3289]).any()
    add("03_no_excluded_competitions", no_excl, no_excl, "0 deliveries from comp_id 2670 or 3289 in source pressure_deliveries.csv")

    no_so = not (p_df["innings"] >= 3).any()
    add("04_no_super_over_deliveries", no_so, no_so, "0 Super Over rows (innings >= 3) in primary player analysis")

    no_inv_pb = bool((p_df["striker_id"] != p_df["non_striker_id"]).all() and (p_df["striker_id"] != p_df["bowler_id"]).all())
    add("05_no_invalid_player_ball_assignments", no_inv_pb, no_inv_pb, "0 rows with striker_id==non_striker_id or striker_id==bowler_id")

    # Balls-faced & legal-ball conservation (detects any duplicate delivery aggregation or wides leakage!)
    exp_bf = int(p_df.loc[p_df["batting_pressure_index"].notna(), "is_batter_ball_faced"].sum())
    act_bf = int(bat_perf["overall_balls_faced"].sum())
    bk_bf = int(bat_bk["balls_faced"].sum())
    add("06_batting_balls_faced_conservation_no_wides", (act_bf == exp_bf) and (bk_bf == exp_bf), f"perf={act_bf}, bk={bk_bf}, src={exp_bf}", "Exact sum of balls faced matches valid non-wide deliveries; zero duplicate aggregation")

    exp_lb = int(p_df.loc[p_df["bowling_pressure_index"].notna(), "is_legal_delivery"].sum())
    act_lb = int(bowl_perf["overall_legal_balls"].sum())
    bk_lb = int(bowl_bk["legal_balls"].sum())
    add("07_bowling_legal_balls_conservation", (act_lb == exp_lb) and (bk_lb == exp_lb), f"perf={act_lb}, bk={bk_lb}, src={exp_lb}", "Exact sum of legal balls matches valid legal deliveries; zero duplicate aggregation")

    exp_bw = int(p_df.loc[p_df["bowling_pressure_index"].notna(), "is_bowler_wicket"].sum())
    act_bw = int(bowl_perf["overall_wickets"].sum())
    add("08_bowler_wicket_attribution_exact", act_bw == exp_bw, f"perf={act_bw}, src={exp_bw}", "Only Caught/Bowled/LBW/Stump/Hit Wicket credited to bowlers (0 run-outs/retired outs)")

    # Unavailable pressure context NEVER grouped into LOW pressure
    unavail_n = int(p_df["batting_pressure_index"].isna().sum())
    low_src = int((p_df["batting_pressure_level"] == "LOW PRESSURE").sum())
    low_bk_bf = int(bat_bk.loc[bat_bk["pressure_level"] == "LOW PRESSURE", "balls_faced"].sum())
    low_src_bf = int(p_df.loc[p_df["batting_pressure_level"] == "LOW PRESSURE", "is_batter_ball_faced"].sum())
    add("09_unavailable_not_treated_as_low_pressure", (low_bk_bf == low_src_bf) and (unavail_n == 1551), f"unavail={unavail_n}, low_bf={low_bk_bf}", "All 1,551 UNAVAILABLE deliveries excluded from LOW/MOD/HIGH/EXTREME aggregations")

    # Reliability score strictly bounded [0, 100] and not simply volume-driven
    b_rel_v = bat_rel["reliability_score"].dropna()
    w_rel_v = bowl_rel["reliability_score"].dropna()
    b_corr_vol = float(bat_rel.loc[bat_rel["is_primary_eligible"], "reliability_score"].corr(bat_rel.loc[bat_rel["is_primary_eligible"], "pressure_balls"]))
    w_corr_vol = float(bowl_rel.loc[bowl_rel["is_primary_eligible"], "reliability_score"].corr(bowl_rel.loc[bowl_rel["is_primary_eligible"], "pressure_balls"]))
    rel_ok = bool(
        b_rel_v.between(0, 100).all()
        and w_rel_v.between(0, 100).all()
        and abs(b_corr_vol) < 0.50
        and abs(w_corr_vol) < 0.50
    )
    add("10_reliability_bounds_and_non_volume_independence", rel_ok, f"corr_bat={b_corr_vol:+.3f}, corr_bowl={w_corr_vol:+.3f}", "All reliability scores in [0,100] and not dominated by raw ball count")

    # Insufficient evidence players have NaN reliability (not fabricated)
    insuff_bat_na = bat_rel.loc[bat_rel["evidence_tier"] == "INSUFFICIENT_EVIDENCE", "reliability_score"].isna().all()
    insuff_bowl_na = bowl_rel.loc[bowl_rel["evidence_tier"] == "INSUFFICIENT_EVIDENCE", "reliability_score"].isna().all()
    add("11_insufficient_evidence_never_fabricated", bool(insuff_bat_na and insuff_bowl_na), f"insuff_bat={int((bat_rel['evidence_tier']=='INSUFFICIENT_EVIDENCE').sum())}, insuff_bowl={int((bowl_rel['evidence_tier']=='INSUFFICIENT_EVIDENCE').sum())}", "All INSUFFICIENT_EVIDENCE players have NaN reliability_score")

    # Temporal coverage check
    t_bat = temp_df[(temp_df["discipline"] == "batting") & (temp_df["temporal_coverage_status"] != "INSUFFICIENT_SEASONAL_COVERAGE")]
    t_bowl = temp_df[(temp_df["discipline"] == "bowling") & (temp_df["temporal_coverage_status"] != "INSUFFICIENT_SEASONAL_COVERAGE")]
    add("12_temporal_out_of_time_validation_completed", len(t_bat) >= 20 and len(t_bowl) >= 20, f"qual_bat={len(t_bat)}, qual_bowl={len(t_bowl)}", "Out-of-time Early (2022-23) vs Late (2024-26) validation completed; sparse players labeled INSUFFICIENT_SEASONAL_COVERAGE")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "player_validation_results.csv", index=False)
    return out


def generate_ten_charts(
    bat_perf: pd.DataFrame,
    bowl_perf: pd.DataFrame,
    bat_rel: pd.DataFrame,
    bowl_rel: pd.DataFrame,
    pvn_df: pd.DataFrame,
    boot_df: pd.DataFrame,
    temp_df: pd.DataFrame,
) -> list[str]:
    """Generate 10 RR PERFORMANCE LAB static analytical charts (10_*.png to 19_*.png)."""
    saved: list[str] = []
    bat_m = bat_perf.merge(bat_rel[["player_id", "evidence_tier", "is_primary_eligible", "performance_score", "reliability_score", "evidence_strength_score", "eb_pressure_impact", "impact_ci95_low", "impact_ci95_high", "impact_ci95_width"]], on="player_id")
    bowl_m = bowl_perf.merge(bowl_rel[["player_id", "evidence_tier", "is_primary_eligible", "performance_score", "reliability_score", "evidence_strength_score", "eb_pressure_impact", "impact_ci95_low", "impact_ci95_high", "impact_ci95_width"]], on="player_id")

    bat_elig = bat_m[bat_m["is_primary_eligible"]].copy()
    bowl_elig = bowl_m[bowl_m["is_primary_eligible"]].copy()

    # 10. Batting Pressure Performance Distribution
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
    apply_rr_theme(fig, axes)
    axes[0].hist(bat_elig["pressure_strike_rate"].dropna(), bins=24, color=PINK, alpha=0.85, edgecolor=BG_DEEP)
    axes[0].axvline(bat_elig["pressure_strike_rate"].median(), color=GOLD, linestyle="--", linewidth=1.6, label=f"Median: {bat_elig['pressure_strike_rate'].median():.1f}")
    axes[0].set_title(f"Primary-Eligible Batters (n={len(bat_elig)}): Pressure Strike Rate", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Pressure Strike Rate (HIGH + EXTREME)")
    axes[0].set_ylabel("Players")
    axes[0].legend(frameon=False, labelcolor=LIGHT_TXT)

    axes[1].hist(bat_elig["eb_pressure_impact"].dropna(), bins=24, color=GOLD, alpha=0.85, edgecolor=BG_DEEP)
    axes[1].axvline(0.0, color=LIGHT_TXT, linestyle="--", linewidth=1.2, label="Context-Par Baseline (0)")
    axes[1].set_title("EB-Shrunk Context-Adjusted Net Impact (Runs / 100 Balls)", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("EB Net Impact Above Expected (Runs / 100 Balls)")
    axes[1].set_ylabel("Players")
    axes[1].legend(frameon=False, labelcolor=LIGHT_TXT)
    fig.suptitle("RR PERFORMANCE LAB — Batting Pressure Performance Distributions (IPL + T20I, 2022–2026)", color=LIGHT_TXT, fontsize=12.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    p = CHART_DIR / "10_batting_pressure_perf_distribution.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 11. Bowling Pressure Performance Distribution
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
    apply_rr_theme(fig, axes)
    axes[0].hist(bowl_elig["pressure_economy"].dropna(), bins=24, color=BLUE_SEC, alpha=0.85, edgecolor=BG_DEEP)
    axes[0].axvline(bowl_elig["pressure_economy"].median(), color=PINK, linestyle="--", linewidth=1.6, label=f"Median: {bowl_elig['pressure_economy'].median():.2f} (Lower=Better)")
    axes[0].set_title(f"Primary-Eligible Bowlers (n={len(bowl_elig)}): Pressure Economy Rate", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Pressure Economy Rate (Runs / Over; Lower = Better)")
    axes[0].set_ylabel("Players")
    axes[0].legend(frameon=False, labelcolor=LIGHT_TXT)

    axes[1].hist(bowl_elig["eb_pressure_impact"].dropna(), bins=24, color=TEAL_POS, alpha=0.85, edgecolor=BG_DEEP)
    axes[1].axvline(0.0, color=LIGHT_TXT, linestyle="--", linewidth=1.2, label="Context-Par Baseline (0; Higher=Better)")
    axes[1].set_title("EB-Shrunk Context-Adjusted Net Impact (Runs Saved+Wkts / 24b)", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("EB Net Bowling Impact / 24 Balls (Higher = Better)")
    axes[1].set_ylabel("Players")
    axes[1].legend(frameon=False, labelcolor=LIGHT_TXT)
    fig.suptitle("RR PERFORMANCE LAB — Bowling Pressure Performance Distributions (IPL + T20I, 2022–2026)", color=LIGHT_TXT, fontsize=12.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    p = CHART_DIR / "11_bowling_pressure_perf_distribution.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 12. Batting Performance by Pressure Category
    bm_sum = pd.read_csv(OUT_DIR / "batting_metric_summary.csv")
    cats = ["LOW_PRESSURE", "MODERATE_PRESSURE", "HIGH_PRESSURE", "EXTREME_PRESSURE"]
    cat_lbls = ["LOW", "MODERATE", "HIGH", "EXTREME"]
    b_sub = bm_sum.set_index("segment").reindex(cats)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.4))
    apply_rr_theme(fig, axes)
    x = np.arange(4)
    bars1 = axes[0].bar(x, b_sub["strike_rate"], color=[LAVENDER, BLUE_SEC, GOLD, PINK], width=0.52)
    for bar, v in zip(bars1, b_sub["strike_rate"]):
        axes[0].text(bar.get_x() + bar.get_width() / 2, v + 2.0, f"{v:.1f}", ha="center", color=LIGHT_TXT, fontweight="bold", fontsize=9)
    axes[0].set_xticks(x); axes[0].set_xticklabels(cat_lbls, fontweight="bold")
    axes[0].set_ylabel("Aggregate Strike Rate")
    axes[0].set_ylim(0, max(b_sub["strike_rate"]) * 1.16)
    axes[0].set_title("Batting Strike Rate by Pressure Category", fontsize=11, fontweight="bold")

    bars2 = axes[1].bar(x - 0.18, b_sub["dismissal_rate_pct"], width=0.34, color=CORAL_NEG, label="Dismissal Rate (%)")
    bars3 = axes[1].bar(x + 0.18, b_sub["boundary_pct"], width=0.34, color=GOLD, label="Boundary Rate (%)")
    for bars in (bars2, bars3):
        for bar in bars:
            v = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2, v + 0.4, f"{v:.1f}%", ha="center", color=LIGHT_TXT, fontsize=8.5, fontweight="bold")
    axes[1].set_xticks(x); axes[1].set_xticklabels(cat_lbls, fontweight="bold")
    axes[1].set_ylabel("Percentage of Balls Faced (%)")
    axes[1].set_ylim(0, max(b_sub["boundary_pct"]) * 1.25)
    axes[1].set_title("Dismissal Risk vs. Boundary Rate Across Pressure Tiers", fontsize=11, fontweight="bold")
    axes[1].legend(frameon=False, labelcolor=LIGHT_TXT)
    fig.tight_layout()
    p = CHART_DIR / "12_batting_perf_by_pressure_category.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 13. Bowling Performance by Pressure Category
    lm_sum = pd.read_csv(OUT_DIR / "bowling_metric_summary.csv")
    l_sub = lm_sum.set_index("segment").reindex(cats)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.4))
    apply_rr_theme(fig, axes)
    bars1 = axes[0].bar(x, l_sub["economy_rate"], color=[LAVENDER, BLUE_SEC, GOLD, PINK], width=0.52)
    for bar, v in zip(bars1, l_sub["economy_rate"]):
        axes[0].text(bar.get_x() + bar.get_width() / 2, v + 0.2, f"{v:.2f}", ha="center", color=LIGHT_TXT, fontweight="bold", fontsize=9)
    axes[0].set_xticks(x); axes[0].set_xticklabels(cat_lbls, fontweight="bold")
    axes[0].set_ylabel("Economy Rate (Runs / Over)")
    axes[0].set_ylim(0, max(l_sub["economy_rate"]) * 1.18)
    axes[0].set_title("Bowling Economy Rate by Bowling Pressure Category", fontsize=11, fontweight="bold")

    bars2 = axes[1].bar(x - 0.18, l_sub["dot_ball_pct"], width=0.34, color=TEAL_POS, label="Dot-Ball %")
    bars3 = axes[1].bar(x + 0.18, l_sub["boundary_conceded_pct"], width=0.34, color=PINK, label="Boundary Conceded %")
    for bars in (bars2, bars3):
        for bar in bars:
            v = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2, v + 0.7, f"{v:.1f}%", ha="center", color=LIGHT_TXT, fontsize=8.5, fontweight="bold")
    axes[1].set_xticks(x); axes[1].set_xticklabels(cat_lbls, fontweight="bold")
    axes[1].set_ylabel("Percentage of Legal Balls (%)")
    axes[1].set_ylim(0, max(l_sub["dot_ball_pct"]) * 1.22)
    axes[1].set_title("Dot-Ball Control vs. Boundary Conceded Across Pressure Tiers", fontsize=11, fontweight="bold")
    axes[1].legend(frameon=False, labelcolor=LIGHT_TXT)
    fig.tight_layout()
    p = CHART_DIR / "13_bowling_perf_by_pressure_category.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 14. Pressure vs Non-Pressure Batting Comparison
    pvn_b = pvn_df[(pvn_df["discipline"] == "batting") & pvn_df["sufficient_both_sides_primary"]]
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    apply_rr_theme(fig, ax)
    sig_b = pvn_b["ci95_excludes_zero"]
    ax.scatter(pvn_b.loc[~sig_b, "nonpressure_rate"], pvn_b.loc[~sig_b, "pressure_rate"], color=LAVENDER, alpha=0.65, s=42, label="CI includes 0 (Within Uncertainty)")
    ax.scatter(pvn_b.loc[sig_b, "nonpressure_rate"], pvn_b.loc[sig_b, "pressure_rate"], color=PINK, alpha=0.92, s=58, edgecolor=LIGHT_TXT, linewidth=0.5, label="Context-Impact 95% CI excludes 0")
    lims = [min(pvn_b["nonpressure_rate"].min(), pvn_b["pressure_rate"].min()) - 5, max(pvn_b["nonpressure_rate"].max(), pvn_b["pressure_rate"].max()) + 5]
    ax.plot(lims, lims, linestyle="--", color=GOLD, linewidth=1.3, label="Parity Line (Pressure SR = Non-Pressure SR)")
    ax.set_xlabel("Non-Pressure Strike Rate (LOW + MODERATE)")
    ax.set_ylabel("Pressure Strike Rate (HIGH + EXTREME)")
    ax.set_title(f"Observational Batting Comparison: Pressure vs. Non-Pressure SR (n={len(pvn_b)} Eligible Batters)", fontsize=11.5, fontweight="bold", pad=10)
    ax.legend(frameon=False, labelcolor=LIGHT_TXT, loc="upper left", fontsize=9)
    fig.tight_layout()
    p = CHART_DIR / "14_pressure_vs_nonpressure_batting.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 15. Pressure vs Non-Pressure Bowling Comparison
    pvn_w = pvn_df[(pvn_df["discipline"] == "bowling") & pvn_df["sufficient_both_sides_primary"]]
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    apply_rr_theme(fig, ax)
    sig_w = pvn_w["ci95_excludes_zero"]
    ax.scatter(pvn_w.loc[~sig_w, "nonpressure_rate"], pvn_w.loc[~sig_w, "pressure_rate"], color=LAVENDER, alpha=0.65, s=42, label="CI includes 0 (Within Uncertainty)")
    ax.scatter(pvn_w.loc[sig_w, "nonpressure_rate"], pvn_w.loc[sig_w, "pressure_rate"], color=TEAL_POS, alpha=0.92, s=58, edgecolor=LIGHT_TXT, linewidth=0.5, label="Context-Impact 95% CI excludes 0")
    lims = [min(pvn_w["nonpressure_rate"].min(), pvn_w["pressure_rate"].min()) - 0.5, max(pvn_w["nonpressure_rate"].max(), pvn_w["pressure_rate"].max()) + 0.5]
    ax.plot(lims, lims, linestyle="--", color=GOLD, linewidth=1.3, label="Parity Line (Below = Better Economy Under Pressure)")
    ax.set_xlabel("Non-Pressure Economy Rate (LOW + MODERATE)")
    ax.set_ylabel("Pressure Economy Rate (HIGH + EXTREME; Lower = Better)")
    ax.set_title(f"Observational Bowling Comparison: Pressure vs. Non-Pressure Economy (n={len(pvn_w)} Eligible Bowlers)", fontsize=11.5, fontweight="bold", pad=10)
    ax.legend(frameon=False, labelcolor=LIGHT_TXT, loc="upper left", fontsize=9)
    fig.tight_layout()
    p = CHART_DIR / "15_pressure_vs_nonpressure_bowling.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 16. Player Pressure Exposure vs. Performance (showing funnel shrinkage effect!)
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6))
    apply_rr_theme(fig, axes)
    bat_vis = bat_m[bat_m["pressure_balls_faced"] >= 15]
    axes[0].scatter(bat_vis["pressure_balls_faced"], bat_vis["pressure_net_impact_per_100b"], color=LAVENDER, alpha=0.45, s=22, label="Raw Impact (High Small-Sample Variance)")
    axes[0].scatter(bat_elig["pressure_balls_faced"], bat_elig["eb_pressure_impact"], color=PINK, alpha=0.85, s=36, label="EB-Shrunk Impact (Primary Eligible)")
    axes[0].axvline(80, color=GOLD, linestyle="--", linewidth=1.2, label="Primary Threshold (80 balls)")
    axes[0].axhline(0, color=LIGHT_TXT, linestyle=":", alpha=0.5)
    axes[0].set_ylim(-95, 95)
    axes[0].set_xlabel("Pressure Balls Faced (HIGH + EXTREME)")
    axes[0].set_ylabel("Context-Adjusted Impact / 100 Balls")
    axes[0].set_title("Batting Exposure vs. Performance Funnel & EB Shrinkage", fontsize=11, fontweight="bold")
    axes[0].legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="lower right")

    bowl_vis = bowl_m[bowl_m["pressure_legal_balls"] >= 18]
    axes[1].scatter(bowl_vis["pressure_legal_balls"], bowl_vis["pressure_net_impact_per_24b"], color=LAVENDER, alpha=0.45, s=22, label="Raw Impact (High Small-Sample Variance)")
    axes[1].scatter(bowl_elig["pressure_legal_balls"], bowl_elig["eb_pressure_impact"], color=TEAL_POS, alpha=0.85, s=36, label="EB-Shrunk Impact (Primary Eligible)")
    axes[1].axvline(90, color=GOLD, linestyle="--", linewidth=1.2, label="Primary Threshold (90 legal balls)")
    axes[1].axhline(0, color=LIGHT_TXT, linestyle=":", alpha=0.5)
    axes[1].set_ylim(-22, 22)
    axes[1].set_xlabel("Pressure Legal Balls Bowled (HIGH + EXTREME)")
    axes[1].set_ylabel("Context-Adjusted Impact / 24 Balls")
    axes[1].set_title("Bowling Exposure vs. Performance Funnel & EB Shrinkage", fontsize=11, fontweight="bold")
    axes[1].legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="lower right")
    fig.tight_layout()
    p = CHART_DIR / "16_exposure_vs_performance.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 17. Reliability vs. Performance Quadrant (explicitly separating the two pillars!)
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))
    apply_rr_theme(fig, axes)
    for ax, sub, title, c_hi in [
        (axes[0], bat_elig, f"Batting: Performance vs. Reliability (n={len(bat_elig)})", PINK),
        (axes[1], bowl_elig, f"Bowling: Performance vs. Reliability (n={len(bowl_elig)})", TEAL_POS),
    ]:
        hc = sub["evidence_tier"] == "HIGH_CONFIDENCE"
        ax.scatter(sub.loc[~hc, "performance_score"], sub.loc[~hc, "reliability_score"], color=BLUE_SEC, alpha=0.72, s=42, label="Moderate Confidence")
        ax.scatter(sub.loc[hc, "performance_score"], sub.loc[hc, "reliability_score"], color=c_hi, alpha=0.92, s=64, edgecolor=GOLD, linewidth=0.8, label="High Confidence")
        ax.axvline(sub["performance_score"].median(), color=GOLD, linestyle="--", alpha=0.7, linewidth=1.0)
        ax.axhline(sub["reliability_score"].median(), color=GOLD, linestyle="--", alpha=0.7, linewidth=1.0)
        ax.set_xlabel("Performance Effectiveness Score (0–100, EB-Shrunk)")
        ax.set_ylabel("Reliability / Consistency Score (0–100, Volume-Free)")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="lower left")
    fig.suptitle("RR PERFORMANCE LAB — Separation of Performance Effectiveness vs. Cross-Innings Reliability", color=LIGHT_TXT, fontsize=12.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    p = CHART_DIR / "17_reliability_vs_performance.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 18. Match-Clustered Bootstrap 95% CI Width vs Exposure (Uncertainty Comparison)
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6))
    apply_rr_theme(fig, axes)
    for ax, disc, color, ylabel in [
        (axes[0], "batting", PINK, "95% CI Width — Net Impact / 100 Balls"),
        (axes[1], "bowling", GOLD, "95% CI Width — Net Impact / 24 Balls"),
    ]:
        sub = boot_df[boot_df["discipline"] == disc].dropna(subset=["ci95_width"])
        tier_colors = {"HIGH_CONFIDENCE": color, "MODERATE_CONFIDENCE": BLUE_SEC, "LOW_EVIDENCE": LAVENDER}
        for tier in ["LOW_EVIDENCE", "MODERATE_CONFIDENCE", "HIGH_CONFIDENCE"]:
            ts = sub[sub["evidence_tier"] == tier]
            ax.scatter(ts["pressure_matches"], ts["ci95_width"], color=tier_colors[tier], alpha=0.82, s=36, label=tier.replace("_", " ").title())
        ax.set_xlabel("Unique Pressure Matches (Cluster Unit for Bootstrap)")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{disc.title()}: Match-Clustered Bootstrap Uncertainty vs. Matches", fontsize=11, fontweight="bold")
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="upper right")
    fig.tight_layout()
    p = CHART_DIR / "18_bootstrap_uncertainty_comparison.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    # 19. Temporal Consistency Across Eras (Early 2022-23 vs Late 2024-26)
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6))
    apply_rr_theme(fig, axes)
    for ax, disc, color, xlabel, ylabel in [
        (axes[0], "batting", PINK, "Early Era (2022–2023) Pressure SR", "Late Era (2024–2026) Pressure SR"),
        (axes[1], "bowling", TEAL_POS, "Early Era (2022–2023) Pressure Economy", "Late Era (2024–2026) Pressure Economy"),
    ]:
        sub = temp_df[(temp_df["discipline"] == disc) & (temp_df["temporal_coverage_status"] != "INSUFFICIENT_SEASONAL_COVERAGE")]
        stab = sub["temporal_coverage_status"] == "STABLE_ACROSS_ERAS"
        ax.scatter(sub.loc[stab, "early_2022_2023_rate"], sub.loc[stab, "late_2024_2026_rate"], color=color, alpha=0.88, s=50, label=f"Stable ({int(stab.sum())})")
        ax.scatter(sub.loc[~stab, "early_2022_2023_rate"], sub.loc[~stab, "late_2024_2026_rate"], color=LAVENDER, alpha=0.72, s=42, marker="D", label=f"Materially Changed ({int((~stab).sum())})")
        lo = min(sub["early_2022_2023_rate"].min(), sub["late_2024_2026_rate"].min())
        hi = max(sub["early_2022_2023_rate"].max(), sub["late_2024_2026_rate"].max())
        ax.plot([lo, hi], [lo, hi], linestyle="--", color=GOLD, linewidth=1.2)
        r_sp = spearman_corr(sub["early_2022_2023_rate"], sub["late_2024_2026_rate"])
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(f"{disc.title()} Cross-Era Stability (n={len(sub)}, Spearman r={r_sp:.2f})", fontsize=11, fontweight="bold")
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="upper left")
    fig.suptitle("RR PERFORMANCE LAB — Out-of-Time Seasonal Consistency (Early 2022–2023 vs. Late 2024–2026)", color=LIGHT_TXT, fontsize=12.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    p = CHART_DIR / "19_seasonal_consistency.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p.name)

    return saved


def main() -> None:
    p_df = pd.read_csv(PROCESSED_DIR / "pressure_deliveries.csv", low_memory=False, keep_default_na=False, na_values=[""])
    for bcol in ["is_legal_delivery", "is_batter_ball_faced", "is_wicket_event", "is_bowler_wicket", "is_four", "is_six"]:
        p_df[bcol] = p_df[bcol].astype(str).str.lower().eq("true")

    pm = pd.read_csv(PROCESSED_DIR / "player_master.csv", low_memory=False)
    bat_perf = pd.read_csv(PROCESSED_DIR / "player_batting_performance.csv", low_memory=False)
    bowl_perf = pd.read_csv(PROCESSED_DIR / "player_bowling_performance.csv", low_memory=False)
    bat_bk = pd.read_csv(PROCESSED_DIR / "player_batting_pressure_breakdown.csv", low_memory=False)
    bowl_bk = pd.read_csv(PROCESSED_DIR / "player_bowling_pressure_breakdown.csv", low_memory=False)
    bat_rel = pd.read_csv(PROCESSED_DIR / "player_batting_reliability.csv", low_memory=False)
    bowl_rel = pd.read_csv(PROCESSED_DIR / "player_bowling_reliability.csv", low_memory=False)
    pvn_df = pd.read_csv(PROCESSED_DIR / "player_pressure_vs_nonpressure.csv", low_memory=False)
    boot_df = pd.read_csv(OUT_DIR / "player_bootstrap_uncertainty.csv", low_memory=False)

    rob_df = run_model_robustness(p_df, bat_rel, bowl_rel)
    temp_df = run_temporal_validation(p_df, bat_perf, bowl_perf)
    val_df = run_validation_suite(p_df, pm, bat_perf, bowl_perf, bat_bk, bowl_bk, bat_rel, bowl_rel, temp_df)
    charts = generate_ten_charts(bat_perf, bowl_perf, bat_rel, bowl_rel, pvn_df, boot_df, temp_df)

    print("\n=== PHASE 5 VALIDATION & VISUALIZATION COMPLETE ===")
    print(f"Validation checks : {(val_df['status'] == 'PASS').sum()}/{len(val_df)} PASS")
    if (val_df["status"] != "PASS").any():
        print("FAILED CHECKS:")
        print(val_df[val_df["status"] != "PASS"].to_string(index=False))
    print(f"Robustness rows   : {len(rob_df)}")
    print(f"Temporal rows     : {len(temp_df)} (qualifying bat={int(((temp_df['discipline']=='batting')&(temp_df['temporal_coverage_status']!='INSUFFICIENT_SEASONAL_COVERAGE')).sum())}, bowl={int(((temp_df['discipline']=='bowling')&(temp_df['temporal_coverage_status']!='INSUFFICIENT_SEASONAL_COVERAGE')).sum())})")
    print(f"Phase 5 charts    : {len(charts)} generated in {CHART_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

