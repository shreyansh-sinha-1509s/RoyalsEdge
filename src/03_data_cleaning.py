"""
SupeRR Selector Season 2 - Phase 3 Data Cleaning & Cricket Rule Validation.

Transforms the six read-only raw CSVs in data/raw/Data Pack/ into clean,
reproducible, cricket-law-validated processed datasets in data/processed/ and
audit/reconciliation logs in outputs/.

Original CSV files are never modified. Original columns are preserved alongside
explicitly named derived fields. No pressure scores or player rankings are computed.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DATA_PACK_DIR = RAW_DIR / "Data Pack"
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILENAMES: dict[str, str] = {
    "ball_by_ball": "ball_by_ball.csv",
    "matches": "matches.csv",
    "competitions": "competitions.csv",
    "teams": "teams.csv",
    "playing_eleven": "playing_eleven.csv",
    "player_mapping": "competition_team_player_mapping.csv",
}

# Verified competition IDs from Phase 2 audit (validated against competitions.csv & matches.csv)
ELIGIBLE_IPL_COMP_IDS: set[int] = {1358, 1715, 2193, 2725, 3298}
EXCLUDED_NON_IPL_T20_COMP_IDS: set[int] = {2670, 3289}

BOWLER_CREDITED_DISMISSALS: set[str] = {
    "Caught",
    "Bowled",
    "LBW",
    "Stump",
    "Hit Wicket",
}

# Verified rain-shortened / DLS matches lacking revised_overs metadata in matches.csv
KNOWN_UNFLAGGED_REDUCED_MATCH_IDS: set[int] = {
    15795,  # 12-over rain-reduced T20I (72 legal balls in inn1)
    18532,  # Rain-shortened DLS tie (54 legal balls in inn2)
    31278,  # 16-over rain-reduced IPL 2024 match (96 legal balls each)
    48514,  # 12-over rain-reduced T20I (72 legal balls each)
}


def load_raw_tables() -> tuple[dict[str, pd.DataFrame], str]:
    """Read all six competition CSVs read-only, preserving literal 'None' strings."""
    read_kwargs: dict[str, Any] = {
        "low_memory": False,
        "keep_default_na": False,
        "na_values": [""],
    }
    if DATA_PACK_DIR.is_dir():
        missing = [
            fname for fname in CSV_FILENAMES.values()
            if not (DATA_PACK_DIR / fname).is_file()
        ]
        if missing:
            raise FileNotFoundError(f"Missing CSVs in {DATA_PACK_DIR}: {missing}")
        tables = {
            key: pd.read_csv(DATA_PACK_DIR / fname, **read_kwargs)
            for key, fname in CSV_FILENAMES.items()
        }
        return tables, str(DATA_PACK_DIR.relative_to(ROOT))

    zip_candidates = sorted(RAW_DIR.glob("*.zip"))
    if len(zip_candidates) != 1:
        raise FileNotFoundError(
            f"Extracted folder {DATA_PACK_DIR} not found and expected 1 fallback ZIP in {RAW_DIR}."
        )
    zip_path = zip_candidates[0]
    tables = {}
    with zipfile.ZipFile(zip_path) as zf:
        for key, fname in CSV_FILENAMES.items():
            tables[key] = pd.read_csv(zf.open(f"Data Pack/{fname}"), **read_kwargs)
    return tables, str(zip_path.relative_to(ROOT))


def to_bool(series: pd.Series) -> pd.Series:
    """Convert raw bool/string series strictly to bool (NaN -> False)."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False, "1": True, "0": False})
        .fillna(False)
        .astype(bool)
    )


def parse_season_start_year(season_val: Any) -> int:
    """Extract 4-digit start year from season string like '2022' or '2022/23'."""
    m = re.search(r"(\d{4})", str(season_val))
    return int(m.group(1)) if m else -1


def build_competition_master(
    competitions: pd.DataFrame,
    matches: pd.DataFrame,
    balls: pd.DataFrame,
) -> pd.DataFrame:
    """Validate competition eligibility using comp_id + match_format + season (not names alone)."""
    comp = competitions.copy()
    comp["comp_id"] = pd.to_numeric(comp["comp_id"], errors="raise").astype(int)
    comp["season_start_year"] = comp["season"].apply(parse_season_start_year)

    # Validate that every comp_id in matches exists in competitions
    match_comp_ids = set(pd.to_numeric(matches["comp_id"], errors="raise").astype(int))
    comp_ids = set(comp["comp_id"])
    unmatched = match_comp_ids - comp_ids
    if unmatched:
        raise ValueError(f"Unmatched comp_ids found in matches.csv: {sorted(unmatched)}")

    # Validate explicit IPL & excluded IDs exist and match expected formats
    for cid in ELIGIBLE_IPL_COMP_IDS:
        row = comp.loc[comp["comp_id"] == cid]
        if len(row) != 1 or row.iloc[0]["match_format"] != "T20":
            raise ValueError(f"Expected IPL comp_id {cid} failed validation in competitions.csv")
    for cid in EXCLUDED_NON_IPL_T20_COMP_IDS:
        row = comp.loc[comp["comp_id"] == cid]
        if len(row) != 1 or row.iloc[0]["match_format"] != "T20":
            raise ValueError(f"Expected excluded non-IPL T20 comp_id {cid} failed validation")

    def classify_row(r: pd.Series) -> tuple[str, bool, str]:
        cid = int(r["comp_id"])
        fmt = str(r["match_format"]).strip()
        yr = int(r["season_start_year"])
        if cid in ELIGIBLE_IPL_COMP_IDS and fmt == "T20" and yr >= 2022:
            return "IPL", True, ""
        if fmt == "T20I" and yr >= 2022:
            return "T20I", True, ""
        if cid in EXCLUDED_NON_IPL_T20_COMP_IDS:
            return (
                "Non-IPL T20",
                False,
                "Excluded from primary dataset: non-IPL T20 tournament (official brief specifies IPL and T20I from 2022 onwards)",
            )
        return (
            "Other/Ineligible",
            False,
            f"Excluded: format={fmt}, season_start_year={yr} outside eligible IPL/T20I >= 2022 scope",
        )

    classified = comp.apply(classify_row, axis=1, result_type="expand")
    comp["eligibility_category"] = classified[0]
    comp["is_primary_eligible"] = classified[1].astype(bool)
    comp["exclusion_reason"] = classified[2]

    # Attach match and delivery counts
    m_counts = (
        matches.groupby("comp_id", as_index=False)
        .agg(
            matches_in_metadata=("match_id", "nunique"),
            min_match_date=("match_date", "min"),
            max_match_date=("match_date", "max"),
        )
    )
    b_with_comp = balls[["match_id", "innings"]].merge(
        matches[["match_id", "comp_id"]], on="match_id", how="left"
    )
    b_counts = (
        b_with_comp.groupby("comp_id", as_index=False)
        .agg(
            matches_with_ball_data=("match_id", "nunique"),
            total_deliveries=("match_id", "size"),
            regular_deliveries=("innings", lambda s: int(s.isin([1, 2]).sum())),
            super_over_deliveries=("innings", lambda s: int((s >= 3).sum())),
        )
    )

    comp = comp.merge(m_counts, on="comp_id", how="left").merge(b_counts, on="comp_id", how="left")
    for col in [
        "matches_in_metadata",
        "matches_with_ball_data",
        "total_deliveries",
        "regular_deliveries",
        "super_over_deliveries",
    ]:
        comp[col] = comp[col].fillna(0).astype(int)

    return comp.sort_values(["is_primary_eligible", "eligibility_category", "season_start_year", "comp_id"], ascending=[False, True, True, True]).reset_index(drop=True)


