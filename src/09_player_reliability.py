"""
SupeRR Selector Season 2 - Phase 5 Player Reliability, Uncertainty & Pressure-vs-Non-Pressure Modeling.

Strictly separates three analytical pillars for both batting and bowling:
  1. Performance Under Pressure (Raw & Empirical-Bayes shrunk context-adjusted impact)
  2. Reliability / Consistency (0-100 stability across innings, conditions & seasons — NOT volume)
  3. Evidence Strength & Uncertainty (Match-clustered bootstrap 95% CIs & exposure tiers)

Key statistical guarantees:
  - Resampling for bootstrap CIs is strictly clustered at the match_id level (never ball-level).
  - Empirical Bayes shrinkage k = sigma_within^2 / tau_between^2 is estimated empirically from
    match-level variance components (never an arbitrary constant).
  - Players with insufficient pressure exposure (< 5 pressure innings or below minimum balls)
    are explicitly labeled INSUFFICIENT_EVIDENCE rather than given fabricated ratings.
  - Pressure vs. non-pressure comparisons are strictly observational (never causal claims).
  - No final Top 10 rankings are produced in this script.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"

HIGH_PRESSURE_CATS = ["HIGH PRESSURE", "EXTREME PRESSURE"]
NON_PRESSURE_CATS = ["LOW PRESSURE", "MODERATE PRESSURE"]
BOOTSTRAP_B = 500
RNG_SEED = 42


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load pressure_deliveries.csv plus Phase 5 batting and bowling performance tables."""
    df = pd.read_csv(
        PROCESSED_DIR / "pressure_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    bat_perf = pd.read_csv(PROCESSED_DIR / "player_batting_performance.csv", low_memory=False)
    bowl_perf = pd.read_csv(PROCESSED_DIR / "player_bowling_performance.csv", low_memory=False)

    for bcol in [
        "is_legal_delivery", "is_batter_ball_faced", "is_wicket_event",
        "is_bowler_wicket", "is_four", "is_six",
    ]:
        df[bcol] = df[bcol].astype(str).str.lower().eq("true")

    df["season_year"] = df["season"].astype(str).str.extract(r"(\d{4})")[0].astype(int)
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                {
                    "innings_key": df["match_id"].astype(str) + "_" + df["innings"].astype(str),
                    "dismissed_player_id_int": pd.to_numeric(df["dismissed_player_id"], errors="coerce"),
                },
                index=df.index,
            ),
        ],
        axis=1,
    )
    return df, bat_perf, bowl_perf


def attach_lomo_expectations(df: pd.DataFrame) -> pd.DataFrame:
    """Attach LOMO format x innings x phase x pressure_level batting & bowling expected values."""
    w = df.copy()
    # Batting expectations
    bv = w[w["batting_pressure_index"].notna() & w["is_batter_ball_faced"]]
    bg = ["eligibility_category", "innings", "match_phase", "batting_pressure_level"]
    bm = bv.groupby(bg + ["match_id"], as_index=False).agg(r=("batter_runs", "sum"), n=("is_batter_ball_faced", "sum"), k=("is_wicket_event", "sum"))
    bt = bm.groupby(bg, as_index=False).agg(tr=("r", "sum"), tn=("n", "sum"), tk=("k", "sum"))
    bm = bm.merge(bt, on=bg, how="left")
    den = np.maximum(bm["tn"] - bm["n"], 1)
    bm["exp_bat_r"] = (bm["tr"] - bm["r"]) / den
    bm["exp_bat_k"] = (bm["tk"] - bm["k"]) / den
    w = w.merge(bm[bg + ["match_id", "exp_bat_r", "exp_bat_k"]], on=bg + ["match_id"], how="left")

    # Bowling expectations
    lv = w[w["bowling_pressure_index"].notna()]
    lg = ["eligibility_category", "innings", "match_phase", "bowling_pressure_level"]
    lm = lv.groupby(lg + ["match_id"], as_index=False).agg(rc=("bowler_conceded_runs", "sum"), lb=("is_legal_delivery", "sum"), bw=("is_bowler_wicket", "sum"))
    lt = lm.groupby(lg, as_index=False).agg(trc=("rc", "sum"), tlb=("lb", "sum"), tbw=("bw", "sum"))
    lm = lm.merge(lt, on=lg, how="left")
    lden = np.maximum(lm["tlb"] - lm["lb"], 1)
    lm["exp_bowl_rc"] = (lm["trc"] - lm["rc"]) / lden
    lm["exp_bowl_bw"] = (lm["tbw"] - lm["bw"]) / lden
    w = w.merge(lm[lg + ["match_id", "exp_bowl_rc", "exp_bowl_bw"]], on=lg + ["match_id"], how="left")
    return w


