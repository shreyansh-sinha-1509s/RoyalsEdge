"""
SupeRR Selector Season 2 - Phase 5 Batting Performance Under Pressure.

Computes role-aware, format-adjusted, cricket-law-validated batting performance
metrics across Model C pressure categories (LOW, MODERATE, HIGH, EXTREME),
first innings vs. chases, match phases, and IPL vs. T20I environments.

Key guardrails:
  - Primary key is strictly player_id (never merged by player name).
  - Balls faced strictly exclude wides (is_batter_ball_faced == True).
  - Dismissals strictly use dismissed_player_id (capturing non-striker run-outs
    accurately without misassigning them to the striker).
  - UNAVAILABLE pressure rows are never silently grouped into LOW pressure.
  - No final Top 10 rankings are generated in this script.
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

PRESSURE_CATS = ["LOW PRESSURE", "MODERATE PRESSURE", "HIGH PRESSURE", "EXTREME PRESSURE"]
HIGH_PRESSURE_CATS = ["HIGH PRESSURE", "EXTREME PRESSURE"]
NON_PRESSURE_CATS = ["LOW PRESSURE", "MODERATE PRESSURE"]


def load_pressure_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load validated Phase 4 pressure_deliveries.csv and player_master.csv."""
    df = pd.read_csv(
        PROCESSED_DIR / "pressure_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    pm = pd.read_csv(
        PROCESSED_DIR / "player_master.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    for bcol in [
        "is_legal_delivery",
        "is_batter_ball_faced",
        "is_wicket_event",
        "is_bowler_wicket",
        "is_four",
        "is_six",
        "is_retired_hurt",
        "is_super_over",
        "is_primary_eligible",
    ]:
        df[bcol] = df[bcol].astype(str).str.lower().eq("true")

    df["season_year"] = df["season"].astype(str).str.extract(r"(\d{4})")[0].astype(int)
    df["innings_key"] = df["match_id"].astype(str) + "_" + df["innings"].astype(str)
    df["dismissed_player_id_int"] = pd.to_numeric(df["dismissed_player_id"], errors="coerce")
    return df, pm


