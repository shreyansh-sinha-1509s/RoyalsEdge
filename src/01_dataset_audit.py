from pathlib import Path
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DATA_PACK_DIR = RAW_DIR / "Data Pack"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILENAMES = {
    "competitions": "competitions.csv",
    "teams": "teams.csv",
    "matches": "matches.csv",
    "ball_by_ball": "ball_by_ball.csv",
    "player_mapping": "competition_team_player_mapping.csv",
    "playing_eleven": "playing_eleven.csv",
}


def load_raw_tables() -> tuple[dict[str, pd.DataFrame], str]:
    """Load the six competition CSVs read-only from data/raw/Data Pack/, with optional ZIP fallback."""
    if DATA_PACK_DIR.is_dir():
        missing = [
            fname for fname in CSV_FILENAMES.values()
            if not (DATA_PACK_DIR / fname).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                f"Required CSVs missing from {DATA_PACK_DIR}: {', '.join(missing)}"
            )
        source_desc = f"extracted directory ({DATA_PACK_DIR.relative_to(ROOT)})"
        print(f"Reading source CSVs (read-only) from: {source_desc}")
        tables = {}
        for key, fname in CSV_FILENAMES.items():
            kwargs = {"low_memory": False} if key == "ball_by_ball" else {}
            tables[key] = pd.read_csv(DATA_PACK_DIR / fname, **kwargs)
        return tables, source_desc

    # Optional ZIP fallback if extracted Data Pack folder is unavailable
    zip_candidates = sorted(RAW_DIR.glob("*.zip"))
    if len(zip_candidates) != 1:
        raise FileNotFoundError(
            f"Extracted folder {DATA_PACK_DIR} not found, and expected exactly one fallback ZIP "
            f"in {RAW_DIR} (found {len(zip_candidates)})."
        )
    zip_path = zip_candidates[0]
    source_desc = f"ZIP archive ({zip_path.relative_to(ROOT)})"
    print(f"Reading source ZIP (read-only): {source_desc}")

    zip_entries = {key: f"Data Pack/{fname}" for key, fname in CSV_FILENAMES.items()}
    with zipfile.ZipFile(zip_path) as zf:
        available = {
            name for name in zf.namelist()
            if not name.startswith("__MACOSX/") and not Path(name).name.startswith("._")
        }
        missing = [p for p in zip_entries.values() if p not in available]
        if missing:
            raise FileNotFoundError("Required CSVs missing from ZIP: " + ", ".join(missing))
        tables = {}
        for key, entry in zip_entries.items():
            kwargs = {"low_memory": False} if key == "ball_by_ball" else {}
            tables[key] = pd.read_csv(zf.open(entry), **kwargs)
    return tables, source_desc