def estimate_empirical_bayes_k(
    match_df: pd.DataFrame,
    player_col: str,
    num_col: str,
    den_col: str,
    scale_factor: float,
    min_matches: int = 10,
) -> tuple[float, float, float, float]:
    """
    Estimate empirical Bayes shrinkage prior k = sigma_within^2 / tau_between^2
    via ball-weighted method-of-moments variance decomposition across match-level
    spells (preventing 1-ball duck denominator explosions).
    Returns: (grand_mean_rate, sigma_within_sq, tau_between_sq, k_matches)
    """
    counts = match_df.groupby(player_col).size()
    elig = counts[counts >= min_matches].index
    sub = match_df[match_df[player_col].isin(elig)].copy()
    if sub.empty:
        return 0.0, 1.0, 1.0, 10.0

    # Ball-weighted player rates (immune to 1-ball duck rate blow-ups)
    p_agg = (
        sub.groupby(player_col)
        .agg(
            n_m=(num_col, "size"),
            sum_num=(num_col, "sum"),
            sum_den=(den_col, "sum"),
            var_runs=(num_col, "var"),
            mean_den=(den_col, "mean"),
        )
        .dropna()
    )
    p_agg = p_agg[p_agg["sum_den"] > 0]
    p_agg["rate"] = p_agg["sum_num"] / p_agg["sum_den"] * scale_factor
    grand_mean = float(p_agg["sum_num"].sum() / p_agg["sum_den"].sum() * scale_factor)

    # Convert match-level run variance into rate-scale variance via delta method:
    # Var(rate_per_match) ~ Var(net_impact_runs) * (scale_factor / mean_balls_per_match)^2
    mean_b_per_match = float(p_agg["mean_den"].mean())
    sigma_within_runs_sq = float(np.average(p_agg["var_runs"], weights=np.maximum(p_agg["n_m"] - 1, 1)))
    sigma_within_sq = sigma_within_runs_sq * (scale_factor / max(mean_b_per_match, 1.0)) ** 2

    obs_between_var = float(p_agg["rate"].var(ddof=1))
    mean_inv_n = float((1.0 / p_agg["n_m"]).mean())
    tau_between_sq = max(obs_between_var - sigma_within_sq * mean_inv_n, sigma_within_sq / 30.0)
    k_matches = float(np.clip(sigma_within_sq / tau_between_sq, 4.0, 30.0))
    return grand_mean, sigma_within_sq, tau_between_sq, k_matches


def match_clustered_bootstrap(
    match_table: pd.DataFrame,
    num_col: str,
    den_col: str,
    scale_factor: float,
    rng: np.random.Generator,
    n_boot: int = BOOTSTRAP_B,
) -> tuple[float, float, float, float]:
    """
    Perform match-clustered ratio bootstrap resampling whole matches with replacement.
    Returns (point_est, ci_low_95, ci_high_95, boot_se).
    """
    nums = match_table[num_col].to_numpy(dtype=float)
    dens = match_table[den_col].to_numpy(dtype=float)
    n_m = len(nums)
    if n_m < 3 or dens.sum() <= 0:
        return np.nan, np.nan, np.nan, np.nan
    point = float(nums.sum() / dens.sum() * scale_factor)
    idx = rng.integers(0, n_m, size=(n_boot, n_m))
    b_num = nums[idx].sum(axis=1)
    b_den = dens[idx].sum(axis=1)
    valid = b_den > 0
    if valid.sum() < 20:
        return point, np.nan, np.nan, np.nan
    est = b_num[valid] / b_den[valid] * scale_factor
    ci_lo, ci_hi = np.percentile(est, [2.5, 97.5])
    se = float(np.std(est, ddof=1))
    return point, float(ci_lo), float(ci_hi), se


def build_batting_match_spells(df: pd.DataFrame) -> pd.DataFrame:
    """Build match-level batting spells separately for pressure vs non-pressure."""
    valid = df[df["batting_pressure_index"].notna()].copy()
    valid["pressure_regime"] = np.where(
        valid["batting_pressure_level"].isin(HIGH_PRESSURE_CATS), "pressure", "non_pressure"
    )
    faced = valid[valid["is_batter_ball_faced"]].copy()
    faced["rvae"] = faced["batter_runs"] - faced["exp_bat_r"]

    spells = (
        faced.groupby(["striker_id", "match_id", "innings", "season_year", "eligibility_category", "pressure_regime"], as_index=False)
        .agg(
            runs=("batter_runs", "sum"),
            balls_faced=("is_batter_ball_faced", "sum"),
            rvae=("rvae", "sum"),
            exp_k=("exp_bat_k", "sum"),
            mean_pi=("batting_pressure_index", "mean"),
        )
        .rename(columns={"striker_id": "player_id"})
    )
    # Match-level dismissals via dismissed_player_id
    wkts = valid[valid["is_wicket_event"] & valid["dismissed_player_id_int"].notna()].copy()
    wkts["player_id"] = wkts["dismissed_player_id_int"].astype(int)
    w_agg = wkts.groupby(["player_id", "match_id", "innings", "pressure_regime"], as_index=False).agg(dismissals=("is_wicket_event", "sum"))
    spells = spells.merge(w_agg, on=["player_id", "match_id", "innings", "pressure_regime"], how="left")
    spells["dismissals"] = spells["dismissals"].fillna(0).astype(int)
    spells["net_impact_runs"] = spells["rvae"] + 12.0 * (spells["exp_k"] - spells["dismissals"])
    spells["net_impact_per_100b"] = spells["net_impact_runs"] / spells["balls_faced"] * 100.0
    spells["spell_z_impact"] = spells["net_impact_runs"] / np.sqrt(spells["balls_faced"])
    spells["sr"] = spells["runs"] / spells["balls_faced"] * 100.0
    return spells