def compute_context_batting_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute empirical expected batter runs per ball faced and dismissal probability per
    ball faced by (eligibility_category, innings, match_phase, batting_pressure_level)
    using leave-one-match-out (LOMO) averages so IPL and T20I scoring environments are
    explicitly separated and a match never leaks into its own benchmark.
    """
    valid = df[df["batting_pressure_index"].notna() & df["is_batter_ball_faced"]].copy()
    grp_cols = ["eligibility_category", "innings", "match_phase", "batting_pressure_level"]

    m_agg = (
        valid.groupby(grp_cols + ["match_id"], as_index=False)
        .agg(
            m_runs=("batter_runs", "sum"),
            m_bf=("is_batter_ball_faced", "sum"),
            m_wkts=("is_wicket_event", "sum"),
        )
    )
    tot_agg = (
        m_agg.groupby(grp_cols, as_index=False)
        .agg(t_runs=("m_runs", "sum"), t_bf=("m_bf", "sum"), t_wkts=("m_wkts", "sum"))
    )
    m_agg = m_agg.merge(tot_agg, on=grp_cols, how="left")
    denom = np.maximum(m_agg["t_bf"] - m_agg["m_bf"], 1)
    m_agg["exp_bat_runs_per_ball"] = (m_agg["t_runs"] - m_agg["m_runs"]) / denom
    m_agg["exp_bat_wkt_per_ball"] = (m_agg["t_wkts"] - m_agg["m_wkts"]) / denom

    out = df.merge(
        m_agg[grp_cols + ["match_id", "exp_bat_runs_per_ball", "exp_bat_wkt_per_ball"]],
        on=grp_cols + ["match_id"],
        how="left",
    )
    return out


def assign_batting_roles(df: pd.DataFrame, pm: pd.DataFrame) -> pd.DataFrame:
    """Data-driven batting role classification with UNKNOWN / INSUFFICIENT EVIDENCE fallback."""
    faced = df[df["is_batter_ball_faced"]].copy()
    inn_pos = (
        faced.groupby(["striker_id", "innings_key"], as_index=False)
        .agg(
            pos=("batter_position", "min"),
            inn_bf=("is_batter_ball_faced", "sum"),
        )
    )
    pos_stats = (
        inn_pos.groupby("striker_id", as_index=False)
        .agg(
            total_innings_batted=("innings_key", "nunique"),
            median_batting_position=("pos", "median"),
            mean_batting_position=("pos", "mean"),
            opener_innings_share=("pos", lambda s: float((s <= 2).mean())),
        )
    )
    phase_bf = (
        faced[faced["match_phase"] != "Unavailable"]
        .pivot_table(index="striker_id", columns="match_phase", values="is_batter_ball_faced", aggfunc="sum", fill_value=0)
    )
    for ph in ["Powerplay", "Middle", "Death"]:
        if ph not in phase_bf.columns:
            phase_bf[ph] = 0
    phase_tot = phase_bf[["Powerplay", "Middle", "Death"]].sum(axis=1).replace(0, np.nan)
    phase_shares = pd.DataFrame({
        "striker_id": phase_bf.index,
        "pp_bf_share": (phase_bf["Powerplay"] / phase_tot).fillna(0.0).values,
        "middle_bf_share": (phase_bf["Middle"] / phase_tot).fillna(0.0).values,
        "death_bf_share": (phase_bf["Death"] / phase_tot).fillna(0.0).values,
    })

    tot_bf = faced.groupby("striker_id", as_index=False).agg(total_primary_bf=("is_batter_ball_faced", "sum"))
    tot_lb = df[df["is_legal_delivery"]].groupby("bowler_id", as_index=False).agg(total_primary_lb=("is_legal_delivery", "sum"))

    roles = (
        tot_bf.merge(pos_stats, on="striker_id", how="left")
        .merge(phase_shares, on="striker_id", how="left")
        .merge(tot_lb.rename(columns={"bowler_id": "striker_id"}), on="striker_id", how="left")
        .merge(pm[["player_id", "standardized_display_name", "ever_wk", "batting_type"]], left_on="striker_id", right_on="player_id", how="left")
    )
    roles["total_primary_lb"] = roles["total_primary_lb"].fillna(0).astype(int)
    roles["ever_wk"] = roles["ever_wk"].astype(str).str.lower().eq("true")

    def classify_role(r: pd.Series) -> str:
        if r["total_primary_bf"] < 30 or r["total_innings_batted"] < 5 or pd.isna(r["median_batting_position"]):
            return "UNKNOWN / INSUFFICIENT EVIDENCE"
        pos = float(r["median_batting_position"])
        if pos <= 2.5 or r["opener_innings_share"] >= 0.50:
            return "Opener"
        if pos <= 3.5:
            return "Top-Order"
        if pos <= 5.5:
            return "Middle-Order"
        if pos <= 7.5:
            return "Finisher / Lower-Middle"
        return "Lower-Order / Tail"

    roles["batting_role"] = roles.apply(classify_role, axis=1)
    roles["is_dual_discipline_allrounder"] = (roles["total_primary_bf"] >= 60) & (roles["total_primary_lb"] >= 60)
    return roles


def aggregate_batting_slice(
    df_slice: pd.DataFrame,
    group_cols: list[str],
    team_inn_totals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate cricket-law-accurate batting stats for any grouping slice.
    Crucially counts dismissals via dismissed_player_id (not striker_id) so
    non-striker run-outs are attributed to the actual dismissed batter.
    """
    faced = df_slice[df_slice["is_batter_ball_faced"]].copy()
    if faced.empty:
        return pd.DataFrame()

    faced["is_boundary_ball"] = faced["is_four"] | faced["is_six"]
    faced["is_dot_ball"] = faced["batter_runs"] == 0
    faced["rvae"] = faced["batter_runs"] - faced["exp_bat_runs_per_ball"]

    # Base aggregation by striker_id (+ extra group cols)
    gcols_s = ["striker_id"] + group_cols
    agg = (
        faced.groupby(gcols_s, as_index=False)
        .agg(
            runs=("batter_runs", "sum"),
            balls_faced=("is_batter_ball_faced", "sum"),
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
            boundary_balls=("is_boundary_ball", "sum"),
            dot_balls=("is_dot_ball", "sum"),
            innings_count=("innings_key", "nunique"),
            matches_count=("match_id", "nunique"),
            seasons_count=("season_year", "nunique"),
            exp_runs=("exp_bat_runs_per_ball", "sum"),
            exp_dismissals=("exp_bat_wkt_per_ball", "sum"),
            mean_pressure_index=("batting_pressure_index", "mean"),
        )
        .rename(columns={"striker_id": "player_id"})
    )

    # Dismissals attributed strictly via dismissed_player_id within the SAME slice
    wkts = df_slice[df_slice["is_wicket_event"] & df_slice["dismissed_player_id_int"].notna()].copy()
    wkts["player_id"] = wkts["dismissed_player_id_int"].astype(int)
    d_cols = ["player_id"] + group_cols
    dism_agg = (
        wkts.groupby(d_cols, as_index=False)
        .agg(
            dismissals=("is_wicket_event", "sum"),
            bowler_credited_dismissals=("is_bowler_wicket", "sum"),
            run_out_dismissals=("is_run_out", lambda s: int(s.astype(str).str.lower().eq("true").sum())),
        )
    )
    agg = agg.merge(dism_agg, on=d_cols, how="left")
    for c in ["dismissals", "bowler_credited_dismissals", "run_out_dismissals"]:
        agg[c] = agg[c].fillna(0).astype(int)

    # Innings-level consistency & team contribution within slice
    inn_gcols = ["striker_id"] + group_cols + ["match_id", "innings", "innings_key"]
    inn_df = (
        faced.groupby(inn_gcols, as_index=False)
        .agg(
            inn_runs=("batter_runs", "sum"),
            inn_bf=("is_batter_ball_faced", "sum"),
            inn_rvae=("rvae", "sum"),
        )
        .rename(columns={"striker_id": "player_id"})
        .merge(team_inn_totals, on=["match_id", "innings"], how="left")
    )
    inn_df["inn_contrib_pct"] = np.where(
        inn_df["team_innings_runs"] > 0,
        inn_df["inn_runs"] / inn_df["team_innings_runs"] * 100.0,
        np.nan,
    )
    inn_df["inn_sr"] = np.where(inn_df["inn_bf"] > 0, inn_df["inn_runs"] / inn_df["inn_bf"] * 100.0, np.nan)

    cons_agg = (
        inn_df.groupby(d_cols, as_index=False)
        .agg(
            mean_runs_per_innings=("inn_runs", "mean"),
            std_runs_per_innings=("inn_runs", "std"),
            iqr_runs_per_innings=("inn_runs", lambda s: float(np.percentile(s, 75) - np.percentile(s, 25)) if len(s) >= 2 else np.nan),
            mean_pressure_contribution_pct=("inn_contrib_pct", "mean"),
            std_innings_rvae=("inn_rvae", "std"),
        )
    )
    agg = agg.merge(cons_agg, on=d_cols, how="left")

    # Derived cricket rates (NaN when denominator is 0; never fabricated)
    agg["strike_rate"] = np.where(agg["balls_faced"] > 0, agg["runs"] / agg["balls_faced"] * 100.0, np.nan)
    agg["batting_average"] = np.where(agg["dismissals"] > 0, agg["runs"] / agg["dismissals"], np.nan)
    agg["runs_per_dismissal"] = agg["batting_average"]
    agg["boundary_pct"] = np.where(agg["balls_faced"] > 0, agg["boundary_balls"] / agg["balls_faced"] * 100.0, np.nan)
    agg["dot_ball_pct"] = np.where(agg["balls_faced"] > 0, agg["dot_balls"] / agg["balls_faced"] * 100.0, np.nan)
    agg["dismissal_rate_pct"] = np.where(agg["balls_faced"] > 0, agg["dismissals"] / agg["balls_faced"] * 100.0, np.nan)
    agg["rvae_total"] = agg["runs"] - agg["exp_runs"]
    agg["rvae_per_100b"] = np.where(agg["balls_faced"] > 0, agg["rvae_total"] / agg["balls_faced"] * 100.0, np.nan)
    agg["survival_above_exp"] = agg["exp_dismissals"] - agg["dismissals"]
    # Net context-adjusted impact per 100 balls: RVAE + survival value (12 runs per saved wicket)
    agg["net_impact_per_100b"] = np.where(
        agg["balls_faced"] > 0,
        (agg["rvae_total"] + 12.0 * agg["survival_above_exp"]) / agg["balls_faced"] * 100.0,
        np.nan,
    )

    round_cols = [
        "strike_rate", "batting_average", "runs_per_dismissal", "boundary_pct",
        "dot_ball_pct", "dismissal_rate_pct", "mean_runs_per_innings", "std_runs_per_innings",
        "iqr_runs_per_innings", "mean_pressure_contribution_pct", "std_innings_rvae",
        "exp_runs", "exp_dismissals", "rvae_total", "rvae_per_100b", "survival_above_exp",
        "net_impact_per_100b", "mean_pressure_index",
    ]
    for c in round_cols:
        if c in agg.columns:
            agg[c] = agg[c].round(3)

    return agg


