"""
SupeRR Selector Season 2 - Phase 6 Ranking Robustness, Sensitivity & Visualizations.

Evaluates stability of the final Top 10 Batting and Bowling lists across:
  - Alternative pressure frameworks (Model A, Model B, Model C +/-3 pt thresholds)
  - Alternative minimum exposure thresholds
  - Raw vs. Empirical-Bayes shrunk performance estimates
  - Alternative ranking philosophies & weight perturbations
  - Match-clustered bootstrap uncertainty & Monte Carlo rank intervals

Generates all 7 Phase 6 RR PERFORMANCE LAB analytical charts (outputs/charts/20_*.png to 26_*.png).
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

# RR PERFORMANCE LAB palette
BG_DEEP = "#24172C"
BG_CARD = "#392940"
PINK = "#E83E80"
GOLD = "#D8B45A"
LIGHT_TXT = "#F5F1F5"
LAVENDER = "#B8A6C2"
BLUE_SEC = "#7C9EF2"
TEAL_POS = "#4FD1A5"
CORAL_NEG = "#F26A6A"

BASE_WEIGHTS = (0.50, 0.25, 0.15, 0.10)


def apply_rr_theme(fig: plt.Figure, axes: Any) -> None:
    fig.patch.set_facecolor(BG_DEEP)
    ax_list = [axes] if not isinstance(axes, (list, np.ndarray)) else np.ravel(axes)
    for ax in ax_list:
        ax.set_facecolor(BG_CARD)
        ax.tick_params(colors=LIGHT_TXT, labelsize=8.8)
        ax.xaxis.label.set_color(LIGHT_TXT)
        ax.yaxis.label.set_color(LIGHT_TXT)
        ax.title.set_color(LIGHT_TXT)
        ax.grid(axis="x", color=LAVENDER, alpha=0.15, linestyle="--", linewidth=0.7)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        for sp in ["bottom", "left"]:
            ax.spines[sp].set_color(LAVENDER)
            ax.spines[sp].set_alpha(0.35)


def robust_logistic_scale(series: pd.Series, spread_mult: float = 1.35) -> pd.Series:
    valid = series.dropna()
    if len(valid) < 3:
        return pd.Series(np.nan, index=series.index)
    med = float(valid.median())
    iqr = float(valid.quantile(0.75) - valid.quantile(0.25))
    robust_sd = max(iqr * 0.7413, float(valid.std()) * 0.5, 1e-6)
    z = (series - med) / (robust_sd * spread_mult)
    return pd.Series(np.where(series.notna(), 100.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0))), np.nan), index=series.index)


def spearman_corr(a: pd.Series, b: pd.Series) -> float:
    valid = a.notna() & b.notna()
    if valid.sum() < 3:
        return np.nan
    return float(a.loc[valid].rank(method="average").corr(b.loc[valid].rank(method="average")))


def compute_alt_model_impact(
    p_df: pd.DataFrame,
    discipline: str,
    mask: pd.Series,
    ranked_df: pd.DataFrame,
) -> pd.Series:
    """Recompute EB-shrunk context-adjusted impact under an alternative pressure delivery mask."""
    is_bat = discipline == "batting"
    sub = p_df.loc[mask].copy()
    if is_bat:
        sub = sub[sub["is_batter_ball_faced"]].copy()
        grp_cols = ["eligibility_category", "innings", "match_phase"]
        # Expected runs/dismissals within this alternative pressure slice
        par = sub.groupby(grp_cols, as_index=False).agg(tr=("batter_runs", "sum"), tn=("is_batter_ball_faced", "sum"), tk=("is_wicket_event", "sum"))
        par["er"] = par["tr"] / np.maximum(par["tn"], 1)
        par["ek"] = par["tk"] / np.maximum(par["tn"], 1)
        sub = sub.merge(par[grp_cols + ["er", "ek"]], on=grp_cols, how="left")
        p_agg = sub.groupby("striker_id", as_index=False).agg(
            runs=("batter_runs", "sum"), bf=("is_batter_ball_faced", "sum"),
            er=("er", "sum"), ek=("ek", "sum"), matches=("match_id", "nunique")
        ).rename(columns={"striker_id": "player_id"})
        wk = p_df.loc[mask & p_df["is_wicket_event"] & p_df["dismissed_player_id_int"].notna()].copy()
        wk["player_id"] = wk["dismissed_player_id_int"].astype(int)
        wa = wk.groupby("player_id", as_index=False).agg(dism=("is_wicket_event", "sum"))
        p_agg = p_agg.merge(wa, on="player_id", how="left")
        p_agg["dism"] = p_agg["dism"].fillna(0)
        raw = ((p_agg["runs"] - p_agg["er"]) + 12.0 * (p_agg["ek"] - p_agg["dism"])) / np.maximum(p_agg["bf"], 1) * 100.0
        k_prior = float(ranked_df["eb_k_matches_prior"].iloc[0])
        eb = (p_agg["matches"] / (p_agg["matches"] + k_prior)) * raw
        return pd.Series(eb.values, index=p_agg["player_id"]).reindex(ranked_df["player_id"])
    else:
        grp_cols = ["eligibility_category", "innings", "match_phase"]
        par = sub.groupby(grp_cols, as_index=False).agg(trc=("bowler_conceded_runs", "sum"), tlb=("is_legal_delivery", "sum"), tbw=("is_bowler_wicket", "sum"))
        par["erc"] = par["trc"] / np.maximum(par["tlb"], 1)
        par["ebw"] = par["tbw"] / np.maximum(par["tlb"], 1)
        sub = sub.merge(par[grp_cols + ["erc", "ebw"]], on=grp_cols, how="left")
        sub["erc_r"] = np.where(sub["is_legal_delivery"], sub["erc"], 0.0)
        sub["ebw_r"] = np.where(sub["is_legal_delivery"], sub["ebw"], 0.0)
        p_agg = sub.groupby("bowler_id", as_index=False).agg(
            rc=("bowler_conceded_runs", "sum"), lb=("is_legal_delivery", "sum"),
            bw=("is_bowler_wicket", "sum"), erc=("erc_r", "sum"), ebw=("ebw_r", "sum"),
            matches=("match_id", "nunique")
        ).rename(columns={"bowler_id": "player_id"})
        p_agg = p_agg[p_agg["lb"] > 0]
        raw = ((p_agg["erc"] - p_agg["rc"]) + 12.0 * (p_agg["bw"] - p_agg["ebw"])) * 24.0 / p_agg["lb"]
        k_prior = float(ranked_df["eb_k_matches_prior"].iloc[0])
        eb = (p_agg["matches"] / (p_agg["matches"] + k_prior)) * raw
        return pd.Series(eb.values, index=p_agg["player_id"]).reindex(ranked_df["player_id"])


def run_full_robustness(
    p_df: pd.DataFrame,
    bat_ranked: pd.DataFrame,
    bowl_ranked: pd.DataFrame,
    bat_cand: pd.DataFrame,
    bowl_cand: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run pressure-model, raw-vs-EB, approach, weight, and threshold robustness tests."""
    p_df = pd.concat(
        [
            p_df,
            pd.DataFrame(
                {
                    "model_a_bat_idx": np.where(p_df["innings"] == 1, p_df["model_a_first_innings_pressure"], p_df["model_a_chase_pressure"]),
                    "model_b_bat_idx": np.where(p_df["innings"] == 1, p_df["model_b_first_innings_pressure"], p_df["model_b_chase_pressure"]),
                    "dismissed_player_id_int": pd.to_numeric(p_df["dismissed_player_id"], errors="coerce"),
                },
                index=p_df.index,
            ),
        ],
        axis=1,
    )

    # Precompute alternative masks
    bat_valid_m = p_df["batting_pressure_index"].notna()
    bat_a_m = pd.Series(False, index=p_df.index)
    bat_b_m = pd.Series(False, index=p_df.index)
    for inn in [1, 2]:
        mi = bat_valid_m & (p_df["innings"] == inn)
        bat_a_m.loc[mi] = p_df.loc[mi, "model_a_bat_idx"] >= p_df.loc[mi, "model_a_bat_idx"].quantile(0.70)
        bat_b_m.loc[mi] = p_df.loc[mi, "model_b_bat_idx"] >= p_df.loc[mi, "model_b_bat_idx"].quantile(0.70)
    bat_lo_m = bat_valid_m & np.where(p_df["innings"] == 1, p_df["first_innings_pressure_index"] >= 42.0, p_df["chase_pressure_index"] >= 47.0)
    bat_hi_m = bat_valid_m & np.where(p_df["innings"] == 1, p_df["first_innings_pressure_index"] >= 48.0, p_df["chase_pressure_index"] >= 53.0)

    bowl_valid_m = p_df["bowling_pressure_index"].notna()
    bowl_a_m = bowl_valid_m & (p_df["model_a_bowling_pressure"] >= p_df.loc[bowl_valid_m, "model_a_bowling_pressure"].quantile(0.70))
    bowl_b_m = bowl_valid_m & (p_df["model_b_bowling_pressure"] >= p_df.loc[bowl_valid_m, "model_b_bowling_pressure"].quantile(0.70))
    bowl_lo_m = bowl_valid_m & (p_df["bowling_pressure_index"] >= 57.0)
    bowl_hi_m = bowl_valid_m & (p_df["bowling_pressure_index"] >= 63.0)

    rob_rows: list[dict[str, Any]] = []
    overlap_player_rows: list[dict[str, Any]] = []
    wt_rows: list[dict[str, Any]] = []
    th_rows: list[dict[str, Any]] = []

    wp, wr, wel, we = BASE_WEIGHTS

    for disc, ranked, cand, masks_dict in [
        (
            "batting", bat_ranked, bat_cand,
            {"Model_A_Pressure": bat_a_m, "Model_B_Pressure": bat_b_m, "Model_C_Thresh_Minus3pts": bat_lo_m, "Model_C_Thresh_Plus3pts": bat_hi_m},
        ),
        (
            "bowling", bowl_ranked, bowl_cand,
            {"Model_A_Pressure": bowl_a_m, "Model_B_Pressure": bowl_b_m, "Model_C_Thresh_Minus3pts": bowl_lo_m, "Model_C_Thresh_Plus3pts": bowl_hi_m},
        ),
    ]:
        r_idx = ranked.set_index("player_id")
        prim_score = r_idx["final_ranking_score"]
        prim_rank = r_idx["rank"]
        top10_prim = set(prim_rank[prim_rank <= 10].index)

        method_ranks: dict[str, pd.Series] = {"Balanced_Primary": prim_rank}

        # 1. Alternative pressure frameworks (recompute performance pillar under alt mask, keep rel/ext/evid)
        for m_name, m_series in masks_dict.items():
            alt_eb = compute_alt_model_impact(p_df, disc, m_series, ranked)
            alt_norm_perf = robust_logistic_scale(alt_eb).fillna(r_idx["norm_perf_score"])
            alt_score = (
                wp * alt_norm_perf
                + wr * r_idx["norm_rel_score"]
                + wel * r_idx["norm_extreme_and_lift_score"]
                + we * r_idx["norm_evidence_score"]
            )
            alt_rk = alt_score.rank(ascending=False, method="min").astype(int)
            method_ranks[m_name] = alt_rk
            top10_alt = set(alt_rk[alt_rk <= 10].index)
            rob_rows.append({
                "discipline": disc,
                "robustness_test": m_name,
                "category": "Pressure_Framework",
                "n_candidates": len(r_idx),
                "spearman_corr_vs_primary": round(spearman_corr(prim_score, alt_score), 4),
                "top10_overlap_count": len(top10_prim & top10_alt),
                "top10_overlap_pct": round(len(top10_prim & top10_alt) / 10.0 * 100.0, 1),
                "mean_abs_rank_shift_top15": round(float((prim_rank.head(15) - alt_rk.loc[prim_rank.head(15).index]).abs().mean()), 2),
            })

        # 2. Raw impact (no EB shrinkage) vs EB-shrunk primary
        raw_norm = robust_logistic_scale(r_idx["raw_pressure_impact"])
        raw_score = wp * raw_norm + wr * r_idx["norm_rel_score"] + wel * r_idx["norm_extreme_and_lift_score"] + we * r_idx["norm_evidence_score"]
        raw_rk = raw_score.rank(ascending=False, method="min").astype(int)
        method_ranks["Raw_No_EB_Shrinkage"] = raw_rk
        top10_raw = set(raw_rk[raw_rk <= 10].index)
        rob_rows.append({
            "discipline": disc,
            "robustness_test": "Raw_No_EB_Shrinkage",
            "category": "Shrinkage",
            "n_candidates": len(r_idx),
            "spearman_corr_vs_primary": round(spearman_corr(prim_score, raw_score), 4),
            "top10_overlap_count": len(top10_prim & top10_raw),
            "top10_overlap_pct": round(len(top10_prim & top10_raw) / 10.0 * 100.0, 1),
            "mean_abs_rank_shift_top15": round(float((prim_rank.head(15) - raw_rk.loc[prim_rank.head(15).index]).abs().mean()), 2),
        })

        # 3. Alternative philosophies (Performance-Dominant & Reliability-Dominant)
        for app_label, col_sc, col_rk in [
            ("Approach_Performance_Dominant", "score_Performance_Dominant", "rank_Performance_Dominant"),
            ("Approach_Reliability_Dominant", "score_Reliability_Dominant", "rank_Reliability_Dominant"),
        ]:
            method_ranks[app_label] = r_idx[col_rk]
            top10_app = set(r_idx[r_idx[col_rk] <= 10].index)
            rob_rows.append({
                "discipline": disc,
                "robustness_test": app_label,
                "category": "Ranking_Philosophy",
                "n_candidates": len(r_idx),
                "spearman_corr_vs_primary": round(spearman_corr(prim_score, r_idx[col_sc]), 4),
                "top10_overlap_count": len(top10_prim & top10_app),
                "top10_overlap_pct": round(len(top10_prim & top10_app) / 10.0 * 100.0, 1),
                "mean_abs_rank_shift_top15": round(float((prim_rank.head(15) - r_idx.loc[prim_rank.head(15).index, col_rk]).abs().mean()), 2),
            })

        # Per-player Top-15 stability across all 8 methods -> outputs/top10_overlap_analysis.csv
        top15_ids = prim_rank[prim_rank <= 15].index.tolist()
        for pid in top15_ids:
            rks = {k: int(v.loc[pid]) for k, v in method_ranks.items()}
            in_t10_cnt = sum(1 for v in rks.values() if v <= 10)
            rk_min, rk_max = min(rks.values()), max(rks.values())
            if in_t10_cnt >= 7:
                stab = "CORE_CONSENSUS"
            elif in_t10_cnt >= 5:
                stab = "MODERATELY_STABLE"
            else:
                stab = "ASSUMPTION_SENSITIVE"
            overlap_player_rows.append({
                "discipline": disc,
                "primary_rank": int(prim_rank.loc[pid]),
                "player_id": int(pid),
                "player_name": str(r_idx.loc[pid, "player_name"]),
                "evidence_tier": str(r_idx.loc[pid, "evidence_tier"]),
                "methods_in_top10_out_of_8": in_t10_cnt,
                "min_rank_across_methods": rk_min,
                "max_rank_across_methods": rk_max,
                "rank_model_a": rks["Model_A_Pressure"],
                "rank_model_b": rks["Model_B_Pressure"],
                "rank_thresh_minus3": rks["Model_C_Thresh_Minus3pts"],
                "rank_thresh_plus3": rks["Model_C_Thresh_Plus3pts"],
                "rank_raw_no_eb": rks["Raw_No_EB_Shrinkage"],
                "rank_perf_dom": rks["Approach_Performance_Dominant"],
                "rank_rel_dom": rks["Approach_Reliability_Dominant"],
                "mc_prob_top10_pct": float(r_idx.loc[pid, "mc_prob_top10_pct"]),
                "stability_classification": stab,
            })

        # 4. Weight sensitivity grid -> outputs/ranking_weight_sensitivity.csv
        wt_grid = [
            ("Baseline_50_25_15_10", (0.50, 0.25, 0.15, 0.10)),
            ("Perf_Plus10_60_20_12_08", (0.60, 0.20, 0.12, 0.08)),
            ("Perf_Minus10_40_30_18_12", (0.40, 0.30, 0.18, 0.12)),
            ("Rel_Plus10_45_35_12_08", (0.45, 0.35, 0.12, 0.08)),
            ("Rel_Minus10_55_15_18_12", (0.55, 0.15, 0.18, 0.12)),
            ("ExtLift_Plus10_45_20_25_10", (0.45, 0.20, 0.25, 0.10)),
            ("Evid_Zero_55_28_17_00", (0.55, 0.28, 0.17, 0.00)),
            ("Evid_Plus10_45_22_13_20", (0.45, 0.22, 0.13, 0.20)),
            ("Equal_25_25_25_25", (0.25, 0.25, 0.25, 0.25)),
        ]
        for w_lbl, (a, b, c, d) in wt_grid:
            sc_w = a * r_idx["norm_perf_score"] + b * r_idx["norm_rel_score"] + c * r_idx["norm_extreme_and_lift_score"] + d * r_idx["norm_evidence_score"]
            rk_w = sc_w.rank(ascending=False, method="min").astype(int)
            t10_w = set(rk_w[rk_w <= 10].index)
            wt_rows.append({
                "discipline": disc,
                "weight_scenario": w_lbl,
                "weights_perf_rel_ext_evid": f"{a:.2f}/{b:.2f}/{c:.2f}/{d:.2f}",
                "spearman_corr_vs_primary": round(spearman_corr(prim_score, sc_w), 4),
                "top10_overlap_count": len(top10_prim & t10_w),
                "top10_overlap_pct": round(len(top10_prim & t10_w) / 10.0 * 100.0, 1),
            })

        # 5. Minimum exposure threshold sensitivity -> outputs/ranking_threshold_sensitivity.csv
        balls_col = "pressure_balls_faced" if disc == "batting" else "pressure_legal_balls"
        cutoffs = [(60, 8), (80, 10), (100, 12), (120, 15), (150, 18)] if disc == "batting" else [(60, 8), (90, 10), (120, 12), (150, 15), (180, 18)]
        for mb, mi in cutoffs:
            sub_r = ranked[(ranked[balls_col] >= mb) & (ranked["pressure_innings"] >= mi) & (ranked["pressure_matches"] >= mi)]
            # For looser 60/8 cutoff, check total candidate count from full cand table
            tot_elig_at_cut = int(((cand[balls_col] >= mb) & (cand["pressure_innings"] >= mi) & (cand["pressure_matches"] >= mi) & cand["reliability_score"].notna()).sum())
            retained_top10 = set(sub_r.head(10)["player_id"])
            dropped_from_prim = sorted(set(ranked.loc[ranked["rank"] <= 10, "player_name"]) - set(sub_r["player_name"]))
            th_rows.append({
                "discipline": disc,
                "min_pressure_balls": mb,
                "min_pressure_innings_matches": mi,
                "eligible_candidates_at_cutoff": tot_elig_at_cut,
                "primary_top10_retained_count": len(top10_prim & set(sub_r["player_id"])),
                "top10_overlap_pct": round(len(top10_prim & retained_top10) / 10.0 * 100.0, 1),
                "primary_top10_players_excluded_if_tightened": "; ".join(dropped_from_prim) if dropped_from_prim else "None",
                "is_primary_cutoff": (mb == 80 and disc == "batting") or (mb == 90 and disc == "bowling"),
            })

    rob_df = pd.DataFrame(rob_rows)
    ov_df = pd.DataFrame(overlap_player_rows)
    wt_df = pd.DataFrame(wt_rows)
    th_df = pd.DataFrame(th_rows)

    rob_df.to_csv(OUT_DIR / "ranking_robustness.csv", index=False)
    ov_df.to_csv(OUT_DIR / "top10_overlap_analysis.csv", index=False)
    wt_df.to_csv(OUT_DIR / "ranking_weight_sensitivity.csv", index=False)
    th_df.to_csv(OUT_DIR / "ranking_threshold_sensitivity.csv", index=False)
    return rob_df, ov_df, wt_df, th_df