def build_bowling_match_spells(df: pd.DataFrame) -> pd.DataFrame:
    """Build match-level bowling spells separately for pressure vs non-pressure."""
    valid = df[df["bowling_pressure_index"].notna()].copy()
    valid["pressure_regime"] = np.where(
        valid["bowling_pressure_level"].isin(HIGH_PRESSURE_CATS), "pressure", "non_pressure"
    )
    valid["exp_rc_row"] = np.where(valid["is_legal_delivery"], valid["exp_bowl_rc"], 0.0)
    valid["exp_bw_row"] = np.where(valid["is_legal_delivery"], valid["exp_bowl_bw"], 0.0)

    spells = (
        valid.groupby(["bowler_id", "match_id", "innings", "season_year", "eligibility_category", "pressure_regime"], as_index=False)
        .agg(
            runs_conceded=("bowler_conceded_runs", "sum"),
            legal_balls=("is_legal_delivery", "sum"),
            bowler_wickets=("is_bowler_wicket", "sum"),
            exp_rc=("exp_rc_row", "sum"),
            exp_bw=("exp_bw_row", "sum"),
            mean_pi=("bowling_pressure_index", "mean"),
        )
        .rename(columns={"bowler_id": "player_id"})
    )
    spells = spells[spells["legal_balls"] > 0].copy()
    spells["rsae"] = spells["exp_rc"] - spells["runs_conceded"]
    spells["net_impact_runs"] = spells["rsae"] + 12.0 * (spells["bowler_wickets"] - spells["exp_bw"])
    spells["net_impact_per_24b"] = spells["net_impact_runs"] * 24.0 / spells["legal_balls"]
    spells["spell_z_impact"] = spells["net_impact_runs"] / np.sqrt(spells["legal_balls"])
    spells["econ"] = spells["runs_conceded"] * 6.0 / spells["legal_balls"]
    return spells


