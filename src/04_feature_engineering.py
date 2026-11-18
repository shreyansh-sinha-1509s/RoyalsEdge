"""
SupeRR Selector Season 2 - Phase 3 Pre-Delivery Feature Engineering.

Reads data/processed/clean_deliveries.csv, clean_matches.csv, and player_master.csv,
computes strictly PRE-DELIVERY match-state, phase, batting/bowling context, and chase
features (with zero future-outcome leakage and explicit unavailable handling for DLS
matches lacking revised-overs metadata), writes the enriched clean_deliveries.csv,
and generates outputs/feature_dictionary.csv.

No pressure scores or player rankings are computed in this script.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"

ENGINEERED_COLUMNS: list[str] = [
    "striker_display_name",
    "bowler_display_name",
    "batting_team_name",
    "bowling_team_name",
    "batter_position",
    "bowling_style_clean",
    "pace_or_spin_clean",
    "delivery_style_clean",
    "cum_score_before",
    "wickets_before",
    "wickets_in_hand_before",
    "legal_balls_before",
    "overs_completed_before",
    "current_run_rate_before",
    "scheduled_legal_balls",
    "scheduled_balls_source",
    "legal_balls_remaining_before",
    "powerplay_legal_balls",
    "death_start_legal_ball",
    "match_phase",
    "target_runs",
    "runs_remaining_before",
    "required_run_rate_before",
    "chase_context_available",
    "batter_runs_before",
    "batter_balls_faced_before",
    "bowler_legal_balls_before",
    "bowler_runs_conceded_before",
    "bowler_wickets_before",
]

FEATURE_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "striker_display_name": ("Context", "Standardized batter display name joined strictly via striker_id -> player_master.player_id"),
    "bowler_display_name": ("Context", "Standardized bowler display name joined strictly via bowler_id -> player_master.player_id"),
    "batting_team_name": ("Context", "Team name of batting_team_id resolved from clean_matches"),
    "bowling_team_name": ("Context", "Team name of bowling_team_id resolved from clean_matches"),
    "batter_position": ("Context", "Integer batting position of striker in innings (from batting_order)"),
    "bowling_style_clean": ("Context", "Standardized bowling style string (from bowling_type)"),
    "pace_or_spin_clean": ("Context", "Pace vs Spin classification (from pace_or_spin)"),
    "delivery_style_clean": ("Context", "Delivery variation/type with literal 'None' set to NaN (raw delivery_style preserved)"),
    "cum_score_before": ("Match State (Pre-Delivery)", "Cumulative team total_runs in current innings strictly BEFORE this delivery"),
    "wickets_before": ("Match State (Pre-Delivery)", "Cumulative team wickets fallen (is_wicket_event) strictly BEFORE this delivery (excludes retired hurt)"),
    "wickets_in_hand_before": ("Match State (Pre-Delivery)", "10 - wickets_before strictly BEFORE this delivery"),
    "legal_balls_before": ("Match State (Pre-Delivery)", "Cumulative legal deliveries bowled in innings strictly BEFORE this delivery"),
    "overs_completed_before": ("Match State (Pre-Delivery)", "Exact fractional overs completed before this delivery (legal_balls_before / 6.0)"),
    "current_run_rate_before": ("Match State (Pre-Delivery)", "Innings run rate strictly before this delivery (cum_score_before * 6 / legal_balls_before; NaN when legal_balls_before == 0)"),
    "scheduled_legal_balls": ("Match State (Setup)", "Defensible scheduled legal deliveries for innings (120 for standard 20-over; revised balls when provided; NaN when DLS/reduced overs metadata is missing)"),
    "scheduled_balls_source": ("Match State (Setup)", "Provenance of scheduled_legal_balls ('standard_20_overs', 'revised_overs_metadata', or 'unavailable_dls_or_reduced_missing')"),
    "legal_balls_remaining_before": ("Match State (Pre-Delivery)", "Scheduled legal balls minus legal_balls_before (clipped at >= 0; NaN when scheduled_legal_balls is unavailable)"),
    "powerplay_legal_balls": ("Match Phase", "Number of legal balls in Powerplay (36 for 20-over; ICC Clause 28.7.3 scaled for known reduced overs; NaN if scheduled balls unavailable)"),
    "death_start_legal_ball": ("Match Phase", "0-indexed legal ball where Death phase begins (90 for 20-over [overs 16-20]; final ceil(0.25*overs) for known reduced overs; NaN if unavailable)"),
    "match_phase": ("Match Phase", "Pre-delivery T20 phase ('Powerplay', 'Middle', 'Death', or 'Unavailable' when scheduled overs are missing)"),
    "target_runs": ("Chase Context", "2nd-innings target runs (revised_target when populated; inn1_total_runs + 1 for non-DLS; NaN for 1st innings or DLS matches missing revised_target)"),
    "runs_remaining_before": ("Chase Context (Pre-Delivery)", "2nd-innings runs needed before this delivery (max(target_runs - cum_score_before, 0); NaN for 1st innings or unavailable target)"),
    "required_run_rate_before": ("Chase Context (Pre-Delivery)", "2nd-innings required run rate before this delivery (runs_remaining_before * 6 / legal_balls_remaining_before; NaN if 1st innings or denominator/target unavailable)"),
    "chase_context_available": ("Chase Context", "Boolean flag indicating both target_runs and legal_balls_remaining_before are defensibly available in 2nd innings"),
    "batter_runs_before": ("Batter State (Pre-Delivery)", "Striker's cumulative batter_runs in current innings strictly BEFORE this delivery"),
    "batter_balls_faced_before": ("Batter State (Pre-Delivery)", "Striker's cumulative balls faced (is_batter_ball_faced) in current innings strictly BEFORE this delivery"),
    "bowler_legal_balls_before": ("Bowler State (Pre-Delivery)", "Bowler's cumulative legal deliveries in current innings strictly BEFORE this delivery"),
    "bowler_runs_conceded_before": ("Bowler State (Pre-Delivery)", "Bowler's cumulative bowler_conceded_runs in current innings strictly BEFORE this delivery"),
    "bowler_wickets_before": ("Bowler State (Pre-Delivery)", "Bowler's cumulative bowler-credited wickets in current innings strictly BEFORE this delivery"),
}


def icc_powerplay_overs(scheduled_overs: float) -> int:
    """Official ICC T20 Playing Conditions (Clause 28.7.3) Powerplay length by scheduled overs."""
    ov = int(round(scheduled_overs))
    if ov >= 19:
        return 6
    if ov >= 15:
        return 5
    if ov >= 12:
        return 4
    if ov >= 9:
        return 3
    if ov >= 5:
        return 2
    return max(1, int(round(ov * 0.30)))


def icc_death_overs(scheduled_overs: float) -> int:
    """Final 25% of scheduled overs (equals 5 overs [16-20] for standard 20-over T20)."""
    ov = int(round(scheduled_overs))
    return max(1, int(math.ceil(ov * 0.25)))


def engineer_features(
    deliveries: pd.DataFrame,
    matches: pd.DataFrame,
    player_master: pd.DataFrame,
) -> pd.DataFrame:
    """Compute all strictly pre-delivery analytical features without future leakage."""
    df = deliveries.copy()

    # Drop any previously engineered columns so reruns are idempotent
    to_drop = [c for c in ENGINEERED_COLUMNS if c in df.columns]
    if to_drop:
        df = df.drop(columns=to_drop)

    # Strict deterministic ordering
    df = df.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)

    # Attach standardized player display names via player_id
    pid_to_name = player_master.set_index("player_id")["standardized_display_name"]
    df["striker_display_name"] = df["striker_id"].map(pid_to_name)
    df["bowler_display_name"] = df["bowler_id"].map(pid_to_name)

    # Attach match metadata needed for team names & pre-innings setup (no future result columns used)
    match_setup_cols = [
        "match_id",
        "home_team_id",
        "home_team",
        "away_team_id",
        "away_team",
        "first_inn_revised_balls",
        "second_inn_revised_balls",
        "revised_target_num",
        "is_missing_inn1_revised_balls",
        "is_missing_inn2_revised_balls",
        "is_missing_revised_target",
    ]
    m_sub = matches[match_setup_cols].copy()
    df = df.merge(m_sub, on="match_id", how="left")

    df["batting_team_name"] = np.where(
        df["batting_team_id"] == df["home_team_id"], df["home_team"], df["away_team"]
    )
    df["bowling_team_name"] = np.where(
        df["bowling_team_id"] == df["home_team_id"], df["home_team"], df["away_team"]
    )

    df["batter_position"] = pd.to_numeric(df["batting_order"], errors="coerce").astype("Int64")
    df["bowling_style_clean"] = df["bowling_type"].astype(str).str.strip()
    df["pace_or_spin_clean"] = df["pace_or_spin"].astype(str).str.strip()
    df["delivery_style_clean"] = df["delivery_style"].replace({"None": np.nan, "": np.nan})

    # Pre-delivery innings state (strictly BEFORE current ball)
    grp_inn = df.groupby(["match_id", "innings"], sort=False)
    df["cum_score_before"] = grp_inn["total_runs"].cumsum() - df["total_runs"]
    wkt_int = df["is_wicket_event"].astype(int)
    df["wickets_before"] = grp_inn["is_wicket_event"].cumsum() - wkt_int
    df["wickets_in_hand_before"] = (10 - df["wickets_before"]).clip(lower=0)

    legal_int = df["is_legal_delivery"].astype(int)
    df["legal_balls_before"] = grp_inn["is_legal_delivery"].cumsum() - legal_int
    df["overs_completed_before"] = (df["legal_balls_before"] / 6.0).round(4)
    df["current_run_rate_before"] = np.where(
        df["legal_balls_before"] > 0,
        (df["cum_score_before"] * 6.0 / df["legal_balls_before"]).round(4),
        np.nan,
    )

    # Scheduled legal balls per innings (never inventing missing DLS/reduced overs)
    inn1 = df["innings"] == 1
    inn2 = df["innings"] == 2

    sched_balls = np.full(len(df), np.nan, dtype=float)
    sched_src = np.full(len(df), "unavailable_dls_or_reduced_missing", dtype=object)

    # Innings 1 setup
    mask_i1_rev = inn1 & df["first_inn_revised_balls"].notna() & (df["first_inn_revised_balls"] > 0)
    mask_i1_std = inn1 & df["first_inn_revised_balls"].isna() & (~df["is_missing_inn1_revised_balls"].fillna(False))
    sched_balls[mask_i1_rev] = df.loc[mask_i1_rev, "first_inn_revised_balls"]
    sched_src[mask_i1_rev] = "revised_overs_metadata"
    sched_balls[mask_i1_std] = 120.0
    sched_src[mask_i1_std] = "standard_20_overs"

    # Innings 2 setup
    mask_i2_rev = inn2 & df["second_inn_revised_balls"].notna() & (df["second_inn_revised_balls"] > 0)
    mask_i2_std = inn2 & df["second_inn_revised_balls"].isna() & (~df["is_missing_inn2_revised_balls"].fillna(False))
    sched_balls[mask_i2_rev] = df.loc[mask_i2_rev, "second_inn_revised_balls"]
    sched_src[mask_i2_rev] = "revised_overs_metadata"
    sched_balls[mask_i2_std] = 120.0
    sched_src[mask_i2_std] = "standard_20_overs"

    df["scheduled_legal_balls"] = sched_balls
    df["scheduled_balls_source"] = sched_src
    df["legal_balls_remaining_before"] = np.where(
        df["scheduled_legal_balls"].notna(),
        np.maximum(df["scheduled_legal_balls"] - df["legal_balls_before"], 0.0),
        np.nan,
    )

    # Match phase based on legal_balls_before and defensible scheduled_legal_balls
    pp_balls = np.full(len(df), np.nan, dtype=float)
    death_start = np.full(len(df), np.nan, dtype=float)

    valid_sched = df["scheduled_legal_balls"].notna()
    unique_sched = df.loc[valid_sched, "scheduled_legal_balls"].unique()
    for sb in unique_sched:
        ov = sb / 6.0
        pp_b = float(icc_powerplay_overs(ov) * 6)
        d_start = float(sb - icc_death_overs(ov) * 6)
        # Ensure non-overlapping ordering on ultra-short innings (e.g., 5 overs -> pp=12, death_start=18)
        if d_start < pp_b:
            d_start = pp_b
        mask_sb = df["scheduled_legal_balls"] == sb
        pp_balls[mask_sb] = pp_b
        death_start[mask_sb] = d_start

    df["powerplay_legal_balls"] = pp_balls
    df["death_start_legal_ball"] = death_start
    df["match_phase"] = np.select(
        [
            ~valid_sched,
            df["legal_balls_before"] < df["powerplay_legal_balls"],
            df["legal_balls_before"] < df["death_start_legal_ball"],
        ],
        [
            "Unavailable",
            "Powerplay",
            "Middle",
        ],
        default="Death",
    )

    # Chase context for 2nd innings (1st-innings final total is known BEFORE ball 1 of 2nd innings)
    inn1_totals = (
        df[inn1].groupby("match_id")["total_runs"].sum()
    )
    inn1_score_mapped = df["match_id"].map(inn1_totals)

    target = np.full(len(df), np.nan, dtype=float)
    mask_t_rev = inn2 & df["revised_target_num"].notna()
    mask_t_std = inn2 & df["revised_target_num"].isna() & (~df["is_missing_revised_target"].fillna(False)) & inn1_score_mapped.notna()
    target[mask_t_rev] = df.loc[mask_t_rev, "revised_target_num"]
    target[mask_t_std] = inn1_score_mapped.loc[mask_t_std] + 1.0

    df["target_runs"] = target
    df["runs_remaining_before"] = np.where(
        inn2 & df["target_runs"].notna(),
        np.maximum(df["target_runs"] - df["cum_score_before"], 0.0),
        np.nan,
    )
    df["required_run_rate_before"] = np.where(
        inn2
        & df["runs_remaining_before"].notna()
        & df["legal_balls_remaining_before"].notna()
        & (df["legal_balls_remaining_before"] > 0),
        (df["runs_remaining_before"] * 6.0 / df["legal_balls_remaining_before"]).round(4),
        np.nan,
    )
    df["chase_context_available"] = (
        inn2 & df["target_runs"].notna() & df["legal_balls_remaining_before"].notna()
    )

    # Pre-delivery individual batter & bowler innings state
    grp_bat = df.groupby(["match_id", "innings", "striker_id"], sort=False)
    df["batter_runs_before"] = grp_bat["batter_runs"].cumsum() - df["batter_runs"]
    bf_int = df["is_batter_ball_faced"].astype(int)
    df["batter_balls_faced_before"] = grp_bat["is_batter_ball_faced"].cumsum() - bf_int

    grp_bowl = df.groupby(["match_id", "innings", "bowler_id"], sort=False)
    df["bowler_legal_balls_before"] = grp_bowl["is_legal_delivery"].cumsum() - legal_int
    df["bowler_runs_conceded_before"] = grp_bowl["bowler_conceded_runs"].cumsum() - df["bowler_conceded_runs"]
    bw_int = df["is_bowler_wicket"].astype(int)
    df["bowler_wickets_before"] = grp_bowl["is_bowler_wicket"].cumsum() - bw_int

    # Drop temporary merge helper columns
    helper_cols = [
        "home_team_id",
        "home_team",
        "away_team_id",
        "away_team",
        "first_inn_revised_balls",
        "second_inn_revised_balls",
        "revised_target_num",
        "is_missing_inn1_revised_balls",
        "is_missing_inn2_revised_balls",
        "is_missing_revised_target",
    ]
    df = df.drop(columns=helper_cols)
    return df


def build_feature_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    """Create outputs/feature_dictionary.csv documenting all columns in clean_deliveries.csv."""
    rows = []
    for col in df.columns:
        s = df[col]
        if col in FEATURE_DESCRIPTIONS:
            group, desc = FEATURE_DESCRIPTIONS[col]
            origin = "engineered_phase3_04"
        elif col in {
            "match_id", "innings", "overid", "over_ball_num", "innings_ball_num",
            "batting_team_id", "bowling_team_id", "striker_id", "striker_name",
            "non_striker_id", "non_striker_name", "bowler_id", "bowler_name",
            "batting_type", "bowling_type", "batting_order", "runs", "is_four",
            "is_six", "is_wicket", "dismissal_type_id", "dismissal_type",
            "dismissed_player_id", "extras_type", "extras1_runs", "extras_2_runs",
            "pace_or_spin", "bowl_speed", "stroke", "delivery_style",
            "over_or_around", "on_or_off", "delivery_ist_time",
        }:
            group, desc = "Raw Source", "Original unmodified column from ball_by_ball.csv"
            origin = "raw_source"
        else:
            group, desc = "Cleaned / Derived Rule", "Derived cricket-rule or validation column from 03_data_cleaning.py"
            origin = "cleaned_phase3_03"

        rows.append({
            "column_name": col,
            "origin": origin,
            "feature_group": group,
            "dtype": str(s.dtype),
            "non_null_count": int(s.notna().sum()),
            "missing_count": int(s.isna().sum()),
            "missing_pct": round(s.isna().mean() * 100, 4),
            "unique_values": int(s.nunique(dropna=True)),
            "description": desc,
        })
    return pd.DataFrame(rows)


def main() -> None:
    clean_del_path = PROCESSED_DIR / "clean_deliveries.csv"
    clean_matches_path = PROCESSED_DIR / "clean_matches.csv"
    player_master_path = PROCESSED_DIR / "player_master.csv"

    deliveries = pd.read_csv(clean_del_path, low_memory=False, keep_default_na=False, na_values=[""])
    matches = pd.read_csv(clean_matches_path, low_memory=False, keep_default_na=False, na_values=[""])
    player_master = pd.read_csv(player_master_path, low_memory=False, keep_default_na=False, na_values=[""])

    # Ensure boolean/numeric dtypes after CSV reload
    for bcol in ["is_primary_eligible", "is_super_over", "is_wide", "is_overstep_noball", "is_other_noball",
                 "is_noball", "is_byes", "is_legbyes", "is_penalty_extra", "is_legal_delivery",
                 "is_batter_ball_faced", "is_wicket_event", "is_retired_hurt", "is_bowler_wicket",
                 "is_run_out", "is_retired_out", "is_obstructing_field", "has_delivery_anomaly"]:
        if bcol in deliveries.columns:
            deliveries[bcol] = deliveries[bcol].astype(str).str.lower().eq("true")

    for bcol in ["is_missing_inn1_revised_balls", "is_missing_inn2_revised_balls", "is_missing_revised_target"]:
        if bcol in matches.columns:
            matches[bcol] = matches[bcol].astype(str).str.lower().eq("true")

    enriched = engineer_features(deliveries, matches, player_master)
    enriched.to_csv(clean_del_path, index=False)

    feat_dict = build_feature_dictionary(enriched)
    feat_dict.to_csv(OUT_DIR / "feature_dictionary.csv", index=False)

    # Append feature engineering validation checks to outputs/reconciliation_checks.csv
    recon_path = OUT_DIR / "reconciliation_checks.csv"
    recon_df = pd.read_csv(recon_path) if recon_path.is_file() else pd.DataFrame()
    recon_df = recon_df[~recon_df["check_name"].astype(str).str.startswith("fe_")].copy()

    # Check 1: Every innings ball #1 has cum_score_before==0, wickets_before==0, legal_balls_before==0, CRR==NaN
    first_balls = enriched.groupby(["match_id", "innings"], sort=False).head(1)
    first_ball_zero_ok = bool(
        (first_balls["cum_score_before"] == 0).all()
        and (first_balls["wickets_before"] == 0).all()
        and (first_balls["legal_balls_before"] == 0).all()
        and first_balls["current_run_rate_before"].isna().all()
    )
    # Check 2: Innings 1 has 0 non-null chase features
    inn1_chase_null_ok = bool(
        enriched.loc[enriched["innings"] == 1, ["target_runs", "runs_remaining_before", "required_run_rate_before"]].isna().all().all()
    )
    # Check 3: Unavailable scheduled_legal_balls implies Unavailable phase & NaN RRR
    unavail_mask = enriched["scheduled_legal_balls"].isna()
    dls_unavail_ok = bool(
        (enriched.loc[unavail_mask, "match_phase"] == "Unavailable").all()
        and enriched.loc[unavail_mask, "legal_balls_remaining_before"].isna().all()
        and enriched.loc[unavail_mask, "required_run_rate_before"].isna().all()
    )
    # Check 4: Negative pre-delivery metrics == 0
    no_neg_ok = bool(
        (enriched["cum_score_before"] >= 0).all()
        and (enriched["wickets_before"] >= 0).all()
        and (enriched["legal_balls_before"] >= 0).all()
        and (enriched["runs_remaining_before"].dropna() >= 0).all()
    )

    fe_checks = pd.DataFrame([
        {"check_name": "fe_first_delivery_pre_state_zero", "status": "PASS" if first_ball_zero_ok else "FAIL", "expected": True, "actual": first_ball_zero_ok, "details": "Every innings starts with cum_score_before=0, wickets_before=0, legal_balls_before=0"},
        {"check_name": "fe_innings_1_chase_features_null", "status": "PASS" if inn1_chase_null_ok else "FAIL", "expected": True, "actual": inn1_chase_null_ok, "details": "target_runs, runs_remaining_before, required_run_rate_before are NaN in innings 1"},
        {"check_name": "fe_dls_missing_revised_overs_unavailable", "status": "PASS" if dls_unavail_ok else "FAIL", "expected": True, "actual": dls_unavail_ok, "details": f"Unavailable scheduled_legal_balls rows: {int(unavail_mask.sum()):,}; all marked match_phase='Unavailable' and NaN RRR"},
        {"check_name": "fe_no_negative_pre_delivery_values", "status": "PASS" if no_neg_ok else "FAIL", "expected": True, "actual": no_neg_ok, "details": "All pre-delivery counts, scores, and runs_remaining are non-negative"},
    ])
    pd.concat([recon_df, fe_checks], ignore_index=True).to_csv(recon_path, index=False)

    print("\n=== PHASE 3 FEATURE ENGINEERING COMPLETE ===")
    print(f"Enriched clean_deliveries.csv : {len(enriched):,} rows x {len(enriched.columns)} cols")
    print("Match phase distribution:")
    print(enriched["match_phase"].value_counts().to_string())
    print(f"Chase context available (inn 2): {int(enriched['chase_context_available'].sum()):,} / {int((enriched['innings'] == 2).sum()):,}")
    print(f"Feature dictionary saved       : {(OUT_DIR / 'feature_dictionary.csv').relative_to(ROOT)} ({len(feat_dict)} columns)")


if __name__ == "__main__":
    main()