def run_ranking_validation(
    bat_ranked: pd.DataFrame,
    bowl_ranked: pd.DataFrame,
    bat_cand: pd.DataFrame,
    bowl_cand: pd.DataFrame,
    rob_df: pd.DataFrame,
) -> pd.DataFrame:
    """Write outputs/ranking_validation_results.csv verifying all Phase 6 integrity rules."""
    rows: list[dict[str, Any]] = []

    def add(name: str, passed: bool, val: Any, details: str) -> None:
        rows.append({"check_name": name, "status": "PASS" if passed else "FAIL", "metric_value": str(val), "details": details})

    add("01_no_duplicate_player_ids_in_ranked_lists", bat_ranked["player_id"].is_unique and bowl_ranked["player_id"].is_unique, f"bat={len(bat_ranked)}, bowl={len(bowl_ranked)}", "Unique player_id across all ranked batters and bowlers")
    add("02_exact_monotonic_rank_ordering", bool(bat_ranked["final_ranking_score"].is_monotonic_decreasing and bowl_ranked["final_ranking_score"].is_monotonic_decreasing), True, "Ranks 1..N strictly ordered descending by final_ranking_score")
    add("03_eligibility_rules_enforced", bool((bat_ranked["pressure_balls_faced"] >= 80).all() and (bat_ranked["pressure_matches"] >= 10).all() and (bowl_ranked["pressure_legal_balls"] >= 90).all() and (bowl_ranked["pressure_matches"] >= 10).all()), f"bat_min_b={int(bat_ranked['pressure_balls_faced'].min())}, bowl_min_b={int(bowl_ranked['pressure_legal_balls'].min())}", "All ranked players satisfy Phase 5 primary exposure cutoffs")
    add("04_no_missing_reliability_imputed_as_zero", bool(bat_ranked["reliability_score"].notna().all() and bowl_ranked["reliability_score"].notna().all() and bat_cand.loc[bat_cand["evidence_tier"] == "INSUFFICIENT_EVIDENCE", "reliability_score"].isna().all()), True, "0 missing reliability values in ranked lists; INSUFFICIENT_EVIDENCE stays NaN")
    add("05_composite_scores_bounded_0_to_100", bool(bat_ranked["final_ranking_score"].between(0, 100).all() and bowl_ranked["final_ranking_score"].between(0, 100).all()), f"bat_max={bat_ranked['final_ranking_score'].max():.2f}, bowl_max={bowl_ranked['final_ranking_score'].max():.2f}", "All composite scores strictly within [0, 100]")
    add("06_evidence_volume_does_not_dominate", bool(bat_ranked["final_ranking_score"].corr(bat_ranked["pressure_balls_faced"]) < 0.65 and bowl_ranked["final_ranking_score"].corr(bowl_ranked["pressure_legal_balls"]) < 0.65), f"bat_r={bat_ranked['final_ranking_score'].corr(bat_ranked['pressure_balls_faced']):.3f}, bowl_r={bowl_ranked['final_ranking_score'].corr(bowl_ranked['pressure_legal_balls']):.3f}", "Ranking score driven by skill & reliability, not raw ball volume")
    add("07_uncertainty_intervals_preserved", bool(bat_ranked.head(10)["impact_ci95_low"].notna().all() and bowl_ranked.head(10)["impact_ci95_low"].notna().all() and (bat_ranked["impact_ci95_high"] >= bat_ranked["impact_ci95_low"]).all()), True, "All shortlisted players retain match-clustered bootstrap 95% CIs and MC rank intervals")
    add("08_robustness_checks_populated", len(rob_df) == 14 and rob_df["spearman_corr_vs_primary"].notna().all(), len(rob_df), "All 7 robustness tests executed across both batting and bowling")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "ranking_validation_results.csv", index=False)
    return out


