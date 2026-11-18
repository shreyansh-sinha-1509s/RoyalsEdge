"""
SupeRR Selector Season 2 - Phase 5 Bowling Performance Under Pressure.

Computes role-aware, format-adjusted, cricket-law-validated bowling performance
metrics across Model C bowling pressure categories (LOW, MODERATE, HIGH, EXTREME),
innings 1 vs. 2, match phases, and IPL vs. T20I environments.

Key guardrails:
  - Primary key is strictly player_id (never merged by player name).
  - Legal deliveries exclude wides, Overstep no-balls, and 'other' no-balls.
  - Bowler-conceded runs exclude byes, leg-byes, penalty runs, and extras_2_runs.
  - Bowler wickets strictly use is_bowler_wicket (never run-outs/retired outs).
  - Explicit metric direction: lower economy & boundary-conceded % = better;
    higher wicket frequency & dot-ball % = better.
  - No final Top 10 rankings are generated in this script.
"""

from __future__ import annotations

from pathlib import Path

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
        "is_wide",
        "is_noball",
        "is_super_over",
        "is_primary_eligible",
    ]:
        df[bcol] = df[bcol].astype(str).str.lower().eq("true")

    df["season_year"] = df["season"].astype(str).str.extract(r"(\d{4})")[0].astype(int)
    df["innings_key"] = df["match_id"].astype(str) + "_" + df["innings"].astype(str)
    return df, pm


