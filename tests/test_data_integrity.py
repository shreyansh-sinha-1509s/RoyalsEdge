"""Automated tests for dataset integrity, competition eligibility, Super Over separation, and player mapping."""

from pathlib import Path
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "Data Pack"
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"


def test_raw_files_unchanged() -> None:
    expected_sizes = {
        "ball_by_ball.csv": 41071837,
        "competitions.csv": 7624,
        "competition_team_player_mapping.csv": 462969,
        "matches.csv": 123864,
        "playing_eleven.csv": 966287,
        "teams.csv": 6922,
    }
    for fname, size in expected_sizes.items():
        assert (RAW_DIR / fname).stat().st_size == size


def test_competition_eligibility_and_exclusion() -> None:
    clean_del = pd.read_csv(PROCESSED_DIR / "clean_deliveries.csv", low_memory=False)
    clean_matches = pd.read_csv(PROCESSED_DIR / "clean_matches.csv", low_memory=False)
    excl_del = pd.read_csv(PROCESSED_DIR / "excluded_competition_deliveries.csv", low_memory=False)
    comp_master = pd.read_csv(PROCESSED_DIR / "competition_master.csv", low_memory=False)

    assert set(clean_del["eligibility_category"].unique()) == {"IPL", "T20I"}
    assert set(clean_matches["eligibility_category"].unique()) == {"IPL", "T20I"}
    assert not clean_del["comp_id"].isin([2670, 3289]).any()
    assert not clean_matches["comp_id"].isin([2670, 3289]).any()
    assert set(excl_del["comp_id"].unique()) == {2670, 3289}
    assert len(excl_del) == 6985
    assert int(comp_master["is_primary_eligible"].sum()) == 139


def test_super_over_separation_and_row_conservation() -> None:
    raw_balls = pd.read_csv(RAW_DIR / "ball_by_ball.csv", usecols=["match_id", "innings"])
    clean_del = pd.read_csv(PROCESSED_DIR / "clean_deliveries.csv", usecols=["match_id", "innings"])
    so_del = pd.read_csv(PROCESSED_DIR / "super_over_deliveries.csv", low_memory=False)
    excl_del = pd.read_csv(PROCESSED_DIR / "excluded_competition_deliveries.csv", usecols=["match_id", "innings"])

    # Clean primary deliveries contain ONLY regular innings 1 and 2
    assert set(clean_del["innings"].unique()) == {1, 2}
    # Super Over file contains ONLY innings >= 3
    assert (so_del["innings"] >= 3).all()
    assert len(so_del) == 38

    # Exact row conservation: clean_regular + primary_super_over + excluded_comp == raw total
    prim_so = int(so_del["is_primary_eligible"].astype(str).str.lower().eq("true").sum())
    assert len(clean_del) + prim_so + len(excl_del) == len(raw_balls) == 200999


def test_player_mapping_integrity() -> None:
    clean_del = pd.read_csv(
        PROCESSED_DIR / "clean_deliveries.csv",
        usecols=["striker_id", "non_striker_id", "bowler_id", "striker_display_name", "bowler_display_name"],
    )
    pm = pd.read_csv(PROCESSED_DIR / "player_master.csv", low_memory=False)

    # Unique primary key on player_id
    assert pm["player_id"].is_unique
    assert len(pm) == 1217

    # 100% ID coverage for all primary delivery participants
    pm_ids = set(pm["player_id"])
    assert set(clean_del["striker_id"]).issubset(pm_ids)
    assert set(clean_del["non_striker_id"]).issubset(pm_ids)
    assert set(clean_del["bowler_id"]).issubset(pm_ids)
    assert clean_del["striker_display_name"].notna().all()
    assert clean_del["bowler_display_name"].notna().all()

    # Shared-name distinct individuals were NOT merged
    assert {4722, 20172}.issubset(pm_ids)  # Two distinct Rashid Khans
    assert {6922, 7446}.issubset(pm_ids)   # Two distinct Abdul Samads
    assert {7338, 28756}.issubset(pm_ids)  # Two distinct Haider Alis

    # Cross-table mismatch 4458 standardized cleanly while keeping original names
    r4458 = pm.loc[pm["player_id"] == 4458].iloc[0]
    assert r4458["standardized_display_name"] == "Aneurin Donald"
    assert "AHT Donald" in str(r4458["mapping_source_names"])


def test_innings_score_reconciliation() -> None:
    clean_del = pd.read_csv(
        PROCESSED_DIR / "clean_deliveries.csv",
        usecols=["match_id", "innings", "total_runs", "bowler_conceded_runs", "non_bowler_extras_runs", "is_legal_delivery"],
    )
    inn_sum = pd.read_csv(PROCESSED_DIR / "innings_summary.csv", low_memory=False)
    recon = pd.read_csv(OUT_DIR / "reconciliation_checks.csv")

    recalc = clean_del.groupby(["match_id", "innings"], as_index=False)["total_runs"].sum()
    merged = inn_sum[["match_id", "innings", "total_runs"]].merge(
        recalc, on=["match_id", "innings"], suffixes=("_summary", "_recalc")
    )
    assert len(merged) == len(inn_sum)
    assert (merged["total_runs_summary"] == merged["total_runs_recalc"]).all()
    assert (inn_sum["runs_formula_diff"] == 0).all()
    assert (inn_sum["bowler_runs_reconcile_diff"] == 0).all()
    assert (inn_sum["wickets_reconcile_diff"] == 0).all()
    assert (inn_sum["legal_ball_reconcile_diff"] == 0).all()

    # No FAIL checks in reconciliation_checks.csv
    assert (recon["status"] == "FAIL").sum() == 0

