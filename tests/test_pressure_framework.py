"""Automated tests for Phase 4 Pressure Framework, Thresholds, Leakage Guards, and Validation."""

from pathlib import Path
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
CHART_DIR = OUT_DIR / "charts"

CHASE_T = (32.0, 50.0, 74.0)
I1_T = (30.0, 45.0, 61.0)
BOWL_T = (47.0, 60.0, 68.0)


@pytest.fixture(scope="module")
def p_df() -> pd.DataFrame:
    df = pd.read_csv(
        PROCESSED_DIR / "pressure_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    for col in ["is_super_over", "is_primary_eligible", "chase_context_available", "chase_target_integrity_ok"]:
        df[col] = df[col].astype(str).str.lower().eq("true")
    return df


def test_only_eligible_regular_deliveries(p_df: pd.DataFrame) -> None:
    assert len(p_df) == 193988
    assert set(p_df["eligibility_category"].unique()) == {"IPL", "T20I"}
    assert not p_df["comp_id"].isin([2670, 3289]).any()
    assert set(p_df["innings"].unique()) == {1, 2}
    assert (~p_df["is_super_over"]).all()


def test_all_indices_bounded_0_to_100(p_df: pd.DataFrame) -> None:
    for col in [
        "chase_pressure_index",
        "first_innings_pressure_index",
        "bowling_pressure_index",
        "model_a_chase_pressure",
        "model_a_first_innings_pressure",
        "model_a_bowling_pressure",
        "model_b_chase_pressure",
        "model_b_first_innings_pressure",
        "model_b_bowling_pressure",
        "model_c_chase_pressure",
        "model_c_first_innings_pressure",
        "model_c_bowling_pressure",
    ]:
        s = p_df[col].dropna()
        assert len(s) > 0, f"Column {col} has no valid values"
        assert (s >= 0.0).all() and (s <= 100.0).all(), f"Column {col} out of [0, 100] bounds"


def test_missing_and_corrupted_contexts_marked_unavailable(p_df: pd.DataFrame) -> None:
    # Innings 1 must NEVER have a chase_pressure_index; Innings 2 must NEVER have first_innings_pressure_index
    assert p_df.loc[p_df["innings"] == 1, "chase_pressure_index"].isna().all()
    assert p_df.loc[p_df["innings"] == 2, "first_innings_pressure_index"].isna().all()

    # Unavailable DLS / missing revised overs must have NaN indices and UNAVAILABLE levels
    unavail = p_df[p_df["scheduled_balls_source"] == "unavailable_dls_or_reduced_missing"]
    assert len(unavail) == 1539
    assert unavail["batting_pressure_index"].isna().all()
    assert unavail["bowling_pressure_index"].isna().all()
    assert (unavail["batting_pressure_level"] == "UNAVAILABLE").all()
    assert (unavail["bowling_pressure_level"] == "UNAVAILABLE").all()

    # Corrupted revised_target rows in match 48610 (cum_score_before >= target_runs) must be UNAVAILABLE
    bad_tgt = p_df[~p_df["chase_target_integrity_ok"]]
    assert len(bad_tgt) == 12
    assert bad_tgt["chase_pressure_index"].isna().all()
    assert bad_tgt["bowling_pressure_index"].isna().all()


def test_classifications_match_documented_thresholds(p_df: pd.DataFrame) -> None:
    for idx_col, lvl_col, (t1, t2, t3) in [
        ("chase_pressure_index", "chase_pressure_level", CHASE_T),
        ("first_innings_pressure_index", "first_innings_pressure_level", I1_T),
        ("bowling_pressure_index", "bowling_pressure_level", BOWL_T),
    ]:
        valid = p_df[idx_col].notna()
        s = p_df.loc[valid, idx_col]
        lvls = p_df.loc[valid, lvl_col]
        assert (lvls[s < t1] == "LOW PRESSURE").all()
        assert (lvls[(s >= t1) & (s < t2)] == "MODERATE PRESSURE").all()
        assert (lvls[(s >= t2) & (s < t3)] == "HIGH PRESSURE").all()
        assert (lvls[s >= t3] == "EXTREME PRESSURE").all()
        assert (p_df.loc[~valid, lvl_col] == "UNAVAILABLE").all()


def test_three_frameworks_are_distinct_and_cricket_valid(p_df: pd.DataFrame) -> None:
    i2 = p_df[p_df["chase_pressure_index"].notna()]
    i1 = p_df[p_df["first_innings_pressure_index"].notna()]
    # Opposing wicket-resource polarity guarantees batting != bowling pressure
    assert i1["first_innings_pressure_index"].corr(i1["bowling_pressure_index"]) < -0.30
    assert i2["chase_pressure_index"].corr(i2["bowling_pressure_index"]) < 0.0

    # High RRR + lost wickets >> Low RRR + wickets in hand
    hard = i2.loc[(i2["required_run_rate_before"] >= 14) & (i2["wickets_before"] >= 5), "chase_pressure_index"].mean()
    easy = i2.loc[(i2["required_run_rate_before"] <= 6) & (i2["wickets_before"] <= 2), "chase_pressure_index"].mean()
    assert hard > 75.0 and easy < 25.0


def test_leakage_validation_and_sensitivity_outputs_pass() -> None:
    leak = pd.read_csv(OUT_DIR / "pressure_leakage_checks.csv")
    val = pd.read_csv(OUT_DIR / "pressure_validation_results.csv")
    sens = pd.read_csv(OUT_DIR / "pressure_sensitivity_analysis.csv")
    assert (leak["status"] == "PASS").all(), f"Leakage failure:\n{leak[leak['status'] != 'PASS']}"
    assert (val["status"] == "PASS").all(), f"Validation failure:\n{val[val['status'] != 'PASS']}"
    wt_sens = sens[sens["scenario"].str.startswith("Weight_")]
    assert (wt_sens["spearman_corr_vs_baseline"] > 0.90).all()


def test_all_nine_charts_and_required_outputs_exist() -> None:
    expected_csvs = [
        PROCESSED_DIR / "pressure_deliveries.csv",
        PROCESSED_DIR / "pressure_innings_summary.csv",
        PROCESSED_DIR / "pressure_match_summary.csv",
        OUT_DIR / "pressure_distribution.csv",
        OUT_DIR / "pressure_level_summary.csv",
        OUT_DIR / "pressure_component_summary.csv",
        OUT_DIR / "pressure_threshold_analysis.csv",
        OUT_DIR / "pressure_model_comparison.csv",
        OUT_DIR / "pressure_sensitivity_analysis.csv",
        OUT_DIR / "pressure_validation_results.csv",
        OUT_DIR / "pressure_exposure_summary.csv",
        OUT_DIR / "pressure_leakage_checks.csv",
    ]
    for p in expected_csvs:
        assert p.is_file() and p.stat().st_size > 0, f"Missing or empty: {p}"

    expected_charts = [
        "01_pressure_score_distribution.png",
        "02_pressure_category_distribution.png",
        "03_pressure_by_match_phase.png",
        "04_pressure_by_wickets_remaining.png",
        "05_pressure_by_required_run_rate.png",
        "06_ipl_vs_t20i_pressure_comparison.png",
        "07_first_innings_vs_chase_comparison.png",
        "08_model_comparison.png",
        "09_threshold_sensitivity.png",
    ]
    for c in expected_charts:
        cp = CHART_DIR / c
        assert cp.is_file() and cp.stat().st_size > 5000, f"Missing or invalid chart: {cp}"