def main() -> None:
    tables, source_desc = load_raw_tables()
    competitions = tables["competitions"]
    teams = tables["teams"]
    matches = tables["matches"]
    mapping = tables["player_mapping"]
    playing_xi = tables["playing_eleven"]
    balls = tables["ball_by_ball"]

    # Inventory
    frames = [
        ("competitions", competitions),
        ("teams", teams),
        ("matches", matches),
        ("ball_by_ball", balls),
        ("player_mapping", mapping),
        ("playing_eleven", playing_xi),
    ]
    inventory = pd.DataFrame([{
        "file": name,
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_full_rows": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
    } for name, df in frames])
    inventory.to_csv(OUT_DIR / "01_file_inventory.csv", index=False)

    # Competition coverage and explicit IPL/T20I eligibility candidates
    coverage = (
        competitions.groupby(["match_format", "season"], dropna=False)
        .agg(competitions=("comp_id", "nunique"))
        .reset_index()
        .sort_values(["match_format", "season"])
    )
    coverage.to_csv(OUT_DIR / "02_competition_coverage.csv", index=False)
    competitions.to_csv(OUT_DIR / "03_all_competitions.csv", index=False)

    ipl = competitions[competitions["comp_name"].astype(str).str.fullmatch(r"IPL\s+\d{4}", case=False)]
    ipl.to_csv(OUT_DIR / "04_ipl_competitions.csv", index=False)

    t20_non_ipl = competitions[
        (competitions["match_format"].eq("T20")) & (~competitions["comp_id"].isin(ipl["comp_id"]))
    ]
    t20_non_ipl.to_csv(OUT_DIR / "05_non_ipl_t20_competitions.csv", index=False)

    t20i = competitions[competitions["match_format"].eq("T20I")]
    t20i.to_csv(OUT_DIR / "06_t20i_competitions.csv", index=False)

    # Match reconciliation
    match_ids = set(matches["match_id"].dropna().astype(int))
    ball_match_ids = set(balls["match_id"].dropna().astype(int))
    missing_ball_ids = sorted(match_ids - ball_match_ids)
    extra_ball_ids = sorted(ball_match_ids - match_ids)
    missing_matches = matches[matches["match_id"].isin(missing_ball_ids)].merge(
        competitions, on="comp_id", how="left"
    )
    missing_matches.to_csv(OUT_DIR / "07_matches_without_ball_data.csv", index=False)

    recon = pd.DataFrame([
        {"check": "metadata_unique_matches", "value": matches["match_id"].nunique()},
        {"check": "ball_data_unique_matches", "value": balls["match_id"].nunique()},
        {"check": "metadata_matches_without_ball_data", "value": len(missing_ball_ids)},
        {"check": "ball_matches_without_metadata", "value": len(extra_ball_ids)},
        {"check": "player_ids_in_mapping", "value": mapping["player_id"].nunique()},
        {"check": "unique_player_names_in_mapping", "value": mapping["player_name"].nunique()},
        {"check": "playing_xi_unique_matches", "value": playing_xi["match_id"].nunique()},
    ])
    recon.to_csv(OUT_DIR / "08_match_reconciliation.csv", index=False)

    # Delivery quality
    quality = pd.DataFrame([
        {"check": "ball_by_ball_rows", "value": len(balls)},
        {"check": "duplicate_full_delivery_rows", "value": int(balls.duplicated().sum())},
        {"check": "duplicate_match_innings_ball_keys", "value": int(balls.duplicated(["match_id", "innings", "innings_ball_num"]).sum())},
        {"check": "innings_values", "value": ", ".join(map(str, sorted(balls["innings"].dropna().unique())))},
        {"check": "innings_1_and_2_matches", "value": balls[balls["innings"].isin([1, 2])]["match_id"].nunique()},
        {"check": "matches_with_innings_3_or_4_super_over_records", "value": balls[balls["innings"] >= 3]["match_id"].nunique()},
        {"check": "missing_striker_id", "value": int(balls["striker_id"].isna().sum())},
        {"check": "missing_bowler_id", "value": int(balls["bowler_id"].isna().sum())},
        {"check": "missing_runs", "value": int(balls["runs"].isna().sum())},
        {"check": "missing_is_wicket", "value": int(balls["is_wicket"].isna().sum())},
    ])
    quality.to_csv(OUT_DIR / "09_delivery_quality_checks.csv", index=False)

    # Abandoned/no-ball matches and innings records
    abandoned = matches[matches["result"].astype(str).str.contains("abandoned", case=False, na=False)]
    abandoned.to_csv(OUT_DIR / "10_abandoned_matches.csv", index=False)

    innings_summary = (
        balls.groupby(["match_id", "innings"])
        .agg(
            deliveries=("innings_ball_num", "size"),
            batters=("striker_id", "nunique"),
            bowlers=("bowler_id", "nunique"),
            batter_runs=("runs", "sum"),
            wickets=("is_wicket", "sum"),
        )
        .reset_index()
    )
    innings_summary.to_csv(OUT_DIR / "11_innings_summary.csv", index=False)

    # Column missingness
    missingness = (
        balls.isna()
        .sum()
        .rename("missing_count")
        .to_frame()
        .assign(missing_pct=lambda d: (d["missing_count"] / len(balls) * 100).round(2))
        .reset_index(names="column")
    )
    missingness.to_csv(OUT_DIR / "12_ball_column_missingness.csv", index=False)

    print("\nDATASET AUDIT COMPLETE")
    print(f"Source: {source_desc}")
    print(f"Deliveries: {len(balls):,}")
    print(f"Matches in metadata: {matches['match_id'].nunique():,}")
    print(f"Matches in ball data: {balls['match_id'].nunique():,}")
    print(f"Metadata matches without ball data: {len(missing_ball_ids):,}")
    print(f"Player IDs in mapping: {mapping['player_id'].nunique():,}")
    print(f"IPL competitions: {len(ipl):,}; other T20 competitions: {len(t20_non_ipl):,}; T20I competitions: {len(t20i):,}")
    print(f"Matches with innings 3/4 records: {balls[balls['innings'] >= 3]['match_id'].nunique():,}")
    print(f"Reports saved to: {OUT_DIR.relative_to(ROOT)}")
    print("No pressure scores or player rankings have been calculated.")


if __name__ == "__main__":
    main()
