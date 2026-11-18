"""
SupeRR Selector Season 2 - Phase 6 Final Player Ranking Model (RR PERFORMANCE LAB).

Builds separate, transparent, statistically defensible final ranking models for:
  1. Batters under pressure (173 primary-eligible candidates -> ordered Top 10)
  2. Bowlers under pressure (165 primary-eligible candidates -> ordered Top 10)

Directly follows the Official Round 1 Problem Statement requirements:
  - Two separate ordered Top 10 lists (Batters Ranks 1-10, Bowlers Ranks 1-10)
  - Eligible historical IPL + T20I data from 2022 onwards (Super Overs & non-IPL T20 excluded)
  - Evaluates high-pressure performance relative to usual baseline + cross-match consistency
  - Strictly separates Performance Effectiveness, Reliability, and Evidence Strength

Compares three defensible ranking philosophies:
  - Approach 1: Performance-Dominant (65% Perf / 20% Rel / 10% Extreme+Lift / 5% Evid)
  - Approach 2: Reliability-Dominant (30% Perf / 50% Rel / 10% Extreme+Lift / 10% Evid)
  - Approach 3: Balanced Performance-Reliability-Evidence (50% Perf / 25% Rel / 15% Extreme+Lift / 10% Evid) [PRIMARY]

Original raw files are never modified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Primary validated eligibility cutoffs from Phase 5
BAT_MIN_BALLS = 80
BAT_MIN_INN_MATCHES = 10
BOWL_MIN_BALLS = 90
BOWL_MIN_INN_MATCHES = 10

# Three ranking weight specifications: (w_perf, w_rel, w_ext_lift, w_evid)
RANKING_APPROACHES: dict[str, tuple[float, float, float, float]] = {
    "Balanced_Primary": (0.50, 0.25, 0.15, 0.10),
    "Performance_Dominant": (0.65, 0.20, 0.10, 0.05),
    "Reliability_Dominant": (0.30, 0.50, 0.10, 0.10),
}

RNG_SEED = 42


def robust_logistic_scale(series: pd.Series, spread_mult: float = 1.35) -> pd.Series:
    """
    Calibrate a metric smoothly onto [0, 100] over the eligible pool using median & IQR-derived
    robust scale so all pillars share comparable variance without clipping extremes.
    Preserves NaN (never replaces missing values with 0).
    """
    valid = series.dropna()
    if len(valid) < 3:
        return pd.Series(np.nan, index=series.index)
    med = float(valid.median())
    iqr = float(valid.quantile(0.75) - valid.quantile(0.25))
    robust_sd = max(iqr * 0.7413, float(valid.std()) * 0.5, 1e-6)
    z = (series - med) / (robust_sd * spread_mult)
    return np.where(series.notna(), 100.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0))), np.nan)


def spearman_corr(a: pd.Series, b: pd.Series) -> float:
    valid = a.notna() & b.notna()
    if valid.sum() < 3:
        return np.nan
    return float(a.loc[valid].rank(method="average").corr(b.loc[valid].rank(method="average")))


def build_season_years_lookup(season_df: pd.DataFrame, discipline: str) -> pd.Series:
    """Return formatted season years represented per player_id (e.g., '2022, 2023, 2024, 2025, 2026')."""
    sub = season_df[season_df["discipline"] == discipline]
    return (
        sub.groupby("player_id")["season_year"]
        .agg(lambda s: ", ".join(map(str, sorted(set(s.astype(int))))))
    )


def build_player_competition_context(pm: pd.DataFrame) -> pd.DataFrame:
    """Summarize verified teams and IPL/T20I competition exposure from player_master.csv."""
    ctx = pm[["player_id", "standardized_display_name", "team_names", "in_ipl", "in_t20i"]].copy()
    ctx["in_ipl"] = ctx["in_ipl"].astype(str).str.lower().eq("true")
    ctx["in_t20i"] = ctx["in_t20i"].astype(str).str.lower().eq("true")
    ctx["competition_context"] = np.where(
        ctx["in_ipl"] & ctx["in_t20i"],
        "IPL + T20I",
        np.where(ctx["in_ipl"], "IPL Only", np.where(ctx["in_t20i"], "T20I Only", "Other")),
    )
    return ctx


def build_discipline_rankings(
    discipline: str,
    perf_df: pd.DataFrame,
    rel_df: pd.DataFrame,
    bk_df: pd.DataFrame,
    pvn_df: pd.DataFrame,
    season_df: pd.DataFrame,
    pm_ctx: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    """
    Build full candidate table, eligible ranked table, score decomposition,
    rank-uncertainty simulation, and unselected-candidate audit for one discipline.
    """
    is_bat = discipline == "batting"
    balls_col = "pressure_balls_faced" if is_bat else "pressure_legal_balls"
    min_balls = BAT_MIN_BALLS if is_bat else BOWL_MIN_BALLS
    min_inn = BAT_MIN_INN_MATCHES if is_bat else BOWL_MIN_INN_MATCHES
    bk_cnt_col = "balls_faced" if is_bat else "legal_balls"
    bk_imp_col = "net_impact_per_100b" if is_bat else "net_impact_per_24b"
    role_col = "batting_role" if is_bat else "bowling_role"

    # Merge performance + reliability + player_master context strictly on player_id
    rel_cols_keep = [
        "player_id", "evidence_tier", "is_primary_eligible", "raw_pressure_impact",
        "eb_shrinkage_weight", "eb_k_matches_prior", "eb_pressure_impact",
        "innings_impact_iqr", "innings_impact_sd", "seasonal_impact_sd",
        "comp_innings_stability", "comp_floor_consistency", "comp_cross_condition_stability",
        "comp_seasonal_stability", "performance_score", "reliability_score",
        "evidence_strength_score", "impact_ci95_low", "impact_ci95_high",
        "impact_ci95_width", "impact_boot_se", "raw_rate_ci95_low", "raw_rate_ci95_high",
    ]
    df = perf_df.merge(rel_df[rel_cols_keep], on="player_id", how="inner")
    df = df.merge(
        pm_ctx[["player_id", "team_names", "competition_context", "in_ipl", "in_t20i"]],
        on="player_id",
        how="left",
    )

    # Attach EXTREME pressure specific stats (from breakdown table)
    ext_bk = bk_df[bk_df["pressure_level"] == "EXTREME PRESSURE"][
        ["player_id", bk_cnt_col, bk_imp_col, "strike_rate" if is_bat else "economy_rate", "innings_count"]
    ].rename(columns={
        bk_cnt_col: "extreme_balls",
        bk_imp_col: "extreme_raw_impact",
        "strike_rate" if is_bat else "economy_rate": "extreme_primary_rate",
        "innings_count": "extreme_innings",
    })
    df = df.merge(ext_bk, on="player_id", how="left")
    df["extreme_balls"] = df["extreme_balls"].fillna(0).astype(int)
    df["extreme_innings"] = df["extreme_innings"].fillna(0).astype(int)

    # Attach Pressure vs Non-Pressure context lift (from Phase 5 observational table)
    pvn_sub = pvn_df[pvn_df["discipline"] == discipline][
        ["player_id", "context_impact_diff_p_minus_np", "context_impact_diff_ci95_low", "context_impact_diff_ci95_high", "ci95_excludes_zero", "sufficient_both_sides_primary"]
    ]
    df = df.merge(pvn_sub, on="player_id", how="left")

    # Attach season years list
    seas_yrs = build_season_years_lookup(season_df, discipline)
    df["season_years_represented"] = df["player_id"].map(seas_yrs).fillna("")

    # Explicit eligibility audit reason (strictly enforcing Phase 5 cutoffs + non-null reliability)
    def eligibility_status(r: pd.Series) -> tuple[bool, str]:
        reasons = []
        if r[balls_col] < min_balls:
            reasons.append(f"pressure_balls<{min_balls} ({int(r[balls_col])})")
        if r["pressure_innings"] < min_inn:
            reasons.append(f"pressure_innings<{min_inn} ({int(r['pressure_innings'])})")
        if r["pressure_matches"] < min_inn:
            reasons.append(f"pressure_matches<{min_inn} ({int(r['pressure_matches'])})")
        if pd.isna(r["reliability_score"]):
            reasons.append("reliability_unavailable")
        if pd.isna(r["eb_pressure_impact"]):
            reasons.append("eb_impact_unavailable")
        if reasons:
            return False, "; ".join(reasons)
        return True, "ELIGIBLE"

    elig_res = df.apply(eligibility_status, axis=1, result_type="expand")
    df["ranking_eligible"] = elig_res[0].astype(bool)
    df["eligibility_reason"] = elig_res[1]

    # Compute EB-shrunk Extreme-Pressure execution + Pressure-vs-Non-Pressure lift (strictly for eligible pool)
    elig = df[df["ranking_eligible"]].copy()

    # Shrink extreme-pressure impact toward 0 with prior k_ext = 40 balls (prevents 3-ball extreme flukes)
    k_ext = 40.0
    ext_raw_filled = elig["extreme_raw_impact"].fillna(0.0)
    elig["extreme_eb_impact"] = (elig["extreme_balls"] / (elig["extreme_balls"] + k_ext)) * ext_raw_filled

    # Shrink context_impact_diff_p_minus_np toward 0 for players with smaller non-pressure sample
    np_balls_col = "nonpressure_balls_faced" if is_bat else "nonpressure_legal_balls"
    lift_wt = elig[np_balls_col] / (elig[np_balls_col] + 80.0)
    elig["pvn_shrunk_lift"] = elig["context_impact_diff_p_minus_np"].fillna(0.0) * lift_wt

    # Calibrate all 4 pillars cleanly onto a common 0-100 scale within the eligible pool
    # so nominal weights correspond to actual variance contribution (avoiding scale distortion)
    elig["norm_perf_score"] = np.round(robust_logistic_scale(elig["eb_pressure_impact"]), 3)
    elig["norm_rel_score"] = np.round(robust_logistic_scale(elig["reliability_score"]), 3)
    norm_ext = robust_logistic_scale(elig["extreme_eb_impact"])
    norm_lift = robust_logistic_scale(elig["pvn_shrunk_lift"])
    elig["norm_extreme_and_lift_score"] = np.round(0.60 * norm_ext + 0.40 * norm_lift, 3)
    elig["norm_evidence_score"] = np.round(robust_logistic_scale(elig["evidence_strength_score"]), 3)

    # Calculate composite score & rank under all three approaches
    for app_name, (wp, wr, wel, we) in RANKING_APPROACHES.items():
        sc = (
            wp * elig["norm_perf_score"]
            + wr * elig["norm_rel_score"]
            + wel * elig["norm_extreme_and_lift_score"]
            + we * elig["norm_evidence_score"]
        ).clip(0.0, 100.0).round(3)
        elig[f"score_{app_name}"] = sc
        elig[f"rank_{app_name}"] = sc.rank(ascending=False, method="min").astype(int)

    # Primary ranking = Balanced_Primary
    elig["final_ranking_score"] = elig["score_Balanced_Primary"]
    elig = elig.sort_values(
        ["final_ranking_score", "eb_pressure_impact", "reliability_score", "player_id"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    elig["rank"] = np.arange(1, len(elig) + 1)

    # Monte Carlo rank uncertainty simulation (1,000 draws perturbing eb_pressure_impact by its
    # match-clustered bootstrap SE * eb_shrinkage_weight) to quantify rank CIs and Top-10 inclusion prob!
    n_mc = 1000
    eb_vals = elig["eb_pressure_impact"].to_numpy(float)
    eb_ses = (elig["impact_boot_se"].fillna(elig["impact_boot_se"].median()) * elig["eb_shrinkage_weight"]).to_numpy(float)
    eb_med = float(np.median(eb_vals))
    eb_rsd = max(float((np.percentile(eb_vals, 75) - np.percentile(eb_vals, 25)) * 0.7413), 1e-6)

    rel_comp = elig["norm_rel_score"].to_numpy(float)
    ext_comp = elig["norm_extreme_and_lift_score"].to_numpy(float)
    ev_comp = elig["norm_evidence_score"].to_numpy(float)

    wp, wr, wel, we = RANKING_APPROACHES["Balanced_Primary"]
    draws = rng.normal(loc=eb_vals[:, None], scale=eb_ses[:, None], size=(len(elig), n_mc))
    norm_perf_draws = 100.0 / (1.0 + np.exp(-np.clip((draws - eb_med) / (eb_rsd * 1.35), -20.0, 20.0)))
    score_draws = wp * norm_perf_draws + wr * rel_comp[:, None] + wel * ext_comp[:, None] + we * ev_comp[:, None]
    # Rank each column descending (1 = highest)
    order_draws = np.argsort(-score_draws, axis=0)
    rank_draws = np.empty_like(order_draws)
    cols_idx = np.arange(n_mc)[None, :]
    rank_draws[order_draws, cols_idx] = np.arange(1, len(elig) + 1)[:, None]

    elig["mc_rank_p05"] = np.percentile(rank_draws, 5, axis=1).round(1)
    elig["mc_rank_median"] = np.percentile(rank_draws, 50, axis=1).round(1)
    elig["mc_rank_p95"] = np.percentile(rank_draws, 95, axis=1).round(1)
    elig["mc_prob_top10_pct"] = (rank_draws <= 10).mean(axis=1).round(4) * 100.0
    elig["mc_prob_top10_pct"] = elig["mc_prob_top10_pct"].round(1)

    # Data-driven strengths, limitations, and confidence descriptions (strictly statistical, never generic!)
    strengths_list, lims_list, conf_list = [], [], []
    for r in elig.itertuples():
        if is_bat:
            st_parts = [
                f"EB pressure impact {r.eb_pressure_impact:+.1f} runs/100b (raw {r.raw_pressure_impact:+.1f})",
                f"Pressure SR {r.pressure_strike_rate:.1f}, avg {r.pressure_average:.1f}" if pd.notna(r.pressure_average) else f"Pressure SR {r.pressure_strike_rate:.1f}",
                f"Boundary {r.pressure_boundary_pct:.1f}%, dot {r.pressure_dot_ball_pct:.1f}%",
            ]
            if r.extreme_balls >= 25 and pd.notna(r.extreme_primary_rate):
                st_parts.append(f"Extreme pressure: {r.extreme_balls}b @ SR {r.extreme_primary_rate:.1f}")
            lim_parts = []
            if r.evidence_tier != "HIGH_CONFIDENCE":
                lim_parts.append(f"Moderate sample ({int(r.pressure_balls_faced)} pressure balls across {int(r.pressure_matches)} matches)")
            if pd.notna(r.impact_ci95_width) and r.impact_ci95_width > 95:
                lim_parts.append(f"Wide 95% CI ({r.impact_ci95_low:+.1f} to {r.impact_ci95_high:+.1f} runs/100b)")
            if r.extreme_balls < 30:
                lim_parts.append(f"Limited EXTREME-tier exposure ({int(r.extreme_balls)} balls)")
            if r.pressure_seasons < 3:
                lim_parts.append(f"Only {int(r.pressure_seasons)} season(s) represented")
            if not r.in_ipl:
                lim_parts.append("T20I-only exposure (no IPL pressure data)")
            elif not r.in_t20i:
                lim_parts.append("IPL-only exposure (no T20I pressure data)")
            if not lim_parts:
                lim_parts.append(f"Rank uncertainty spans #{r.mc_rank_p05:.0f}-#{r.mc_rank_p95:.0f} (90% MC interval)")
        else:
            st_parts = [
                f"EB pressure impact {r.eb_pressure_impact:+.2f} runs/24b (raw {r.raw_pressure_impact:+.2f})",
                f"Pressure econ {r.pressure_economy:.2f}, {int(r.pressure_wickets)} wkts (SR {r.pressure_bowling_strike_rate:.1f})" if pd.notna(r.pressure_bowling_strike_rate) else f"Pressure econ {r.pressure_economy:.2f}",
                f"RSAE {r.pressure_rsae_per_over:+.2f}/ov, dot {r.pressure_dot_ball_pct:.1f}%",
            ]
            if r.extreme_balls >= 24 and pd.notna(r.extreme_primary_rate):
                st_parts.append(f"Extreme pressure: {r.extreme_balls}b @ econ {r.extreme_primary_rate:.2f}")
            lim_parts = []
            if r.evidence_tier != "HIGH_CONFIDENCE":
                lim_parts.append(f"Moderate sample ({int(r.pressure_legal_balls)} pressure legal balls across {int(r.pressure_matches)} matches)")
            if pd.notna(r.impact_ci95_width) and r.impact_ci95_width > 20:
                lim_parts.append(f"Wide 95% CI ({r.impact_ci95_low:+.1f} to {r.impact_ci95_high:+.1f} runs/24b)")
            if r.extreme_balls < 30:
                lim_parts.append(f"Limited EXTREME-tier exposure ({int(r.extreme_balls)} legal balls)")
            if r.pressure_seasons < 3:
                lim_parts.append(f"Only {int(r.pressure_seasons)} season(s) represented")
            if not r.in_ipl:
                lim_parts.append("T20I-only exposure (no IPL pressure data)")
            elif not r.in_t20i:
                lim_parts.append("IPL-only exposure (no T20I pressure data)")
            if not lim_parts:
                lim_parts.append(f"Rank uncertainty spans #{r.mc_rank_p05:.0f}-#{r.mc_rank_p95:.0f} (90% MC interval)")

        if r.evidence_tier == "HIGH_CONFIDENCE" and r.mc_prob_top10_pct >= 70.0:
            conf_desc = f"High Confidence ({int(r.pressure_matches)} matches, {int(r.pressure_seasons)} seasons; {r.mc_prob_top10_pct:.0f}% MC Top-10 prob)"
        elif r.evidence_tier == "HIGH_CONFIDENCE":
            conf_desc = f"High Exposure / Borderline Order ({int(r.pressure_matches)} matches; {r.mc_prob_top10_pct:.0f}% MC Top-10 prob)"
        else:
            conf_desc = f"Moderate Confidence ({int(r.pressure_matches)} matches, {int(r.pressure_seasons)} seasons; {r.mc_prob_top10_pct:.0f}% MC Top-10 prob)"

        strengths_list.append("; ".join(st_parts))
        lims_list.append("; ".join(lim_parts))
        conf_list.append(conf_desc)

    elig["key_strengths"] = strengths_list
    elig["main_limitation"] = lims_list
    elig["confidence_description"] = conf_list

    # Full candidate table (all players, attaching final rank/score where eligible)
    cand = df.merge(
        elig[["player_id", "rank", "final_ranking_score", "rank_Performance_Dominant", "rank_Reliability_Dominant", "mc_prob_top10_pct"]],
        on="player_id",
        how="left",
    ).sort_values(["ranking_eligible", "rank", balls_col], ascending=[False, True, False]).reset_index(drop=True)

    # Score component table for auditability
    comp_tbl = elig[[
        "rank", "player_id", "player_name", role_col, "evidence_tier",
        "norm_perf_score", "norm_rel_score", "norm_extreme_and_lift_score", "norm_evidence_score",
        "score_Balanced_Primary", "score_Performance_Dominant", "score_Reliability_Dominant",
        "rank_Balanced_Primary", "rank_Performance_Dominant", "rank_Reliability_Dominant",
    ]].rename(columns={role_col: "role"}).copy()
    comp_tbl.insert(0, "discipline", discipline)

    # Uncertainty table
    unc_tbl = elig[[
        "rank", "player_id", "player_name", "evidence_tier", balls_col, "pressure_matches",
        "raw_pressure_impact", "eb_pressure_impact", "eb_shrinkage_weight",
        "impact_ci95_low", "impact_ci95_high", "impact_ci95_width", "impact_boot_se",
        "raw_rate_ci95_low", "raw_rate_ci95_high",
        "mc_rank_p05", "mc_rank_median", "mc_rank_p95", "mc_prob_top10_pct",
    ]].rename(columns={balls_col: "pressure_balls"}).copy()
    unc_tbl.insert(0, "discipline", discipline)

    # Unselected candidate audit (Section 9)
    alt_rows: list[dict[str, Any]] = []
    # 1. Narrow misses (Ranks 11-15)
    for r in elig[elig["rank"].between(11, 15)].itertuples():
        alt_rows.append({
            "discipline": discipline,
            "audit_group": "narrow_miss_ranks_11_to_15",
            "player_id": r.player_id,
            "player_name": r.player_name,
            "role": getattr(r, role_col),
            "primary_rank": int(r.rank),
            "final_ranking_score": r.final_ranking_score,
            "eb_pressure_impact": r.eb_pressure_impact,
            "reliability_score": r.reliability_score,
            "evidence_strength_score": r.evidence_strength_score,
            "pressure_balls": int(getattr(r, balls_col)),
            "pressure_matches": int(r.pressure_matches),
            "note": f"Rank #{int(r.rank)} (score {r.final_ranking_score:.2f}); Perf-Dom #{int(r.rank_Performance_Dominant)}, Rel-Dom #{int(r.rank_Reliability_Dominant)}; MC Top-10 prob {r.mc_prob_top10_pct:.1f}%",
        })
    # 2. High raw performance but insufficient evidence (ineligible with >= 25 pressure balls)
    inelig_hi = df[(~df["ranking_eligible"]) & (df[balls_col] >= 25)].sort_values("raw_pressure_impact", ascending=False).head(5)
    for r in inelig_hi.itertuples():
        alt_rows.append({
            "discipline": discipline,
            "audit_group": "high_raw_performance_insufficient_evidence",
            "player_id": r.player_id,
            "player_name": r.player_name,
            "role": getattr(r, role_col),
            "primary_rank": np.nan,
            "final_ranking_score": np.nan,
            "eb_pressure_impact": r.eb_pressure_impact,
            "reliability_score": r.reliability_score,
            "evidence_strength_score": r.evidence_strength_score,
            "pressure_balls": int(getattr(r, balls_col)),
            "pressure_matches": int(r.pressure_matches),
            "note": f"Excluded: {r.eligibility_reason}; raw impact {r.raw_pressure_impact:+.1f}",
        })
    # 3. High reliability (top 10 reliability) but outside Top 10 overall due to lower performance
    hi_rel_miss = elig[(elig["rank"] > 10)].sort_values("reliability_score", ascending=False).head(5)
    for r in hi_rel_miss.itertuples():
        alt_rows.append({
            "discipline": discipline,
            "audit_group": "high_reliability_lower_performance",
            "player_id": r.player_id,
            "player_name": r.player_name,
            "role": getattr(r, role_col),
            "primary_rank": int(r.rank),
            "final_ranking_score": r.final_ranking_score,
            "eb_pressure_impact": r.eb_pressure_impact,
            "reliability_score": r.reliability_score,
            "evidence_strength_score": r.evidence_strength_score,
            "pressure_balls": int(getattr(r, balls_col)),
            "pressure_matches": int(r.pressure_matches),
            "note": f"Strong consistency (Rel {r.reliability_score:.1f}) but modest performance score ({r.performance_score:.1f}, EB impact {r.eb_pressure_impact:+.2f})",
        })
    # 4. High exposure (top 15 balls) but inconsistent (bottom quartile reliability)
    hi_exp_incons = elig[(elig[balls_col] >= elig[balls_col].quantile(0.85)) & (elig["reliability_score"] <= elig["reliability_score"].quantile(0.25))].head(5)
    for r in hi_exp_incons.itertuples():
        alt_rows.append({
            "discipline": discipline,
            "audit_group": "high_exposure_inconsistent_results",
            "player_id": r.player_id,
            "player_name": r.player_name,
            "role": getattr(r, role_col),
            "primary_rank": int(r.rank),
            "final_ranking_score": r.final_ranking_score,
            "eb_pressure_impact": r.eb_pressure_impact,
            "reliability_score": r.reliability_score,
            "evidence_strength_score": r.evidence_strength_score,
            "pressure_balls": int(getattr(r, balls_col)),
            "pressure_matches": int(r.pressure_matches),
            "note": f"Heavy exposure ({int(getattr(r, balls_col))} balls, {int(r.pressure_matches)} matches) but high innings volatility (Rel {r.reliability_score:.1f}, IQR {r.innings_impact_iqr:.1f})",
        })

    return elig, cand, comp_tbl, unc_tbl, alt_rows


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    bat_perf = pd.read_csv(PROCESSED_DIR / "player_batting_performance.csv", low_memory=False)
    bowl_perf = pd.read_csv(PROCESSED_DIR / "player_bowling_performance.csv", low_memory=False)
    bat_rel = pd.read_csv(PROCESSED_DIR / "player_batting_reliability.csv", low_memory=False)
    bowl_rel = pd.read_csv(PROCESSED_DIR / "player_bowling_reliability.csv", low_memory=False)
    bat_bk = pd.read_csv(PROCESSED_DIR / "player_batting_pressure_breakdown.csv", low_memory=False)
    bowl_bk = pd.read_csv(PROCESSED_DIR / "player_bowling_pressure_breakdown.csv", low_memory=False)
    pvn_df = pd.read_csv(PROCESSED_DIR / "player_pressure_vs_nonpressure.csv", low_memory=False)
    season_df = pd.read_csv(PROCESSED_DIR / "player_season_performance.csv", low_memory=False)
    pm = pd.read_csv(PROCESSED_DIR / "player_master.csv", low_memory=False)
    pm_ctx = build_player_competition_context(pm)

    bat_ranked, bat_cand, bat_comp, bat_unc, bat_alts = build_discipline_rankings(
        "batting", bat_perf, bat_rel, bat_bk, pvn_df, season_df, pm_ctx, rng
    )
    bowl_ranked, bowl_cand, bowl_comp, bowl_unc, bowl_alts = build_discipline_rankings(
        "bowling", bowl_perf, bowl_rel, bowl_bk, pvn_df, season_df, pm_ctx, rng
    )

    # Save processed ranking datasets
    bat_ranked.to_csv(PROCESSED_DIR / "final_batting_rankings.csv", index=False)
    bowl_ranked.to_csv(PROCESSED_DIR / "final_bowling_rankings.csv", index=False)
    bat_cand.to_csv(PROCESSED_DIR / "batting_ranking_candidates.csv", index=False)
    bowl_cand.to_csv(PROCESSED_DIR / "bowling_ranking_candidates.csv", index=False)
    pd.concat([bat_comp, bowl_comp], ignore_index=True).to_csv(PROCESSED_DIR / "ranking_score_components.csv", index=False)
    pd.concat([bat_unc, bowl_unc], ignore_index=True).to_csv(PROCESSED_DIR / "ranking_uncertainty.csv", index=False)

    # Eligibility audit table
    elig_audit_rows = []
    for disc, cand, min_b, min_i in [
        ("batting", bat_cand, BAT_MIN_BALLS, BAT_MIN_INN_MATCHES),
        ("bowling", bowl_cand, BOWL_MIN_BALLS, BOWL_MIN_INN_MATCHES),
    ]:
        tot = len(cand)
        n_el = int(cand["ranking_eligible"].sum())
        n_hc = int((cand["ranking_eligible"] & (cand["evidence_tier"] == "HIGH_CONFIDENCE")).sum())
        n_ex = tot - n_el
        elig_audit_rows.append({
            "discipline": disc,
            "total_analyzed_players": tot,
            "min_pressure_balls_rule": min_b,
            "min_pressure_innings_matches_rule": min_i,
            "eligible_candidates": n_el,
            "high_confidence_candidates": n_hc,
            "excluded_candidates": n_ex,
            "eligible_pct": round(n_el / tot * 100.0, 2),
        })
    pd.DataFrame(elig_audit_rows).to_csv(PROCESSED_DIR / "ranking_eligibility_audit.csv", index=False)

    # Method comparison summary (Approach 1 vs Approach 2 vs Approach 3 Primary)
    mc_rows = []
    for disc, ranked in [("batting", bat_ranked), ("bowling", bowl_ranked)]:
        top10_prim = set(ranked.loc[ranked["rank"] <= 10, "player_id"])
        for app_name, (wp, wr, wel, we) in RANKING_APPROACHES.items():
            sc_col = f"score_{app_name}"
            rk_col = f"rank_{app_name}"
            top10_app = set(ranked.loc[ranked[rk_col] <= 10, "player_id"])
            sp = spearman_corr(ranked["final_ranking_score"], ranked[sc_col])
            t10_sub = ranked[ranked[rk_col] <= 10]
            mc_rows.append({
                "discipline": disc,
                "approach": app_name,
                "weights_perf_rel_ext_evid": f"{wp:.2f}/{wr:.2f}/{wel:.2f}/{we:.2f}",
                "eligible_n": int(len(ranked)),
                "spearman_vs_primary": round(sp, 4),
                "top10_overlap_with_primary_count": len(top10_prim & top10_app),
                "top10_overlap_with_primary_pct": round(len(top10_prim & top10_app) / 10.0 * 100.0, 1),
                "top10_mean_eb_impact": round(float(t10_sub["eb_pressure_impact"].mean()), 3),
                "top10_mean_reliability": round(float(t10_sub["reliability_score"].mean()), 2),
                "top10_mean_evidence": round(float(t10_sub["evidence_strength_score"].mean()), 2),
                "is_selected_primary": app_name == "Balanced_Primary",
            })
    pd.DataFrame(mc_rows).to_csv(OUT_DIR / "ranking_method_comparison.csv", index=False)
    pd.DataFrame(bat_alts + bowl_alts).to_csv(OUT_DIR / "shortlist_alternatives.csv", index=False)

    print("\n=== PHASE 6 FINAL RANKING MODEL COMPLETE ===")
    print(f"Eligible Batters : {len(bat_ranked)} / {len(bat_cand)}")
    print("TOP 10 BATTERS (Balanced Primary):")
    print(bat_ranked.head(10)[[
        "rank", "player_id", "player_name", "batting_role", "final_ranking_score",
        "eb_pressure_impact", "pressure_strike_rate", "reliability_score",
        "evidence_strength_score", "pressure_balls_faced", "pressure_matches", "mc_prob_top10_pct",
    ]].to_string(index=False))

    print(f"\nEligible Bowlers : {len(bowl_ranked)} / {len(bowl_cand)}")
    print("TOP 10 BOWLERS (Balanced Primary):")
    print(bowl_ranked.head(10)[[
        "rank", "player_id", "player_name", "bowling_role", "final_ranking_score",
        "eb_pressure_impact", "pressure_economy", "pressure_wickets", "reliability_score",
        "evidence_strength_score", "pressure_legal_balls", "pressure_matches", "mc_prob_top10_pct",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()