def compute_context_bowling_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute leave-one-match-out (LOMO) expected bowler-conceded runs per legal ball
    and expected bowler wickets per legal ball by (eligibility_category, innings,
    match_phase, bowling_pressure_level) so IPL and T20I scoring hazards are separated.
    """
    valid = df[df["bowling_pressure_index"].notna()].copy()
    grp_cols = ["eligibility_category", "innings", "match_phase", "bowling_pressure_level"]

    m_agg = (
        valid.groupby(grp_cols + ["match_id"], as_index=False)
        .agg(
            m_rc=("bowler_conceded_runs", "sum"),
            m_lb=("is_legal_delivery", "sum"),
            m_bw=("is_bowler_wicket", "sum"),
        )
    )
    tot_agg = (
        m_agg.groupby(grp_cols, as_index=False)
        .agg(t_rc=("m_rc", "sum"), t_lb=("m_lb", "sum"), t_bw=("m_bw", "sum"))
    )
    m_agg = m_agg.merge(tot_agg, on=grp_cols, how="left")
    denom = np.maximum(m_agg["t_lb"] - m_agg["m_lb"], 1)
    m_agg["exp_bowl_runs_per_lb"] = (m_agg["t_rc"] - m_agg["m_rc"]) / denom
    m_agg["exp_bowl_wkt_per_lb"] = (m_agg["t_bw"] - m_agg["m_bw"]) / denom

    out = df.merge(
        m_agg[grp_cols + ["match_id", "exp_bowl_runs_per_lb", "exp_bowl_wkt_per_lb"]],
        on=grp_cols + ["match_id"],
        how="left",
    )
    return out


def assign_bowling_roles(df: pd.DataFrame, pm: pd.DataFrame) -> pd.DataFrame:
    """Data-driven bowling role classification with UNKNOWN / INSUFFICIENT EVIDENCE fallback."""
    legal = df[df["is_legal_delivery"]].copy()
    tot = (
        legal.groupby("bowler_id", as_index=False)
        .agg(
            total_primary_lb=("is_legal_delivery", "sum"),
            total_innings_bowled=("innings_key", "nunique"),
            pace_or_spin=("pace_or_spin_clean", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
            bowling_style=("bowling_style_clean", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
        )
    )
    ph_lb = (
        legal[legal["match_phase"] != "Unavailable"]
        .pivot_table(index="bowler_id", columns="match_phase", values="is_legal_delivery", aggfunc="sum", fill_value=0)
    )
    for ph in ["Powerplay", "Middle", "Death"]:
        if ph not in ph_lb.columns:
            ph_lb[ph] = 0
    ph_tot = ph_lb[["Powerplay", "Middle", "Death"]].sum(axis=1).replace(0, np.nan)
    ph_shares = pd.DataFrame({
        "bowler_id": ph_lb.index,
        "pp_lb_share": (ph_lb["Powerplay"] / ph_tot).fillna(0.0).values,
        "middle_lb_share": (ph_lb["Middle"] / ph_tot).fillna(0.0).values,
        "death_lb_share": (ph_lb["Death"] / ph_tot).fillna(0.0).values,
    })

    tot_bf = df[df["is_batter_ball_faced"]].groupby("striker_id", as_index=False).agg(total_primary_bf=("is_batter_ball_faced", "sum"))
    roles = (
        tot.merge(ph_shares, on="bowler_id", how="left")
        .merge(tot_bf.rename(columns={"striker_id": "bowler_id"}), on="bowler_id", how="left")
        .merge(pm[["player_id", "standardized_display_name"]], left_on="bowler_id", right_on="player_id", how="left")
    )
    roles["total_primary_bf"] = roles["total_primary_bf"].fillna(0).astype(int)

    def classify_role(r: pd.Series) -> str:
        if r["total_primary_lb"] < 36 or r["total_innings_bowled"] < 5:
            return "UNKNOWN / INSUFFICIENT EVIDENCE"
        ps = str(r["pace_or_spin"])
        if r["death_lb_share"] >= 0.35:
            return f"Death Specialist ({ps})"
        if r["pp_lb_share"] >= 0.40:
            return f"Powerplay Specialist ({ps})"
        if r["middle_lb_share"] >= 0.55:
            return f"Middle-Overs Enforcer ({ps})"
        return f"All-Phase ({ps})"

    roles["bowling_role"] = roles.apply(classify_role, axis=1)
    roles["is_dual_discipline_allrounder"] = (roles["total_primary_bf"] >= 60) & (roles["total_primary_lb"] >= 60)
    return roles


def aggregate_bowling_slice(df_slice: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Aggregate cricket-law-accurate bowling metrics for any grouping slice."""
    if df_slice.empty:
        return pd.DataFrame()

    w = df_slice.copy()
    w["is_dot_ball"] = w["is_legal_delivery"] & (w["bowler_conceded_runs"] == 0)
    w["is_boundary_conceded"] = w["is_four"] | w["is_six"]
    # Expected conceded runs and wickets accrued per legal ball
    w["exp_rc_row"] = np.where(w["is_legal_delivery"], w["exp_bowl_runs_per_lb"], 0.0)
    w["exp_bw_row"] = np.where(w["is_legal_delivery"], w["exp_bowl_wkt_per_lb"], 0.0)

    gcols = ["bowler_id"] + group_cols
    agg = (
        w.groupby(gcols, as_index=False)
        .agg(
            runs_conceded=("bowler_conceded_runs", "sum"),
            legal_balls=("is_legal_delivery", "sum"),
            total_deliveries_bowled=("match_id", "size"),
            wides_bowled=("is_wide", "sum"),
            noballs_bowled=("is_noball", "sum"),
            bowler_wickets=("is_bowler_wicket", "sum"),
            dot_balls=("is_dot_ball", "sum"),
            boundary_conceded_balls=("is_boundary_conceded", "sum"),
            innings_count=("innings_key", "nunique"),
            matches_count=("match_id", "nunique"),
            seasons_count=("season_year", "nunique"),
            exp_runs_conceded=("exp_rc_row", "sum"),
            exp_bowler_wickets=("exp_bw_row", "sum"),
            mean_pressure_index=("bowling_pressure_index", "mean"),
        )
        .rename(columns={"bowler_id": "player_id"})
    )
    # Require >= 1 legal ball in slice
    agg = agg[agg["legal_balls"] > 0].copy()

    # Innings-level economy & consistency
    inn_gcols = ["bowler_id"] + group_cols + ["match_id", "innings", "innings_key"]
    inn_df = (
        w.groupby(inn_gcols, as_index=False)
        .agg(
            inn_rc=("bowler_conceded_runs", "sum"),
            inn_lb=("is_legal_delivery", "sum"),
            inn_bw=("is_bowler_wicket", "sum"),
            inn_exp_rc=("exp_rc_row", "sum"),
            inn_exp_bw=("exp_bw_row", "sum"),
        )
        .rename(columns={"bowler_id": "player_id"})
    )
    inn_df = inn_df[inn_df["inn_lb"] > 0].copy()
    inn_df["inn_econ"] = inn_df["inn_rc"] * 6.0 / inn_df["inn_lb"]
    inn_df["inn_rsae"] = inn_df["inn_exp_rc"] - inn_df["inn_rc"]

    d_cols = ["player_id"] + group_cols
    cons_agg = (
        inn_df.groupby(d_cols, as_index=False)
        .agg(
            mean_innings_economy=("inn_econ", "mean"),
            std_innings_economy=("inn_econ", "std"),
            iqr_innings_economy=("inn_econ", lambda s: float(np.percentile(s, 75) - np.percentile(s, 25)) if len(s) >= 2 else np.nan),
            std_innings_rsae=("inn_rsae", "std"),
        )
    )
    agg = agg.merge(cons_agg, on=d_cols, how="left")

    # Derived bowling rates (explicit directions documented)
    agg["overs"] = agg["legal_balls"] / 6.0
    agg["economy_rate"] = agg["runs_conceded"] / agg["overs"]
    agg["bowling_average"] = np.where(agg["bowler_wickets"] > 0, agg["runs_conceded"] / agg["bowler_wickets"], np.nan)
    agg["bowling_strike_rate"] = np.where(agg["bowler_wickets"] > 0, agg["legal_balls"] / agg["bowler_wickets"], np.nan)
    agg["dot_ball_pct"] = agg["dot_balls"] / agg["legal_balls"] * 100.0
    agg["boundary_conceded_pct"] = agg["boundary_conceded_balls"] / agg["legal_balls"] * 100.0
    agg["wicket_frequency"] = agg["bowler_wickets"] / agg["legal_balls"]

    # Positive = BETTER context-adjusted bowling value (runs saved + wickets above expected)
    agg["rsae_total"] = agg["exp_runs_conceded"] - agg["runs_conceded"]
    agg["rsae_per_over"] = agg["rsae_total"] / agg["overs"]
    agg["wickets_above_exp"] = agg["bowler_wickets"] - agg["exp_bowler_wickets"]
    # Net bowling impact per 24 balls (4-over spell): runs saved + 12 runs * wickets above expected
    agg["net_impact_per_24b"] = (agg["rsae_total"] + 12.0 * agg["wickets_above_exp"]) * 24.0 / agg["legal_balls"]

    round_cols = [
        "overs", "economy_rate", "bowling_average", "bowling_strike_rate",
        "dot_ball_pct", "boundary_conceded_pct", "mean_innings_economy",
        "std_innings_economy", "iqr_innings_economy", "std_innings_rsae",
        "exp_runs_conceded", "exp_bowler_wickets", "rsae_total", "rsae_per_over",
        "wickets_above_exp", "net_impact_per_24b", "mean_pressure_index",
    ]
    for c in round_cols:
        if c in agg.columns:
            agg[c] = agg[c].round(3)
    agg["wicket_frequency"] = agg["wicket_frequency"].round(5)
    return agg


