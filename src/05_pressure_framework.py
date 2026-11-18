"""
SupeRR Selector Season 2 - Phase 4 Pressure Framework & Index Development.

Develops three distinct, transparent, strictly pre-delivery pressure frameworks
on the validated Phase 3 dataset (data/processed/clean_deliveries.csv):
  1. chase_pressure_index         (2nd innings chase batting difficulty)
  2. first_innings_pressure_index (1st innings batting difficulty vs format baseline)
  3. bowling_pressure_index       (Bowling difficulty across 1st & 2nd innings)

Implements three explainable alternative models for comparison:
  - Model A: Transparent rule-based weighted index (fixed domain bounds)
  - Model B: Empirical percentile (ECDF) normalized index
  - Model C: Context-normalized model with leave-one-match-out (LOMO)
             IPL vs T20I historical scoring baselines (Primary recommended model)

Zero current-delivery outcomes, future innings totals, or match results are used.
No player performance scores or player rankings are calculated in this script.
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

# Empirically calibrated framework-specific classification thresholds on the 0-100 scale,
# anchored to observed p35 / p70 / p90 distributions (rounded to clean integers) so each
# framework yields ~35% LOW, ~35% MODERATE, ~20% HIGH, ~10% EXTREME without warping raw scores.
# Full comparison against equal-interval (25/50/75), shared fixed (35/55/72), and quantile
# schemes is logged in outputs/pressure_threshold_analysis.csv.
CHASE_THRESHOLDS: tuple[float, float, float] = (32.0, 50.0, 74.0)
FIRST_INNINGS_THRESHOLDS: tuple[float, float, float] = (30.0, 45.0, 61.0)
BOWLING_THRESHOLDS: tuple[float, float, float] = (47.0, 60.0, 68.0)

PRESSURE_LABELS: list[str] = [
    "LOW PRESSURE",
    "MODERATE PRESSURE",
    "HIGH PRESSURE",
    "EXTREME PRESSURE",
]


def sigmoid(x: np.ndarray | pd.Series) -> np.ndarray:
    """Numerically stable logistic sigmoid mapping (-inf, +inf) -> (0, 1)."""
    arr = np.asarray(x, dtype=float)
    clipped = np.clip(arr, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def ecdf_rank(series: pd.Series) -> pd.Series:
    """Empirical percentile rank in [0, 1] over non-null values (preserves NaN)."""
    return series.rank(pct=True, method="average")


def classify_pressure(
    scores: pd.Series,
    thresholds: tuple[float, float, float] = CHASE_THRESHOLDS,
) -> pd.Series:
    """Classify continuous 0-100 pressure scores into 4 categories; preserve UNAVAILABLE for NaN."""
    t1, t2, t3 = thresholds
    out = pd.Series("UNAVAILABLE", index=scores.index, dtype="object")
    valid = scores.notna()
    s = scores[valid]
    out.loc[valid] = np.select(
        [s < t1, s < t2, s < t3],
        PRESSURE_LABELS[:3],
        default=PRESSURE_LABELS[3],
    )
    return out


def compute_lomo_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute leave-one-match-out (LOMO) competition-specific (IPL vs T20I) empirical
    baselines strictly from pre-delivery state trajectories and phase run rates.

    Because each match is excluded from its own baseline denominator, a match's own
    trajectory never leaks into its own expected score or expected wickets.
    """
    work = df.copy()
    valid_sched = work["scheduled_legal_balls"].notna() & (work["scheduled_legal_balls"] > 0)

    # Progress fraction in [0, 1] and 20-over-equivalent bin (0..20)
    work["innings_progress"] = np.where(
        valid_sched,
        np.clip(work["legal_balls_before"] / work["scheduled_legal_balls"], 0.0, 1.0),
        np.nan,
    )
    work["progress_bin"] = np.where(
        valid_sched,
        np.clip(np.floor(work["innings_progress"] * 20.0), 0, 20),
        np.nan,
    )

    # 1. Format-level overall par RPO (LOMO by match_id)
    # Use legal balls & total runs per (format, match_id) excluding current match
    match_fmt_agg = (
        work.groupby(["eligibility_category", "match_id"], as_index=False)
        .agg(m_runs=("total_runs", "sum"), m_legal=("is_legal_delivery", "sum"))
    )
    fmt_tot = match_fmt_agg.groupby("eligibility_category", as_index=False).agg(
        f_runs=("m_runs", "sum"), f_legal=("m_legal", "sum")
    )
    match_fmt_agg = match_fmt_agg.merge(fmt_tot, on="eligibility_category", how="left")
    match_fmt_agg["format_par_rpo_lomo"] = (
        (match_fmt_agg["f_runs"] - match_fmt_agg["m_runs"])
        * 6.0
        / (match_fmt_agg["f_legal"] - match_fmt_agg["m_legal"])
    )
    work = work.merge(
        match_fmt_agg[["eligibility_category", "match_id", "format_par_rpo_lomo"]],
        on=["eligibility_category", "match_id"],
        how="left",
    )

    # 2. Format x Innings x Match Phase RPO baseline (LOMO by match_id)
    phase_m = (
        work[work["match_phase"] != "Unavailable"]
        .groupby(["eligibility_category", "innings", "match_phase", "match_id"], as_index=False)
        .agg(pm_runs=("total_runs", "sum"), pm_legal=("is_legal_delivery", "sum"))
    )
    phase_tot = phase_m.groupby(["eligibility_category", "innings", "match_phase"], as_index=False).agg(
        p_runs=("pm_runs", "sum"), p_legal=("pm_legal", "sum")
    )
    phase_m = phase_m.merge(phase_tot, on=["eligibility_category", "innings", "match_phase"], how="left")
    phase_m["phase_rpo_baseline_lomo"] = (
        (phase_m["p_runs"] - phase_m["pm_runs"])
        * 6.0
        / np.maximum(phase_m["p_legal"] - phase_m["pm_legal"], 1)
    )
    work = work.merge(
        phase_m[["eligibility_category", "innings", "match_phase", "match_id", "phase_rpo_baseline_lomo"]],
        on=["eligibility_category", "innings", "match_phase", "match_id"],
        how="left",
    )

    # 3. Format x Innings x Progress Bin empirical pre-delivery score & wickets trajectory (LOMO by match_id)
    # Normalize score to 20-over equivalent (score * 120 / scheduled_legal_balls) for baseline lookup,
    # then scale expected score back by scheduled_legal_balls / 120 so reduced-over matches get scaled par!
    valid_rows = work[valid_sched].copy()
    valid_rows["score_scaled_120"] = (
        valid_rows["cum_score_before"] * 120.0 / valid_rows["scheduled_legal_balls"]
    )
    # Match-level average per bin (one observation per match per bin so matches have equal weight)
    bin_m = (
        valid_rows.groupby(["eligibility_category", "innings", "progress_bin", "match_id"], as_index=False)
        .agg(
            mb_score=("score_scaled_120", "mean"),
            mb_wkts=("wickets_before", "mean"),
        )
    )
    bin_tot = bin_m.groupby(["eligibility_category", "innings", "progress_bin"], as_index=False).agg(
        b_score_sum=("mb_score", "sum"),
        b_wkts_sum=("mb_wkts", "sum"),
        b_n=("match_id", "count"),
        b_score_iqr=("mb_score", lambda s: float(np.percentile(s, 75) - np.percentile(s, 25)) if len(s) >= 4 else 16.0),
        b_wkts_iqr=("mb_wkts", lambda s: float(np.percentile(s, 75) - np.percentile(s, 25)) if len(s) >= 4 else 2.0),
    )
    bin_m = bin_m.merge(bin_tot, on=["eligibility_category", "innings", "progress_bin"], how="left")
    bin_m["exp_score_120_lomo"] = np.where(
        bin_m["b_n"] > 1,
        (bin_m["b_score_sum"] - bin_m["mb_score"]) / (bin_m["b_n"] - 1),
        bin_m["mb_score"],
    )
    bin_m["exp_wkts_lomo"] = np.where(
        bin_m["b_n"] > 1,
        (bin_m["b_wkts_sum"] - bin_m["mb_wkts"]) / (bin_m["b_n"] - 1),
        bin_m["mb_wkts"],
    )
    work = work.merge(
        bin_m[[
            "eligibility_category", "innings", "progress_bin", "match_id",
            "exp_score_120_lomo", "exp_wkts_lomo", "b_score_iqr", "b_wkts_iqr",
        ]],
        on=["eligibility_category", "innings", "progress_bin", "match_id"],
        how="left",
    )

    # Scale expected score back to the match's scheduled legal balls
    work["expected_score_lomo"] = np.where(
        valid_sched,
        work["exp_score_120_lomo"] * work["scheduled_legal_balls"] / 120.0,
        np.nan,
    )
    work["expected_score_iqr"] = np.where(
        valid_sched,
        np.maximum(work["b_score_iqr"] * work["scheduled_legal_balls"] / 120.0, 8.0),
        np.nan,
    )
    work["expected_wkts_lomo"] = np.where(valid_sched, work["exp_wkts_lomo"], np.nan)

    # Expected run rate at current point in innings
    work["expected_crr_lomo"] = np.where(
        valid_sched & (work["legal_balls_before"] > 0),
        work["expected_score_lomo"] * 6.0 / work["legal_balls_before"],
        work["format_par_rpo_lomo"],
    )

    # 4. Expected remaining RPO from progress_bin to end of innings (LOMO by format x innings x progress_bin)
    # Built from historical deliveries at >= progress_bin excluding current match
    bin_rem_rows = []
    for (fmt, inn_num), grp in valid_rows.groupby(["eligibility_category", "innings"]):
        # Per-match runs and legal balls in each progress_bin
        mb = (
            grp.groupby(["match_id", "progress_bin"], as_index=False)
            .agg(r=("total_runs", "sum"), l=("is_legal_delivery", "sum"))
        )
        # Total runs and legal balls at >= b across all matches and per match
        all_bins = sorted(mb["progress_bin"].unique())
        for b in all_bins:
            ge = mb[mb["progress_bin"] >= b]
            tot_r = ge["r"].sum()
            tot_l = ge["l"].sum()
            per_m = ge.groupby("match_id", as_index=False).agg(mr=("r", "sum"), ml=("l", "sum"))
            per_m["eligibility_category"] = fmt
            per_m["innings"] = inn_num
            per_m["progress_bin"] = b
            per_m["expected_remaining_rpo_lomo"] = (
                (tot_r - per_m["mr"]) * 6.0 / np.maximum(tot_l - per_m["ml"], 1)
            )
            bin_rem_rows.append(
                per_m[["eligibility_category", "innings", "progress_bin", "match_id", "expected_remaining_rpo_lomo"]]
            )
    rem_df = pd.concat(bin_rem_rows, ignore_index=True)
    work = work.merge(
        rem_df,
        on=["eligibility_category", "innings", "progress_bin", "match_id"],
        how="left",
    )

    # Clean up intermediate helper columns
    work = work.drop(columns=["exp_score_120_lomo", "b_score_iqr", "b_wkts_iqr"])
    return work


