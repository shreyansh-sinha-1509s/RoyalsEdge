"""
SupeRR Selector Season 2 - Phase 2 Comprehensive Dataset Audit & Data Quality Validation.

Reads the six competition CSV files directly (read-only) from data/raw/Data Pack/
(with optional ZIP fallback in data/raw/), runs full schema, reconciliation,
competition, delivery-level, and player-mapping validation using Pandas and DuckDB,
and writes reproducible audit CSV reports into outputs/.

No raw data is modified. No pressure scores or player rankings are calculated.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DATA_PACK_DIR = RAW_DIR / "Data Pack"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILENAMES: dict[str, str] = {
    "ball_by_ball": "ball_by_ball.csv",
    "matches": "matches.csv",
    "competitions": "competitions.csv",
    "teams": "teams.csv",
    "playing_eleven": "playing_eleven.csv",
    "player_mapping": "competition_team_player_mapping.csv",
}

# Only empty strings are treated as true raw missing values when reading string fields
# so literal tokens such as "None" in extras_type are preserved and audited explicitly.
RAW_NA_VALUES = [""]

COLUMN_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("ball_by_ball", "match_id"): "Foreign key to matches.match_id",
    ("ball_by_ball", "innings"): "Innings number (1-2 regulation; 3-4 Super Over)",
    ("ball_by_ball", "overid"): "1-indexed over number within innings",
    ("ball_by_ball", "over_ball_num"): "1-indexed sequential delivery number within over (includes wides/no-balls)",
    ("ball_by_ball", "innings_ball_num"): "1-indexed sequential delivery number within innings (includes wides/no-balls)",
    ("ball_by_ball", "batting_team_id"): "Team ID of batting side",
    ("ball_by_ball", "bowling_team_id"): "Team ID of bowling side",
    ("ball_by_ball", "striker_id"): "Player ID of batter facing delivery",
    ("ball_by_ball", "striker_name"): "Player name of striker recorded in ball feed",
    ("ball_by_ball", "non_striker_id"): "Player ID of non-striker",
    ("ball_by_ball", "non_striker_name"): "Player name of non-striker recorded in ball feed",
    ("ball_by_ball", "bowler_id"): "Player ID of bowler",
    ("ball_by_ball", "bowler_name"): "Player name of bowler recorded in ball feed",
    ("ball_by_ball", "batting_type"): "Batter handedness (e.g., RHB/LHB)",
    ("ball_by_ball", "bowling_type"): "Detailed bowling style",
    ("ball_by_ball", "batting_order"): "Striker batting position in innings",
    ("ball_by_ball", "runs"): "Runs scored off the bat by striker",
    ("ball_by_ball", "is_four"): "Boolean indicator for boundary four",
    ("ball_by_ball", "is_six"): "Boolean indicator for boundary six",
    ("ball_by_ball", "is_wicket"): "Boolean indicator for wicket falling on delivery",
    ("ball_by_ball", "dismissal_type_id"): "Numeric code for dismissal type",
    ("ball_by_ball", "dismissal_type"): "Text description of dismissal type",
    ("ball_by_ball", "dismissed_player_id"): "Player ID of dismissed batter",
    ("ball_by_ball", "extras_type"): "Category of extras ('None', 'wide', 'legbyes', 'byes', 'Overstep', 'other', 'Penalty')",
    ("ball_by_ball", "extras1_runs"): "Primary extras runs (wide, no-ball penalty, byes, legbyes, or penalty runs)",
    ("ball_by_ball", "extras_2_runs"): "Secondary extras runs (e.g., byes/legbyes off a no-ball)",
    ("ball_by_ball", "pace_or_spin"): "High-level bowler category (Pace/Spin)",
    ("ball_by_ball", "bowl_speed"): "Ball speed (0 frequently acts as unrecorded sentinel)",
    ("ball_by_ball", "stroke"): "Recorded batting shot type",
    ("ball_by_ball", "delivery_style"): "Recorded delivery variation/type",
    ("ball_by_ball", "over_or_around"): "Bowler angle relative to wicket (Over/Around)",
    ("ball_by_ball", "on_or_off"): "Shot/ball side indicator (On-side/Off-side)",
    ("ball_by_ball", "delivery_ist_time"): "Timestamp string of delivery",
    ("matches", "match_id"): "Primary key for match",
    ("matches", "comp_id"): "Foreign key to competitions.comp_id",
    ("matches", "match_number"): "Match sequence number within competition",
    ("matches", "match_date"): "Scheduled/played match date (YYYY-MM-DD)",
    ("matches", "stage"): "Tournament stage (League, Final, Semi-Final, etc.)",
    ("matches", "venue_id"): "Numeric venue identifier",
    ("matches", "venue_country"): "Country hosting the venue",
    ("matches", "home_team_id"): "Home team identifier",
    ("matches", "home_team"): "Home team name",
    ("matches", "away_team_id"): "Away team identifier",
    ("matches", "away_team"): "Away team name",
    ("matches", "home_team_captain_id"): "Home captain player ID",
    ("matches", "away_team_captain_id"): "Away captain player ID",
    ("matches", "toss_win_team_id"): "Team ID winning the toss",
    ("matches", "toss_opted"): "Toss decision (Batting/Fielding)",
    ("matches", "man_of_the_match"): "Player ID of Player of the Match (0 may indicate unrecorded)",
    ("matches", "first_inn_revised_overs"): "Revised overs allocation for 1st innings (DLS/rain)",
    ("matches", "second_inn_revised_overs"): "Revised overs allocation for 2nd innings (DLS/rain)",
    ("matches", "revised_target"): "Revised target runs for 2nd innings (DLS)",
    ("matches", "knock_out"): "Knockout match indicator (0/1)",
    ("matches", "win_team_id"): "Winning team ID",
    ("matches", "result"): "Text match result description",
    ("competitions", "comp_id"): "Primary key for competition/series",
    ("competitions", "comp_name"): "Competition or bilateral series name",
    ("competitions", "match_format"): "Format code (T20I, T20)",
    ("competitions", "season"): "Season label (YYYY or YYYY/YY)",
    ("teams", "comp_id"): "Foreign key to competitions.comp_id",
    ("teams", "team_id"): "Team identifier within competition",
    ("teams", "team_name"): "Team display name",
    ("playing_eleven", "match_id"): "Foreign key to matches.match_id",
    ("playing_eleven", "team_id"): "Team identifier",
    ("playing_eleven", "player_id"): "Player identifier",
    ("playing_eleven", "batting_order"): "Listed batting order in team sheet",
    ("playing_eleven", "is_played"): "Whether player featured in the match",
    ("playing_eleven", "is_captain"): "Captain flag",
    ("playing_eleven", "is_wk"): "Wicketkeeper flag",
    ("playing_eleven", "is_impact"): "Impact player subbed-in flag",
    ("playing_eleven", "is_impact_off"): "Impact player subbed-off flag",
    ("player_mapping", "comp_id"): "Foreign key to competitions.comp_id",
    ("player_mapping", "comp_name"): "Competition name",
    ("player_mapping", "team_id"): "Team identifier",
    ("player_mapping", "team_name"): "Team name",
    ("player_mapping", "player_id"): "Player identifier",
    ("player_mapping", "player_name"): "Player canonical name in mapping table",
}


def load_raw_tables(preserve_literal_none: bool = True) -> tuple[dict[str, pd.DataFrame], str]:
    """Read all six CSVs directly from data/raw/Data Pack/, with optional ZIP fallback."""
    read_kwargs: dict[str, Any] = {"low_memory": False}
    if preserve_literal_none:
        read_kwargs["keep_default_na"] = False
        read_kwargs["na_values"] = RAW_NA_VALUES

    if DATA_PACK_DIR.is_dir():
        missing = [
            fname for fname in CSV_FILENAMES.values()
            if not (DATA_PACK_DIR / fname).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                f"Required CSVs missing from {DATA_PACK_DIR}: {', '.join(missing)}"
            )
        source_desc = str(DATA_PACK_DIR.relative_to(ROOT))
        tables = {
            key: pd.read_csv(DATA_PACK_DIR / fname, **read_kwargs)
            for key, fname in CSV_FILENAMES.items()
        }
        return tables, source_desc

    zip_candidates = sorted(RAW_DIR.glob("*.zip"))
    if len(zip_candidates) != 1:
        raise FileNotFoundError(
            f"Extracted folder {DATA_PACK_DIR} not found, and expected exactly one fallback ZIP "
            f"in {RAW_DIR} (found {len(zip_candidates)})."
        )
    zip_path = zip_candidates[0]
    source_desc = str(zip_path.relative_to(ROOT))
    tables = {}
    with zipfile.ZipFile(zip_path) as zf:
        available = {
            n for n in zf.namelist()
            if not n.startswith("__MACOSX/") and not Path(n).name.startswith("._")
        }
        for key, fname in CSV_FILENAMES.items():
            entry = f"Data Pack/{fname}"
            if entry not in available:
                raise FileNotFoundError(f"Missing {entry} in {zip_path.name}")
            tables[key] = pd.read_csv(zf.open(entry), **read_kwargs)
    return tables, source_desc


def classify_competition(comp_name: str, match_format: str) -> str:
    """Explicitly separate IPL, T20I, and non-IPL T20 competitions without silently merging."""
    name_str = str(comp_name).strip()
    fmt_str = str(match_format).strip()
    if re.fullmatch(r"IPL\s+\d{4}", name_str, flags=re.IGNORECASE):
        return "IPL"
    if fmt_str == "T20I":
        return "T20I"
    if fmt_str == "T20":
        return "Non-IPL T20"
    return "Other/Unknown"


def to_bool_series(s: pd.Series) -> pd.Series:
    """Safely convert boolean or lowercase string boolean series to nullable boolean."""
    if pd.api.types.is_bool_dtype(s):
        return s.astype("boolean")
    mapped = s.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False, "1.0": True, "0.0": False}
    )
    return mapped.astype("boolean")


def build_data_quality_and_missing_reports(
    tables_raw: dict[str, pd.DataFrame],
    tables_default: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate file-level data_quality_report, missing_values_report, and column_dictionary."""
    key_specs: dict[str, list[str]] = {
        "ball_by_ball": ["match_id", "innings", "innings_ball_num"],
        "matches": ["match_id"],
        "competitions": ["comp_id"],
        "teams": ["comp_id", "team_id"],
        "playing_eleven": ["match_id", "team_id", "player_id"],
        "player_mapping": ["comp_id", "team_id", "player_id"],
    }

    dq_rows = []
    missing_rows = []
    dict_rows = []

    for name in CSV_FILENAMES:
        df_raw = tables_raw[name]
        df_def = tables_default[name]
        key_cols = key_specs[name]

        mem_mb = round(df_raw.memory_usage(deep=True).sum() / (1024 * 1024), 3)
        dup_full = int(df_raw.duplicated().sum())
        dup_key = int(df_raw.duplicated(subset=key_cols).sum())
        raw_missing_total = int(df_raw.isna().sum().sum())
        def_missing_total = int(df_def.isna().sum().sum())

        notes = []
        if dup_full > 0:
            notes.append(f"{dup_full} exact duplicate rows")
        if dup_key > 0:
            notes.append(f"{dup_key} duplicate natural-key rows on {key_cols}")
        if def_missing_total != raw_missing_total:
            notes.append(
                f"Default pandas NA count ({def_missing_total:,}) exceeds blank-cell count "
                f"({raw_missing_total:,}) due to literal strings like 'None'"
            )

        dq_rows.append({
            "table_name": name,
            "file_name": CSV_FILENAMES[name],
            "row_count": len(df_raw),
            "column_count": len(df_raw.columns),
            "memory_usage_mb": mem_mb,
            "natural_key": " + ".join(key_cols),
            "duplicate_full_rows": dup_full,
            "duplicate_natural_key_rows": dup_key,
            "raw_blank_missing_cells": raw_missing_total,
            "pandas_default_na_cells": def_missing_total,
            "columns_with_raw_blanks": int((df_raw.isna().sum() > 0).sum()),
            "notes": "; ".join(notes) if notes else "Clean natural key; no exact duplicate rows",
        })

        for col in df_raw.columns:
            s_raw = df_raw[col]
            s_def = df_def[col]
            raw_na = int(s_raw.isna().sum())
            def_na = int(s_def.isna().sum())
            n_rows = len(df_raw)
            literal_none = int(
                s_raw.dropna().astype(str).str.strip().eq("None").sum()
            ) if s_raw.dtype == object or pd.api.types.is_string_dtype(s_raw) else 0

            zero_sentinel = 0
            col_notes = []
            if col in {"bowl_speed", "man_of_the_match"}:
                num_s = pd.to_numeric(s_raw, errors="coerce")
                zero_sentinel = int((num_s == 0).sum())
                if zero_sentinel > 0:
                    col_notes.append(f"{zero_sentinel:,} rows equal 0 (likely unrecorded sentinel)")
            if literal_none > 0:
                col_notes.append(
                    f"{literal_none:,} rows contain literal string 'None' (parsed as NaN by default read_csv)"
                )

            missing_rows.append({
                "table_name": name,
                "file_name": CSV_FILENAMES[name],
                "column": col,
                "dtype_raw": str(s_raw.dtype),
                "dtype_default_pandas": str(s_def.dtype),
                "row_count": n_rows,
                "raw_blank_count": raw_na,
                "raw_blank_pct": round(raw_na / n_rows * 100, 4) if n_rows else 0.0,
                "pandas_default_na_count": def_na,
                "pandas_default_na_pct": round(def_na / n_rows * 100, 4) if n_rows else 0.0,
                "literal_none_count": literal_none,
                "zero_sentinel_count": zero_sentinel,
                "notes": "; ".join(col_notes),
            })

            non_null_vals = s_raw.dropna()
            unique_cnt = int(non_null_vals.nunique())
            samples = non_null_vals.drop_duplicates().head(5).astype(str).tolist()
            dict_rows.append({
                "table_name": name,
                "file_name": CSV_FILENAMES[name],
                "column": col,
                "dtype": str(s_raw.dtype),
                "non_null_count": int(non_null_vals.shape[0]),
                "raw_blank_count": raw_na,
                "unique_non_null_count": unique_cnt,
                "sample_values": " | ".join(samples),
                "description": COLUMN_DESCRIPTIONS.get((name, col), ""),
            })

    return (
        pd.DataFrame(dq_rows),
        pd.DataFrame(missing_rows),
        pd.DataFrame(dict_rows),
    )