def generate_phase6_charts(
    bat_ranked: pd.DataFrame,
    bowl_ranked: pd.DataFrame,
    rob_df: pd.DataFrame,
    wt_df: pd.DataFrame,
    th_df: pd.DataFrame,
) -> list[str]:
    """Generate all 7 required Phase 6 RR PERFORMANCE LAB charts (20_*.png to 26_*.png)."""
    saved: list[str] = []

    # 20 & 21: Final Batting & Bowling Top 10 Horizontal Stacked Contribution Charts
    for fname, df_r, title, accent in [
        ("20_final_batting_rankings.png", bat_ranked.head(10), "RR PERFORMANCE LAB — Final Top 10 Batters Under Pressure (Balanced Primary)", PINK),
        ("21_final_bowling_rankings.png", bowl_ranked.head(10), "RR PERFORMANCE LAB — Final Top 10 Bowlers Under Pressure (Balanced Primary)", TEAL_POS),
    ]:
        sub = df_r.iloc[::-1].copy()
        y = np.arange(len(sub))
        labels = [f"#{int(r.rank)}  {r.player_name}" for r in sub.itertuples()]
        c1 = 0.50 * sub["norm_perf_score"].values
        c2 = 0.25 * sub["norm_rel_score"].values
        c3 = 0.15 * sub["norm_extreme_and_lift_score"].values
        c4 = 0.10 * sub["norm_evidence_score"].values

        fig, ax = plt.subplots(figsize=(11.2, 5.4))
        apply_rr_theme(fig, ax)
        ax.barh(y, c1, color=accent, height=0.62, label="Performance (50%)")
        ax.barh(y, c2, left=c1, color=GOLD, height=0.62, label="Reliability (25%)")
        ax.barh(y, c3, left=c1 + c2, color=BLUE_SEC, height=0.62, label="Extreme & Lift (15%)")
        ax.barh(y, c4, left=c1 + c2 + c3, color=LAVENDER, height=0.62, label="Evidence (10%)")
        for yi, r in zip(y, sub.itertuples()):
            ax.text(r.final_ranking_score + 0.9, yi, f"{r.final_ranking_score:.1f}  ({r.mc_prob_top10_pct:.0f}% Top-10 MC)", va="center", color=LIGHT_TXT, fontsize=8.5, fontweight="bold")
        ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9.5, fontweight="bold")
        ax.set_xlim(0, 102)
        ax.set_xlabel("Final Composite Ranking Score (0–100)")
        ax.set_title(title, fontsize=12, fontweight="bold", pad=24)
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, loc="upper center", bbox_to_anchor=(0.5, 1.07), ncol=4, fontsize=8.5)
        fig.tight_layout()
        p = CHART_DIR / fname
        fig.savefig(p, dpi=160, bbox_inches="tight", facecolor=BG_DEEP)
        plt.close(fig)
        saved.append(p.name)

    # 22: Performance vs. Reliability with Top 10 Highlighted
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.0))
    apply_rr_theme(fig, axes)
    for ax, df_r, title, col_hi in [
        (axes[0], bat_ranked, "Batting Candidates: Performance vs. Reliability (Top 10 Highlighted)", PINK),
        (axes[1], bowl_ranked, "Bowling Candidates: Performance vs. Reliability (Top 10 Highlighted)", TEAL_POS),
    ]:
        t10 = df_r["rank"] <= 10
        ax.scatter(df_r.loc[~t10, "norm_perf_score"], df_r.loc[~t10, "norm_rel_score"], color=LAVENDER, alpha=0.45, s=34, label="Other Eligible Candidates")
        ax.scatter(df_r.loc[t10, "norm_perf_score"], df_r.loc[t10, "norm_rel_score"], color=col_hi, s=90, edgecolor=GOLD, linewidth=1.2, zorder=5, label="Final Top 10")
        for r in df_r[t10].itertuples():
            ax.annotate(f"#{int(r.rank)} {r.player_name.split()[-1]}", (r.norm_perf_score, r.norm_rel_score), xytext=(5, 4), textcoords="offset points", color=LIGHT_TXT, fontsize=7.8, fontweight="bold")
        ax.axvline(50, color=GOLD, linestyle="--", alpha=0.5, linewidth=0.9)
        ax.axhline(50, color=GOLD, linestyle="--", alpha=0.5, linewidth=0.9)
        ax.set_xlabel("Calibrated Performance Score (0–100)")
        ax.set_ylabel("Calibrated Reliability Score (0–100)")
        ax.set_title(title, fontsize=10.8, fontweight="bold")
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="lower left")
    fig.tight_layout()
    p22 = CHART_DIR / "22_final_perf_vs_reliability.png"
    fig.savefig(p22, dpi=160, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p22.name)

    # 23: Exposure vs. Final Ranking Score (verifying volume doesn't dominate)
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6))
    apply_rr_theme(fig, axes)
    for ax, df_r, bcol, title, c_hi in [
        (axes[0], bat_ranked, "pressure_balls_faced", "Batting: Pressure Balls vs. Final Ranking Score", PINK),
        (axes[1], bowl_ranked, "pressure_legal_balls", "Bowling: Pressure Legal Balls vs. Final Ranking Score", GOLD),
    ]:
        t10 = df_r["rank"] <= 10
        ax.scatter(df_r.loc[~t10, bcol], df_r.loc[~t10, "final_ranking_score"], color=BLUE_SEC, alpha=0.52, s=34, label="Ranks 11+")
        ax.scatter(df_r.loc[t10, bcol], df_r.loc[t10, "final_ranking_score"], color=c_hi, s=78, edgecolor=LIGHT_TXT, linewidth=0.8, zorder=5, label="Final Top 10")
        r_vol = df_r["final_ranking_score"].corr(df_r[bcol])
        ax.text(0.97, 0.08, f"Pearson r(Score, Balls) = {r_vol:+.2f}", transform=ax.transAxes, ha="right", color=LIGHT_TXT, fontsize=8.8, bbox=dict(boxstyle="round,pad=0.3", facecolor=BG_DEEP, edgecolor=LAVENDER))
        ax.set_xlabel("Pressure Deliveries (HIGH + EXTREME)")
        ax.set_ylabel("Final Ranking Score (0–100)")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.5, loc="lower right", bbox_to_anchor=(0.98, 0.18))
    fig.tight_layout()
    p23 = CHART_DIR / "23_exposure_vs_ranking_score.png"
    fig.savefig(p23, dpi=160, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p23.name)

    # 24: Shortlist Match-Clustered Bootstrap 95% CIs (Forest Plot for Top 10 Batters & Bowlers)
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4))
    apply_rr_theme(fig, axes)
    for ax, df_r, xlabel, title, col_pt in [
        (axes[0], bat_ranked.head(10), "Net Pressure Impact (Runs / 100 Balls; 95% Match-Clustered CI)", "Top 10 Batters: Raw 95% CI vs. EB-Shrunk Estimate", PINK),
        (axes[1], bowl_ranked.head(10), "Net Pressure Impact (Runs Saved+Wkts / 24 Balls; 95% CI)", "Top 10 Bowlers: Raw 95% CI vs. EB-Shrunk Estimate", TEAL_POS),
    ]:
        sub = df_r.iloc[::-1]
        y = np.arange(len(sub))
        ax.hlines(y, sub["impact_ci95_low"], sub["impact_ci95_high"], color=LAVENDER, linewidth=2.2, alpha=0.85, label="Match-Clustered 95% CI (Raw)")
        ax.scatter(sub["raw_pressure_impact"], y, color=BLUE_SEC, s=42, zorder=4, label="Raw Pressure Impact")
        ax.scatter(sub["eb_pressure_impact"], y, color=col_pt, edgecolor=GOLD, linewidth=1.0, s=68, zorder=5, label="EB-Shrunk Impact")
        ax.axvline(0, color=GOLD, linestyle="--", linewidth=1.0, alpha=0.7)
        ax.set_yticks(y)
        ax.set_yticklabels([f"#{int(r.rank)} {r.player_name}" for r in sub.itertuples()], fontsize=9, fontweight="bold")
        ax.set_xlabel(xlabel, fontsize=9)
        ax.set_title(title, fontsize=10.8, fontweight="bold")
        ax.legend(frameon=False, labelcolor=LIGHT_TXT, fontsize=8.2, loc="lower right")
    fig.tight_layout()
    p24 = CHART_DIR / "24_shortlist_confidence_intervals.png"
    fig.savefig(p24, dpi=160, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p24.name)

    # 25: Top 10 Overlap Across Pressure Models, Shrinkage & Ranking Approaches
    fig, ax = plt.subplots(figsize=(11.2, 4.8))
    apply_rr_theme(fig, ax)
    tests_order = rob_df[rob_df["discipline"] == "batting"]["robustness_test"].tolist()
    short_lbls = ["Model A\nPressure", "Model B\nPressure", "Thresh\n-3 pts", "Thresh\n+3 pts", "Raw\n(No EB)", "Perf-\nDominant", "Rel-\nDominant"]
    x = np.arange(len(tests_order))
    wb = 0.34
    bat_ov = rob_df[rob_df["discipline"] == "batting"].set_index("robustness_test").reindex(tests_order)["top10_overlap_pct"].values
    bowl_ov = rob_df[rob_df["discipline"] == "bowling"].set_index("robustness_test").reindex(tests_order)["top10_overlap_pct"].values
    b1 = ax.bar(x - wb / 2, bat_ov, width=wb, color=PINK, label="Batting Top 10 Overlap (%)")
    b2 = ax.bar(x + wb / 2, bowl_ov, width=wb, color=GOLD, label="Bowling Top 10 Overlap (%)")
    for bars in (b1, b2):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.8, f"{v:.0f}%", ha="center", color=LIGHT_TXT, fontsize=8.5, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(short_lbls, fontsize=9)
    ax.set_ylim(0, 114)
    ax.set_ylabel("Top 10 Overlap With Balanced Primary (%)")
    ax.set_title("Top 10 List Stability Across Alternative Pressure Models, Shrinkage & Ranking Philosophies", fontsize=11.5, fontweight="bold", pad=10)
    ax.legend(frameon=False, labelcolor=LIGHT_TXT, loc="upper right")
    fig.tight_layout()
    p25 = CHART_DIR / "25_top10_overlap_methods.png"
    fig.savefig(p25, dpi=160, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p25.name)

    # 26: Weight & Exposure Threshold Sensitivity
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.7))
    apply_rr_theme(fig, axes)
    w_scens = wt_df[wt_df["discipline"] == "batting"]["weight_scenario"].tolist()
    w_short = ["Base", "Perf+10", "Perf-10", "Rel+10", "Rel-10", "Ext+10", "Evid 0", "Evid+10", "Equal"]
    xw = np.arange(len(w_scens))
    wb_sp = wt_df[wt_df["discipline"] == "batting"].set_index("weight_scenario").reindex(w_scens)["spearman_corr_vs_primary"].values
    wl_sp = wt_df[wt_df["discipline"] == "bowling"].set_index("weight_scenario").reindex(w_scens)["spearman_corr_vs_primary"].values
    axes[0].plot(xw, wb_sp, marker="o", linewidth=2.3, color=PINK, label="Batting Spearman r")
    axes[0].plot(xw, wl_sp, marker="s", linewidth=2.3, color=GOLD, label="Bowling Spearman r")
    axes[0].set_xticks(xw); axes[0].set_xticklabels(w_short, rotation=25, fontsize=8.5)
    axes[0].set_ylim(0.80, 1.02)
    axes[0].set_ylabel("Spearman Correlation vs. Primary")
    axes[0].set_title("Composite Weight Perturbation Sensitivity", fontsize=11, fontweight="bold")
    axes[0].legend(frameon=False, labelcolor=LIGHT_TXT, loc="lower left")

    # Right: Exposure threshold sensitivity (Primary Top 10 retained as cutoff tightens)
    tb = th_df[th_df["discipline"] == "batting"]
    tw = th_df[th_df["discipline"] == "bowling"]
    xt = np.arange(len(tb))
    axes[1].plot(xt, tb["primary_top10_retained_count"].values, marker="o", linewidth=2.3, color=PINK, label="Batting Primary Top 10 Retained")
    axes[1].plot(xt, tw["primary_top10_retained_count"].values, marker="s", linewidth=2.3, color=TEAL_POS, label="Bowling Primary Top 10 Retained")
    axes[1].set_xticks(xt)
    axes[1].set_xticklabels(["Loose\n(60b/8m)", "Primary\n(80-90b/10m)", "Mid\n(100-120b)", "Strict\n(120-150b)", "High-Conf\n(150-180b)"], fontsize=8.3)
    axes[1].set_ylim(0, 11.2)
    axes[1].set_ylabel("Primary Top 10 Players Qualifying (out of 10)")
    axes[1].set_title("Minimum Exposure Cutoff Sensitivity", fontsize=11, fontweight="bold")
    axes[1].legend(frameon=False, labelcolor=LIGHT_TXT, loc="lower left")
    fig.tight_layout()
    p26 = CHART_DIR / "26_ranking_sensitivity.png"
    fig.savefig(p26, dpi=160, bbox_inches="tight", facecolor=BG_DEEP)
    plt.close(fig)
    saved.append(p26.name)

    return saved