def compute_all_pressure_models(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Models A, B, and C for Chase, First Innings, and Bowling pressure (0-100)."""
    w = compute_lomo_baselines(df)

    # Integrity guard: detect live 2nd-innings deliveries where cum_score_before >= target_runs
    # (verified in Phase 4 inspection on match 48610 where revised_target=115 is corrupted)
    w["chase_target_integrity_ok"] = ~(
        (w["innings"] == 2)
        & w["target_runs"].notna()
        & (w["cum_score_before"] >= w["target_runs"])
    )

    # Valid masks for the 3 frameworks
    valid_i1 = (w["innings"] == 1) & w["scheduled_legal_balls"].notna() & (w["match_phase"] != "Unavailable")
    valid_i2 = (
        (w["innings"] == 2)
        & w["chase_context_available"]
        & w["chase_target_integrity_ok"]
        & w["required_run_rate_before"].notna()
        & w["legal_balls_remaining_before"].notna()
        & (w["legal_balls_remaining_before"] > 0)
        & (w["match_phase"] != "Unavailable")
    )
    valid_bowl = valid_i1 | valid_i2

    w["first_innings_pressure_available"] = valid_i1
    w["chase_pressure_available"] = valid_i2
    w["bowling_pressure_available"] = valid_bowl

    # Common pre-delivery derived inputs (zero leakage)
    progress = w["innings_progress"].fillna(0.0)
    progress_weight = np.clip(w["legal_balls_before"] / 18.0, 0.20, 1.0)
    wkts_lost = w["wickets_before"].astype(float)
    wkts_hand = w["wickets_in_hand_before"].astype(float)
    rrr = w["required_run_rate_before"].astype(float)
    crr = w["current_run_rate_before"].astype(float)
    # On ball 1 (legal_balls_before == 0), CRR is NaN; use format par RPO as neutral fallback for gap
    crr_filled = crr.fillna(w["format_par_rpo_lomo"])
    rrr_minus_crr = rrr - crr_filled

    # Pre-delivery striker threat (current innings ONLY, zero future info)
    bf_before = w["batter_balls_faced_before"].astype(float)
    br_before = w["batter_runs_before"].astype(float)
    pre_sr = np.where(bf_before > 0, br_before * 100.0 / bf_before, 100.0)
    sr_confidence = np.clip(bf_before / 12.0, 0.0, 1.0)
    format_par_sr = w["format_par_rpo_lomo"] * (100.0 / 6.0)

    # =========================================================================
    # MODEL A: Transparent Rule-Based Weighted Pressure Index (Fixed Domain Bounds)
    # =========================================================================
    # A1. Chase Pressure (Innings 2)
    a_rrr = np.clip((rrr - 6.0) / 10.0, 0.0, 1.0)
    a_accel = np.where(w["legal_balls_before"] > 0, np.clip((rrr - crr_filled) / 8.0, 0.0, 1.0), a_rrr)
    a_wkts = np.power(np.clip(wkts_lost / 9.0, 0.0, 1.0), 1.35)
    a_urg = np.power(progress, 1.2) * np.clip((rrr - 6.0) / 8.0, 0.15, 1.0)
    a_chase_int = a_rrr * a_wkts
    model_a_chase = 100.0 * (
        0.35 * a_rrr + 0.15 * a_accel + 0.25 * a_wkts + 0.10 * a_urg + 0.15 * a_chase_int
    )
    w["model_a_chase_pressure"] = np.where(valid_i2, np.clip(model_a_chase, 0.0, 100.0), np.nan)

    # A2. First-Innings Batting Pressure (Innings 1, fixed 8.5 RPO par)
    a_exp_score_i1 = 8.5 * w["legal_balls_before"] / 6.0
    a_exp_wkts_i1 = 6.0 * progress
    a_i1_wkt_exc = np.clip((wkts_lost - a_exp_wkts_i1 + 1.5) / 5.5, 0.0, 1.0)
    a_i1_wkt_abs = np.power(np.clip(wkts_lost / 9.0, 0.0, 1.0), 1.35)
    a_i1_lag = np.clip((a_exp_score_i1 - w["cum_score_before"] + 10.0) / 45.0, 0.0, 1.0) * progress_weight
    a_i1_stage = np.clip((progress - 0.50) / 0.50, 0.0, 1.0) * (0.4 + 0.6 * a_i1_lag)
    a_i1_int = a_i1_wkt_exc * a_i1_lag
    model_a_i1 = 100.0 * (
        0.30 * a_i1_wkt_exc + 0.20 * a_i1_wkt_abs + 0.25 * a_i1_lag + 0.10 * a_i1_stage + 0.15 * a_i1_int
    )
    w["model_a_first_innings_pressure"] = np.where(valid_i1, np.clip(model_a_i1, 0.0, 100.0), np.nan)

    # A3. Bowling Pressure (Both Innings)
    a_phase_map = w["match_phase"].map({"Death": 1.0, "Powerplay": 0.65, "Middle": 0.35}).fillna(np.nan)
    a_wkts_hand = np.power(np.clip(wkts_hand / 10.0, 0.0, 1.0), 1.2)
    a_bat_threat = np.clip(
        0.65 * np.clip(br_before / 45.0, 0.0, 1.0)
        + 0.35 * np.clip((pre_sr - 100.0) / 100.0, 0.0, 1.0) * sr_confidence,
        0.0,
        1.0,
    )
    # Inn 2 bowling
    a_b2_close = np.exp(-0.5 * np.square((rrr - 10.0) / 4.0))
    a_b2_end = progress * a_b2_close
    model_a_bowl_i2 = 100.0 * (
        0.30 * a_b2_close + 0.25 * a_wkts_hand + 0.20 * a_phase_map + 0.15 * a_bat_threat + 0.10 * a_b2_end
    )
    # Inn 1 bowling
    a_b1_surge = np.clip((w["cum_score_before"] - a_exp_score_i1 + 15.0) / 50.0, 0.0, 1.0) * progress_weight + 0.35 * (1.0 - progress_weight)
    a_b1_int = a_b1_surge * a_wkts_hand
    model_a_bowl_i1 = 100.0 * (
        0.28 * a_b1_surge + 0.22 * a_wkts_hand + 0.22 * a_phase_map + 0.15 * a_bat_threat + 0.13 * a_b1_int
    )
    w["model_a_bowling_pressure"] = np.where(
        valid_i1,
        np.clip(model_a_bowl_i1, 0.0, 100.0),
        np.where(valid_i2, np.clip(model_a_bowl_i2, 0.0, 100.0), np.nan),
    )

    # =========================================================================
    # MODEL B: Empirical Percentile-Based Pressure Index (ECDF Rank Scaling)
    # =========================================================================
    # B1. Chase Pressure (Innings 2, pooled ECDF ranks over valid_i2)
    b_rrr_pct = ecdf_rank(rrr.where(valid_i2))
    b_acc_pct = ecdf_rank(rrr_minus_crr.where(valid_i2))
    b_wkt_pct = ecdf_rank(wkts_lost.where(valid_i2))
    b_prog_pct = ecdf_rank(progress.where(valid_i2))
    b_chase_int = b_rrr_pct * b_wkt_pct
    model_b_chase = 100.0 * (
        0.35 * b_rrr_pct + 0.15 * b_acc_pct + 0.25 * b_wkt_pct + 0.10 * b_prog_pct + 0.15 * b_chase_int
    )
    w["model_b_chase_pressure"] = np.where(valid_i2, np.clip(model_b_chase, 0.0, 100.0), np.nan)

    # B2. First-Innings Batting Pressure (pooled median score/wkts deficit ECDF)
    pooled_score_med = w.loc[valid_i1].groupby("progress_bin")["cum_score_before"].transform("median")
    pooled_wkts_med = w.loc[valid_i1].groupby("progress_bin")["wickets_before"].transform("median")
    score_def_b = pd.Series(np.nan, index=w.index, dtype=float)
    wkts_exc_b = pd.Series(np.nan, index=w.index, dtype=float)
    score_def_b.loc[valid_i1] = (pooled_score_med - w.loc[valid_i1, "cum_score_before"]) * progress_weight.loc[valid_i1]
    wkts_exc_b.loc[valid_i1] = w.loc[valid_i1, "wickets_before"] - pooled_wkts_med

    b_i1_def_pct = ecdf_rank(score_def_b)
    b_i1_wexc_pct = ecdf_rank(wkts_exc_b)
    b_i1_wabs_pct = ecdf_rank(wkts_lost.where(valid_i1))
    b_i1_prog_pct = ecdf_rank(progress.where(valid_i1))
    b_i1_int = b_i1_def_pct * b_i1_wexc_pct
    model_b_i1 = 100.0 * (
        0.30 * b_i1_def_pct + 0.30 * b_i1_wexc_pct + 0.15 * b_i1_wabs_pct + 0.10 * b_i1_prog_pct + 0.15 * b_i1_int
    )
    w["model_b_first_innings_pressure"] = np.where(valid_i1, np.clip(model_b_i1, 0.0, 100.0), np.nan)

    # B3. Bowling Pressure (ECDF normalized per innings)
    b_close_raw = pd.Series(np.nan, index=w.index, dtype=float)
    b_close_raw.loc[valid_i2] = -np.abs(rrr.loc[valid_i2] - rrr.loc[valid_i2].median())
    b_b2_close_pct = ecdf_rank(b_close_raw)
    b_b2_whand_pct = ecdf_rank(wkts_hand.where(valid_i2))
    b_b2_phase_pct = ecdf_rank(a_phase_map.where(valid_i2))
    b_b2_threat_pct = ecdf_rank(pd.Series(a_bat_threat, index=w.index).where(valid_i2))
    b_b2_end_pct = b_b2_close_pct * b_prog_pct
    model_b_bowl_i2 = 100.0 * (
        0.30 * b_b2_close_pct + 0.25 * b_b2_whand_pct + 0.18 * b_b2_phase_pct + 0.15 * b_b2_threat_pct + 0.12 * b_b2_end_pct
    )

    b_b1_surge_pct = ecdf_rank((-score_def_b).where(valid_i1))
    b_b1_whand_pct = ecdf_rank(wkts_hand.where(valid_i1))
    b_b1_phase_pct = ecdf_rank(a_phase_map.where(valid_i1))
    b_b1_threat_pct = ecdf_rank(pd.Series(a_bat_threat, index=w.index).where(valid_i1))
    b_b1_int = b_b1_surge_pct * b_b1_whand_pct
    model_b_bowl_i1 = 100.0 * (
        0.28 * b_b1_surge_pct + 0.22 * b_b1_whand_pct + 0.20 * b_b1_phase_pct + 0.15 * b_b1_threat_pct + 0.15 * b_b1_int
    )
    w["model_b_bowling_pressure"] = np.where(
        valid_i1,
        np.clip(model_b_bowl_i1, 0.0, 100.0),
        np.where(valid_i2, np.clip(model_b_bowl_i2, 0.0, 100.0), np.nan),
    )

    # =========================================================================
    # MODEL C (PRIMARY): Context-Normalized Model with LOMO IPL vs T20I Baselines
    # =========================================================================
    # C1. Chase Pressure (Innings 2)
    c_rrr_vs_rem = sigmoid((rrr - w["expected_remaining_rpo_lomo"]) / 2.75)
    c_rrr_vs_fmt = sigmoid((rrr - w["format_par_rpo_lomo"]) / 3.0)
    c_rrr_comp = 0.65 * c_rrr_vs_rem + 0.35 * c_rrr_vs_fmt

    c_wkt_abs = np.power(np.clip(wkts_lost / 9.0, 0.0, 1.0), 1.30)
    c_wkt_rel = sigmoid((wkts_lost - w["expected_wkts_lomo"]) / 1.50)
    c_wkt_comp = 0.60 * c_wkt_abs + 0.40 * c_wkt_rel

    c_accel_comp = np.where(
        w["legal_balls_before"] > 0,
        sigmoid(((rrr - crr_filled) - 0.50) / 3.0),
        c_rrr_comp,
    )
    c_endgame_comp = progress * sigmoid((rrr - w["format_par_rpo_lomo"] + 1.50) / 2.50)
    c_chase_int = c_rrr_comp * c_wkt_comp

    # Store transparent sub-components for audit & sensitivity analysis
    w["comp_chase_rrr"] = np.where(valid_i2, c_rrr_comp, np.nan)
    w["comp_chase_wickets"] = np.where(valid_i2, c_wkt_comp, np.nan)
    w["comp_chase_accel"] = np.where(valid_i2, c_accel_comp, np.nan)
    w["comp_chase_urgency"] = np.where(valid_i2, c_endgame_comp, np.nan)
    w["comp_chase_interaction"] = np.where(valid_i2, c_chase_int, np.nan)

    model_c_chase = 100.0 * (
        0.34 * c_rrr_comp
        + 0.24 * c_wkt_comp
        + 0.14 * c_accel_comp
        + 0.12 * c_endgame_comp
        + 0.16 * c_chase_int
    )
    w["model_c_chase_pressure"] = np.where(valid_i2, np.clip(model_c_chase, 0.0, 100.0), np.nan)

    # C2. First-Innings Batting Pressure (Innings 1)
    # Robust z-score of score deficit using format-specific LOMO trajectory & IQR
    robust_sd = np.maximum(w["expected_score_iqr"] * 0.7413, 8.0)
    c_i1_score_def = sigmoid((w["expected_score_lomo"] - w["cum_score_before"]) / robust_sd) * progress_weight + 0.30 * (1.0 - progress_weight)
    c_i1_wkt_rel = sigmoid((wkts_lost - w["expected_wkts_lomo"]) / 1.35)
    c_i1_wkt_abs = np.power(np.clip(wkts_lost / 9.0, 0.0, 1.0), 1.30)
    c_i1_wkt_comp = 0.55 * c_i1_wkt_rel + 0.45 * c_i1_wkt_abs
    c_i1_crr_lag = np.where(
        w["legal_balls_before"] > 0,
        sigmoid((w["expected_crr_lomo"] - crr_filled) / 2.20) * progress_weight + 0.30 * (1.0 - progress_weight),
        0.30,
    )
    c_i1_stage = np.clip((progress - 0.55) / 0.45, 0.0, 1.0) * (0.45 + 0.55 * c_i1_score_def)
    c_i1_int = c_i1_score_def * c_i1_wkt_comp

    w["comp_i1_score_deficit"] = np.where(valid_i1, c_i1_score_def, np.nan)
    w["comp_i1_wicket_collapse"] = np.where(valid_i1, c_i1_wkt_comp, np.nan)
    w["comp_i1_crr_lag"] = np.where(valid_i1, c_i1_crr_lag, np.nan)
    w["comp_i1_stage_urgency"] = np.where(valid_i1, c_i1_stage, np.nan)
    w["comp_i1_interaction"] = np.where(valid_i1, c_i1_int, np.nan)

    model_c_i1 = 100.0 * (
        0.30 * c_i1_score_def
        + 0.30 * c_i1_wkt_comp
        + 0.15 * c_i1_crr_lag
        + 0.10 * c_i1_stage
        + 0.15 * c_i1_int
    )
    w["model_c_first_innings_pressure"] = np.where(valid_i1, np.clip(model_c_i1, 0.0, 100.0), np.nan)

    # C3. Bowling Pressure (Both Innings)
    c_b_whand = np.power(np.clip(wkts_hand / 10.0, 0.0, 1.0), 1.15)
    c_b_phase = np.clip((w["phase_rpo_baseline_lomo"] - 7.0) / 4.5, 0.20, 1.0)
    c_b_threat = np.clip(
        0.55 * sigmoid((br_before - 22.0) / 14.0)
        + 0.45 * sigmoid((pre_sr - format_par_sr) / 35.0) * sr_confidence
        + 0.15 * (1.0 - sr_confidence) * 0.45,
        0.0,
        1.0,
    )

    # Inn 2 bowling (defending target)
    c_b2_close = np.exp(-0.5 * np.square((rrr - w["expected_remaining_rpo_lomo"]) / 3.80))
    c_b2_endgame = progress * c_b2_close
    model_c_bowl_i2 = 100.0 * (
        0.30 * c_b2_close
        + 0.22 * c_b_whand
        + 0.18 * c_b_phase
        + 0.15 * c_b_threat
        + 0.15 * c_b2_endgame
    )

    # Inn 1 bowling (containing opponent momentum)
    c_b1_opp = sigmoid((w["cum_score_before"] - w["expected_score_lomo"]) / robust_sd) * progress_weight + 0.35 * (1.0 - progress_weight)
    c_b1_int = c_b1_opp * c_b_whand
    model_c_bowl_i1 = 100.0 * (
        0.28 * c_b1_opp
        + 0.22 * c_b_whand
        + 0.20 * c_b_phase
        + 0.15 * c_b_threat
        + 0.15 * c_b1_int
    )

    w["comp_bowl_situation"] = np.where(valid_i1, c_b1_opp, np.where(valid_i2, c_b2_close, np.nan))
    w["comp_bowl_wickets_in_hand"] = np.where(valid_bowl, c_b_whand, np.nan)
    w["comp_bowl_phase_hazard"] = np.where(valid_bowl, c_b_phase, np.nan)
    w["comp_bowl_batter_threat"] = np.where(valid_bowl, c_b_threat, np.nan)
    w["comp_bowl_leverage_interaction"] = np.where(valid_i1, c_b1_int, np.where(valid_i2, c_b2_endgame, np.nan))

    w["model_c_bowling_pressure"] = np.where(
        valid_i1,
        np.clip(model_c_bowl_i1, 0.0, 100.0),
        np.where(valid_i2, np.clip(model_c_bowl_i2, 0.0, 100.0), np.nan),
    )

    # =========================================================================
    # Primary Selected Indices (= Model C) & 4-Tier Classification
    # =========================================================================
    w["chase_pressure_index"] = w["model_c_chase_pressure"].round(4)
    w["first_innings_pressure_index"] = w["model_c_first_innings_pressure"].round(4)
    w["bowling_pressure_index"] = w["model_c_bowling_pressure"].round(4)
    w["batting_pressure_index"] = np.where(
        w["innings"] == 1, w["first_innings_pressure_index"], w["chase_pressure_index"]
    )

    # Round alternative model indices cleanly
    for col in [
        "model_a_chase_pressure", "model_a_first_innings_pressure", "model_a_bowling_pressure",
        "model_b_chase_pressure", "model_b_first_innings_pressure", "model_b_bowling_pressure",
        "model_c_chase_pressure", "model_c_first_innings_pressure", "model_c_bowling_pressure",
    ]:
        w[col] = w[col].round(4)

    w["chase_pressure_level"] = classify_pressure(w["chase_pressure_index"], CHASE_THRESHOLDS)
    w["first_innings_pressure_level"] = classify_pressure(w["first_innings_pressure_index"], FIRST_INNINGS_THRESHOLDS)
    w["bowling_pressure_level"] = classify_pressure(w["bowling_pressure_index"], BOWLING_THRESHOLDS)
    w["batting_pressure_level"] = np.where(
        w["innings"] == 1, w["first_innings_pressure_level"], w["chase_pressure_level"]
    )

    return w


def build_summaries_and_outputs(w: pd.DataFrame) -> None:
    """Write processed pressure datasets and Phase 4 summary CSV outputs."""
    # 1. data/processed/pressure_deliveries.csv
    w.to_csv(PROCESSED_DIR / "pressure_deliveries.csv", index=False)

    # 2. data/processed/pressure_innings_summary.csv
    inn_sum = (
        w.groupby(["match_id", "innings", "comp_id", "comp_name", "eligibility_category", "season", "innings_type"], as_index=False)
        .agg(
            total_deliveries=("match_id", "size"),
            legal_deliveries=("is_legal_delivery", "sum"),
            batting_pressure_valid_balls=("batting_pressure_index", lambda s: int(s.notna().sum())),
            bowling_pressure_valid_balls=("bowling_pressure_index", lambda s: int(s.notna().sum())),
            mean_batting_pressure=("batting_pressure_index", "mean"),
            max_batting_pressure=("batting_pressure_index", "max"),
            high_or_extreme_batting_balls=("batting_pressure_level", lambda s: int(s.isin(["HIGH PRESSURE", "EXTREME PRESSURE"]).sum())),
            extreme_batting_balls=("batting_pressure_level", lambda s: int((s == "EXTREME PRESSURE").sum())),
            mean_bowling_pressure=("bowling_pressure_index", "mean"),
            max_bowling_pressure=("bowling_pressure_index", "max"),
            high_or_extreme_bowling_balls=("bowling_pressure_level", lambda s: int(s.isin(["HIGH PRESSURE", "EXTREME PRESSURE"]).sum())),
            extreme_bowling_balls=("bowling_pressure_level", lambda s: int((s == "EXTREME PRESSURE").sum())),
        )
    )
    for c in ["mean_batting_pressure", "max_batting_pressure", "mean_bowling_pressure", "max_bowling_pressure"]:
        inn_sum[c] = inn_sum[c].round(3)
    inn_sum["has_high_or_extreme_batting"] = inn_sum["high_or_extreme_batting_balls"] > 0
    inn_sum["has_high_or_extreme_bowling"] = inn_sum["high_or_extreme_bowling_balls"] > 0
    inn_sum.to_csv(PROCESSED_DIR / "pressure_innings_summary.csv", index=False)

    # 3. data/processed/pressure_match_summary.csv
    match_sum = (
        w.groupby(["match_id", "comp_id", "comp_name", "eligibility_category", "season"], as_index=False)
        .agg(
            total_deliveries=("match_id", "size"),
            innings_count=("innings", "nunique"),
            mean_i1_pressure=("first_innings_pressure_index", "mean"),
            max_i1_pressure=("first_innings_pressure_index", "max"),
            mean_chase_pressure=("chase_pressure_index", "mean"),
            max_chase_pressure=("chase_pressure_index", "max"),
            mean_bowling_pressure=("bowling_pressure_index", "mean"),
            max_bowling_pressure=("bowling_pressure_index", "max"),
            high_or_extreme_batting_balls=("batting_pressure_level", lambda s: int(s.isin(["HIGH PRESSURE", "EXTREME PRESSURE"]).sum())),
            high_or_extreme_bowling_balls=("bowling_pressure_level", lambda s: int(s.isin(["HIGH PRESSURE", "EXTREME PRESSURE"]).sum())),
        )
    )
    for c in ["mean_i1_pressure", "max_i1_pressure", "mean_chase_pressure", "max_chase_pressure", "mean_bowling_pressure", "max_bowling_pressure"]:
        match_sum[c] = match_sum[c].round(3)
    match_sum.to_csv(PROCESSED_DIR / "pressure_match_summary.csv", index=False)

    # 4. outputs/pressure_distribution.csv (quantiles & moments by framework and competition)
    dist_rows = []
    framework_specs = [
        ("chase_pressure_index", "Chase (Inn 2)"),
        ("first_innings_pressure_index", "First Innings (Inn 1)"),
        ("batting_pressure_index", "Batting Combined (Inn 1+2)"),
        ("bowling_pressure_index", "Bowling (Inn 1+2)"),
    ]
    for col, label in framework_specs:
        for scope_name, sub_df in [
            ("ALL_PRIMARY", w),
            ("IPL", w[w["eligibility_category"] == "IPL"]),
            ("T20I", w[w["eligibility_category"] == "T20I"]),
        ]:
            s = sub_df[col].dropna()
            if len(s) == 0:
                continue
            qs = s.quantile([0.05, 0.10, 0.25, 0.50, 0.75, 0.85, 0.90, 0.95]).to_dict()
            dist_rows.append({
                "framework": label,
                "column": col,
                "scope": scope_name,
                "valid_deliveries": int(len(s)),
                "unavailable_deliveries": int(sub_df[col].isna().sum()),
                "mean": round(float(s.mean()), 3),
                "std": round(float(s.std()), 3),
                "min": round(float(s.min()), 3),
                "p05": round(float(qs[0.05]), 3),
                "p10": round(float(qs[0.10]), 3),
                "p25": round(float(qs[0.25]), 3),
                "p50": round(float(qs[0.50]), 3),
                "p75": round(float(qs[0.75]), 3),
                "p85": round(float(qs[0.85]), 3),
                "p90": round(float(qs[0.90]), 3),
                "p95": round(float(qs[0.95]), 3),
                "max": round(float(s.max()), 3),
            })
    pd.DataFrame(dist_rows).to_csv(OUT_DIR / "pressure_distribution.csv", index=False)

    # 5. outputs/pressure_level_summary.csv (deliveries, unique innings, unique matches per level)
    level_rows = []
    for idx_col, lvl_col, fw_label, base_mask in [
        ("chase_pressure_index", "chase_pressure_level", "Chase (Inn 2)", w["innings"] == 2),
        ("first_innings_pressure_index", "first_innings_pressure_level", "First Innings (Inn 1)", w["innings"] == 1),
        ("batting_pressure_index", "batting_pressure_level", "Batting Combined (Inn 1+2)", pd.Series(True, index=w.index)),
        ("bowling_pressure_index", "bowling_pressure_level", "Bowling (Inn 1+2)", pd.Series(True, index=w.index)),
    ]:
        sub = w[base_mask].copy()
        sub["innings_key"] = sub["match_id"].astype(str) + "_" + sub["innings"].astype(str)
        total_valid = int(sub[idx_col].notna().sum())
        for lvl in PRESSURE_LABELS + ["UNAVAILABLE"]:
            grp = sub[sub[lvl_col] == lvl]
            n_del = int(len(grp))
            n_inn = int(grp["innings_key"].nunique())
            n_mat = int(grp["match_id"].nunique())
            level_rows.append({
                "framework": fw_label,
                "pressure_level": lvl,
                "deliveries": n_del,
                "pct_of_scope_deliveries": round(n_del / len(sub) * 100.0, 2) if len(sub) else 0.0,
                "pct_of_valid_deliveries": round(n_del / total_valid * 100.0, 2) if (lvl != "UNAVAILABLE" and total_valid) else np.nan,
                "unique_innings": n_inn,
                "unique_matches": n_mat,
                "mean_balls_per_exposed_innings": round(n_del / n_inn, 2) if n_inn else 0.0,
                "mean_index": round(float(grp[idx_col].mean()), 2) if grp[idx_col].notna().any() else np.nan,
            })
    pd.DataFrame(level_rows).to_csv(OUT_DIR / "pressure_level_summary.csv", index=False)

    # 6. outputs/pressure_component_summary.csv
    comp_cols = [
        ("Chase", "comp_chase_rrr", 0.34, "chase_pressure_index"),
        ("Chase", "comp_chase_wickets", 0.24, "chase_pressure_index"),
        ("Chase", "comp_chase_accel", 0.14, "chase_pressure_index"),
        ("Chase", "comp_chase_urgency", 0.12, "chase_pressure_index"),
        ("Chase", "comp_chase_interaction", 0.16, "chase_pressure_index"),
        ("First Innings", "comp_i1_score_deficit", 0.30, "first_innings_pressure_index"),
        ("First Innings", "comp_i1_wicket_collapse", 0.30, "first_innings_pressure_index"),
        ("First Innings", "comp_i1_crr_lag", 0.15, "first_innings_pressure_index"),
        ("First Innings", "comp_i1_stage_urgency", 0.10, "first_innings_pressure_index"),
        ("First Innings", "comp_i1_interaction", 0.15, "first_innings_pressure_index"),
        ("Bowling", "comp_bowl_situation", 0.29, "bowling_pressure_index"),
        ("Bowling", "comp_bowl_wickets_in_hand", 0.22, "bowling_pressure_index"),
        ("Bowling", "comp_bowl_phase_hazard", 0.19, "bowling_pressure_index"),
        ("Bowling", "comp_bowl_batter_threat", 0.15, "bowling_pressure_index"),
        ("Bowling", "comp_bowl_leverage_interaction", 0.15, "bowling_pressure_index"),
    ]
    comp_rows = []
    for fw, col, wt, target_col in comp_cols:
        valid = w[col].notna() & w[target_col].notna()
        s = w.loc[valid, col]
        corr = float(s.corr(w.loc[valid, target_col]))
        comp_rows.append({
            "framework": fw,
            "component": col,
            "nominal_weight": wt,
            "valid_n": int(len(s)),
            "mean": round(float(s.mean()), 4),
            "std": round(float(s.std()), 4),
            "p10": round(float(s.quantile(0.10)), 4),
            "p50": round(float(s.quantile(0.50)), 4),
            "p90": round(float(s.quantile(0.90)), 4),
            "pearson_corr_with_index": round(corr, 4),
        })
    pd.DataFrame(comp_rows).to_csv(OUT_DIR / "pressure_component_summary.csv", index=False)

    # 7. outputs/pressure_exposure_summary.csv (multi-dimensional exposure with unique innings & matches)
    w_exp = w.copy()
    w_exp["innings_key"] = w_exp["match_id"].astype(str) + "_" + w_exp["innings"].astype(str)
    w_exp["season_year"] = w_exp["season"].astype(str).str.extract(r"(\d{4})")[0]
    w_exp["over_bucket"] = pd.cut(
        w_exp["overid"], bins=[0, 6, 10, 15, 20], labels=["Overs 1-6", "Overs 7-10", "Overs 11-15", "Overs 16-20"]
    ).astype(str)
    w_exp["wkts_rem_bucket"] = pd.cut(
        w_exp["wickets_in_hand_before"], bins=[-1, 3, 5, 7, 10], labels=["1-3 Wkts Left", "4-5 Wkts Left", "6-7 Wkts Left", "8-10 Wkts Left"]
    ).astype(str)
    w_exp["rrr_bucket"] = pd.cut(
        w_exp["required_run_rate_before"],
        bins=[-0.01, 6.0, 8.5, 11.0, 14.0, 18.0, 1000.0],
        labels=["<=6.0 RPO", "6.0-8.5 RPO", "8.5-11.0 RPO", "11.0-14.0 RPO", "14.0-18.0 RPO", ">18.0 RPO"],
    ).astype(str).replace({"nan": "N/A (Inn 1 or Unavail)"})

    exp_rows = []
    for dim_name, dim_col in [
        ("match_phase", "match_phase"),
        ("over_bucket", "over_bucket"),
        ("wickets_remaining", "wkts_rem_bucket"),
        ("required_run_rate", "rrr_bucket"),
        ("competition_format", "eligibility_category"),
        ("season_year", "season_year"),
    ]:
        for val, grp in w_exp.groupby(dim_col, dropna=False):
            bat_hi = grp[grp["batting_pressure_level"].isin(["HIGH PRESSURE", "EXTREME PRESSURE"])]
            bowl_hi = grp[grp["bowling_pressure_level"].isin(["HIGH PRESSURE", "EXTREME PRESSURE"])]
            exp_rows.append({
                "dimension": dim_name,
                "segment": str(val),
                "total_deliveries": int(len(grp)),
                "unique_innings": int(grp["innings_key"].nunique()),
                "unique_matches": int(grp["match_id"].nunique()),
                "mean_batting_pressure": round(float(grp["batting_pressure_index"].mean()), 2) if grp["batting_pressure_index"].notna().any() else np.nan,
                "high_extreme_batting_deliveries": int(len(bat_hi)),
                "high_extreme_batting_pct": round(len(bat_hi) / max(int(grp["batting_pressure_index"].notna().sum()), 1) * 100.0, 2),
                "high_extreme_batting_innings": int(bat_hi["innings_key"].nunique()),
                "high_extreme_batting_matches": int(bat_hi["match_id"].nunique()),
                "mean_bowling_pressure": round(float(grp["bowling_pressure_index"].mean()), 2) if grp["bowling_pressure_index"].notna().any() else np.nan,
                "high_extreme_bowling_deliveries": int(len(bowl_hi)),
                "high_extreme_bowling_pct": round(len(bowl_hi) / max(int(grp["bowling_pressure_index"].notna().sum()), 1) * 100.0, 2),
                "high_extreme_bowling_innings": int(bowl_hi["innings_key"].nunique()),
                "high_extreme_bowling_matches": int(bowl_hi["match_id"].nunique()),
            })
    pd.DataFrame(exp_rows).to_csv(OUT_DIR / "pressure_exposure_summary.csv", index=False)


def main() -> None:
    df = pd.read_csv(
        PROCESSED_DIR / "clean_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    for bcol in ["is_legal_delivery", "is_wicket_event", "is_super_over", "is_primary_eligible", "chase_context_available"]:
        df[bcol] = df[bcol].astype(str).str.lower().eq("true")

    print(f"Loaded {len(df):,} primary regular deliveries from data/processed/clean_deliveries.csv")
    enriched = compute_all_pressure_models(df)
    build_summaries_and_outputs(enriched)

    print("\n=== PHASE 4 PRESSURE FRAMEWORK COMPLETE ===")
    for col, label in [
        ("chase_pressure_index", "Chase Pressure (Inn 2)"),
        ("first_innings_pressure_index", "First Innings Pressure (Inn 1)"),
        ("bowling_pressure_index", "Bowling Pressure (Inn 1+2)"),
    ]:
        s = enriched[col].dropna()
        print(
            f"  {label:30s}: valid={len(s):>7,} | mean={s.mean():5.2f} | std={s.std():5.2f} | "
            f"p25={s.quantile(0.25):5.2f} | p50={s.quantile(0.50):5.2f} | p75={s.quantile(0.75):5.2f} | p90={s.quantile(0.90):5.2f}"
        )
    print("\nLevel distribution (Batting Combined):")
    print(enriched["batting_pressure_level"].value_counts().to_string())
    print("\nLevel distribution (Bowling):")
    print(enriched["bowling_pressure_level"].value_counts().to_string())


if __name__ == "__main__":
    main()