def build_competition_summary(
    con: duckdb.DuckDBPyConnection,
    competitions: pd.DataFrame,
    matches: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Produce per-competition summary separating IPL, T20I, Non-IPL T20, and unknown comp_ids."""
    comp_enriched = competitions.copy()
    comp_enriched["eligibility_category"] = [
        classify_competition(n, f)
        for n, f in zip(comp_enriched["comp_name"], comp_enriched["match_format"])
    ]
    con.register("comp_enriched", comp_enriched)

    summary_df = con.execute("""
        WITH match_agg AS (
            SELECT
                comp_id,
                COUNT(*) AS matches_in_metadata,
                COUNT(DISTINCT match_id) AS unique_matches_in_metadata,
                MIN(match_date) AS min_match_date,
                MAX(match_date) AS max_match_date,
                COUNT(DISTINCT home_team_id) AS distinct_home_teams,
                SUM(CASE WHEN LOWER(COALESCE(result, '')) LIKE '%abandon%' THEN 1 ELSE 0 END) AS abandoned_matches,
                SUM(CASE WHEN LOWER(COALESCE(result, '')) LIKE '%no result%' THEN 1 ELSE 0 END) AS no_result_matches,
                SUM(CASE WHEN LOWER(COALESCE(result, '')) LIKE '%tie%' THEN 1 ELSE 0 END) AS tied_matches
            FROM matches
            GROUP BY comp_id
        ),
        ball_agg AS (
            SELECT
                m.comp_id,
                COUNT(DISTINCT b.match_id) AS matches_with_ball_data,
                COUNT(*) AS total_deliveries,
                SUM(CASE WHEN COALESCE(b.extras_type, 'None') NOT IN ('wide', 'Overstep', 'other') THEN 1 ELSE 0 END) AS legal_deliveries
            FROM ball_by_ball b
            LEFT JOIN matches m ON b.match_id = m.match_id
            GROUP BY m.comp_id
        ),
        team_agg AS (
            SELECT comp_id, COUNT(DISTINCT team_id) AS teams_in_teams_csv
            FROM teams
            GROUP BY comp_id
        ),
        map_agg AS (
            SELECT comp_id, COUNT(DISTINCT player_id) AS players_in_mapping
            FROM player_mapping
            GROUP BY comp_id
        )
        SELECT
            c.comp_id,
            c.comp_name,
            c.match_format,
            c.season,
            c.eligibility_category,
            COALESCE(ma.matches_in_metadata, 0) AS matches_in_metadata,
            COALESCE(ba.matches_with_ball_data, 0) AS matches_with_ball_data,
            COALESCE(ma.unique_matches_in_metadata, 0) - COALESCE(ba.matches_with_ball_data, 0) AS matches_without_ball_data,
            COALESCE(ba.total_deliveries, 0) AS total_deliveries,
            COALESCE(ba.legal_deliveries, 0) AS legal_deliveries,
            COALESCE(ta.teams_in_teams_csv, 0) AS teams_in_teams_csv,
            COALESCE(pa.players_in_mapping, 0) AS players_in_mapping,
            COALESCE(ma.abandoned_matches, 0) AS abandoned_matches,
            COALESCE(ma.no_result_matches, 0) AS no_result_matches,
            COALESCE(ma.tied_matches, 0) AS tied_matches,
            ma.min_match_date,
            ma.max_match_date
        FROM comp_enriched c
        LEFT JOIN match_agg ma ON c.comp_id = ma.comp_id
        LEFT JOIN ball_agg ba ON c.comp_id = ba.comp_id
        LEFT JOIN team_agg ta ON c.comp_id = ta.comp_id
        LEFT JOIN map_agg pa ON c.comp_id = pa.comp_id
        ORDER BY c.eligibility_category, c.season, c.comp_id
    """).df()

    unknown_match_comps = set(matches["comp_id"].dropna()) - set(competitions["comp_id"].dropna())
    comp_ids_in_teams = set(con.execute("SELECT DISTINCT comp_id FROM teams WHERE comp_id IS NOT NULL").df()["comp_id"])
    comp_ids_in_map = set(con.execute("SELECT DISTINCT comp_id FROM player_mapping WHERE comp_id IS NOT NULL").df()["comp_id"])
    known_comps = set(competitions["comp_id"].dropna())

    unmatched_counts = {
        "matches_unknown_comp_ids": len(unknown_match_comps),
        "teams_unknown_comp_ids": len(comp_ids_in_teams - known_comps),
        "mapping_unknown_comp_ids": len(comp_ids_in_map - known_comps),
        "competitions_with_zero_matches": int((summary_df["matches_in_metadata"] == 0).sum()),
    }
    return summary_df, unmatched_counts


def build_innings_and_match_reconciliation(
    con: duckdb.DuckDBPyConnection,
    matches: pd.DataFrame,
    balls: pd.DataFrame,
    competitions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build innings_summary.csv and comprehensive match_reconciliation.csv."""
    comp_enriched = competitions.copy()
    comp_enriched["eligibility_category"] = [
        classify_competition(n, f)
        for n, f in zip(comp_enriched["comp_name"], comp_enriched["match_format"])
    ]
    con.register("comp_enriched_inn", comp_enriched)

    innings_df = con.execute("""
        SELECT
            b.match_id,
            b.innings,
            m.comp_id,
            c.comp_name,
            c.match_format,
            c.season,
            c.eligibility_category,
            m.match_date,
            MIN(b.batting_team_id) AS batting_team_id,
            MIN(b.bowling_team_id) AS bowling_team_id,
            COUNT(DISTINCT b.batting_team_id) AS distinct_batting_team_ids,
            COUNT(DISTINCT b.bowling_team_id) AS distinct_bowling_team_ids,
            COUNT(*) AS total_deliveries,
            SUM(CASE WHEN COALESCE(b.extras_type, 'None') NOT IN ('wide', 'Overstep', 'other') THEN 1 ELSE 0 END) AS legal_deliveries,
            SUM(CASE WHEN b.extras_type = 'wide' THEN 1 ELSE 0 END) AS wides,
            SUM(CASE WHEN b.extras_type = 'Overstep' THEN 1 ELSE 0 END) AS overstep_noballs,
            SUM(CASE WHEN b.extras_type = 'other' THEN 1 ELSE 0 END) AS other_noballs,
            SUM(CASE WHEN b.extras_type = 'byes' THEN 1 ELSE 0 END) AS byes_balls,
            SUM(CASE WHEN b.extras_type = 'legbyes' THEN 1 ELSE 0 END) AS legbyes_balls,
            SUM(CASE WHEN b.extras_type = 'Penalty' THEN 1 ELSE 0 END) AS penalty_balls,
            SUM(COALESCE(TRY_CAST(b.runs AS BIGINT), 0)) AS batter_runs,
            SUM(COALESCE(TRY_CAST(b.extras1_runs AS BIGINT), 0)) AS extras1_runs,
            SUM(COALESCE(TRY_CAST(b.extras_2_runs AS BIGINT), 0)) AS extras2_runs,
            SUM(
                COALESCE(TRY_CAST(b.runs AS BIGINT), 0)
                + COALESCE(TRY_CAST(b.extras1_runs AS BIGINT), 0)
                + COALESCE(TRY_CAST(b.extras_2_runs AS BIGINT), 0)
            ) AS total_runs,
            SUM(CASE WHEN LOWER(CAST(b.is_wicket AS VARCHAR)) = 'true' THEN 1 ELSE 0 END) AS wickets,
            COUNT(DISTINCT b.striker_id) AS unique_strikers,
            COUNT(DISTINCT b.bowler_id) AS unique_bowlers,
            MIN(b.overid) AS min_overid,
            MAX(b.overid) AS max_overid,
            MAX(b.innings_ball_num) AS max_innings_ball_num,
            CASE WHEN b.innings = 1 THEN m.first_inn_revised_overs
                 WHEN b.innings = 2 THEN m.second_inn_revised_overs
                 ELSE NULL END AS revised_overs,
            m.revised_target,
            m.result,
            CASE WHEN b.innings >= 3 THEN TRUE ELSE FALSE END AS is_super_over
        FROM ball_by_ball b
        LEFT JOIN matches m ON b.match_id = m.match_id
        LEFT JOIN comp_enriched_inn c ON m.comp_id = c.comp_id
        GROUP BY
            b.match_id, b.innings, m.comp_id, c.comp_name, c.match_format,
            c.season, c.eligibility_category, m.match_date,
            m.first_inn_revised_overs, m.second_inn_revised_overs,
            m.revised_target, m.result
        ORDER BY b.match_id, b.innings
    """).df()

    # Classify innings completeness conservatively without guessing causes
    def flag_innings(row: pd.Series) -> str:
        if row["innings"] >= 3:
            return "super_over"
        if row["innings"] not in (1, 2):
            return "unusual_innings_number"
        res = str(row["result"] or "").lower()
        if row["innings"] == 1:
            if row["wickets"] >= 10:
                return "complete_all_out"
            if pd.notna(row["revised_overs"]) and str(row["revised_overs"]).strip() != "":
                return "revised_overs_innings"
            if row["legal_deliveries"] >= 120:
                return "complete_full_overs"
            if "no result" in res or "abandon" in res:
                return "incomplete_no_result_or_abandoned"
            return "short_first_innings_check"
        # Innings 2
        if row["wickets"] >= 10:
            return "complete_all_out"
        if re.search(r"won.*(wicket|wkt)", res):
            return "chase_completed"
        if pd.notna(row["revised_overs"]) and str(row["revised_overs"]).strip() != "":
            return "revised_overs_innings"
        if row["legal_deliveries"] >= 120:
            return "complete_full_overs"
        if "no result" in res or "abandon" in res:
            return "incomplete_no_result_or_abandoned"
        if "d/l" in res or "dls" in res or "vjd" in res:
            return "dls_affected"
        if "tie" in res or "super over" in res or "eliminator" in res:
            return "tied_or_super_over_match"
        return "short_second_innings_check"

    innings_df["innings_status_flag"] = innings_df.apply(flag_innings, axis=1)

    # Match reconciliation checks (all 10 Section C items)
    meta_ids = set(matches["match_id"].dropna().astype(int))
    ball_ids = set(balls["match_id"].dropna().astype(int))
    missing_ball_ids = sorted(meta_ids - ball_ids)
    extra_ball_ids = sorted(ball_ids - meta_ids)

    missing_meta_df = matches[matches["match_id"].isin(missing_ball_ids)].copy()
    missing_result_breakdown = (
        missing_meta_df["result"].fillna("<BLANK>").value_counts().to_dict()
    )
    missing_breakdown_str = "; ".join(f"{k}: {v}" for k, v in missing_result_breakdown.items())

    res_lower = matches["result"].fillna("").astype(str).str.lower()
    abandoned_matches = matches[res_lower.str.contains("abandon", na=False)]
    no_result_matches = matches[res_lower.str.contains("no result", na=False)]
    tied_matches = matches[res_lower.str.contains(r"\btie\b|\btied\b", regex=True, na=False)]
    super_over_result_matches = matches[res_lower.str.contains(r"super over|one over eliminator", regex=True, na=False)]
    dls_result_matches = matches[res_lower.str.contains(r"d/l|dls|duckworth", regex=True, na=False)]
    blank_result_matches = matches[matches["result"].isna() | (matches["result"].astype(str).str.strip() == "")]

    # Matches with ball data by innings structure
    inn_by_match = innings_df.groupby("match_id")["innings"].apply(lambda s: tuple(sorted(s.unique())))
    only_inn1_matches = inn_by_match[inn_by_match == (1,)].index.tolist()
    super_over_ball_matches = innings_df[innings_df["innings"] >= 3]["match_id"].nunique()
    unusual_inn_rows = int((~balls["innings"].isin([1, 2, 3, 4])).sum())
    inn_multi_team = int(
        ((innings_df["distinct_batting_team_ids"] > 1) | (innings_df["distinct_bowling_team_ids"] > 1)).sum()
    )

    # Check duplicate (match_id, innings, innings_ball_num) & (match_id, innings, overid, over_ball_num)
    dup_mib = int(balls.duplicated(["match_id", "innings", "innings_ball_num"]).sum())
    dup_miob = int(balls.duplicated(["match_id", "innings", "overid", "over_ball_num"]).sum())

    # Check missing team or competition IDs
    miss_comp_matches = int(matches["comp_id"].isna().sum())
    miss_home_matches = int(matches["home_team_id"].isna().sum())
    miss_away_matches = int(matches["away_team_id"].isna().sum())
    miss_bat_team_balls = int(balls["batting_team_id"].isna().sum())
    miss_bowl_team_balls = int(balls["bowling_team_id"].isna().sum())

    # Check whether batting/bowling team IDs in balls match home/away in matches
    team_mismatch = con.execute("""
        SELECT COUNT(DISTINCT b.match_id) AS cnt
        FROM ball_by_ball b
        JOIN matches m ON b.match_id = m.match_id
        WHERE b.batting_team_id NOT IN (m.home_team_id, m.away_team_id)
           OR b.bowling_team_id NOT IN (m.home_team_id, m.away_team_id)
           OR b.batting_team_id = b.bowling_team_id
    """).fetchone()[0]

    # Matches with revised overs / target
    revised_overs_matches = int(
        (matches["first_inn_revised_overs"].notna() | matches["second_inn_revised_overs"].notna()).sum()
    )
    revised_target_matches = int(matches["revised_target"].notna().sum())

    # Short 1st innings without revised overs or no-result/abandoned
    short_inn1_unexplained = innings_df[innings_df["innings_status_flag"] == "short_first_innings_check"]
    short_inn2_unexplained = innings_df[innings_df["innings_status_flag"] == "short_second_innings_check"]

    # Playing XI reconciliation
    pxi_ids = set(con.execute("SELECT DISTINCT match_id FROM playing_eleven").df()["match_id"].dropna().astype(int))

    recon_rows = [
        {"category": "ID Coverage", "check": "matches_in_matches_csv", "count": len(meta_ids), "details": f"Total rows in matches.csv: {len(matches)}"},
        {"category": "ID Coverage", "check": "matches_in_ball_by_ball_csv", "count": len(ball_ids), "details": "Unique match_id values with >= 1 delivery"},
        {"category": "ID Coverage", "check": "matches_in_playing_eleven_csv", "count": len(pxi_ids), "details": f"In matches but not playing_eleven: {len(meta_ids - pxi_ids)}; in playing_eleven but not matches: {len(pxi_ids - meta_ids)}"},
        {"category": "ID Coverage", "check": "metadata_matches_absent_from_ball_data", "count": len(missing_ball_ids), "details": f"Verified result breakdown: {missing_breakdown_str}"},
        {"category": "ID Coverage", "check": "ball_data_matches_absent_from_metadata", "count": len(extra_ball_ids), "details": "Match IDs in ball_by_ball.csv missing from matches.csv"},
        {"category": "Match Outcomes", "check": "abandoned_matches_in_metadata", "count": len(abandoned_matches), "details": f"With ball data: {abandoned_matches['match_id'].isin(ball_ids).sum()}; without ball data: {(~abandoned_matches['match_id'].isin(ball_ids)).sum()}"},
        {"category": "Match Outcomes", "check": "no_result_matches_in_metadata", "count": len(no_result_matches), "details": f"With ball data: {no_result_matches['match_id'].isin(ball_ids).sum()}; without ball data: {(~no_result_matches['match_id'].isin(ball_ids)).sum()}"},
        {"category": "Match Outcomes", "check": "tied_matches_in_metadata", "count": len(tied_matches), "details": f"Result text mentions tie/tied; Super Over text mentions: {len(super_over_result_matches)}"},
        {"category": "Match Outcomes", "check": "blank_result_matches_in_metadata", "count": len(blank_result_matches), "details": f"With ball data: {blank_result_matches['match_id'].isin(ball_ids).sum()}; without ball data: {(~blank_result_matches['match_id'].isin(ball_ids)).sum()}"},
        {"category": "Match Outcomes", "check": "dls_or_revised_overs_matches", "count": revised_overs_matches, "details": f"Revised overs: {revised_overs_matches}; revised_target populated: {revised_target_matches}; D/L or DLS in result text: {len(dls_result_matches)}"},
        {"category": "Innings Structure", "check": "matches_with_only_innings_1_in_ball_data", "count": len(only_inn1_matches), "details": f"Sample match_ids: {only_inn1_matches[:10]}"},
        {"category": "Innings Structure", "check": "matches_with_super_over_innings_3_or_4", "count": int(super_over_ball_matches), "details": f"Innings 3 rows: {int((balls['innings'] == 3).sum())}; Innings 4 rows: {int((balls['innings'] == 4).sum())}"},
        {"category": "Innings Structure", "check": "unusual_innings_number_rows_not_in_1_to_4", "count": unusual_inn_rows, "details": f"Distinct innings values observed: {sorted(balls['innings'].dropna().unique().tolist())}"},
        {"category": "Innings Structure", "check": "short_first_innings_without_revised_overs_or_nr", "count": len(short_inn1_unexplained), "details": f"Sample match_ids: {short_inn1_unexplained['match_id'].head(10).tolist()}"},
        {"category": "Innings Structure", "check": "short_second_innings_without_chase_or_dls_or_nr", "count": len(short_inn2_unexplained), "details": f"Sample match_ids: {short_inn2_unexplained['match_id'].head(10).tolist()}"},
        {"category": "Innings Structure", "check": "innings_with_multiple_batting_or_bowling_team_ids", "count": inn_multi_team, "details": "Checks whether batting_team_id or bowling_team_id changes mid-innings"},
        {"category": "Integrity", "check": "missing_comp_or_team_ids_in_matches", "count": miss_comp_matches + miss_home_matches + miss_away_matches, "details": f"comp_id: {miss_comp_matches}, home_team_id: {miss_home_matches}, away_team_id: {miss_away_matches}"},
        {"category": "Integrity", "check": "missing_team_ids_in_ball_by_ball", "count": miss_bat_team_balls + miss_bowl_team_balls, "details": f"batting_team_id: {miss_bat_team_balls}, bowling_team_id: {miss_bowl_team_balls}"},
        {"category": "Integrity", "check": "ball_team_id_not_matching_match_home_or_away", "count": int(team_mismatch), "details": "Matches where ball batting/bowling team_id differs from home/away team_id"},
        {"category": "Duplicates", "check": "duplicate_match_innings_ball_num_keys", "count": dup_mib, "details": "Duplicate (match_id, innings, innings_ball_num) in ball_by_ball.csv"},
        {"category": "Duplicates", "check": "duplicate_match_innings_over_ball_keys", "count": dup_miob, "details": "Duplicate (match_id, innings, overid, over_ball_num) in ball_by_ball.csv"},
    ]
    return innings_df, pd.DataFrame(recon_rows)


def build_delivery_validation_report(balls: pd.DataFrame) -> pd.DataFrame:
    """Validate delivery-level runs, extras, legal balls, wickets, speeds, and categoricals."""
    runs = pd.to_numeric(balls["runs"], errors="coerce")
    e1 = pd.to_numeric(balls["extras1_runs"], errors="coerce")
    e2 = pd.to_numeric(balls["extras_2_runs"], errors="coerce")
    total_runs = runs.fillna(0) + e1.fillna(0) + e2.fillna(0)
    et = balls["extras_type"].fillna("<BLANK>").astype(str)

    is_four = to_bool_series(balls["is_four"])
    is_six = to_bool_series(balls["is_six"])
    is_wicket = to_bool_series(balls["is_wicket"])

    non_legal_mask = et.isin(["wide", "Overstep", "other"])
    legal_mask = ~non_legal_mask

    # Over-level legal delivery check (flag completed overs with >6 legal balls)
    over_legal = (
        balls.assign(_is_legal=legal_mask.astype(int))
        .groupby(["match_id", "innings", "overid"])["_is_legal"]
        .sum()
    )
    overs_gt6_legal = over_legal[over_legal > 6]

    # Bowl speed checks
    speed = pd.to_numeric(balls["bowl_speed"], errors="coerce")
    speed_zero = int((speed == 0).sum())
    speed_neg = int((speed < 0).sum())
    speed_gt_165 = int((speed > 165).sum())
    speed_lt_50_pos = int(((speed > 0) & (speed < 50)).sum())
    speed_valid = speed[(speed >= 50) & (speed <= 165)]

    # Wicket & dismissal consistency
    wkt_true = is_wicket.fillna(False)
    wkt_no_type = int((wkt_true & balls["dismissal_type"].isna()).sum())
    type_no_wkt = int((~wkt_true & balls["dismissal_type"].notna()).sum())
    wkt_no_player = int((wkt_true & balls["dismissed_player_id"].isna()).sum())
    player_no_wkt = int((~wkt_true & balls["dismissed_player_id"].notna()).sum())
    dismissed_not_on_crease = int(
        (
            wkt_true
            & balls["dismissed_player_id"].notna()
            & (balls["dismissed_player_id"] != balls["striker_id"])
            & (balls["dismissed_player_id"] != balls["non_striker_id"])
        ).sum()
    )

    # Boundary vs runs reconciliation
    four_not_4 = int((is_four.fillna(False) & (runs != 4)).sum())
    runs4_not_four = int((~is_four.fillna(False) & (runs == 4)).sum())
    six_not_6 = int((is_six.fillna(False) & (runs != 6)).sum())
    runs6_not_six = int((~is_six.fillna(False) & (runs == 6)).sum())

    # Extras reconciliation
    none_with_extras = balls[(et == "None") & ((e1.fillna(0) != 0) | (e2.fillna(0) != 0))]
    non_none_zero_e1 = balls[(et != "None") & (e1.fillna(0) == 0)]
    wide_with_batter_runs = balls[(et == "wide") & (runs.fillna(0) != 0)]
    byes_with_batter_runs = balls[(et == "byes") & (runs.fillna(0) != 0)]
    legbyes_with_batter_runs = balls[(et == "legbyes") & (runs.fillna(0) != 0)]
    neg_runs_or_extras = int(((runs < 0) | (e1 < 0) | (e2 < 0)).sum())
    runs_gt_7 = int((runs > 7).sum())
    total_runs_gt_8 = int((total_runs > 8).sum())

    # Striker == non-striker or striker == bowler
    striker_eq_nonstriker = int((balls["striker_id"] == balls["non_striker_id"]).sum())
    striker_eq_bowler = int((balls["striker_id"] == balls["bowler_id"]).sum())

    # Over numbering checks
    over_out_of_range = int(((balls["overid"] < 1) | (balls["overid"] > 20)).sum())
    super_over_overid_gt1 = int(((balls["innings"] >= 3) & (balls["overid"] > 1)).sum())
    ball_num_le0 = int(((balls["over_ball_num"] < 1) | (balls["innings_ball_num"] < 1)).sum())

    # Dismissal type spelling anomalies
    dismissal_counts = balls["dismissal_type"].dropna().value_counts().to_dict()
    dismissal_str = "; ".join(f"{k}: {v}" for k, v in dismissal_counts.items())
    obstruct_typo = int((balls["dismissal_type"] == "Obstracting the field").sum())

    # Extras breakdown string
    et_counts = et.value_counts().to_dict()
    et_str = "; ".join(f"{k}: {v}" for k, v in et_counts.items())

    # Bowling type / pace_or_spin
    bt_missing = int(balls["bowling_type"].isna().sum())
    ps_counts = balls["pace_or_spin"].fillna("<BLANK>").value_counts().to_dict()
    ps_str = "; ".join(f"{k}: {v}" for k, v in ps_counts.items())

    rows = [
        {"section": "Delivery Volume", "check": "total_deliveries", "value": len(balls), "severity": "info", "details": "Total rows in ball_by_ball.csv"},
        {"section": "Delivery Volume", "check": "legal_deliveries", "value": int(legal_mask.sum()), "severity": "info", "details": "Excludes extras_type in {'wide', 'Overstep', 'other'}"},
        {"section": "Delivery Volume", "check": "non_legal_deliveries", "value": int(non_legal_mask.sum()), "severity": "info", "details": f"wide: {et_counts.get('wide', 0)}, Overstep (no-ball): {et_counts.get('Overstep', 0)}, other (no-ball): {et_counts.get('other', 0)}"},
        {"section": "Extras Breakdown", "check": "extras_type_distribution", "value": len(et_counts), "severity": "info", "details": et_str},
        {"section": "Extras Reconciliation", "check": "extras_type_None_with_nonzero_extras", "value": len(none_with_extras), "severity": "warning" if len(none_with_extras) else "ok", "details": f"match_ids: {none_with_extras['match_id'].tolist()}; rows have extras1_runs or extras_2_runs > 0 despite extras_type='None'"},
        {"section": "Extras Reconciliation", "check": "non_None_extras_type_with_zero_extras1", "value": len(non_none_zero_e1), "severity": "warning" if len(non_none_zero_e1) else "ok", "details": f"match_ids: {non_none_zero_e1['match_id'].tolist()}; extras_type: {non_none_zero_e1['extras_type'].tolist()}; runs: {non_none_zero_e1['runs'].tolist()}"},
        {"section": "Extras Reconciliation", "check": "wide_with_nonzero_batter_runs", "value": len(wide_with_batter_runs), "severity": "error" if len(wide_with_batter_runs) else "ok", "details": "Wides cannot credit runs to batter"},
        {"section": "Extras Reconciliation", "check": "byes_with_nonzero_batter_runs", "value": len(byes_with_batter_runs), "severity": "warning" if len(byes_with_batter_runs) else "ok", "details": f"match_ids: {byes_with_batter_runs['match_id'].head(10).tolist()}"},
        {"section": "Extras Reconciliation", "check": "legbyes_with_nonzero_batter_runs", "value": len(legbyes_with_batter_runs), "severity": "warning" if len(legbyes_with_batter_runs) else "ok", "details": f"match_ids: {legbyes_with_batter_runs['match_id'].head(10).tolist()}"},
        {"section": "Runs Reconciliation", "check": "total_runs_column_present", "value": 0, "severity": "info", "details": "No precomputed total_runs column in raw CSV; derived as runs + extras1_runs + extras_2_runs"},
        {"section": "Runs Reconciliation", "check": "negative_runs_or_extras", "value": neg_runs_or_extras, "severity": "error" if neg_runs_or_extras else "ok", "details": "Checks runs < 0, extras1_runs < 0, extras_2_runs < 0"},
        {"section": "Runs Reconciliation", "check": "batter_runs_gt_7", "value": runs_gt_7, "severity": "warning" if runs_gt_7 else "ok", "details": f"Max batter runs: {int(runs.max())}; distribution: {runs.value_counts().sort_index().to_dict()}"},
        {"section": "Runs Reconciliation", "check": "derived_total_runs_gt_8", "value": total_runs_gt_8, "severity": "warning" if total_runs_gt_8 else "ok", "details": f"Max derived total_runs on single ball: {int(total_runs.max())}"},
        {"section": "Boundary Flags", "check": "is_four_true_but_runs_ne_4", "value": four_not_4, "severity": "warning" if four_not_4 else "ok", "details": "Boundary four flag set when batter runs != 4 (e.g., overthrows or flag error)"},
        {"section": "Boundary Flags", "check": "runs_eq_4_but_is_four_false", "value": runs4_not_four, "severity": "info", "details": "All-run 4s (or unflagged fours) where runs == 4 and is_four == false"},
        {"section": "Boundary Flags", "check": "is_six_true_but_runs_ne_6", "value": six_not_6, "severity": "warning" if six_not_6 else "ok", "details": "Boundary six flag set when batter runs != 6"},
        {"section": "Boundary Flags", "check": "runs_eq_6_but_is_six_false", "value": runs6_not_six, "severity": "warning" if runs6_not_six else "ok", "details": "Rows where runs == 6 and is_six == false"},
        {"section": "Over & Ball Numbering", "check": "overid_outside_1_to_20", "value": over_out_of_range, "severity": "error" if over_out_of_range else "ok", "details": f"Min overid: {int(balls['overid'].min())}, Max overid: {int(balls['overid'].max())}"},
        {"section": "Over & Ball Numbering", "check": "super_over_overid_gt_1", "value": super_over_overid_gt1, "severity": "warning" if super_over_overid_gt1 else "ok", "details": "Super over deliveries with overid > 1"},
        {"section": "Over & Ball Numbering", "check": "over_ball_or_innings_ball_num_le_0", "value": ball_num_le0, "severity": "error" if ball_num_le0 else "ok", "details": "Ball numbering must be >= 1"},
        {"section": "Over & Ball Numbering", "check": "overs_with_more_than_6_legal_deliveries", "value": len(overs_gt6_legal), "severity": "warning" if len(overs_gt6_legal) else "ok", "details": f"Sample (match_id, innings, overid): {overs_gt6_legal.head(10).to_dict()}"},
        {"section": "Wickets & Dismissals", "check": "total_wickets_flagged", "value": int(wkt_true.sum()), "severity": "info", "details": dismissal_str},
        {"section": "Wickets & Dismissals", "check": "is_wicket_true_missing_dismissal_type", "value": wkt_no_type, "severity": "warning" if wkt_no_type else "ok", "details": "Wicket rows lacking dismissal_type"},
        {"section": "Wickets & Dismissals", "check": "is_wicket_false_with_dismissal_type", "value": type_no_wkt, "severity": "warning" if type_no_wkt else "ok", "details": "Non-wicket rows with populated dismissal_type"},
        {"section": "Wickets & Dismissals", "check": "is_wicket_true_missing_dismissed_player_id", "value": wkt_no_player, "severity": "warning" if wkt_no_player else "ok", "details": "Wicket rows lacking dismissed_player_id"},
        {"section": "Wickets & Dismissals", "check": "is_wicket_false_with_dismissed_player_id", "value": player_no_wkt, "severity": "warning" if player_no_wkt else "ok", "details": "Non-wicket rows with populated dismissed_player_id"},
        {"section": "Wickets & Dismissals", "check": "dismissed_player_neither_striker_nor_non_striker", "value": dismissed_not_on_crease, "severity": "warning" if dismissed_not_on_crease else "ok", "details": "Checks whether dismissed_player_id matches striker_id or non_striker_id"},
        {"section": "Wickets & Dismissals", "check": "dismissal_type_spelling_typo_obstracting", "value": obstruct_typo, "severity": "warning" if obstruct_typo else "ok", "details": "Rows spelled 'Obstracting the field' instead of 'Obstructing the field'"},
        {"section": "Player IDs on Delivery", "check": "striker_id_equals_non_striker_id", "value": striker_eq_nonstriker, "severity": "error" if striker_eq_nonstriker else "ok", "details": "Striker and non-striker cannot be the same player"},
        {"section": "Player IDs on Delivery", "check": "striker_id_equals_bowler_id", "value": striker_eq_bowler, "severity": "error" if striker_eq_bowler else "ok", "details": "Striker and bowler cannot be the same player"},
        {"section": "Bowling Attributes", "check": "missing_bowling_type", "value": bt_missing, "severity": "warning" if bt_missing else "ok", "details": f"Distinct bowling_type values: {balls['bowling_type'].nunique(dropna=True)}"},
        {"section": "Bowling Attributes", "check": "pace_or_spin_distribution", "value": balls["pace_or_spin"].nunique(dropna=False), "severity": "info", "details": ps_str},
        {"section": "Bowling Speed", "check": "bowl_speed_zero_sentinel", "value": speed_zero, "severity": "warning", "details": f"{round(speed_zero / len(balls) * 100, 2)}% of deliveries have bowl_speed == 0 (unrecorded radar speed)"},
        {"section": "Bowling Speed", "check": "bowl_speed_valid_50_to_165_kph", "value": int(len(speed_valid)), "severity": "info", "details": f"Coverage: {round(len(speed_valid) / len(balls) * 100, 2)}%; min={round(float(speed_valid.min()), 2) if len(speed_valid) else None}, median={round(float(speed_valid.median()), 2) if len(speed_valid) else None}, max={round(float(speed_valid.max()), 2) if len(speed_valid) else None}"},
        {"section": "Bowling Speed", "check": "bowl_speed_anomalous_nonzero", "value": speed_neg + speed_lt_50_pos + speed_gt_165, "severity": "warning" if (speed_neg + speed_lt_50_pos + speed_gt_165) else "ok", "details": f"<0: {speed_neg}; (0, 50): {speed_lt_50_pos}; >165: {speed_gt_165}; raw max={round(float(speed.max()), 2) if speed.notna().any() else None}"},
    ]
    return pd.DataFrame(rows)


def build_player_mapping_report(
    con: duckdb.DuckDBPyConnection,
    balls: pd.DataFrame,
    playing_xi: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    """Cross-check player_ids and player_names across ball_by_ball, playing_eleven, and mapping."""
    striker_ids = set(pd.to_numeric(balls["striker_id"], errors="coerce").dropna().astype(int))
    non_striker_ids = set(pd.to_numeric(balls["non_striker_id"], errors="coerce").dropna().astype(int))
    bowler_ids = set(pd.to_numeric(balls["bowler_id"], errors="coerce").dropna().astype(int))
    dismissed_ids = set(pd.to_numeric(balls["dismissed_player_id"], errors="coerce").dropna().astype(int))
    all_ball_player_ids = striker_ids | non_striker_ids | bowler_ids | dismissed_ids

    pxi_player_ids = set(pd.to_numeric(playing_xi["player_id"], errors="coerce").dropna().astype(int))
    map_player_ids = set(pd.to_numeric(mapping["player_id"], errors="coerce").dropna().astype(int))

    in_balls_not_map = sorted(all_ball_player_ids - map_player_ids)
    in_map_not_balls = sorted(map_player_ids - all_ball_player_ids)
    in_pxi_not_map = sorted(pxi_player_ids - map_player_ids)
    in_balls_not_pxi = sorted(all_ball_player_ids - pxi_player_ids)
    in_map_not_pxi = sorted(map_player_ids - pxi_player_ids)

    # Duplicate checks in mapping
    dup_map_exact = int(mapping.duplicated().sum())
    dup_map_comp_team_player = int(mapping.duplicated(["comp_id", "team_id", "player_id"]).sum())
    players_multi_teams_same_comp = int(
        (mapping.groupby(["comp_id", "player_id"])["team_id"].nunique() > 1).sum()
    )

    # Name consistency within mapping (1 player_id -> >1 player_name; 1 player_name -> >1 player_id)
    id_to_names_map = mapping.groupby("player_id")["player_name"].nunique(dropna=True)
    ids_multi_names_in_map = id_to_names_map[id_to_names_map > 1]

    name_to_ids_map = mapping.groupby("player_name")["player_id"].nunique(dropna=True)
    names_multi_ids_in_map = name_to_ids_map[name_to_ids_map > 1]

    # Cross-table name consistency: ball_by_ball (striker/non-striker/bowler) vs mapping
    name_conflicts_df = con.execute("""
        WITH ball_names AS (
            SELECT CAST(striker_id AS BIGINT) AS player_id, striker_name AS ball_name FROM ball_by_ball WHERE striker_id IS NOT NULL AND striker_name IS NOT NULL
            UNION
            SELECT CAST(non_striker_id AS BIGINT) AS player_id, non_striker_name AS ball_name FROM ball_by_ball WHERE non_striker_id IS NOT NULL AND non_striker_name IS NOT NULL
            UNION
            SELECT CAST(bowler_id AS BIGINT) AS player_id, bowler_name AS ball_name FROM ball_by_ball WHERE bowler_id IS NOT NULL AND bowler_name IS NOT NULL
        ),
        map_names AS (
            SELECT DISTINCT CAST(player_id AS BIGINT) AS player_id, player_name AS map_name
            FROM player_mapping
            WHERE player_id IS NOT NULL AND player_name IS NOT NULL
        )
        SELECT b.player_id, b.ball_name, m.map_name
        FROM ball_names b
        JOIN map_names m ON b.player_id = m.player_id
        WHERE TRIM(b.ball_name) <> TRIM(m.map_name)
        ORDER BY b.player_id
    """).df()

    # Players with >1 distinct name inside ball_by_ball itself
    ball_internal_conflicts_df = con.execute("""
        WITH ball_names AS (
            SELECT CAST(striker_id AS BIGINT) AS player_id, striker_name AS ball_name FROM ball_by_ball WHERE striker_id IS NOT NULL AND striker_name IS NOT NULL
            UNION
            SELECT CAST(non_striker_id AS BIGINT) AS player_id, non_striker_name AS ball_name FROM ball_by_ball WHERE non_striker_id IS NOT NULL AND non_striker_name IS NOT NULL
            UNION
            SELECT CAST(bowler_id AS BIGINT) AS player_id, bowler_name AS ball_name FROM ball_by_ball WHERE bowler_id IS NOT NULL AND bowler_name IS NOT NULL
        )
        SELECT player_id, COUNT(DISTINCT TRIM(ball_name)) AS name_count, STRING_AGG(DISTINCT TRIM(ball_name), ' | ') AS names
        FROM ball_names
        GROUP BY player_id
        HAVING COUNT(DISTINCT TRIM(ball_name)) > 1
        ORDER BY player_id
    """).df()

    # Missing competition-team-player relationship for players who actually played in a match
    missing_ctp_rel = con.execute("""
        WITH ball_ctp AS (
            SELECT DISTINCT m.comp_id, b.batting_team_id AS team_id, CAST(b.striker_id AS BIGINT) AS player_id
            FROM ball_by_ball b
            JOIN matches m ON b.match_id = m.match_id
            WHERE b.striker_id IS NOT NULL
            UNION
            SELECT DISTINCT m.comp_id, b.batting_team_id AS team_id, CAST(b.non_striker_id AS BIGINT) AS player_id
            FROM ball_by_ball b
            JOIN matches m ON b.match_id = m.match_id
            WHERE b.non_striker_id IS NOT NULL
            UNION
            SELECT DISTINCT m.comp_id, b.bowling_team_id AS team_id, CAST(b.bowler_id AS BIGINT) AS player_id
            FROM ball_by_ball b
            JOIN matches m ON b.match_id = m.match_id
            WHERE b.bowler_id IS NOT NULL
        ),
        map_ctp AS (
            SELECT DISTINCT comp_id, team_id, CAST(player_id AS BIGINT) AS player_id
            FROM player_mapping
        )
        SELECT b.comp_id, b.team_id, b.player_id
        FROM ball_ctp b
        LEFT JOIN map_ctp mp
          ON b.comp_id = mp.comp_id AND b.team_id = mp.team_id AND b.player_id = mp.player_id
        WHERE mp.player_id IS NULL
    """).df()

    # Comp/team pairs in mapping not in teams.csv
    map_ct_not_in_teams = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT comp_id, team_id FROM player_mapping
            EXCEPT
            SELECT DISTINCT comp_id, team_id FROM teams
        )
    """).fetchone()[0]

    # Sample details for readability
    name_conflict_samples = "; ".join(
        f"{r.player_id}: ball='{r.ball_name}' vs map='{r.map_name}'"
        for r in name_conflicts_df.head(10).itertuples()
    )
    same_name_multi_id_samples = "; ".join(
        f"'{nm}' -> {sorted(mapping.loc[mapping['player_name'] == nm, 'player_id'].unique().tolist())}"
        for nm in names_multi_ids_in_map.index[:10]
    )

    rows = [
        {"category": "Player Coverage", "check": "unique_player_ids_in_ball_by_ball", "count": len(all_ball_player_ids), "details": f"strikers: {len(striker_ids)}, non_strikers: {len(non_striker_ids)}, bowlers: {len(bowler_ids)}, dismissed: {len(dismissed_ids)}"},
        {"category": "Player Coverage", "check": "unique_player_ids_in_playing_eleven", "count": len(pxi_player_ids), "details": "Distinct player_id in playing_eleven.csv"},
        {"category": "Player Coverage", "check": "unique_player_ids_in_mapping", "count": len(map_player_ids), "details": f"Distinct player_name in mapping: {mapping['player_name'].nunique(dropna=True)}"},
        {"category": "Cross-Table Gaps", "check": "players_in_deliveries_missing_from_mapping", "count": len(in_balls_not_map), "details": f"IDs (up to 15): {in_balls_not_map[:15]}"},
        {"category": "Cross-Table Gaps", "check": "players_in_mapping_not_in_deliveries", "count": len(in_map_not_balls), "details": "Squad/bench players or players from matches without ball data"},
        {"category": "Cross-Table Gaps", "check": "players_in_playing_eleven_missing_from_mapping", "count": len(in_pxi_not_map), "details": f"IDs (up to 15): {in_pxi_not_map[:15]}"},
        {"category": "Cross-Table Gaps", "check": "players_in_deliveries_missing_from_playing_eleven", "count": len(in_balls_not_pxi), "details": f"IDs (up to 15): {in_balls_not_pxi[:15]}"},
        {"category": "Cross-Table Gaps", "check": "players_in_mapping_not_in_playing_eleven", "count": len(in_map_not_pxi), "details": "Squad players who did not appear in playing_eleven.csv"},
        {"category": "Duplicates & Keys", "check": "duplicate_exact_rows_in_mapping", "count": dup_map_exact, "details": "Exact duplicate rows in competition_team_player_mapping.csv"},
        {"category": "Duplicates & Keys", "check": "duplicate_comp_team_player_in_mapping", "count": dup_map_comp_team_player, "details": "Duplicate (comp_id, team_id, player_id) rows in mapping"},
        {"category": "Duplicates & Keys", "check": "players_listed_for_multiple_teams_in_same_comp", "count": players_multi_teams_same_comp, "details": "Same player_id mapped to >1 team_id within the same comp_id"},
        {"category": "Name Consistency", "check": "player_ids_with_multiple_names_in_mapping", "count": len(ids_multi_names_in_map), "details": f"IDs: {ids_multi_names_in_map.index.tolist()[:15]}"},
        {"category": "Name Consistency", "check": "player_names_shared_by_multiple_player_ids_in_mapping", "count": len(names_multi_ids_in_map), "details": same_name_multi_id_samples},
        {"category": "Name Consistency", "check": "player_ids_with_multiple_names_within_ball_by_ball", "count": len(ball_internal_conflicts_df), "details": "; ".join(f"{r.player_id}: {r.names}" for r in ball_internal_conflicts_df.head(10).itertuples())},
        {"category": "Name Consistency", "check": "player_name_mismatches_between_ball_by_ball_and_mapping", "count": len(name_conflicts_df), "details": name_conflict_samples},
        {"category": "Relationships", "check": "ball_comp_team_player_triples_missing_from_mapping", "count": len(missing_ctp_rel), "details": f"Unique player_ids affected: {missing_ctp_rel['player_id'].nunique() if len(missing_ctp_rel) else 0}; sample rows: {missing_ctp_rel.head(5).to_dict(orient='records')}"},
        {"category": "Relationships", "check": "mapping_comp_team_pairs_missing_from_teams_csv", "count": int(map_ct_not_in_teams), "details": "(comp_id, team_id) pairs in mapping absent from teams.csv"},
    ]
    return pd.DataFrame(rows)


def main() -> None:
    tables_raw, source_desc = load_raw_tables(preserve_literal_none=True)
    tables_default, _ = load_raw_tables(preserve_literal_none=False)

    print(f"Running Phase 2 Comprehensive Dataset Audit from: {source_desc}")

    con = duckdb.connect(database=":memory:")
    for name, df in tables_raw.items():
        con.register(name, df)

    dq_df, missing_df, dict_df = build_data_quality_and_missing_reports(tables_raw, tables_default)
    comp_df, unmatched_comp_counts = build_competition_summary(
        con, tables_raw["competitions"], tables_raw["matches"]
    )
    innings_df, recon_df = build_innings_and_match_reconciliation(
        con, tables_raw["matches"], tables_raw["ball_by_ball"], tables_raw["competitions"]
    )
    delivery_df = build_delivery_validation_report(tables_raw["ball_by_ball"])
    player_df = build_player_mapping_report(
        con,
        tables_raw["ball_by_ball"],
        tables_raw["playing_eleven"],
        tables_raw["player_mapping"],
    )

    # Append unmatched competition ID summary rows to match_reconciliation for full traceability
    unmatched_rows = pd.DataFrame([
        {
            "category": "Competition Links",
            "check": k,
            "count": v,
            "details": "Cross-table comp_id referential integrity check",
        }
        for k, v in unmatched_comp_counts.items()
    ])
    recon_df = pd.concat([recon_df, unmatched_rows], ignore_index=True)

    # Write all 8 required Phase 2 audit CSVs
    outputs = {
        "data_quality_report.csv": dq_df,
        "competition_summary.csv": comp_df,
        "match_reconciliation.csv": recon_df,
        "missing_values_report.csv": missing_df,
        "player_mapping_report.csv": player_df,
        "delivery_validation_report.csv": delivery_df,
        "innings_summary.csv": innings_df,
        "column_dictionary.csv": dict_df,
    }
    for fname, df in outputs.items():
        df.to_csv(OUT_DIR / fname, index=False)

    print("\n=== PHASE 2 AUDIT COMPLETE ===")
    print(f"Source: {source_desc}")
    print("\nFile Inventory:")
    print(dq_df[["file_name", "row_count", "column_count", "memory_usage_mb", "duplicate_full_rows", "duplicate_natural_key_rows"]].to_string(index=False))
    print("\nCompetition Category Totals:")
    cat_summary = (
        comp_df.groupby("eligibility_category", dropna=False)
        .agg(
            competitions=("comp_id", "nunique"),
            matches_meta=("matches_in_metadata", "sum"),
            matches_ball=("matches_with_ball_data", "sum"),
            deliveries=("total_deliveries", "sum"),
            legal_deliveries=("legal_deliveries", "sum"),
        )
        .reset_index()
    )
    print(cat_summary.to_string(index=False))
    print(f"\nGenerated {len(outputs)} audit reports in: {OUT_DIR.relative_to(ROOT)}")
    print("No raw files were modified. No pressure scores or player rankings were calculated.")


if __name__ == "__main__":
    main()