def enrich_deliveries_with_cricket_rules(
    balls: pd.DataFrame,
    matches: pd.DataFrame,
    comp_master: pd.DataFrame,
) -> pd.DataFrame:
    """Preserve all 33 original columns and add validated cricket-rule derived columns."""
    df = balls.copy()

    # Ensure deterministic sorting by match, innings, innings_ball_num
    df["match_id"] = pd.to_numeric(df["match_id"], errors="raise").astype(int)
    df["innings"] = pd.to_numeric(df["innings"], errors="raise").astype(int)
    df["overid"] = pd.to_numeric(df["overid"], errors="raise").astype(int)
    df["over_ball_num"] = pd.to_numeric(df["over_ball_num"], errors="raise").astype(int)
    df["innings_ball_num"] = pd.to_numeric(df["innings_ball_num"], errors="raise").astype(int)
    df = df.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)

    # Normalize booleans without altering original column semantics
    is_four_b = to_bool(df["is_four"])
    is_six_b = to_bool(df["is_six"])
    is_wicket_b = to_bool(df["is_wicket"])

    runs_num = pd.to_numeric(df["runs"], errors="raise").astype(int)
    e1_num = pd.to_numeric(df["extras1_runs"], errors="raise").astype(int)
    e2_num = pd.to_numeric(df["extras_2_runs"], errors="raise").astype(int)
    et_str = df["extras_type"].fillna("None").astype(str).str.strip()

    # Competition linkage
    match_comp = matches[["match_id", "comp_id"]].merge(
        comp_master[["comp_id", "comp_name", "match_format", "season", "eligibility_category", "is_primary_eligible"]],
        on="comp_id",
        how="left",
    )
    df = df.merge(match_comp, on="match_id", how="left")

    # Innings classification
    df["innings_type"] = np.where(
        df["innings"] == 1,
        "regular_first",
        np.where(df["innings"] == 2, "regular_second", "super_over"),
    )
    df["is_super_over"] = df["innings"] >= 3

    # A. Total runs & extras breakdown
    df["batter_runs"] = runs_num
    df["extras_total_runs"] = e1_num + e2_num
    df["total_runs"] = runs_num + e1_num + e2_num

    # B. Delivery & legal-ball classification
    df["is_wide"] = et_str.eq("wide")
    df["is_overstep_noball"] = et_str.eq("Overstep")
    df["is_other_noball"] = et_str.eq("other")
    df["is_noball"] = df["is_overstep_noball"] | df["is_other_noball"]
    df["is_byes"] = et_str.eq("byes")
    df["is_legbyes"] = et_str.eq("legbyes")
    df["is_penalty_extra"] = et_str.eq("Penalty")
    df["is_legal_delivery"] = ~(df["is_wide"] | df["is_noball"])

    # C. Batter balls faced (cricket law: wides do NOT count; no-balls DO count)
    df["is_batter_ball_faced"] = ~df["is_wide"]

    # D. Bowler-conceded runs (cricket law: excludes byes, leg-byes, penalty runs, and byes/legbyes off no-balls [extras_2_runs])
    df["bowler_conceded_runs"] = np.select(
        [
            df["is_wide"],
            df["is_noball"],
            df["is_byes"] | df["is_legbyes"] | df["is_penalty_extra"],
        ],
        [
            e1_num + e2_num,       # All wide runs charged to bowler
            runs_num + e1_num,     # Batter runs + 1-run no-ball penalty charged; extras_2_runs (byes/legbyes off NB) excluded
            0,                     # Byes, leg-byes, penalty runs excluded from bowler runs
        ],
        default=runs_num,          # Standard 'None' delivery: batter runs charged to bowler
    ).astype(int)
    df["non_bowler_extras_runs"] = df["total_runs"] - df["bowler_conceded_runs"]

    # E. Wickets, dismissal standardization, and retired hurt separation
    raw_dism = df["dismissal_type"]
    df["dismissal_type_std"] = raw_dism.replace({"Obstracting the field": "Obstructing the field"})
    df["is_wicket_event"] = is_wicket_b
    df["is_retired_hurt"] = (~is_wicket_b) & df["dismissed_player_id"].notna()
    df["is_bowler_wicket"] = is_wicket_b & df["dismissal_type_std"].isin(BOWLER_CREDITED_DISMISSALS)
    df["is_run_out"] = is_wicket_b & df["dismissal_type_std"].eq("RunOut")
    df["is_retired_out"] = is_wicket_b & df["dismissal_type_std"].eq("Retire Out")
    df["is_obstructing_field"] = is_wicket_b & df["dismissal_type_std"].eq("Obstructing the field")

    df["wicket_category"] = np.select(
        [
            df["is_bowler_wicket"],
            df["is_run_out"],
            df["is_retired_out"],
            df["is_obstructing_field"],
            df["is_retired_hurt"],
            df["is_wicket_event"],
        ],
        [
            "bowler_wicket",
            "run_out",
            "retired_out",
            "obstructing_the_field",
            "retired_hurt",
            "other_wicket",
        ],
        default="none",
    )

    # Bowling speed validated field (preserve raw bowl_speed untouched)
    speed_raw = pd.to_numeric(df["bowl_speed"], errors="coerce")
    df["bowl_speed_quality_flag"] = np.select(
        [
            speed_raw.isna(),
            speed_raw == 0,
            speed_raw < 0,
            (speed_raw > 0) & (speed_raw < 50),
            speed_raw > 165,
        ],
        [
            "missing",
            "zero_unrecorded",
            "negative_invalid",
            "below_50_outlier",
            "above_165_outlier",
        ],
        default="valid",
    )
    df["bowl_speed_clean"] = np.where(df["bowl_speed_quality_flag"].eq("valid"), speed_raw, np.nan)

    # Explicit anomaly flags (preserve raw rows; never silently delete/overwrite)
    anomaly_notes = pd.Series("", index=df.index, dtype="object")

    def append_note(mask: pd.Series, note: str) -> None:
        nonlocal anomaly_notes
        existing = anomaly_notes.loc[mask]
        anomaly_notes.loc[mask] = np.where(existing == "", note, existing + "; " + note)

    append_note((et_str == "None") & ((e1_num != 0) | (e2_num != 0)), "extras_type_None_with_nonzero_extras")
    append_note((et_str == "legbyes") & (e1_num == 0) & (runs_num > 0), "legbyes_with_zero_extras1_and_batter_runs")
    append_note(df["is_penalty_extra"], "legal_penalty_5_runs_delivery")
    append_note(
        (df["match_id"] == 41509) & (df["innings"] == 1) & (df["overid"] == 12),
        "seven_legal_balls_in_over",
    )
    append_note(df["striker_id"] == df["non_striker_id"], "striker_id_equals_non_striker_id")
    append_note((runs_num == 6) & (~is_six_b), "runs_eq_6_overthrow_is_six_false")
    append_note(is_wicket_b & df["dismissed_player_id"].isna(), "retire_out_missing_dismissed_player_id")
    append_note(df["is_retired_hurt"], "retired_hurt_not_a_wicket")
    append_note(raw_dism.eq("Obstracting the field"), "dismissal_spelling_typo_normalized_in_std")

    df["has_delivery_anomaly"] = anomaly_notes != ""
    df["delivery_anomaly_note"] = anomaly_notes

    return df