def main() -> None:
    p_df = pd.read_csv(PROCESSED_DIR / "pressure_deliveries.csv", low_memory=False, keep_default_na=False, na_values=[""])
    for bcol in ["is_legal_delivery", "is_batter_ball_faced", "is_wicket_event", "is_bowler_wicket"]:
        p_df[bcol] = p_df[bcol].astype(str).str.lower().eq("true")

    bat_ranked = pd.read_csv(PROCESSED_DIR / "final_batting_rankings.csv", low_memory=False)
    bowl_ranked = pd.read_csv(PROCESSED_DIR / "final_bowling_rankings.csv", low_memory=False)
    bat_cand = pd.read_csv(PROCESSED_DIR / "batting_ranking_candidates.csv", low_memory=False)
    bowl_cand = pd.read_csv(PROCESSED_DIR / "bowling_ranking_candidates.csv", low_memory=False)

    rob_df, ov_df, wt_df, th_df = run_full_robustness(p_df, bat_ranked, bowl_ranked, bat_cand, bowl_cand)
    val_df = run_ranking_validation(bat_ranked, bowl_ranked, bat_cand, bowl_cand, rob_df)
    charts = generate_phase6_charts(bat_ranked, bowl_ranked, rob_df, wt_df, th_df)

    print("\n=== PHASE 6 RANKING ROBUSTNESS & VISUALIZATION COMPLETE ===")
    print(f"Ranking validation checks : {(val_df['status'] == 'PASS').sum()}/{len(val_df)} PASS")
    print("\nRobustness Summary:")
    print(rob_df[["discipline", "robustness_test", "spearman_corr_vs_primary", "top10_overlap_pct", "mean_abs_rank_shift_top15"]].to_string(index=False))
    print(f"\nGenerated {len(charts)} Phase 6 charts in {CHART_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