def compute_discipline_reliability(
    discipline: str,
    perf_df: pd.DataFrame,
    spells_all: pd.DataFrame,
    breakdown_df: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Compute strictly separated Performance (EB-shrunk), Reliability (consistency 0-100),
    Evidence Strength (0-100 + tiers), and Match-Clustered Bootstrap CIs for one discipline.
    """
    is_bat = discipline == "batting"
    balls_col = "pressure_balls_faced" if is_bat else "pressure_legal_balls"
    non_balls_col = "nonpressure_balls_faced" if is_bat else "nonpressure_legal_balls"
    spell_den_col = "balls_faced" if is_bat else "legal_balls"
    spell_impact_col = "net_impact_per_100b" if is_bat else "net_impact_per_24b"
    scale_fac = 100.0 if is_bat else 24.0
    raw_rate_num = "runs" if is_bat else "runs_conceded"
    raw_rate_scale = 100.0 if is_bat else 6.0

    # Threshold definitions (grounded in empirical quantiles from pre-execution audit)
    prim_balls, prim_inn = (80, 10) if is_bat else (90, 10)
    hi_balls, hi_inn = (150, 18) if is_bat else (180, 18)
    low_balls, low_inn = (30, 5) if is_bat else (36, 5)

    p_spells = spells_all[spells_all["pressure_regime"] == "pressure"].copy()
    np_spells = spells_all[spells_all["pressure_regime"] == "non_pressure"].copy()

    # Empirical Bayes variance decomposition across match-level pressure spells (ball-weighted, delta-method variance)
    grand_mu, sig_w_sq, tau_b_sq, k_eb = estimate_empirical_bayes_k(
        p_spells, "player_id", "net_impact_runs", spell_den_col, scale_fac, min_matches=prim_inn
    )

    # Cohort 90th-percentile variance-stabilized spell dispersion (net_impact_runs / sqrt(balls))
    # so reliability is invariant to spell length (neither blowing up on 1-ball ducks nor
    # penalizing workhorse players who face/bowl more pressure balls per match)
    elig_p_ids = set(
        perf_df.loc[
            (perf_df[balls_col] >= prim_balls) & (perf_df["pressure_innings"] >= prim_inn),
            "player_id",
        ]
    )
    elig_iqrs = (
        p_spells[p_spells["player_id"].isin(elig_p_ids)]
        .groupby("player_id")["spell_z_impact"]
        .agg(lambda s: float(np.percentile(s, 75) - np.percentile(s, 25)))
    )
    cohort_p90_iqr = float(elig_iqrs.quantile(0.90)) if len(elig_iqrs) else (5.0 if is_bat else 4.5)
    # Neutral floor in variance-stabilized spell impact (avoids penalizing minor misses)
    floor_thresh = -0.60
    cross_cond_scale = 50.0 if is_bat else 10.0
    season_std_scale = 35.0 if is_bat else 8.0

    # Pre-index breakdown for HIGH vs EXTREME cross-condition stability
    bk_hi = breakdown_df[breakdown_df["pressure_level"] == "HIGH PRESSURE"].set_index("player_id")
    bk_ext = breakdown_df[breakdown_df["pressure_level"] == "EXTREME PRESSURE"].set_index("player_id")
    bk_val_col = "net_impact_per_100b" if is_bat else "net_impact_per_24b"
    bk_cnt_col = "balls_faced" if is_bat else "legal_balls"

    rel_rows: list[dict[str, Any]] = []
    boot_rows: list[dict[str, Any]] = []
    pvn_rows: list[dict[str, Any]] = []

    p_groups = {pid: grp for pid, grp in p_spells.groupby("player_id")}
    np_groups = {pid: grp for pid, grp in np_spells.groupby("player_id")}

    for r in perf_df.itertuples():
        pid = int(r.player_id)
        p_balls = int(getattr(r, balls_col))
        np_balls = int(getattr(r, non_balls_col))
        p_inn = int(r.pressure_innings)
        p_mat = int(r.pressure_matches)
        p_seas = int(r.pressure_seasons)

        # Evidence tier
        if p_balls >= hi_balls and p_inn >= hi_inn and p_mat >= hi_inn and p_seas >= 2:
            tier = "HIGH_CONFIDENCE"
        elif p_balls >= prim_balls and p_inn >= prim_inn and p_mat >= prim_inn:
            tier = "MODERATE_CONFIDENCE"
        elif p_balls >= low_balls and p_inn >= low_inn and p_mat >= low_inn:
            tier = "LOW_EVIDENCE"
        else:
            tier = "INSUFFICIENT_EVIDENCE"

        sufficient_for_rel = tier in {"HIGH_CONFIDENCE", "MODERATE_CONFIDENCE", "LOW_EVIDENCE"}
        primary_eligible = tier in {"HIGH_CONFIDENCE", "MODERATE_CONFIDENCE"}

        ps = p_groups.get(pid, pd.DataFrame())
        nps = np_groups.get(pid, pd.DataFrame())

        # Pillar 1: Raw & Empirical-Bayes Shrunk Context-Adjusted Impact (Performance)
        if len(ps) > 0 and ps[spell_den_col].sum() > 0:
            raw_impact = float(ps["net_impact_runs"].sum() / ps[spell_den_col].sum() * scale_fac)
            shrink_wt = p_mat / (p_mat + k_eb)
            eb_impact = float(shrink_wt * raw_impact + (1.0 - shrink_wt) * grand_mu)
        else:
            raw_impact = np.nan
            shrink_wt = 0.0
            eb_impact = np.nan

        # Match-clustered bootstrap CIs (only when >= 5 pressure matches)
        if sufficient_for_rel and len(ps) >= 5:
            _, imp_lo, imp_hi, imp_se = match_clustered_bootstrap(
                ps, "net_impact_runs", spell_den_col, scale_fac, rng
            )
            _, rate_lo, rate_hi, rate_se = match_clustered_bootstrap(
                ps, raw_rate_num, spell_den_col, raw_rate_scale, rng
            )
            ci_width = imp_hi - imp_lo if (pd.notna(imp_hi) and pd.notna(imp_lo)) else np.nan
        else:
            imp_lo = imp_hi = imp_se = rate_lo = rate_hi = rate_se = ci_width = np.nan

        # Pillar 2: Reliability / Consistency (0-100, strictly stability, NOT raw delivery volume!)
        if sufficient_for_rel and len(ps) >= 5:
            vals = ps["spell_z_impact"].to_numpy(dtype=float)
            iqr_val = float(np.percentile(vals, 75) - np.percentile(vals, 25))
            sd_val = float(np.std(vals, ddof=1))
            comp_stab = float(np.clip(1.0 - iqr_val / max(cohort_p90_iqr, 1e-6), 0.0, 1.0))
            comp_floor = float((vals >= floor_thresh).mean())

            # Cross-condition stability: HIGH vs EXTREME and Inn1 vs Inn2 where exposed
            cond_scores = []
            if pid in bk_hi.index and pid in bk_ext.index:
                if bk_hi.loc[pid, bk_cnt_col] >= 15 and bk_ext.loc[pid, bk_cnt_col] >= 15:
                    diff_he = abs(float(bk_hi.loc[pid, bk_val_col]) - float(bk_ext.loc[pid, bk_val_col]))
                    cond_scores.append(float(np.clip(1.0 - diff_he / cross_cond_scale, 0.0, 1.0)))
            i1_s = ps[ps["innings"] == 1]
            i2_s = ps[ps["innings"] == 2]
            if len(i1_s) >= 3 and len(i2_s) >= 3:
                v1 = float(i1_s["net_impact_runs"].sum() / i1_s[spell_den_col].sum() * scale_fac)
                v2 = float(i2_s["net_impact_runs"].sum() / i2_s[spell_den_col].sum() * scale_fac)
                cond_scores.append(float(np.clip(1.0 - abs(v1 - v2) / cross_cond_scale, 0.0, 1.0)))
            comp_cross = float(np.mean(cond_scores)) if cond_scores else 0.50

            # Cross-season stability (seasons with >= 3 pressure innings)
            s_agg = ps.groupby("season_year").agg(
                n=("match_id", "size"),
                nr=("net_impact_runs", "sum"),
                dn=(spell_den_col, "sum"),
            )
            s_qual = s_agg[s_agg["n"] >= 3]
            if len(s_qual) >= 2:
                s_rates = s_qual["nr"] / s_qual["dn"] * scale_fac
                seas_sd = float(s_rates.std(ddof=1))
                comp_seas = float(np.clip(1.0 - seas_sd / season_std_scale, 0.0, 1.0))
            else:
                seas_sd = np.nan
                comp_seas = 0.50

            reliability_score = round(
                100.0 * (0.40 * comp_stab + 0.30 * comp_floor + 0.20 * comp_cross + 0.10 * comp_seas),
                2,
            )
        else:
            iqr_val = sd_val = seas_sd = np.nan
            comp_stab = comp_floor = comp_cross = comp_seas = reliability_score = np.nan

        # Pillar 3: Evidence Strength Score (0-100, strictly confidence/sample sufficiency)
        ev_balls = float(np.clip(p_balls / (hi_balls * 1.5), 0.0, 1.0))
        ev_mat = float(np.clip(p_mat / (hi_inn * 1.5), 0.0, 1.0))
        ev_seas = float(np.clip(p_seas / 4.0, 0.0, 1.0))
        if pd.notna(ci_width):
            ci_ref = 90.0 if is_bat else 22.0
            ev_prec = float(np.clip(1.0 - ci_width / ci_ref, 0.0, 1.0))
        else:
            ev_prec = 0.0
        evidence_strength_score = round(
            100.0 * (0.30 * ev_balls + 0.30 * ev_mat + 0.20 * ev_seas + 0.20 * ev_prec), 2
        )

        rel_rows.append({
            "player_id": pid,
            "player_name": r.player_name,
            "role": r.batting_role if is_bat else r.bowling_role,
            "evidence_tier": tier,
            "is_primary_eligible": primary_eligible,
            "pressure_balls": p_balls,
            "pressure_innings": p_inn,
            "pressure_matches": p_mat,
            "pressure_seasons": p_seas,
            "raw_pressure_impact": round(raw_impact, 3) if pd.notna(raw_impact) else np.nan,
            "eb_shrinkage_weight": round(shrink_wt, 4),
            "eb_k_matches_prior": round(k_eb, 3),
            "eb_pressure_impact": round(eb_impact, 3) if pd.notna(eb_impact) else np.nan,
            "innings_impact_iqr": round(iqr_val, 3) if pd.notna(iqr_val) else np.nan,
            "innings_impact_sd": round(sd_val, 3) if pd.notna(sd_val) else np.nan,
            "seasonal_impact_sd": round(seas_sd, 3) if pd.notna(seas_sd) else np.nan,
            "comp_innings_stability": round(comp_stab, 4) if pd.notna(comp_stab) else np.nan,
            "comp_floor_consistency": round(comp_floor, 4) if pd.notna(comp_floor) else np.nan,
            "comp_cross_condition_stability": round(comp_cross, 4) if pd.notna(comp_cross) else np.nan,
            "comp_seasonal_stability": round(comp_seas, 4) if pd.notna(comp_seas) else np.nan,
            "reliability_score": reliability_score,
            "evidence_strength_score": evidence_strength_score,
            "impact_ci95_low": round(imp_lo, 3) if pd.notna(imp_lo) else np.nan,
            "impact_ci95_high": round(imp_hi, 3) if pd.notna(imp_hi) else np.nan,
            "impact_ci95_width": round(ci_width, 3) if pd.notna(ci_width) else np.nan,
            "impact_boot_se": round(imp_se, 3) if pd.notna(imp_se) else np.nan,
            "raw_rate_ci95_low": round(rate_lo, 3) if pd.notna(rate_lo) else np.nan,
            "raw_rate_ci95_high": round(rate_hi, 3) if pd.notna(rate_hi) else np.nan,
        })

        if sufficient_for_rel:
            boot_rows.append({
                "discipline": discipline,
                "player_id": pid,
                "player_name": r.player_name,
                "evidence_tier": tier,
                "pressure_matches": p_mat,
                "pressure_balls": p_balls,
                "metric_name": spell_impact_col,
                "point_estimate": round(raw_impact, 3) if pd.notna(raw_impact) else np.nan,
                "eb_shrunk_estimate": round(eb_impact, 3) if pd.notna(eb_impact) else np.nan,
                "ci95_low": round(imp_lo, 3) if pd.notna(imp_lo) else np.nan,
                "ci95_high": round(imp_hi, 3) if pd.notna(imp_hi) else np.nan,
                "ci95_width": round(ci_width, 3) if pd.notna(ci_width) else np.nan,
                "bootstrap_se": round(imp_se, 3) if pd.notna(imp_se) else np.nan,
                "raw_rate_metric": "pressure_strike_rate" if is_bat else "pressure_economy",
                "raw_rate_point": getattr(r, "pressure_strike_rate" if is_bat else "pressure_economy"),
                "raw_rate_ci95_low": round(rate_lo, 3) if pd.notna(rate_lo) else np.nan,
                "raw_rate_ci95_high": round(rate_hi, 3) if pd.notna(rate_hi) else np.nan,
            })

        # Pressure vs. Non-Pressure observational comparison with match-clustered bootstrap diff CI
        both_elig = (p_balls >= low_balls and p_mat >= low_inn and np_balls >= low_balls and len(nps) >= low_inn)
        both_primary = (p_balls >= prim_balls and p_mat >= prim_inn and np_balls >= prim_balls and len(nps) >= prim_inn)
        if both_elig:
            # Independent match-clustered bootstrap difference (pressure - non_pressure)
            p_num, p_den = ps["net_impact_runs"].to_numpy(float), ps[spell_den_col].to_numpy(float)
            np_num, np_den = nps["net_impact_runs"].to_numpy(float), nps[spell_den_col].to_numpy(float)
            ip = rng.integers(0, len(p_num), size=(BOOTSTRAP_B, len(p_num)))
            inp = rng.integers(0, len(np_num), size=(BOOTSTRAP_B, len(np_num)))
            d_est = (p_num[ip].sum(axis=1) / p_den[ip].sum(axis=1) - np_num[inp].sum(axis=1) / np_den[inp].sum(axis=1)) * scale_fac
            diff_pt = float((p_num.sum() / p_den.sum() - np_num.sum() / np_den.sum()) * scale_fac)
            diff_lo, diff_hi = np.percentile(d_est, [2.5, 97.5])
            ci_excludes_zero = bool((diff_lo > 0) or (diff_hi < 0))

            p_raw_rate = getattr(r, "pressure_strike_rate" if is_bat else "pressure_economy")
            np_raw_rate = getattr(r, "nonpressure_strike_rate" if is_bat else "nonpressure_economy")
            raw_diff = p_raw_rate - np_raw_rate if (pd.notna(p_raw_rate) and pd.notna(np_raw_rate)) else np.nan
            rel_pct = (raw_diff / np_raw_rate * 100.0) if (pd.notna(raw_diff) and np_raw_rate not in (0, np.nan)) else np.nan

            pvn_rows.append({
                "discipline": discipline,
                "player_id": pid,
                "player_name": r.player_name,
                "role": r.batting_role if is_bat else r.bowling_role,
                "evidence_tier": tier,
                "sufficient_both_sides_primary": both_primary,
                "pressure_balls": p_balls,
                "pressure_matches": p_mat,
                "nonpressure_balls": np_balls,
                "nonpressure_matches": int(len(nps)),
                "primary_rate_name": "strike_rate" if is_bat else "economy_rate",
                "pressure_rate": p_raw_rate,
                "nonpressure_rate": np_raw_rate,
                "raw_rate_diff": round(raw_diff, 3) if pd.notna(raw_diff) else np.nan,
                "raw_rate_rel_change_pct": round(rel_pct, 2) if pd.notna(rel_pct) else np.nan,
                "pressure_net_impact": round(raw_impact, 3),
                "nonpressure_net_impact": round(float(np_num.sum() / np_den.sum() * scale_fac), 3),
                "context_impact_diff_p_minus_np": round(diff_pt, 3),
                "context_impact_diff_ci95_low": round(float(diff_lo), 3),
                "context_impact_diff_ci95_high": round(float(diff_hi), 3),
                "ci95_excludes_zero": ci_excludes_zero,
                "evidence_interpretation": (
                    "Observational difference CI excludes 0 (sufficient primary sample)"
                    if (both_primary and ci_excludes_zero)
                    else ("Observational difference within sampling uncertainty" if both_primary else "Low-evidence observational difference")
                ),
            })

    rel_df = pd.DataFrame(rel_rows)
    # Calibrate 0-100 Performance Effectiveness Score strictly from eb_pressure_impact
    # using smooth logistic scaling anchored on primary-eligible cohort median & IQR (SEPARATE from reliability!)
    elig_eb = rel_df.loc[rel_df["is_primary_eligible"], "eb_pressure_impact"].dropna()
    eb_med = float(elig_eb.median()) if len(elig_eb) else 0.0
    eb_scale = max(float((elig_eb.quantile(0.75) - elig_eb.quantile(0.25)) * 0.7413), 5.0 if is_bat else 1.5)
    z_perf = (rel_df["eb_pressure_impact"] - eb_med) / (eb_scale * 1.45)
    rel_df["performance_score"] = np.where(
        rel_df["eb_pressure_impact"].notna(),
        np.round(100.0 / (1.0 + np.exp(-np.clip(z_perf, -20.0, 20.0))), 2),
        np.nan,
    )
    rel_df = rel_df.sort_values("player_id").reset_index(drop=True)
    return rel_df, boot_rows, pvn_rows


def build_exposure_and_season_tables(
    df: pd.DataFrame,
    bat_perf: pd.DataFrame,
    bowl_perf: pd.DataFrame,
    bat_rel: pd.DataFrame,
    bowl_rel: pd.DataFrame,
    bat_bk: pd.DataFrame,
    bowl_bk: pd.DataFrame,
    bat_spells: pd.DataFrame,
    bowl_spells: pd.DataFrame,
) -> None:
    """Write player_pressure_exposure.csv, player_season_performance.csv, and exposure/sensitivity summaries."""
    # 1. Unified player_pressure_exposure.csv
    exp_parts = []
    for disc, perf, rel, bk, cnt_col in [
        ("batting", bat_perf, bat_rel, bat_bk, "balls_faced"),
        ("bowling", bowl_perf, bowl_rel, bowl_bk, "legal_balls"),
    ]:
        piv = bk.pivot_table(index="player_id", columns="pressure_level", values=cnt_col, aggfunc="sum", fill_value=0)
        for lvl in ["LOW PRESSURE", "MODERATE PRESSURE", "HIGH PRESSURE", "EXTREME PRESSURE"]:
            if lvl not in piv.columns:
                piv[lvl] = 0
        piv = piv.rename(columns={
            "LOW PRESSURE": "low_pressure_balls",
            "MODERATE PRESSURE": "moderate_pressure_balls",
            "HIGH PRESSURE": "high_pressure_balls",
            "EXTREME PRESSURE": "extreme_pressure_balls",
        }).reset_index()

        part = rel[[
            "player_id", "player_name", "role", "evidence_tier", "is_primary_eligible",
            "pressure_balls", "pressure_innings", "pressure_matches", "pressure_seasons", "evidence_strength_score",
        ]].merge(piv, on="player_id", how="left")
        part.insert(0, "discipline", disc)
        for c in ["low_pressure_balls", "moderate_pressure_balls", "high_pressure_balls", "extreme_pressure_balls"]:
            part[c] = part[c].fillna(0).astype(int)
        part["total_valid_balls"] = (
            part["low_pressure_balls"] + part["moderate_pressure_balls"]
            + part["high_pressure_balls"] + part["extreme_pressure_balls"]
        )
        part["high_extreme_share_pct"] = np.where(
            part["total_valid_balls"] > 0,
            (part["pressure_balls"] / part["total_valid_balls"] * 100.0).round(2),
            0.0,
        )
        exp_parts.append(part)

    exposure_df = pd.concat(exp_parts, ignore_index=True)
    exposure_df.to_csv(PROCESSED_DIR / "player_pressure_exposure.csv", index=False)

    # 2. outputs/player_exposure_distribution.csv
    exp_dist = (
        exposure_df.groupby(["discipline", "evidence_tier"], as_index=False)
        .agg(
            player_count=("player_id", "nunique"),
            median_pressure_balls=("pressure_balls", "median"),
            mean_pressure_balls=("pressure_balls", "mean"),
            median_pressure_matches=("pressure_matches", "median"),
            mean_seasons=("pressure_seasons", "mean"),
            mean_evidence_score=("evidence_strength_score", "mean"),
        )
    )
    for c in ["mean_pressure_balls", "mean_seasons", "mean_evidence_score"]:
        exp_dist[c] = exp_dist[c].round(2)
    exp_dist.to_csv(OUT_DIR / "player_exposure_distribution.csv", index=False)

    # 3. outputs/reliability_distribution.csv
    rel_dist_rows = []
    for disc, rel in [("batting", bat_rel), ("bowling", bowl_rel)]:
        for scope, mask in [
            ("ALL_SCORED_GE5_INN", rel["reliability_score"].notna()),
            ("PRIMARY_ELIGIBLE", rel["is_primary_eligible"]),
            ("HIGH_CONFIDENCE", rel["evidence_tier"] == "HIGH_CONFIDENCE"),
        ]:
            sub = rel.loc[mask]
            if sub.empty:
                continue
            rel_dist_rows.append({
                "discipline": disc,
                "scope": scope,
                "player_count": int(len(sub)),
                "reliability_mean": round(float(sub["reliability_score"].mean()), 2),
                "reliability_sd": round(float(sub["reliability_score"].std()), 2),
                "reliability_p25": round(float(sub["reliability_score"].quantile(0.25)), 2),
                "reliability_p50": round(float(sub["reliability_score"].quantile(0.50)), 2),
                "reliability_p75": round(float(sub["reliability_score"].quantile(0.75)), 2),
                "performance_mean": round(float(sub["performance_score"].mean()), 2),
                "evidence_mean": round(float(sub["evidence_strength_score"].mean()), 2),
                "corr_reliability_vs_balls": round(float(sub["reliability_score"].corr(sub["pressure_balls"])), 4),
                "corr_reliability_vs_performance": round(float(sub["reliability_score"].corr(sub["performance_score"])), 4),
            })
    pd.DataFrame(rel_dist_rows).to_csv(OUT_DIR / "reliability_distribution.csv", index=False)

    # 4. outputs/minimum_exposure_sensitivity.csv
    sens_rows = []
    for disc, rel, specs in [
        ("batting", bat_rel, [(30, 5), (60, 8), (80, 10), (100, 12), (120, 15), (150, 18)]),
        ("bowling", bowl_rel, [(36, 5), (60, 8), (90, 10), (120, 12), (150, 15), (180, 18)]),
    ]:
        total_p = len(rel)
        for b_min, i_min in specs:
            sub = rel[(rel["pressure_balls"] >= b_min) & (rel["pressure_innings"] >= i_min) & (rel["pressure_matches"] >= i_min)]
            sens_rows.append({
                "discipline": disc,
                "min_pressure_balls": b_min,
                "min_pressure_innings_and_matches": i_min,
                "eligible_players": int(len(sub)),
                "pct_of_all_players": round(len(sub) / total_p * 100.0, 2),
                "median_ci95_width": round(float(sub["impact_ci95_width"].median()), 3) if len(sub) else np.nan,
                "mean_eb_shrinkage_weight": round(float(sub["eb_shrinkage_weight"].mean()), 4) if len(sub) else np.nan,
                "mean_reliability_score": round(float(sub["reliability_score"].mean()), 2) if len(sub) else np.nan,
                "is_selected_primary_threshold": (b_min == 80 and i_min == 10 and disc == "batting") or (b_min == 90 and i_min == 10 and disc == "bowling"),
            })
    pd.DataFrame(sens_rows).to_csv(OUT_DIR / "minimum_exposure_sensitivity.csv", index=False)

    # 5. data/processed/player_season_performance.csv (per player x discipline x season_year)
    bat_names = bat_perf.set_index("player_id")["player_name"]
    bowl_names = bowl_perf.set_index("player_id")["player_name"]

    bs_p = (
        bat_spells[bat_spells["pressure_regime"] == "pressure"]
        .groupby(["player_id", "season_year"], as_index=False)
        .agg(
            pressure_balls=("balls_faced", "sum"),
            pressure_runs_or_conceded=("runs", "sum"),
            pressure_dismissals_or_wickets=("dismissals", "sum"),
            pressure_matches=("match_id", "nunique"),
            pressure_innings=("innings", "size"),
            net_impact_runs=("net_impact_runs", "sum"),
        )
    )
    bs_p["discipline"] = "batting"
    bs_p["player_name"] = bs_p["player_id"].map(bat_names)
    bs_p["primary_rate"] = (bs_p["pressure_runs_or_conceded"] / bs_p["pressure_balls"] * 100.0).round(2)
    bs_p["net_impact_rate"] = (bs_p["net_impact_runs"] / bs_p["pressure_balls"] * 100.0).round(3)

    ls_p = (
        bowl_spells[bowl_spells["pressure_regime"] == "pressure"]
        .groupby(["player_id", "season_year"], as_index=False)
        .agg(
            pressure_balls=("legal_balls", "sum"),
            pressure_runs_or_conceded=("runs_conceded", "sum"),
            pressure_dismissals_or_wickets=("bowler_wickets", "sum"),
            pressure_matches=("match_id", "nunique"),
            pressure_innings=("innings", "size"),
            net_impact_runs=("net_impact_runs", "sum"),
        )
    )
    ls_p["discipline"] = "bowling"
    ls_p["player_name"] = ls_p["player_id"].map(bowl_names)
    ls_p["primary_rate"] = (ls_p["pressure_runs_or_conceded"] * 6.0 / ls_p["pressure_balls"]).round(2)
    ls_p["net_impact_rate"] = (ls_p["net_impact_runs"] * 24.0 / ls_p["pressure_balls"]).round(3)

    season_df = pd.concat([bs_p, ls_p], ignore_index=True)[
        [
            "discipline", "player_id", "player_name", "season_year",
            "pressure_balls", "pressure_innings", "pressure_matches",
            "pressure_runs_or_conceded", "pressure_dismissals_or_wickets",
            "primary_rate", "net_impact_rate",
        ]
    ].sort_values(["discipline", "player_id", "season_year"]).reset_index(drop=True)
    season_df.to_csv(PROCESSED_DIR / "player_season_performance.csv", index=False)


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    df_raw, bat_perf, bowl_perf = load_inputs()
    df = attach_lomo_expectations(df_raw)

    bat_bk = pd.read_csv(PROCESSED_DIR / "player_batting_pressure_breakdown.csv", low_memory=False)
    bowl_bk = pd.read_csv(PROCESSED_DIR / "player_bowling_pressure_breakdown.csv", low_memory=False)

    bat_spells = build_batting_match_spells(df)
    bowl_spells = build_bowling_match_spells(df)

    bat_rel, bat_boot, bat_pvn = compute_discipline_reliability("batting", bat_perf, bat_spells, bat_bk, rng)
    bowl_rel, bowl_boot, bowl_pvn = compute_discipline_reliability("bowling", bowl_perf, bowl_spells, bowl_bk, rng)

    bat_rel.to_csv(PROCESSED_DIR / "player_batting_reliability.csv", index=False)
    bowl_rel.to_csv(PROCESSED_DIR / "player_bowling_reliability.csv", index=False)

    boot_df = pd.DataFrame(bat_boot + bowl_boot).sort_values(["discipline", "player_id"]).reset_index(drop=True)
    boot_df.to_csv(OUT_DIR / "player_bootstrap_uncertainty.csv", index=False)

    pvn_df = pd.DataFrame(bat_pvn + bowl_pvn).sort_values(["discipline", "player_id"]).reset_index(drop=True)
    pvn_df.to_csv(PROCESSED_DIR / "player_pressure_vs_nonpressure.csv", index=False)

    # Summary table for pressure vs non-pressure observational shifts
    pvn_sum_rows = []
    for disc in ["batting", "bowling"]:
        sub = pvn_df[(pvn_df["discipline"] == disc) & pvn_df["sufficient_both_sides_primary"]]
        pvn_sum_rows.append({
            "discipline": disc,
            "primary_eligible_both_sides_players": int(len(sub)),
            "mean_pressure_rate": round(float(sub["pressure_rate"].mean()), 3),
            "mean_nonpressure_rate": round(float(sub["nonpressure_rate"].mean()), 3),
            "mean_raw_rate_diff": round(float(sub["raw_rate_diff"].mean()), 3),
            "median_raw_rate_diff": round(float(sub["raw_rate_diff"].median()), 3),
            "mean_context_impact_diff": round(float(sub["context_impact_diff_p_minus_np"].mean()), 3),
            "players_ci95_excludes_zero": int(sub["ci95_excludes_zero"].sum()),
            "pct_players_ci95_excludes_zero": round(sub["ci95_excludes_zero"].mean() * 100.0, 2) if len(sub) else 0.0,
            "note": "Observational comparison only (not causal); context_impact adjusts for IPL vs T20I x phase x pressure par",
        })
    pd.DataFrame(pvn_sum_rows).to_csv(OUT_DIR / "pressure_vs_nonpressure_summary.csv", index=False)

    build_exposure_and_season_tables(
        df, bat_perf, bowl_perf, bat_rel, bowl_rel, bat_bk, bowl_bk, bat_spells, bowl_spells
    )

    print("\n=== PHASE 5 RELIABILITY & UNCERTAINTY MODELING COMPLETE ===")
    for disc, rel in [("Batting", bat_rel), ("Bowling", bowl_rel)]:
        prim = rel[rel["is_primary_eligible"]]
        print(
            f"  {disc:8s}: total={len(rel):3d} | primary_eligible={len(prim):3d} | "
            f"high_conf={int((rel['evidence_tier'] == 'HIGH_CONFIDENCE').sum()):3d} | "
            f"EB_k={rel['eb_k_matches_prior'].iloc[0]:.2f} matches | "
            f"rel_mean={prim['reliability_score'].mean():.2f} | "
            f"corr(rel,balls)={prim['reliability_score'].corr(prim['pressure_balls']):+.3f}"
        )


if __name__ == "__main__":
    main()