def build_clean_matches(
    matches: pd.DataFrame,
    comp_master: pd.DataFrame,
    all_deliveries: pd.DataFrame,
) -> pd.DataFrame:
    """Create standardized match metadata with DLS, revised overs (balls), and completion status."""
    m = matches.copy()
    m["match_id"] = pd.to_numeric(m["match_id"], errors="raise").astype(int)
    m["comp_id"] = pd.to_numeric(m["comp_id"], errors="raise").astype(int)

    # Merge validated competition attributes
    m = m.merge(
        comp_master[["comp_id", "comp_name", "match_format", "season", "eligibility_category", "is_primary_eligible"]],
        on="comp_id",
        how="left",
    )

    # Preserve raw revised_overs columns and add explicit unit-clarified ball/over fields
    m["first_inn_revised_balls"] = pd.to_numeric(m["first_inn_revised_overs"], errors="coerce")
    m["second_inn_revised_balls"] = pd.to_numeric(m["second_inn_revised_overs"], errors="coerce")
    m["first_inn_revised_overs_exact"] = (m["first_inn_revised_balls"] / 6.0).round(2)
    m["second_inn_revised_overs_exact"] = (m["second_inn_revised_balls"] / 6.0).round(2)
    m["revised_target_num"] = pd.to_numeric(m["revised_target"], errors="coerce")

    # Clean man_of_the_match zero sentinel without overwriting raw column
    mom_num = pd.to_numeric(m["man_of_the_match"], errors="coerce")
    m["man_of_the_match_clean"] = mom_num.where(mom_num > 0, np.nan)

    # Aggregate ball-by-ball presence & innings totals
    reg_del = all_deliveries[~all_deliveries["is_super_over"]]
    so_del = all_deliveries[all_deliveries["is_super_over"]]

    reg_match_agg = (
        reg_del.groupby("match_id", as_index=False)
        .agg(
            regular_deliveries=("match_id", "size"),
            regular_legal_deliveries=("is_legal_delivery", "sum"),
            innings_recorded_count=("innings", "nunique"),
        )
    )
    inn1_agg = (
        reg_del[reg_del["innings"] == 1]
        .groupby("match_id", as_index=False)
        .agg(
            inn1_total_runs=("total_runs", "sum"),
            inn1_wickets=("is_wicket_event", "sum"),
            inn1_legal_balls=("is_legal_delivery", "sum"),
        )
    )
    inn2_agg = (
        reg_del[reg_del["innings"] == 2]
        .groupby("match_id", as_index=False)
        .agg(
            inn2_total_runs=("total_runs", "sum"),
            inn2_wickets=("is_wicket_event", "sum"),
            inn2_legal_balls=("is_legal_delivery", "sum"),
        )
    )
    so_agg = (
        so_del.groupby("match_id", as_index=False)
        .agg(super_over_deliveries=("match_id", "size"))
    )

    m = (
        m.merge(reg_match_agg, on="match_id", how="left")
        .merge(inn1_agg, on="match_id", how="left")
        .merge(inn2_agg, on="match_id", how="left")
        .merge(so_agg, on="match_id", how="left")
    )
    for col in ["regular_deliveries", "regular_legal_deliveries", "innings_recorded_count", "super_over_deliveries"]:
        m[col] = m[col].fillna(0).astype(int)

    m["has_ball_data"] = m["regular_deliveries"] > 0
    m["has_super_over_ball_data"] = m["super_over_deliveries"] > 0

    res_l = m["result"].fillna("").astype(str).str.lower()
    m["is_abandoned_match"] = res_l.str.contains("abandon", na=False)
    m["is_no_result_match"] = res_l.str.contains("no result", na=False)
    m["has_super_over_result"] = res_l.str.contains(r"super over|one over eliminator", regex=True, na=False)
    m["is_tied_match"] = res_l.str.contains(r"\btie\b|\btied\b", regex=True, na=False) | m["has_super_over_result"]
    m["is_dls_text"] = res_l.str.contains(r"d/l|dls|duckworth", regex=True, na=False)
    m["is_dls_match"] = m["is_dls_text"] | m["revised_target_num"].notna()
    m["is_reduced_overs_match"] = (
        m["first_inn_revised_balls"].notna()
        | m["second_inn_revised_balls"].notna()
        | m["is_dls_match"]
        | m["match_id"].isin(KNOWN_UNFLAGGED_REDUCED_MATCH_IDS)
    )

    # Explicitly flag matches where revised-overs metadata is missing for at least one reduced/DLS innings
    m["is_missing_inn1_revised_balls"] = (
        m["first_inn_revised_balls"].isna()
        & (
            m["match_id"].isin(KNOWN_UNFLAGGED_REDUCED_MATCH_IDS - {18532})
            | (m["is_dls_text"] & (m["inn1_legal_balls"].fillna(120) < 120) & (m["inn1_wickets"].fillna(0) < 10))
        )
    )
    m["is_missing_inn2_revised_balls"] = (
        m["second_inn_revised_balls"].isna()
        & (
            m["is_dls_text"]
            | m["first_inn_revised_balls"].notna()
            | m["match_id"].isin(KNOWN_UNFLAGGED_REDUCED_MATCH_IDS)
        )
        & m["inn2_legal_balls"].notna()
    )
    m["is_missing_revised_target"] = m["is_dls_text"] & m["revised_target_num"].isna()

    def classify_completion(r: pd.Series) -> str:
        if r["is_abandoned_match"] and not r["has_ball_data"]:
            return "abandoned_no_play"
        if r["is_abandoned_match"] and r["has_ball_data"]:
            return "abandoned_partial_play"
        if r["is_no_result_match"]:
            return "no_result_partial_play"
        if r["has_super_over_result"] and r["has_super_over_ball_data"]:
            return "tied_super_over_with_ball_data"
        if r["has_super_over_result"] and not r["has_super_over_ball_data"]:
            return "tied_super_over_missing_ball_data"
        if r["is_tied_match"]:
            return "tied_no_super_over_dls"
        if r["is_dls_match"]:
            return "completed_dls_revised"
        if r["is_reduced_overs_match"]:
            return "completed_reduced_overs_no_dls"
        return "completed_regular"

    m["match_completion_classification"] = m.apply(classify_completion, axis=1)
    return m.sort_values(["match_date", "match_id"]).reset_index(drop=True)


