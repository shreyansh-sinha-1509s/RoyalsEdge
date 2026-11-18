"""Automated tests for Phase 5 Player Performance, Reliability, Uncertainty, and Validation."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
CHART_DIR = OUT_DIR / "charts"


@pytest.fixture(scope="module")
def p5_data() -> dict[str, pd.DataFrame]:
    p_del = pd.read_csv(
        PROCESSED_DIR / "pressure_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    for c in ["is_legal_delivery", "is_batter_ball_faced", "is_wicket_event", "is_bowler_wicket", "is_four", "is_six"]:
        p_del[c] = p_del[c].astype(str).str.lower().eq("true")
    return {
        "p_del": p_del,
        "pm": pd.read_csv(PROCESSED_DIR / "player_master.csv", low_memory=False),
        "bat_perf": pd.read_csv(PROCESSED_DIR / "player_batting_performance.csv", low_memory=False),
        "bowl_perf": pd.read_csv(PROCESSED_DIR / "player_bowling_performance.csv", low_memory=False),
        "bat_bk": pd.read_csv(PROCESSED_DIR / "player_batting_pressure_breakdown.csv", low_memory=False),
        "bowl_bk": pd.read_csv(PROCESSED_DIR / "player_bowling_pressure_breakdown.csv", low_memory=False),
        "bat_rel": pd.read_csv(PROCESSED_DIR / "player_batting_reliability.csv", low_memory=False),
        "bowl_rel": pd.read_csv(PROCESSED_DIR / "player_bowling_reliability.csv", low_memory=False),
        "exposure": pd.read_csv(PROCESSED_DIR / "player_pressure_exposure.csv", low_memory=False),
        "pvn": pd.read_csv(PROCESSED_DIR / "player_pressure_vs_nonpressure.csv", low_memory=False),
        "season": pd.read_csv(PROCESSED_DIR / "player_season_performance.csv", low_memory=False),
        "boot": pd.read_csv(OUT_DIR / "player_bootstrap_uncertainty.csv", low_memory=False),
        "val": pd.read_csv(OUT_DIR / "player_validation_results.csv", low_memory=False),
    }


def test_batting_metrics_and_balls_faced_conservation(p5_data: dict[str, pd.DataFrame]) -> None:
    p_del, bp, bk = p5_data["p_del"], p5_data["bat_perf"], p5_data["bat_bk"]
    valid = p_del[p_del["batting_pressure_index"].notna()]

    # Total balls faced excludes wides and matches source exactly (zero duplicate aggregation)
    exp_bf = int(valid["is_batter_ball_faced"].sum())
    assert int(bp["overall_balls_faced"].sum()) == exp_bf
    assert int(bk["balls_faced"].sum()) == exp_bf

    # Total batter runs matches source exactly
    exp_runs = int(valid.loc[valid["is_batter_ball_faced"], "batter_runs"].sum())
    assert int(bp["overall_runs"].sum()) == exp_runs
    assert int(bk["runs"].sum()) == exp_runs

    # Spot-check SR, average, and boundary % formulas on all batters with pressure balls
    sub = bp[bp["pressure_balls_faced"] > 0]
    assert np.allclose(sub["pressure_strike_rate"], sub["pressure_runs"] / sub["pressure_balls_faced"] * 100.0, atol=0.01)
    with_dism = sub[sub["pressure_dismissals"] > 0]
    assert np.allclose(with_dism["pressure_average"], with_dism["pressure_runs"] / with_dism["pressure_dismissals"], atol=0.01)
    no_dism = sub[sub["pressure_dismissals"] == 0]
    assert no_dism["pressure_average"].isna().all()


def test_bowling_metrics_legal_balls_and_wicket_attribution(p5_data: dict[str, pd.DataFrame]) -> None:
    p_del, wp, wk = p5_data["p_del"], p5_data["bowl_perf"], p5_data["bowl_bk"]
    valid = p_del[p_del["bowling_pressure_index"].notna()]

    # Exact legal balls, runs conceded, and bowler-credited wickets conservation
    assert int(wp["overall_legal_balls"].sum()) == int(valid["is_legal_delivery"].sum())
    assert int(wk["legal_balls"].sum()) == int(valid["is_legal_delivery"].sum())
    assert int(wp["overall_runs_conceded"].sum()) == int(valid["bowler_conceded_runs"].sum())
    assert int(wp["overall_wickets"].sum()) == int(valid["is_bowler_wicket"].sum())

    # Spot-check economy rate and wicket frequency formulas
    sub = wp[wp["pressure_legal_balls"] > 0]
    assert np.allclose(sub["pressure_economy"], sub["pressure_runs_conceded"] * 6.0 / sub["pressure_legal_balls"], atol=0.01)
    assert np.allclose(sub["pressure_wicket_frequency"], sub["pressure_wickets"] / sub["pressure_legal_balls"], atol=1e-4)
    no_wkt = sub[sub["pressure_wickets"] == 0]
    assert no_wkt["pressure_bowling_average"].isna().all()
    assert no_wkt["pressure_bowling_strike_rate"].isna().all()


def test_player_identity_and_no_contamination(p5_data: dict[str, pd.DataFrame]) -> None:
    pm, bp, wp, p_del = p5_data["pm"], p5_data["bat_perf"], p5_data["bowl_perf"], p5_data["p_del"]
    pm_ids = set(pm["player_id"])
    assert bp["player_id"].is_unique and wp["player_id"].is_unique
    assert set(bp["player_id"]).issubset(pm_ids)
    assert set(wp["player_id"]).issubset(pm_ids)
    # Shared names not merged
    assert {6922, 7446}.issubset(set(bp["player_id"]))
    assert {7338, 28756}.issubset(set(bp["player_id"]))
    # No Super Overs or excluded comps in underlying pressure deliveries
    assert not p_del["comp_id"].isin([2670, 3289]).any()
    assert not (p_del["innings"] >= 3).any()


def test_pressure_levels_and_missing_context_exclusion(p5_data: dict[str, pd.DataFrame]) -> None:
    p_del, bk, wk = p5_data["p_del"], p5_data["bat_bk"], p5_data["bowl_bk"]
    assert set(bk["pressure_level"].unique()) == {"LOW PRESSURE", "MODERATE PRESSURE", "HIGH PRESSURE", "EXTREME PRESSURE"}
    assert set(wk["pressure_level"].unique()) == {"LOW PRESSURE", "MODERATE PRESSURE", "HIGH PRESSURE", "EXTREME PRESSURE"}
    # UNAVAILABLE rows (1,551) must not appear in LOW PRESSURE
    src_low_bf = int(p_del.loc[p_del["batting_pressure_level"] == "LOW PRESSURE", "is_batter_ball_faced"].sum())
    assert int(bk.loc[bk["pressure_level"] == "LOW PRESSURE", "balls_faced"].sum()) == src_low_bf


def test_reliability_bounds_eligibility_and_bootstrap_cis(p5_data: dict[str, pd.DataFrame]) -> None:
    br, wr, boot = p5_data["bat_rel"], p5_data["bowl_rel"], p5_data["boot"]

    for rel, min_b, min_i in [(br, 80, 10), (wr, 90, 10)]:
        # Bounded [0, 100]
        s_rel = rel["reliability_score"].dropna()
        s_perf = rel["performance_score"].dropna()
        s_ev = rel["evidence_strength_score"].dropna()
        assert s_rel.between(0, 100).all()
        assert s_perf.between(0, 100).all()
        assert s_ev.between(0, 100).all()

        # Insufficient evidence players must NEVER receive fabricated reliability scores
        insuff = rel[rel["evidence_tier"] == "INSUFFICIENT_EVIDENCE"]
        assert len(insuff) > 0
        assert insuff["reliability_score"].isna().all()

        # Primary eligibility strictly enforces minimum balls, innings, and matches
        prim = rel[rel["is_primary_eligible"]]
        assert (prim["pressure_balls"] >= min_b).all()
        assert (prim["pressure_innings"] >= min_i).all()
        assert (prim["pressure_matches"] >= min_i).all()

        # Reliability must NOT simply reward delivery volume
        assert abs(float(prim["reliability_score"].corr(prim["pressure_balls"]))) < 0.50

    # Match-clustered bootstrap CIs must be properly ordered (ci95_low <= point <= ci95_high or valid width > 0)
    b_valid = boot.dropna(subset=["ci95_low", "ci95_high", "ci95_width"])
    assert len(b_valid) > 400
    assert (b_valid["ci95_high"] >= b_valid["ci95_low"]).all()
    assert (b_valid["ci95_width"] >= 0).all()
    assert (b_valid["bootstrap_se"] >= 0).all()


def test_pressure_vs_nonpressure_and_validation_outputs(p5_data: dict[str, pd.DataFrame]) -> None:
    pvn, val = p5_data["pvn"], p5_data["val"]
    assert set(pvn["discipline"].unique()) == {"batting", "bowling"}
    assert (pvn["context_impact_diff_ci95_high"] >= pvn["context_impact_diff_ci95_low"]).all()
    assert (val["status"] == "PASS").all(), f"Validation failures:\n{val[val['status'] != 'PASS']}"


def test_all_required_phase5_outputs_and_ten_charts_exist() -> None:
    req_processed = [
        "player_batting_performance.csv",
        "player_bowling_performance.csv",
        "player_batting_pressure_breakdown.csv",
        "player_bowling_pressure_breakdown.csv",
        "player_batting_reliability.csv",
        "player_bowling_reliability.csv",
        "player_pressure_exposure.csv",
        "player_pressure_vs_nonpressure.csv",
        "player_season_performance.csv",
    ]
    for f in req_processed:
        p = PROCESSED_DIR / f
        assert p.is_file() and p.stat().st_size > 0, f"Missing processed file: {f}"

    req_outputs = [
        "batting_metric_summary.csv",
        "bowling_metric_summary.csv",
        "player_exposure_distribution.csv",
        "reliability_distribution.csv",
        "minimum_exposure_sensitivity.csv",
        "player_bootstrap_uncertainty.csv",
        "pressure_vs_nonpressure_summary.csv",
        "player_model_robustness.csv",
        "player_temporal_validation.csv",
        "player_validation_results.csv",
    ]
    for f in req_outputs:
        p = OUT_DIR / f
        assert p.is_file() and p.stat().st_size > 0, f"Missing analysis output: {f}"

    req_charts = [
        "10_batting_pressure_perf_distribution.png",
        "11_bowling_pressure_perf_distribution.png",
        "12_batting_perf_by_pressure_category.png",
        "13_bowling_perf_by_pressure_category.png",
        "14_pressure_vs_nonpressure_batting.png",
        "15_pressure_vs_nonpressure_bowling.png",
        "16_exposure_vs_performance.png",
        "17_reliability_vs_performance.png",
        "18_bootstrap_uncertainty_comparison.png",
        "19_seasonal_consistency.png",
    ]
    for c in req_charts:
        p = CHART_DIR / c
        assert p.is_file() and p.stat().st_size > 5000, f"Missing chart: {c}"