def main() -> None:
    df_raw, pm = load_pressure_data()
    df = compute_context_batting_baselines(df_raw)

    # Team innings total runs (for pressure contribution %)
    team_inn_totals = (
        df.groupby(["match_id", "innings"], as_index=False)
        .agg(team_innings_runs=("total_runs", "sum"))
    )

    # Strictly separate valid Model C pressure deliveries from UNAVAILABLE
    valid_df = df[df["batting_pressure_index"].notna()].copy()
    hi_df = valid_df[valid_df["batting_pressure_level"].isin(HIGH_PRESSURE_CATS)].copy()
    non_df = valid_df[valid_df["batting_pressure_level"].isin(NON_PRESSURE_CATS)].copy()

    roles = assign_batting_roles(df, pm)

    # 1. Overall valid, High+Extreme Pressure, and Non-Pressure summaries per player
    all_agg = aggregate_batting_slice(valid_df, [], team_inn_totals)
    hi_agg = aggregate_batting_slice(hi_df, [], team_inn_totals)
    non_agg = aggregate_batting_slice(non_df, [], team_inn_totals)

    # Format splits under pressure (IPL vs T20I)
    hi_ipl = aggregate_batting_slice(hi_df[hi_df["eligibility_category"] == "IPL"], [], team_inn_totals)
    hi_t20i = aggregate_batting_slice(hi_df[hi_df["eligibility_category"] == "T20I"], [], team_inn_totals)

    # Innings splits under pressure (Inn 1 vs Inn 2 Chase)
    hi_inn1 = aggregate_batting_slice(hi_df[hi_df["innings"] == 1], [], team_inn_totals)
    hi_inn2 = aggregate_batting_slice(hi_df[hi_df["innings"] == 2], [], team_inn_totals)

    # Phase splits under pressure (Powerplay, Middle, Death)
    hi_phase = aggregate_batting_slice(hi_df[hi_df["match_phase"] != "Unavailable"], ["match_phase"], team_inn_totals)

    # Assemble master player_batting_performance.csv (one row per batter with >= 1 valid ball faced)
    base = roles[[
        "striker_id", "standardized_display_name", "batting_type", "ever_wk",
        "batting_role", "is_dual_discipline_allrounder", "median_batting_position",
        "opener_innings_share", "pp_bf_share", "middle_bf_share", "death_bf_share",
    ]].rename(columns={"striker_id": "player_id", "standardized_display_name": "player_name"})

    # Merge overall valid metrics
    overall_cols = {
        "runs": "overall_runs",
        "balls_faced": "overall_balls_faced",
        "dismissals": "overall_dismissals",
        "innings_count": "overall_innings",
        "matches_count": "overall_matches",
        "seasons_count": "overall_seasons",
        "strike_rate": "overall_strike_rate",
        "batting_average": "overall_average",
        "boundary_pct": "overall_boundary_pct",
        "dot_ball_pct": "overall_dot_ball_pct",
        "rvae_per_100b": "overall_rvae_per_100b",
    }
    base = base.merge(all_agg[["player_id"] + list(overall_cols.keys())].rename(columns=overall_cols), on="player_id", how="inner")

    # Merge HIGH+EXTREME pressure metrics
    hi_cols = {
        "runs": "pressure_runs",
        "balls_faced": "pressure_balls_faced",
        "dismissals": "pressure_dismissals",
        "bowler_credited_dismissals": "pressure_bowler_dismissals",
        "run_out_dismissals": "pressure_run_out_dismissals",
        "innings_count": "pressure_innings",
        "matches_count": "pressure_matches",
        "seasons_count": "pressure_seasons",
        "strike_rate": "pressure_strike_rate",
        "batting_average": "pressure_average",
        "runs_per_dismissal": "pressure_runs_per_dismissal",
        "boundary_pct": "pressure_boundary_pct",
        "dot_ball_pct": "pressure_dot_ball_pct",
        "dismissal_rate_pct": "pressure_dismissal_rate_pct",
        "mean_runs_per_innings": "pressure_runs_per_innings",
        "std_runs_per_innings": "pressure_std_runs_per_innings",
        "iqr_runs_per_innings": "pressure_iqr_runs_per_innings",
        "mean_pressure_contribution_pct": "pressure_contribution_pct",
        "rvae_total": "pressure_rvae_total",
        "rvae_per_100b": "pressure_rvae_per_100b",
        "survival_above_exp": "pressure_survival_above_exp",
        "net_impact_per_100b": "pressure_net_impact_per_100b",
        "mean_pressure_index": "mean_pressure_index_faced",
    }
    base = base.merge(hi_agg[["player_id"] + list(hi_cols.keys())].rename(columns=hi_cols), on="player_id", how="left")

    # Merge NON-PRESSURE (LOW+MODERATE) metrics
    non_cols = {
        "runs": "nonpressure_runs",
        "balls_faced": "nonpressure_balls_faced",
        "dismissals": "nonpressure_dismissals",
        "innings_count": "nonpressure_innings",
        "matches_count": "nonpressure_matches",
        "strike_rate": "nonpressure_strike_rate",
        "batting_average": "nonpressure_average",
        "boundary_pct": "nonpressure_boundary_pct",
        "dot_ball_pct": "nonpressure_dot_ball_pct",
        "mean_runs_per_innings": "nonpressure_runs_per_innings",
        "rvae_per_100b": "nonpressure_rvae_per_100b",
        "net_impact_per_100b": "nonpressure_net_impact_per_100b",
    }
    base = base.merge(non_agg[["player_id"] + list(non_cols.keys())].rename(columns=non_cols), on="player_id", how="left")

    # Merge IPL vs T20I and Inn 1 vs Chase pressure splits
    for sub_df, pref in [(hi_ipl, "pressure_ipl"), (hi_t20i, "pressure_t20i"), (hi_inn1, "pressure_inn1"), (hi_inn2, "pressure_chase")]:
        if not sub_df.empty:
            ren = {
                "balls_faced": f"{pref}_bf",
                "runs": f"{pref}_runs",
                "strike_rate": f"{pref}_sr",
                "batting_average": f"{pref}_avg",
                "rvae_per_100b": f"{pref}_rvae_per_100b",
            }
            base = base.merge(sub_df[["player_id"] + list(ren.keys())].rename(columns=ren), on="player_id", how="left")

    # Pivot phase pressure BF & SR
    for ph in ["Powerplay", "Middle", "Death"]:
        psub = hi_phase[hi_phase["match_phase"] == ph]
        if not psub.empty:
            p_low = ph.lower()
            base = base.merge(
                psub[["player_id", "balls_faced", "strike_rate", "rvae_per_100b"]].rename(columns={
                    "balls_faced": f"pressure_{p_low}_bf",
                    "strike_rate": f"pressure_{p_low}_sr",
                    "rvae_per_100b": f"pressure_{p_low}_rvae_per_100b",
                }),
                on="player_id",
                how="left",
            )

    # Zero-fill integer count columns (NEVER zero-fill rate/average metrics!)
    for cnt_col in [
        "pressure_runs", "pressure_balls_faced", "pressure_dismissals", "pressure_bowler_dismissals",
        "pressure_run_out_dismissals", "pressure_innings", "pressure_matches", "pressure_seasons",
        "nonpressure_runs", "nonpressure_balls_faced", "nonpressure_dismissals",
        "nonpressure_innings", "nonpressure_matches",
        "pressure_ipl_bf", "pressure_ipl_runs", "pressure_t20i_bf", "pressure_t20i_runs",
        "pressure_inn1_bf", "pressure_inn1_runs", "pressure_chase_bf", "pressure_chase_runs",
        "pressure_powerplay_bf", "pressure_middle_bf", "pressure_death_bf",
    ]:
        if cnt_col in base.columns:
            base[cnt_col] = base[cnt_col].fillna(0).astype(int)

    # Pressure vs Non-Pressure deltas (observational differences; NaN if either side missing)
    base["delta_sr_pressure_vs_non"] = (base["pressure_strike_rate"] - base["nonpressure_strike_rate"]).round(3)
    base["delta_avg_pressure_vs_non"] = (base["pressure_average"] - base["nonpressure_average"]).round(3)
    base["delta_dot_pct_pressure_vs_non"] = (base["pressure_dot_ball_pct"] - base["nonpressure_dot_ball_pct"]).round(3)
    base["delta_boundary_pct_pressure_vs_non"] = (base["pressure_boundary_pct"] - base["nonpressure_boundary_pct"]).round(3)
    base["delta_rvae_pressure_vs_non"] = (base["pressure_rvae_per_100b"] - base["nonpressure_rvae_per_100b"]).round(3)

    # Sort deterministically by player_id (NOT ranked as a Top 10 list!)
    base = base.sort_values("player_id").reset_index(drop=True)
    base.to_csv(PROCESSED_DIR / "player_batting_performance.csv", index=False)

    # 2. Granular breakdown by pressure category (LOW, MODERATE, HIGH, EXTREME)
    cat_agg = aggregate_batting_slice(valid_df, ["batting_pressure_level"], team_inn_totals)
    cat_agg = cat_agg.merge(
        base[["player_id", "player_name", "batting_role"]], on="player_id", how="left"
    ).rename(columns={"batting_pressure_level": "pressure_level"})
    cat_agg["pressure_level"] = pd.Categorical(cat_agg["pressure_level"], categories=PRESSURE_CATS, ordered=True)
    cat_agg = cat_agg.sort_values(["player_id", "pressure_level"]).reset_index(drop=True)
    cat_agg.to_csv(PROCESSED_DIR / "player_batting_pressure_breakdown.csv", index=False)

    # 3. outputs/batting_metric_summary.csv (cohort & category-level aggregate benchmarks)
    sum_rows = []
    for scope_name, sub_df in [
        ("ALL_VALID", valid_df),
        ("LOW_PRESSURE", valid_df[valid_df["batting_pressure_level"] == "LOW PRESSURE"]),
        ("MODERATE_PRESSURE", valid_df[valid_df["batting_pressure_level"] == "MODERATE PRESSURE"]),
        ("HIGH_PRESSURE", valid_df[valid_df["batting_pressure_level"] == "HIGH PRESSURE"]),
        ("EXTREME_PRESSURE", valid_df[valid_df["batting_pressure_level"] == "EXTREME PRESSURE"]),
        ("HIGH_PLUS_EXTREME_ALL", hi_df),
        ("HIGH_PLUS_EXTREME_IPL", hi_df[hi_df["eligibility_category"] == "IPL"]),
        ("HIGH_PLUS_EXTREME_T20I", hi_df[hi_df["eligibility_category"] == "T20I"]),
        ("HIGH_PLUS_EXTREME_INN1", hi_df[hi_df["innings"] == 1]),
        ("HIGH_PLUS_EXTREME_CHASE", hi_df[hi_df["innings"] == 2]),
        ("NON_PRESSURE_LOW_MOD", non_df),
    ]:
        f = sub_df[sub_df["is_batter_ball_faced"]]
        bf = int(len(f))
        runs = int(f["batter_runs"].sum())
        wkts = int(sub_df["is_wicket_event"].sum())
        bnds = int((f["is_four"] | f["is_six"]).sum())
        dots = int((f["batter_runs"] == 0).sum())
        sum_rows.append({
            "segment": scope_name,
            "balls_faced": bf,
            "runs": runs,
            "dismissals": wkts,
            "unique_batters": int(f["striker_id"].nunique()),
            "unique_innings": int(f["innings_key"].nunique()),
            "unique_matches": int(f["match_id"].nunique()),
            "strike_rate": round(runs / bf * 100.0, 2) if bf else np.nan,
            "batting_average": round(runs / wkts, 2) if wkts else np.nan,
            "boundary_pct": round(bnds / bf * 100.0, 2) if bf else np.nan,
            "dot_ball_pct": round(dots / bf * 100.0, 2) if bf else np.nan,
            "dismissal_rate_pct": round(wkts / bf * 100.0, 2) if bf else np.nan,
        })
    pd.DataFrame(sum_rows).to_csv(OUT_DIR / "batting_metric_summary.csv", index=False)

    print("\n=== PHASE 5 BATTING PERFORMANCE COMPLETE ===")
    print(f"Total eligible batters analyzed : {len(base):,}")
    print(f"Batters with >=1 pressure ball  : {int((base['pressure_balls_faced'] > 0).sum()):,}")
    print(f"Batters meeting primary sample  : {int(((base['pressure_balls_faced'] >= 80) & (base['pressure_innings'] >= 10) & (base['pressure_matches'] >= 10)).sum()):,} (>=80 pressure BF, >=10 inn/matches)")
    print("Role distribution:")
    print(base["batting_role"].value_counts().to_string())


if __name__ == "__main__":
    main()