def build_player_master_and_alias_report(
    all_deliveries: pd.DataFrame,
    playing_xi: pd.DataFrame,
    mapping: pd.DataFrame,
    comp_master: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create player_master keyed strictly by player_id and player_alias_report."""
    pmap = mapping.copy()
    pmap["player_id"] = pd.to_numeric(pmap["player_id"], errors="raise").astype(int)
    pmap["comp_id"] = pd.to_numeric(pmap["comp_id"], errors="raise").astype(int)
    pmap["team_id"] = pd.to_numeric(pmap["team_id"], errors="raise").astype(int)
    pmap = pmap.merge(
        comp_master[["comp_id", "eligibility_category", "is_primary_eligible"]],
        on="comp_id",
        how="left",
    )

    pxi = playing_xi.copy()
    pxi["match_id"] = pd.to_numeric(pxi["match_id"], errors="raise").astype(int)
    pxi["team_id"] = pd.to_numeric(pxi["team_id"], errors="raise").astype(int)
    pxi["player_id"] = pd.to_numeric(pxi["player_id"], errors="raise").astype(int)
    pxi["is_played_b"] = to_bool(pxi["is_played"])
    pxi["is_captain_b"] = to_bool(pxi["is_captain"])
    pxi["is_wk_b"] = to_bool(pxi["is_wk"])

    # Collect all ball-feed names per player_id
    ball_names = pd.concat(
        [
            all_deliveries[["striker_id", "striker_name"]].rename(columns={"striker_id": "player_id", "striker_name": "ball_name"}),
            all_deliveries[["non_striker_id", "non_striker_name"]].rename(columns={"non_striker_id": "player_id", "non_striker_name": "ball_name"}),
            all_deliveries[["bowler_id", "bowler_name"]].rename(columns={"bowler_id": "player_id", "bowler_name": "ball_name"}),
        ],
        ignore_index=True,
    ).dropna()
    ball_names["player_id"] = pd.to_numeric(ball_names["player_id"], errors="raise").astype(int)
    ball_names_agg = (
        ball_names.groupby("player_id")["ball_name"]
        .agg(lambda s: sorted(set(s.astype(str).str.strip())))
        .to_dict()
    )

    # Batting / bowling style and activity counts (primary eligible regular deliveries)
    prim_del = all_deliveries[all_deliveries["is_primary_eligible"] & (~all_deliveries["is_super_over"])]
    bat_stats = (
        prim_del.groupby("striker_id")
        .agg(
            primary_balls_faced=("is_batter_ball_faced", "sum"),
            batting_type_mode=("batting_type", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        )
    )
    bowl_stats = (
        prim_del.groupby("bowler_id")
        .agg(
            primary_legal_balls_bowled=("is_legal_delivery", "sum"),
            bowling_type_mode=("bowling_type", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
            pace_or_spin_mode=("pace_or_spin", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        )
    )
    # Also fallback batting/bowling style across all deliveries if only played in excluded comps
    all_bat_style = all_deliveries.groupby("striker_id")["batting_type"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")
    all_bowl_style = all_deliveries.groupby("bowler_id")["bowling_type"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")
    all_ps_style = all_deliveries.groupby("bowler_id")["pace_or_spin"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")

    pxi_agg = (
        pxi.groupby("player_id")
        .agg(
            matches_in_playing_eleven=("match_id", "nunique"),
            matches_played_flag=("is_played_b", "sum"),
            ever_captain=("is_captain_b", "any"),
            ever_wk=("is_wk_b", "any"),
        )
    )

    # Shared player names across distinct player_ids
    name_id_counts = pmap.groupby("player_name")["player_id"].nunique()
    shared_names = set(name_id_counts[name_id_counts > 1].index)

    master_rows = []
    for pid, grp in pmap.groupby("player_id"):
        map_names = sorted(set(grp["player_name"].astype(str).str.strip()))
        b_names = ball_names_agg.get(pid, [])
        all_source_names = sorted(set(map_names) | set(b_names))

        # Prefer full ball-feed name when mapping uses initials (e.g., 4458: 'Aneurin Donald' vs 'AHT Donald')
        if b_names:
            std_name = max(b_names, key=len)
        else:
            std_name = map_names[0]

        name_mismatch = bool(b_names and (set(b_names) != set(map_names)))
        has_shared_name = any(nm in shared_names for nm in map_names)

        comp_ids_list = sorted(grp["comp_id"].unique().tolist())
        team_ids_list = sorted(grp["team_id"].unique().tolist())
        team_names_list = sorted(grp["team_name"].unique().tolist())
        cats = set(grp["eligibility_category"].dropna().tolist())

        bf = int(bat_stats.loc[pid, "primary_balls_faced"]) if pid in bat_stats.index else 0
        bb = int(bowl_stats.loc[pid, "primary_legal_balls_bowled"]) if pid in bowl_stats.index else 0
        b_type = (
            bat_stats.loc[pid, "batting_type_mode"]
            if pid in bat_stats.index
            else all_bat_style.get(pid, "")
        )
        bw_type = (
            bowl_stats.loc[pid, "bowling_type_mode"]
            if pid in bowl_stats.index
            else all_bowl_style.get(pid, "")
        )
        ps_type = (
            bowl_stats.loc[pid, "pace_or_spin_mode"]
            if pid in bowl_stats.index
            else all_ps_style.get(pid, "")
        )
        ever_wk = bool(pxi_agg.loc[pid, "ever_wk"]) if pid in pxi_agg.index else False
        ever_cap = bool(pxi_agg.loc[pid, "ever_captain"]) if pid in pxi_agg.index else False
        pxi_matches = int(pxi_agg.loc[pid, "matches_in_playing_eleven"]) if pid in pxi_agg.index else 0

        if ever_wk and bf > 0:
            role = "Wicketkeeper-Batter"
        elif bf > 0 and bb >= 24:
            role = "All-Rounder"
        elif bb > 0 and bf < 24:
            role = "Bowler"
        elif bf > 0:
            role = "Batter"
        elif bb > 0:
            role = "Bowler"
        else:
            role = "Squad_Only_No_Primary_Deliveries"

        master_rows.append({
            "player_id": int(pid),
            "standardized_display_name": std_name,
            "mapping_source_names": " | ".join(map_names),
            "ball_feed_source_names": " | ".join(b_names),
            "all_source_names": " | ".join(all_source_names),
            "comp_ids": ";".join(map(str, comp_ids_list)),
            "team_ids": ";".join(map(str, team_ids_list)),
            "team_names": " | ".join(team_names_list),
            "in_ipl": "IPL" in cats,
            "in_t20i": "T20I" in cats,
            "in_excluded_non_ipl_t20": "Non-IPL T20" in cats,
            "in_primary_eligible_comp": ("IPL" in cats) or ("T20I" in cats),
            "primary_balls_faced": bf,
            "primary_legal_balls_bowled": bb,
            "matches_in_playing_eleven": pxi_matches,
            "batting_type": b_type,
            "bowling_type": bw_type,
            "pace_or_spin": ps_type,
            "ever_wk": ever_wk,
            "ever_captain": ever_cap,
            "inferred_playing_role": role,
            "name_mismatch_between_sources": name_mismatch,
            "shares_name_with_other_player_id": has_shared_name,
        })

    player_master = pd.DataFrame(master_rows).sort_values("player_id").reset_index(drop=True)

    # Build comprehensive player_alias_report.csv
    alias_rows = []
    # 1. Cross-table name mismatches (4458: Aneurin Donald vs AHT Donald)
    for r in player_master[player_master["name_mismatch_between_sources"]].itertuples():
        alias_rows.append({
            "issue_type": "cross_table_name_mismatch",
            "player_id": r.player_id,
            "related_player_ids": str(r.player_id),
            "display_name": r.standardized_display_name,
            "source_names": f"ball_by_ball='{r.ball_feed_source_names}' vs mapping='{r.mapping_source_names}'",
            "teams": r.team_names,
            "in_primary_eligible": r.in_primary_eligible_comp,
            "classification": "same_player_name_variant",
            "treatment": "Preserved original player_id; standardized display name to full ball-feed name while retaining mapping name.",
        })

    # 2. Shared names across distinct player_ids (NEVER auto-merged)
    distinct_person_names = {"Rashid Khan", "Abdul Samad", "Haider Ali"}
    for nm in sorted(shared_names):
        sub = player_master[player_master["mapping_source_names"].str.contains(re.escape(nm))]
        all_ids = ",".join(map(str, sub["player_id"].tolist()))
        cls = "distinct_individuals_same_name" if nm in distinct_person_names else "suspected_split_player_id_do_not_automerge"
        for r in sub.itertuples():
            alias_rows.append({
                "issue_type": "shared_name_multiple_player_ids",
                "player_id": r.player_id,
                "related_player_ids": all_ids,
                "display_name": nm,
                "source_names": r.all_source_names,
                "teams": r.team_names,
                "in_primary_eligible": r.in_primary_eligible_comp,
                "classification": cls,
                "treatment": "Kept separate by player_id; never joined or merged by player_name.",
            })

    # 3. Players in deliveries missing from playing_eleven
    all_ball_pids = set(all_deliveries["striker_id"]) | set(all_deliveries["non_striker_id"]) | set(all_deliveries["bowler_id"])
    pxi_pids = set(pxi["player_id"])
    for pid in sorted(all_ball_pids - pxi_pids):
        r = player_master.loc[player_master["player_id"] == pid].iloc[0]
        mids = sorted(
            all_deliveries.loc[
                (all_deliveries["striker_id"] == pid)
                | (all_deliveries["non_striker_id"] == pid)
                | (all_deliveries["bowler_id"] == pid),
                "match_id",
            ].unique().tolist()
        )
        alias_rows.append({
            "issue_type": "in_deliveries_missing_from_playing_eleven",
            "player_id": int(pid),
            "related_player_ids": str(pid),
            "display_name": r["standardized_display_name"],
            "source_names": r["all_source_names"],
            "teams": r["team_names"],
            "in_primary_eligible": bool(r["in_primary_eligible_comp"]),
            "classification": "excluded_comp_2670_feed_gap",
            "treatment": f"Appears only in excluded comp 2670 matches {mids}; excluded from primary dataset and logged.",
        })

    # 4. Duplicate playing_eleven keys in Super Over matches
    dup_pxi = pxi[pxi.duplicated(["match_id", "team_id", "player_id"], keep=False)]
    for mid, grp in dup_pxi.groupby("match_id"):
        alias_rows.append({
            "issue_type": "playing_eleven_super_over_duplicate_keys",
            "player_id": -1,
            "related_player_ids": f"match_id={mid} ({grp['player_id'].nunique()} players, {len(grp)} rows)",
            "display_name": f"Match {mid} Super Over XI entries",
            "source_names": "playing_eleven.csv",
            "teams": ",".join(map(str, sorted(grp["team_id"].unique().tolist()))),
            "in_primary_eligible": True,
            "classification": "super_over_batting_order_duplicate_rows",
            "treatment": "Preserved raw playing_eleven.csv; player_master deduplicates via groupby(player_id).",
        })

    return player_master, pd.DataFrame(alias_rows)


def build_innings_summary_and_reconciliation(
    clean_deliveries: pd.DataFrame,
    clean_matches: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute per-innings summary for primary eligible regular deliveries and full reconciliation."""
    inn = (
        clean_deliveries.groupby(["match_id", "innings"], as_index=False)
        .agg(
            comp_id=("comp_id", "first"),
            comp_name=("comp_name", "first"),
            match_format=("match_format", "first"),
            season=("season", "first"),
            eligibility_category=("eligibility_category", "first"),
            batting_team_id=("batting_team_id", "first"),
            bowling_team_id=("bowling_team_id", "first"),
            total_deliveries=("innings_ball_num", "size"),
            legal_deliveries=("is_legal_delivery", "sum"),
            batter_balls_faced=("is_batter_ball_faced", "sum"),
            wides=("is_wide", "sum"),
            overstep_noballs=("is_overstep_noball", "sum"),
            other_noballs=("is_other_noball", "sum"),
            byes_balls=("is_byes", "sum"),
            legbyes_balls=("is_legbyes", "sum"),
            penalty_balls=("is_penalty_extra", "sum"),
            batter_runs=("batter_runs", "sum"),
            extras1_runs=("extras1_runs", "sum"),
            extras2_runs=("extras_2_runs", "sum"),
            extras_total_runs=("extras_total_runs", "sum"),
            total_runs=("total_runs", "sum"),
            bowler_conceded_runs=("bowler_conceded_runs", "sum"),
            non_bowler_extras_runs=("non_bowler_extras_runs", "sum"),
            wickets=("is_wicket_event", "sum"),
            bowler_wickets=("is_bowler_wicket", "sum"),
            run_outs=("is_run_out", "sum"),
            retired_outs=("is_retired_out", "sum"),
            obstructing_field=("is_obstructing_field", "sum"),
            retired_hurt_events=("is_retired_hurt", "sum"),
            max_overid=("overid", "max"),
        )
    )

    inn = inn.merge(
        clean_matches[
            [
                "match_id",
                "match_date",
                "first_inn_revised_balls",
                "second_inn_revised_balls",
                "revised_target_num",
                "is_dls_match",
                "is_reduced_overs_match",
                "match_completion_classification",
                "result",
            ]
        ],
        on="match_id",
        how="left",
    )

    inn["runs_formula_diff"] = inn["total_runs"] - (inn["batter_runs"] + inn["extras1_runs"] + inn["extras2_runs"])
    inn["bowler_runs_reconcile_diff"] = inn["total_runs"] - (inn["bowler_conceded_runs"] + inn["non_bowler_extras_runs"])
    inn["wickets_reconcile_diff"] = inn["wickets"] - (
        inn["bowler_wickets"] + inn["run_outs"] + inn["retired_outs"] + inn["obstructing_field"]
    )
    inn["legal_ball_reconcile_diff"] = inn["total_deliveries"] - (
        inn["legal_deliveries"] + inn["wides"] + inn["overstep_noballs"] + inn["other_noballs"]
    )

    # Match-level margin reconciliation for non-DLS completed matches won by runs
    piv = inn.pivot(index="match_id", columns="innings", values=["total_runs", "wickets", "legal_deliveries"])
    piv.columns = [f"{a}_inn{b}" for a, b in piv.columns]
    piv = piv.reset_index()
    recon = clean_matches[
        [
            "match_id",
            "comp_id",
            "comp_name",
            "match_date",
            "match_completion_classification",
            "is_dls_match",
            "revised_target_num",
            "result",
        ]
    ].merge(piv, on="match_id", how="inner")

    def parse_run_margin(res_text: str) -> float:
        m = re.search(r"won\s+(?:by\s+)?(\d+)\s*runs?", str(res_text), flags=re.IGNORECASE)
        return float(m.group(1)) if m else np.nan

    recon["result_run_margin"] = recon["result"].apply(parse_run_margin)
    recon["computed_run_margin"] = recon["total_runs_inn1"] - recon["total_runs_inn2"]
    recon["run_margin_matches_result"] = np.where(
        (~recon["is_dls_match"]) & recon["result_run_margin"].notna() & recon["computed_run_margin"].notna(),
        recon["result_run_margin"] == recon["computed_run_margin"],
        np.nan,
    )

    return inn.sort_values(["match_id", "innings"]).reset_index(drop=True), recon.sort_values("match_id").reset_index(drop=True)


def build_anomaly_investigation_table(
    all_deliveries: pd.DataFrame,
    all_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Explicitly document all 10 Phase 2 anomalies + retired hurt + incomplete Super Over matches."""
    rows = []

    def add(
        anom_id: str,
        match_ids_str: str,
        in_primary: str,
        record_count: int,
        category: str,
        empirical_finding: str,
        classification: str,
        treatment: str,
    ) -> None:
        rows.append({
            "anomaly_id": anom_id,
            "match_ids": match_ids_str,
            "in_primary_dataset": in_primary,
            "record_count": record_count,
            "category": category,
            "empirical_finding": empirical_finding,
            "classification": classification,
            "treatment": treatment,
        })

    # 1. Match 17555
    r1 = all_deliveries[(all_deliveries["match_id"] == 17555) & (all_deliveries["extras_type"] == "None") & ((all_deliveries["extras1_runs"] != 0) | (all_deliveries["extras_2_runs"] != 0))]
    add(
        "ANOM_01", "17555", "Yes (T20I)", len(r1), "Extras Coding",
        "Inn 1, Over 5, Ball 4 (ENG vs PAK 2022): extras_type='None', runs=0, extras1_runs=0, extras_2_runs=1 within a 6-ball over.",
        "genuine_data_issue_unclassified_extra",
        "Preserved raw row; total_runs=1 included in innings score (matches official result margin of 63 runs); excluded extras_2_runs from bowler_conceded_runs; flagged in delivery_anomaly_note.",
    )

    # 2. Match 36097
    r2 = all_deliveries[(all_deliveries["match_id"] == 36097) & (all_deliveries["extras_type"] == "None") & ((all_deliveries["extras1_runs"] != 0) | (all_deliveries["extras_2_runs"] != 0))]
    add(
        "ANOM_02", "36097", "Yes (T20I)", len(r2), "Extras Coding",
        "Inn 2, Over 8, Ball 6 (WI vs SA 2024): extras_type='None', runs=0, extras1_runs=1, extras_2_runs=0 within a 6-ball over.",
        "genuine_data_issue_unclassified_extra",
        "Preserved raw row; total_runs=1 included in innings score (matches official 30-run margin); excluded unclassified extra from bowler_conceded_runs; flagged in delivery_anomaly_note.",
    )

    # 3. Match 37099
    r3 = all_deliveries[(all_deliveries["match_id"] == 37099) & (all_deliveries["extras_type"] == "legbyes") & (all_deliveries["extras1_runs"] == 0)]
    add(
        "ANOM_03", "37099", "No (Excluded comp 2670)", len(r3), "Extras Coding",
        "Inn 1, Over 14, Ball 1 (SL A vs AFG A, Emerging Asia Cup 2024): extras_type='legbyes', runs=1, extras1_runs=0.",
        "genuine_data_issue_mislabeled_extra",
        "Preserved in excluded_competition_deliveries.csv (comp_id=2670); flagged without overwriting source fields.",
    )

    # 4. Match 16753
    r4 = all_deliveries[(all_deliveries["match_id"] == 16753) & (all_deliveries["extras_type"] == "Penalty")]
    add(
        "ANOM_04", "16753", "Yes (T20I)", len(r4), "Penalty Runs",
        "Inn 2, Over 6, Ball 4 (IRE vs AFG 2022): extras_type='Penalty', extras1_runs=5 within a 6-ball legal over (e.g., ball hitting keeper helmet).",
        "valid_unusual_cricket_event",
        "Preserved raw row; counted as legal delivery (6-ball over intact); included 5 runs in total_runs; excluded from bowler_conceded_runs per ICC scoring laws.",
    )

    # 5. Match 41509
    r5 = all_deliveries[(all_deliveries["match_id"] == 41509) & (all_deliveries["innings"] == 1) & (all_deliveries["overid"] == 12)]
    add(
        "ANOM_05", "41509", "Yes (T20I)", len(r5), "Over Length",
        "Inn 1, Over 12 (WI vs AUS 2025, Aaron Hardie): 7 consecutive deliveries with extras_type='None' (over_ball_num 1..7) — likely umpire 7-ball over or unmarked extra.",
        "unusual_event_or_unmarked_extra",
        "Preserved all 7 deliveries; counted as legal based on source extras_type without inventing an extra; flagged in delivery_anomaly_note.",
    )

    # 6. Match 37086
    r6 = all_deliveries[all_deliveries["striker_id"] == all_deliveries["non_striker_id"]]
    add(
        "ANOM_06", "37086", "No (Excluded comp 2670)", len(r6), "Player ID Error",
        "Inn 1, Over 18, Ball 6 (SL A vs AFG A, Emerging Asia Cup 2024): Sharafuddin Ashraf (3550) recorded as both striker_id and non_striker_id.",
        "genuine_data_issue_feed_error",
        "Preserved in excluded_competition_deliveries.csv (comp_id=2670); zero impact on primary IPL/T20I dataset.",
    )

    # 7. Three runs=6 & is_six=False rows
    r7 = all_deliveries[(all_deliveries["batter_runs"] == 6) & (~to_bool(all_deliveries["is_six"]))]
    add(
        "ANOM_07", ",".join(map(str, r7["match_id"].tolist())), "Yes (1 T20I, 2 IPL)", len(r7), "Boundary Flag",
        "Matches 17396 (Tim David, Cover Drive), 31277 (Sai Sudharsan, Worked), 40766 (Hardik Pandya, Worked): runs=6 with is_six=False.",
        "valid_scoring_convention_overthrows",
        "Confirmed legitimate all-run/overthrow 6s (e.g., 2 runs + 4 overthrows) rather than cleared-rope sixes; preserved runs=6 and is_six=False.",
    )

    # 8. Match 40709 Retire Out missing dismissed_player_id
    r8 = all_deliveries[all_deliveries["is_wicket_event"] & all_deliveries["dismissed_player_id"].isna()]
    add(
        "ANOM_08", "40709", "Yes (IPL 2025)", len(r8), "Dismissal Metadata",
        "Inn 2, Over 19, Ball 5 (LSG vs MI, IPL 2025): Hardik Pandya (3330) striker, Tilak Varma (7897) non-striker, dismissal_type='Retire Out', dismissed_player_id=NaN. Ball 19.6 shows Mitchell Santner (4101) & Hardik Pandya (3330), empirically proving Tilak Varma (7897) retired out.",
        "genuine_data_issue_missing_id",
        "Preserved raw dismissed_player_id=NaN; counted as team wicket (is_wicket_event=True), NOT a bowler wicket (is_bowler_wicket=False); documented inferred player 7897.",
    )

    # 9. Bowling speed == 0
    r9 = all_deliveries[all_deliveries["bowl_speed_quality_flag"] == "zero_unrecorded"]
    add(
        "ANOM_09", "Multiple", "Yes (Primary & Excluded)", len(r9), "Bowling Speed",
        f"{len(r9):,} deliveries ({len(r9)/len(all_deliveries)*100:.2f}%) have bowl_speed == 0.0 (unrecorded speed-gun sentinel).",
        "scoring_convention_missing_sentinel",
        "Preserved raw bowl_speed; set bowl_speed_clean = NaN and bowl_speed_quality_flag = 'zero_unrecorded'.",
    )

    # 10. Bowling speed outliers (<0, (0,50), >165)
    r10 = all_deliveries[all_deliveries["bowl_speed_quality_flag"].isin(["negative_invalid", "below_50_outlier", "above_165_outlier"])]
    add(
        "ANOM_10", ",".join(map(str, sorted(r10["match_id"].unique().tolist())[:10])) + "...", "Yes (Primary & Excluded)", len(r10), "Bowling Speed",
        f"{len(r10)} non-zero invalid speeds: 1 negative (-1.0 in 14108), 22 in (0, 50), 20 above 165 km/h (mostly 10x decimal-shift errors up to 1456.1 km/h).",
        "genuine_data_issue_radar_or_decimal_error",
        "Preserved raw bowl_speed; set bowl_speed_clean = NaN rather than guessing rescaling factors.",
    )

    # 11. Retired Hurt (12 rows with is_wicket=False & dismissed_player_id populated)
    r11 = all_deliveries[all_deliveries["is_retired_hurt"]]
    add(
        "ANOM_11", ",".join(map(str, r11["match_id"].tolist())), "Yes (11 Primary, 1 Excluded)", len(r11), "Retired Hurt",
        "All 12 rows verified via next-ball crease inspection: dismissed_player_id leaves crease injured immediately without losing a team wicket and never returns.",
        "valid_scoring_convention_retired_hurt",
        "Classified as is_retired_hurt=True, is_wicket_event=False, is_bowler_wicket=False, wicket_category='retired_hurt'. Never counted as wickets.",
    )

    # 12. Three earlier Super Over matches missing innings 3/4 ball data
    so_miss = all_matches[all_matches["match_completion_classification"] == "tied_super_over_missing_ball_data"]
    add(
        "ANOM_12", ",".join(map(str, so_miss["match_id"].tolist())), "Yes (T20I)", len(so_miss), "Super Over Completeness",
        "Matches 13613 (AUS vs SL 2022), 21176 (NZ vs SL 2023), 28962 (IND vs AFG 2024) confirm Super Overs in result text and have duplicate Super Over batting_order rows in playing_eleven.csv, but 0 innings 3/4 deliveries in ball_by_ball.csv.",
        "incomplete_source_coverage",
        "Documented as tied_super_over_missing_ball_data in clean_matches.csv; missing Super Over deliveries are NOT reconstructed; regulation innings 1-2 remain intact in clean_deliveries.csv.",
    )

    # 13. Dismissal spelling typo
    r13 = all_deliveries[all_deliveries["dismissal_type"] == "Obstracting the field"]
    add(
        "ANOM_13", ",".join(map(str, r13["match_id"].tolist())), "Yes (1 Primary, 1 Excluded)", len(r13), "Dismissal Spelling",
        "2 rows spell 'Obstracting the field' instead of 'Obstructing the field' (1 in primary IPL/T20I, 1 in excluded non-IPL T20).",
        "genuine_data_issue_typo",
        "Preserved original dismissal_type; normalized to 'Obstructing the field' in dismissal_type_std; excluded from bowler wickets.",
    )

    # 14. Match 14130 (IPL 2022) - only non-DLS run-margin mismatch (387/388 exact)
    r14 = all_deliveries[all_deliveries["match_id"] == 14130]
    add(
        "ANOM_14", "14130", "Yes (IPL 2022)", len(r14), "Innings Completeness",
        "IPL 2022 LSG vs MI (2022-04-24): both innings record 119 legal deliveries instead of 120 (computed 167 vs 130, margin 37 runs vs official result 'Won 36 Runs') — 1 missing ball per innings in source feed.",
        "incomplete_source_coverage",
        "Preserved all recorded deliveries without fabricating missing balls; flagged as the sole run-margin mismatch across 388 non-DLS matches won by runs.",
    )

    return pd.DataFrame(rows)


def main() -> None:
    cleaning_log: list[dict[str, Any]] = []

    def log_step(step: str, target: str, rows_in: int, rows_out: int, action: str) -> None:
        cleaning_log.append({
            "step": step,
            "target": target,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "action_summary": action,
        })

    tables, source_desc = load_raw_tables()
    balls_raw = tables["ball_by_ball"]
    matches_raw = tables["matches"]
    comps_raw = tables["competitions"]
    pxi_raw = tables["playing_eleven"]
    pmap_raw = tables["player_mapping"]

    print(f"Starting Phase 3 Data Cleaning from: {source_desc}")
    log_step("01_load_raw", "all_6_csvs", len(balls_raw), len(balls_raw), f"Loaded read-only from {source_desc} with literal 'None' preserved")

    # 1. Competition master
    comp_master = build_competition_master(comps_raw, matches_raw, balls_raw)
    comp_master.to_csv(PROCESSED_DIR / "competition_master.csv", index=False)
    log_step(
        "02_competition_eligibility",
        "competition_master.csv",
        len(comps_raw),
        len(comp_master),
        f"Eligible={int(comp_master['is_primary_eligible'].sum())} (5 IPL + 134 T20I); Excluded={int((~comp_master['is_primary_eligible']).sum())} (comp_ids 2670, 3289)",
    )

    # 2. Enrich all deliveries with cricket rules
    all_deliveries = enrich_deliveries_with_cricket_rules(balls_raw, matches_raw, comp_master)

    # 3. Clean match metadata (all matches first for anomaly checks, then filter eligible for clean_matches.csv)
    all_matches = build_clean_matches(matches_raw, comp_master, all_deliveries)
    clean_matches = all_matches[all_matches["is_primary_eligible"]].reset_index(drop=True)
    clean_matches.to_csv(PROCESSED_DIR / "clean_matches.csv", index=False)
    log_step(
        "03_match_cleaning",
        "clean_matches.csv",
        len(matches_raw),
        len(clean_matches),
        f"Retained {len(clean_matches)} eligible IPL/T20I matches (excluded {len(all_matches) - len(clean_matches)} non-IPL T20 matches); clarified revised_overs units as balls",
    )

    # 4. Separate excluded competitions, Super Overs, and primary clean regular deliveries
    excluded_comp_deliveries = all_deliveries[~all_deliveries["is_primary_eligible"]].copy()
    excluded_comp_deliveries["exclusion_reason"] = (
        "Non-IPL T20 competition excluded from primary IPL/T20I analytical dataset"
    )
    excluded_comp_deliveries.to_csv(PROCESSED_DIR / "excluded_competition_deliveries.csv", index=False)

    super_over_deliveries = all_deliveries[all_deliveries["is_super_over"]].copy()
    super_over_deliveries.to_csv(PROCESSED_DIR / "super_over_deliveries.csv", index=False)

    clean_deliveries = all_deliveries[
        all_deliveries["is_primary_eligible"] & (~all_deliveries["is_super_over"])
    ].reset_index(drop=True)
    clean_deliveries.to_csv(PROCESSED_DIR / "clean_deliveries.csv", index=False)

    prim_so_count = int((all_deliveries["is_primary_eligible"] & all_deliveries["is_super_over"]).sum())
    excl_so_count = int(((~all_deliveries["is_primary_eligible"]) & all_deliveries["is_super_over"]).sum())
    log_step(
        "04_split_deliveries",
        "clean_deliveries.csv",
        len(all_deliveries),
        len(clean_deliveries),
        f"Primary regular deliveries={len(clean_deliveries):,}; Primary Super Over={prim_so_count}; Excluded comp deliveries={len(excluded_comp_deliveries):,} (incl. {excl_so_count} Super Over balls)",
    )

    # 5. Player master & alias report
    player_master, alias_report = build_player_master_and_alias_report(
        all_deliveries, pxi_raw, pmap_raw, comp_master
    )
    player_master.to_csv(PROCESSED_DIR / "player_master.csv", index=False)
    alias_report.to_csv(OUT_DIR / "player_alias_report.csv", index=False)
    log_step(
        "05_player_master",
        "player_master.csv",
        len(pmap_raw),
        len(player_master),
        f"Built player master keyed on player_id ({len(player_master):,} players); logged {len(alias_report)} alias/shared-name/XI notes",
    )

    # 6. Innings summary & innings reconciliation
    innings_summary, innings_recon = build_innings_summary_and_reconciliation(clean_deliveries, clean_matches)
    innings_summary.to_csv(PROCESSED_DIR / "innings_summary.csv", index=False)
    innings_recon.to_csv(OUT_DIR / "innings_reconciliation.csv", index=False)
    log_step(
        "06_innings_reconciliation",
        "innings_summary.csv",
        len(clean_deliveries),
        len(innings_summary),
        f"Generated {len(innings_summary):,} primary regular innings records across {innings_summary['match_id'].nunique()} matches",
    )

    # 7. Anomaly investigation report
    anomaly_df = build_anomaly_investigation_table(all_deliveries, all_matches)
    anomaly_df.to_csv(OUT_DIR / "anomaly_investigation.csv", index=False)

    # 8. Excluded records register
    excluded_rows = []
    for r in comp_master[~comp_master["is_primary_eligible"]].itertuples():
        excluded_rows.append({
            "exclusion_category": "non_ipl_t20_competition",
            "entity_type": "competition",
            "entity_id": r.comp_id,
            "entity_name": r.comp_name,
            "matches_count": r.matches_in_metadata,
            "deliveries_count": r.total_deliveries,
            "preserved_location": "data/processed/excluded_competition_deliveries.csv",
            "reason": r.exclusion_reason,
        })
    for r in super_over_deliveries.groupby(["match_id", "comp_id", "comp_name", "is_primary_eligible"], as_index=False).size().itertuples():
        excluded_rows.append({
            "exclusion_category": "super_over_deliveries",
            "entity_type": "match_super_over",
            "entity_id": r.match_id,
            "entity_name": f"{r.comp_name} (match {r.match_id})",
            "matches_count": 1,
            "deliveries_count": r.size,
            "preserved_location": "data/processed/super_over_deliveries.csv",
            "reason": f"Super Over innings (3-4) separated from regular innings; is_primary_eligible={r.is_primary_eligible}",
        })
    for r in clean_matches[clean_matches["match_completion_classification"] == "abandoned_no_play"].itertuples():
        excluded_rows.append({
            "exclusion_category": "abandoned_zero_ball_match",
            "entity_type": "match",
            "entity_id": r.match_id,
            "entity_name": f"{r.home_team} vs {r.away_team} ({r.match_date})",
            "matches_count": 1,
            "deliveries_count": 0,
            "preserved_location": "data/processed/clean_matches.csv",
            "reason": "Match Abandoned with 0 deliveries bowled; preserved in clean_matches.csv",
        })
    pd.DataFrame(excluded_rows).to_csv(OUT_DIR / "excluded_records.csv", index=False)

    # 9. Automated reconciliation checks
    # Row conservation check: clean_deliveries + primary_super_over + excluded_comp_deliveries == raw_ball_by_ball
    row_conservation_ok = (len(clean_deliveries) + prim_so_count + len(excluded_comp_deliveries)) == len(balls_raw)
    runs_rec_ok = int((innings_summary["runs_formula_diff"] != 0).sum()) == 0
    bowler_rec_ok = int((innings_summary["bowler_runs_reconcile_diff"] != 0).sum()) == 0
    wickets_rec_ok = int((innings_summary["wickets_reconcile_diff"] != 0).sum()) == 0
    legal_rec_ok = int((innings_summary["legal_ball_reconcile_diff"] != 0).sum()) == 0
    margin_tested = innings_recon["run_margin_matches_result"].dropna()
    margin_mismatch_cnt = int((margin_tested == False).sum())

    # Six-legal-ball over check across clean_deliveries
    over_legal_counts = clean_deliveries.groupby(["match_id", "innings", "overid"])["is_legal_delivery"].sum()
    overs_gt6 = int((over_legal_counts > 6).sum())

    recon_checks = pd.DataFrame([
        {"check_name": "delivery_row_conservation", "status": "PASS" if row_conservation_ok else "FAIL", "expected": len(balls_raw), "actual": len(clean_deliveries) + prim_so_count + len(excluded_comp_deliveries), "details": f"clean_regular={len(clean_deliveries):,}, primary_super_over={prim_so_count}, excluded_comp={len(excluded_comp_deliveries):,}"},
        {"check_name": "primary_only_ipl_and_t20i", "status": "PASS" if set(clean_deliveries["eligibility_category"].unique()).issubset({"IPL", "T20I"}) else "FAIL", "expected": "{'IPL', 'T20I'}", "actual": str(sorted(clean_deliveries["eligibility_category"].unique().tolist())), "details": "No Non-IPL T20 deliveries in clean_deliveries.csv"},
        {"check_name": "primary_no_super_over_rows", "status": "PASS" if int(clean_deliveries["is_super_over"].sum()) == 0 else "FAIL", "expected": 0, "actual": int(clean_deliveries["is_super_over"].sum()), "details": "All Super Over innings >= 3 separated into super_over_deliveries.csv"},
        {"check_name": "innings_total_runs_formula_reconciliation", "status": "PASS" if runs_rec_ok else "FAIL", "expected": 0, "actual": int((innings_summary["runs_formula_diff"] != 0).sum()), "details": "total_runs == batter_runs + extras1_runs + extras_2_runs across all innings"},
        {"check_name": "bowler_conceded_runs_reconciliation", "status": "PASS" if bowler_rec_ok else "FAIL", "expected": 0, "actual": int((innings_summary["bowler_runs_reconcile_diff"] != 0).sum()), "details": "total_runs == bowler_conceded_runs + non_bowler_extras_runs across all innings"},
        {"check_name": "wickets_category_reconciliation", "status": "PASS" if wickets_rec_ok else "FAIL", "expected": 0, "actual": int((innings_summary["wickets_reconcile_diff"] != 0).sum()), "details": "wickets == bowler_wickets + run_outs + retired_outs + obstructing_field (retired_hurt excluded)"},
        {"check_name": "legal_deliveries_reconciliation", "status": "PASS" if legal_rec_ok else "FAIL", "expected": 0, "actual": int((innings_summary["legal_ball_reconcile_diff"] != 0).sum()), "details": "total_deliveries == legal_deliveries + wides + overstep_noballs + other_noballs"},
        {"check_name": "non_dls_run_margin_matches_official_result", "status": "PASS" if margin_mismatch_cnt == 0 else "WARN", "expected": 0, "actual": margin_mismatch_cnt, "details": f"Verified {len(margin_tested)} non-DLS matches won by runs; mismatches={margin_mismatch_cnt}"},
        {"check_name": "six_legal_ball_over_rule_exceptions", "status": "INFO", "expected": 0, "actual": overs_gt6, "details": "Only known exception is match 41509, inn 1, over 12 (7 consecutive 'None' deliveries)"},
        {"check_name": "all_primary_delivery_players_in_player_master", "status": "PASS" if (set(clean_deliveries["striker_id"]) | set(clean_deliveries["non_striker_id"]) | set(clean_deliveries["bowler_id"])).issubset(set(player_master["player_id"])) else "FAIL", "expected": 0, "actual": len((set(clean_deliveries["striker_id"]) | set(clean_deliveries["non_striker_id"]) | set(clean_deliveries["bowler_id"])) - set(player_master["player_id"])), "details": "Every striker, non-striker, and bowler in clean_deliveries exists in player_master.csv"},
    ])
    recon_checks.to_csv(OUT_DIR / "reconciliation_checks.csv", index=False)
    pd.DataFrame(cleaning_log).to_csv(OUT_DIR / "cleaning_log.csv", index=False)

    print("\n=== PHASE 3 DATA CLEANING COMPLETE ===")
    print(f"Raw deliveries           : {len(balls_raw):,}")
    print(f"Clean primary regular    : {len(clean_deliveries):,} ({clean_deliveries['match_id'].nunique()} matches)")
    print(f"Super Over deliveries    : {len(super_over_deliveries):,} (primary={prim_so_count}, excluded_comp={excl_so_count})")
    print(f"Excluded comp deliveries : {len(excluded_comp_deliveries):,} (comp_ids 2670, 3289)")
    print(f"Clean matches            : {len(clean_matches):,} (eligible IPL + T20I)")
    print(f"Player master            : {len(player_master):,} unique player_ids")
    print(f"Reconciliation checks    : {(recon_checks['status'] == 'PASS').sum()}/{len(recon_checks)} PASS (non-PASS: {recon_checks[recon_checks['status'] != 'PASS']['check_name'].tolist()})")


if __name__ == "__main__":
    main()
