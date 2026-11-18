"""Automated tests for Phase 6 Final Player Rankings, Robustness, and Submission Package Consistency."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "Data Pack"
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs"
SUB_DIR = ROOT / "submission"
CHART_DIR = OUT_DIR / "charts"


@pytest.fixture(scope="module")
def p6() -> dict[str, pd.DataFrame]:
    return {
        "bat_r": pd.read_csv(PROCESSED_DIR / "final_batting_rankings.csv", low_memory=False),
        "bowl_r": pd.read_csv(PROCESSED_DIR / "final_bowling_rankings.csv", low_memory=False),
        "bat_c": pd.read_csv(PROCESSED_DIR / "batting_ranking_candidates.csv", low_memory=False),
        "bowl_c": pd.read_csv(PROCESSED_DIR / "bowling_ranking_candidates.csv", low_memory=False),
        "elig": pd.read_csv(PROCESSED_DIR / "ranking_eligibility_audit.csv", low_memory=False),
        "comp": pd.read_csv(PROCESSED_DIR / "ranking_score_components.csv", low_memory=False),
        "unc": pd.read_csv(PROCESSED_DIR / "ranking_uncertainty.csv", low_memory=False),
        "pm": pd.read_csv(PROCESSED_DIR / "player_master.csv", low_memory=False),
        "rob": pd.read_csv(OUT_DIR / "ranking_robustness.csv", low_memory=False),
        "ov": pd.read_csv(OUT_DIR / "top10_overlap_analysis.csv", low_memory=False),
        "val": pd.read_csv(OUT_DIR / "ranking_validation_results.csv", low_memory=False),
        "sub_bat": pd.read_csv(SUB_DIR / "RR_Performance_Lab_Top_10_Batters.csv", low_memory=False),
        "sub_bowl": pd.read_csv(SUB_DIR / "RR_Performance_Lab_Top_10_Bowlers.csv", low_memory=False),
    }


def test_no_duplicates_and_exact_rank_ordering(p6: dict[str, pd.DataFrame]) -> None:
    for key in ["bat_r", "bowl_r", "sub_bat", "sub_bowl"]:
        df = p6[key]
        assert df["player_id"].is_unique, f"Duplicate player_id in {key}"
        assert df["player_name"].is_unique, f"Duplicate player_name in {key}"
        assert list(df["rank"]) == list(range(1, len(df) + 1))
        assert df["final_ranking_score"].is_monotonic_decreasing
        assert df["final_ranking_score"].between(0.0, 100.0).all()

    assert len(p6["sub_bat"]) == 10
    assert len(p6["sub_bowl"]) == 10


def test_identity_eligibility_and_no_missing_reliability_as_zero(p6: dict[str, pd.DataFrame]) -> None:
    pm_ids = set(p6["pm"]["player_id"])
    br, wr = p6["bat_r"], p6["bowl_r"]
    bc, wc = p6["bat_c"], p6["bowl_c"]

    assert set(br["player_id"]).issubset(pm_ids)
    assert set(wr["player_id"]).issubset(pm_ids)

    # Strict primary cutoffs enforced
    assert (br["pressure_balls_faced"] >= 80).all()
    assert (br["pressure_innings"] >= 10).all()
    assert (br["pressure_matches"] >= 10).all()
    assert (wr["pressure_legal_balls"] >= 90).all()
    assert (wr["pressure_innings"] >= 10).all()
    assert (wr["pressure_matches"] >= 10).all()

    # No missing reliability imputed as zero
    assert br["reliability_score"].notna().all()
    assert wr["reliability_score"].notna().all()
    assert bc.loc[bc["evidence_tier"] == "INSUFFICIENT_EVIDENCE", "reliability_score"].isna().all()
    assert wc.loc[wc["evidence_tier"] == "INSUFFICIENT_EVIDENCE", "reliability_score"].isna().all()


def test_metric_directions_uncertainty_and_robustness_consistency(p6: dict[str, pd.DataFrame]) -> None:
    br, wr, rob, val, unc = p6["bat_r"], p6["bowl_r"], p6["rob"], p6["val"], p6["unc"]

    # Correct direction: Top 10 batters have positive EB impact and above-median SR; Top 10 bowlers have positive EB impact and below-median economy
    assert (br.head(10)["eb_pressure_impact"] > 0).all()
    assert br.head(10)["pressure_strike_rate"].mean() > br["pressure_strike_rate"].median()
    assert (wr.head(10)["eb_pressure_impact"] > 0).all()
    assert wr.head(10)["pressure_economy"].mean() < wr["pressure_economy"].median()

    # Uncertainty preserved
    assert (unc["impact_ci95_high"] >= unc["impact_ci95_low"]).all()
    assert (unc["mc_rank_p95"] >= unc["mc_rank_p05"]).all()
    assert p6["sub_bat"]["impact_ci95_low"].notna().all()
    assert p6["sub_bowl"]["impact_ci95_low"].notna().all()

    # Validation & robustness pass
    assert (val["status"] == "PASS").all()
    assert len(rob) == 14
    assert (rob["spearman_corr_vs_primary"] > 0.85).all()


def test_csv_excel_markdown_and_pdf_consistency(p6: dict[str, pd.DataFrame]) -> None:
    sub_bat, sub_bowl = p6["sub_bat"], p6["sub_bowl"]
    br10, wr10 = p6["bat_r"].head(10), p6["bowl_r"].head(10)

    # Submission CSVs match processed Top 10 exactly
    assert list(sub_bat["player_id"]) == list(br10["player_id"])
    assert list(sub_bowl["player_id"]) == list(wr10["player_id"])

    # Excel workbook sheets match CSVs exactly
    xlsx_path = SUB_DIR / "RR_Performance_Lab_Final_Rankings.xlsx"
    assert xlsx_path.is_file() and xlsx_path.stat().st_size > 10000
    xl_bat = pd.read_excel(xlsx_path, sheet_name="Top_10_Batters")
    xl_bowl = pd.read_excel(xlsx_path, sheet_name="Top_10_Bowlers")
    assert list(xl_bat["player_id"]) == list(sub_bat["player_id"])
    assert list(xl_bat["player_name"]) == list(sub_bat["player_name"])
    assert list(xl_bowl["player_id"]) == list(sub_bowl["player_id"])
    assert list(xl_bowl["player_name"]) == list(sub_bowl["player_name"])

    # Markdown report and README_SUBMISSION contain every exact Top 10 batter & bowler name
    md_txt = (SUB_DIR / "RR_Performance_Lab_Methodology_Report.md").read_text(encoding="utf-8")
    rm_txt = (SUB_DIR / "README_SUBMISSION.md").read_text(encoding="utf-8")
    for nm in list(sub_bat["player_name"]) + list(sub_bowl["player_name"]):
        assert nm in md_txt, f"Missing {nm} in Methodology Report MD"
        assert nm in rm_txt, f"Missing {nm} in README_SUBMISSION.md"

    # Both PDFs exist, are valid PDF headers (%PDF-), and non-trivial in size
    for pdf_name in [
        "RR_Performance_Lab_Methodology_Report.pdf",
        "RR_Performance_Lab_Executive_Summary.pdf",
    ]:
        pdf_p = SUB_DIR / pdf_name
        assert pdf_p.is_file() and pdf_p.stat().st_size > 25000
        raw_bytes = pdf_p.read_bytes()
        assert raw_bytes.startswith(b"%PDF-")

    # All 7 Phase 6 charts exist
    for cname in [
        "20_final_batting_rankings.png",
        "21_final_bowling_rankings.png",
        "22_final_perf_vs_reliability.png",
        "23_exposure_vs_ranking_score.png",
        "24_shortlist_confidence_intervals.png",
        "25_top10_overlap_methods.png",
        "26_ranking_sensitivity.png",
    ]:
        cp = CHART_DIR / cname
        assert cp.is_file() and cp.stat().st_size > 5000


def test_raw_competition_files_remain_unchanged() -> None:
    expected = {
        "ball_by_ball.csv": 41071837,
        "competitions.csv": 7624,
        "competition_team_player_mapping.csv": 462969,
        "matches.csv": 123864,
        "playing_eleven.csv": 966287,
        "teams.csv": 6922,
    }
    for fname, sz in expected.items():
        assert (RAW_DIR / fname).stat().st_size == sz