def main() -> None:
    df_raw, pm = load_pressure_data()
    df = compute_context_bowling_baselines(df_raw)

    valid_df = df[df["bowling_pressure_index"].notna()].copy()
    hi_df = valid_df[valid_df["bowling_pressure_level"].isin(HIGH_PRESSURE_CATS)].copy()
    non_df = valid_df[valid_df["bowling_pressure_level"].isin(NON_PRESSURE_CATS)].copy()

    roles = assign_bowling_roles(df, pm)

    all_agg = aggregate_bowling_slice(valid_df, [])
    hi_agg = aggregate_bowling_slice(hi_df, [])
    non_agg = aggregate_bowling_slice(non_df, [])

    hi_ipl = aggregate_bowling_slice(hi_df[hi_df["eligibility_category"] == "IPL"], [])
    hi_t20i = aggregate_bowling_slice(hi_df[hi_df["eligibility_category"] == "T20I"], [])
    hi_inn1 = aggregate_bowling_slice(hi_df[hi_df["innings"] == 1], [])
    hi_inn2 = aggregate_bowling_slice(hi_df[hi_df["innings"] == 2], [])
    hi_phase = aggregate_bowling_slice(hi_df[hi_df["match_phase"] != "Unavailable"], ["match_phase"])

    base = roles[[
        "bowler_id", "standardized_display_name", "pace_or_spin", "bowling_style",
        "bowling_role", "is_dual_discipline_allrounder", "pp_lb_share", "middle_lb_share", "death_lb_share",
    ]].rename(columns={"bowler_id": "player_id", "standardized_display_name": "player_name"})

    overall_cols = {
        "runs_conceded": "overall_runs_conceded",
        "legal_balls": "overall_legal_balls",
        "overs": "overall_overs",
        "bowler_wickets": "overall_wickets",
        "innings_count": "overall_innings",
        "matches_count": "overall_matches",
        "seasons_count": "overall_seasons",
        "economy_rate": "overall_economy",
        "bowling_average": "overall_bowling_average",
        "bowling_strike_rate": "overall_bowling_strike_rate",
        "dot_ball_pct": "overall_dot_ball_pct",
        "boundary_conceded_pct": "overall_boundary_conceded_pct",
        "wicket_frequency": "overall_wicket_frequency",
        "rsae_per_over": "overall_rsae_per_over",
    }
    base = base.merge(all_agg[["player_id"] + list(overall_cols.keys())].rename(columns=overall_cols), on="player_id", how="inner")

    hi_cols = {
        "runs_conceded": "pressure_runs_conceded",
        "legal_balls": "pressure_legal_balls",
        "overs": "pressure_overs",
        "bowler_wickets": "pressure_wickets",
        "wides_bowled": "pressure_wides",
        "noballs_bowled": "pressure_noballs",
        "innings_count": "pressure_innings",
        "matches_count": "pressure_matches",
        "seasons_count": "pressure_seasons",
        "economy_rate": "pressure_economy",
        "bowling_average": "pressure_bowling_average",
        "bowling_strike_rate": "pressure_bowling_strike_rate",
        "dot_ball_pct": "pressure_dot_ball_pct",
        "boundary_conceded_pct": "pressure_boundary_conceded_pct",
        "wicket_frequency": "pressure_wicket_frequency",
        "std_innings_economy": "pressure_std_innings_economy",
        "iqr_innings_economy": "pressure_iqr_innings_economy",
        "rsae_total": "pressure_rsae_total",
        "rsae_per_over": "pressure_rsae_per_over",
        "wickets_above_exp": "pressure_wickets_above_exp",
        "net_impact_per_24b": "pressure_net_impact_per_24b",
        "mean_pressure_index": "mean_pressure_index_bowled",
    }
    base = base.merge(hi_agg[["player_id"] + list(hi_cols.keys())].rename(columns=hi_cols), on="player_id", how="left")

    non_cols = {
        "runs_conceded": "nonpressure_runs_conceded",
        "legal_balls": "nonpressure_legal_balls",
        "bowler_wickets": "nonpressure_wickets",
        "innings_count": "nonpressure_innings",
        "matches_count": "nonpressure_matches",
        "economy_rate": "nonpressure_economy",
        "bowling_average": "nonpressure_bowling_average",
        "bowling_strike_rate": "nonpressure_bowling_strike_rate",
        "dot_ball_pct": "nonpressure_dot_ball_pct",
        "boundary_conceded_pct": "nonpressure_boundary_conceded_pct",
        "wicket_frequency": "nonpressure_wicket_frequency",
        "rsae_per_over": "nonpressure_rsae_per_over",
        "net_impact_per_24b": "nonpressure_net_impact_per_24b",
    }
    base = base.merge(non_agg[["player_id"] + list(non_cols.keys())].rename(columns=non_cols), on="player_id", how="left")

    for sub_df, pref in [(hi_ipl, "pressure_ipl"), (hi_t20i, "pressure_t20i"), (hi_inn1, "pressure_inn1"), (hi_inn2, "pressure_inn2")]:
        if not sub_df.empty:
            ren = {
                "legal_balls": f"{pref}_lb",
                "bowler_wickets": f"{pref}_wkts",
                "economy_rate": f"{pref}_econ",
                "rsae_per_over": f"{pref}_rsae_per_over",
            }
            base = base.merge(sub_df[["player_id"] + list(ren.keys())].rename(columns=ren), on="player_id", how="left")

    for ph in ["Powerplay", "Middle", "Death"]:
        psub = hi_phase[hi_phase["match_phase"] == ph]
        if not psub.empty:
            p_low = ph.lower()
            base = base.merge(
                psub[["player_id", "legal_balls", "economy_rate", "rsae_per_over"]].rename(columns={
                    "legal_balls": f"pressure_{p_low}_lb",
                    "economy_rate": f"pressure_{p_low}_econ",
                    "rsae_per_over": f"pressure_{p_low}_rsae_per_over",
                }),
                on="player_id",
                how="left",
            )

    for cnt_col in [
        "pressure_runs_conceded", "pressure_legal_balls", "pressure_wickets",
        "pressure_wides", "pressure_noballs", "pressure_innings", "pressure_matches", "pressure_seasons",
        "nonpressure_runs_conceded", "nonpressure_legal_balls", "nonpressure_wickets",
        "nonpressure_innings", "nonpressure_matches",
        "pressure_ipl_lb", "pressure_ipl_wkts", "pressure_t20i_lb", "pressure_t20i_wkts",
        "pressure_inn1_lb", "pressure_inn1_wkts", "pressure_inn2_lb", "pressure_inn2_wkts",
        "pressure_powerplay_lb", "pressure_middle_lb", "pressure_death_lb",
    ]:
        if cnt_col in base.columns:
            base[cnt_col] = base[cnt_col].fillna(0).astype(int)

    # Pressure vs Non-Pressure deltas (Note: negative delta_econ means BETTER economy under pressure)
    base["delta_econ_pressure_vs_non"] = (base["pressure_economy"] - base["nonpressure_economy"]).round(3)
    base["delta_wkt_freq_pressure_vs_non"] = (base["pressure_wicket_frequency"] - base["nonpressure_wicket_frequency"]).round(5)
    base["delta_dot_pct_pressure_vs_non"] = (base["pressure_dot_ball_pct"] - base["nonpressure_dot_ball_pct"]).round(3)
    base["delta_boundary_conceded_pressure_vs_non"] = (base["pressure_boundary_conceded_pct"] - base["nonpressure_boundary_conceded_pct"]).round(3)
    base["delta_rsae_pressure_vs_non"] = (base["pressure_rsae_per_over"] - base["nonpressure_rsae_per_over"]).round(3)

    base = base.sort_values("player_id").reset_index(drop=True)
    base.to_csv(PROCESSED_DIR / "player_bowling_performance.csv", index=False)

    # 2. Granular breakdown by pressure category
    cat_agg = aggregate_bowling_slice(valid_df, ["bowling_pressure_level"])
    cat_agg = cat_agg.merge(
        base[["player_id", "player_name", "bowling_role", "pace_or_spin"]], on="player_id", how="left"
    ).rename(columns={"bowling_pressure_level": "pressure_level"})
    cat_agg["pressure_level"] = pd.Categorical(cat_agg["pressure_level"], categories=PRESSURE_CATS, ordered=True)
    cat_agg = cat_agg.sort_values(["player_id", "pressure_level"]).reset_index(drop=True)
    cat_agg.to_csv(PROCESSED_DIR / "player_bowling_pressure_breakdown.csv", index=False)

    # 3. outputs/bowling_metric_summary.csv
    sum_rows = []
    for scope_name, sub_df in [
        ("ALL_VALID", valid_df),
        ("LOW_PRESSURE", valid_df[valid_df["bowling_pressure_level"] == "LOW PRESSURE"]),
        ("MODERATE_PRESSURE", valid_df[valid_df["bowling_pressure_level"] == "MODERATE PRESSURE"]),
        ("HIGH_PRESSURE", valid_df[valid_df["bowling_pressure_level"] == "HIGH PRESSURE"]),
        ("EXTREME_PRESSURE", valid_df[valid_df["bowling_pressure_level"] == "EXTREME PRESSURE"]),
        ("HIGH_PLUS_EXTREME_ALL", hi_df),
        ("HIGH_PLUS_EXTREME_IPL", hi_df[hi_df["eligibility_category"] == "IPL"]),
        ("HIGH_PLUS_EXTREME_T20I", hi_df[hi_df["eligibility_category"] == "T20I"]),
        ("HIGH_PLUS_EXTREME_INN1", hi_df[hi_df["innings"] == 1]),
        ("HIGH_PLUS_EXTREME_INN2", hi_df[hi_df["innings"] == 2]),
        ("NON_PRESSURE_LOW_MOD", non_df),
    ]:
        lb = int(sub_df["is_legal_delivery"].sum())
        rc = int(sub_df["bowler_conceded_runs"].sum())
        bw = int(sub_df["is_bowler_wicket"].sum())
        dots = int((sub_df["is_legal_delivery"] & (sub_df["bowler_conceded_runs"] == 0)).sum())
        bnds = int((sub_df["is_four"] | sub_df["is_six"]).sum())
        sum_rows.append({
            "segment": scope_name,
            "legal_balls": lb,
            "overs": round(lb / 6.0, 2),
            "runs_conceded": rc,
            "bowler_wickets": bw,
            "unique_bowlers": int(sub_df.loc[sub_df["is_legal_delivery"], "bowler_id"].nunique()),
            "unique_innings": int(sub_df["innings_key"].nunique()),
            "unique_matches": int(sub_df["match_id"].nunique()),
            "economy_rate": round(rc * 6.0 / lb, 2) if lb else np.nan,
            "bowling_average": round(rc / bw, 2) if bw else np.nan,
            "bowling_strike_rate": round(lb / bw, 2) if bw else np.nan,
            "dot_ball_pct": round(dots / lb * 100.0, 2) if lb else np.nan,
            "boundary_conceded_pct": round(bnds / lb * 100.0, 2) if lb else np.nan,
            "wicket_frequency": round(bw / lb, 5) if lb else np.nan,
        })
    pd.DataFrame(sum_rows).to_csv(OUT_DIR / "bowling_metric_summary.csv", index=False)

    print("\n=== PHASE 5 BOWLING PERFORMANCE COMPLETE ===")
    print(f"Total eligible bowlers analyzed : {len(base):,}")
    print(f"Bowlers with >=1 pressure ball  : {int((base['pressure_legal_balls'] > 0).sum()):,}")
    print(f"Bowlers meeting primary sample  : {int(((base['pressure_legal_balls'] >= 90) & (base['pressure_innings'] >= 10) & (base['pressure_matches'] >= 10)).sum()):,} (>=90 pressure LB, >=10 inn/matches)")
    print("Role distribution:")
    print(base["bowling_role"].value_counts().to_string())


if __name__ == "__main__":
    main()

