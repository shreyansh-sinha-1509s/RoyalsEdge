"""Automated tests for pre-delivery feature engineering, anti-leakage, and DLS handling."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def fe_df() -> pd.DataFrame:
    df = pd.read_csv(
        PROCESSED_DIR / "clean_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    for col in [
        "is_legal_delivery", "is_wicket_event", "is_retired_hurt",
        "is_batter_ball_faced", "chase_context_available",
    ]:
        df[col] = df[col].astype(str).str.lower().eq("true")
    return df


def test_pre_delivery_cumulative_score_and_wickets_no_leakage(fe_df: pd.DataFrame) -> None:
    # First ball of every innings starts at 0 runs, 0 wickets, 0 legal balls (use head(1) so NaN is not skipped)
    firsts = fe_df.groupby(["match_id", "innings"], sort=False).head(1)
    assert (firsts["cum_score_before"] == 0).all()
    assert (firsts["wickets_before"] == 0).all()
    assert (firsts["legal_balls_before"] == 0).all()
    assert firsts["current_run_rate_before"].isna().all()

    # Last ball pre-delivery state + last ball event == innings total
    lasts = fe_df.groupby(["match_id", "innings"], sort=False).tail(1).set_index(["match_id", "innings"])
    totals = fe_df.groupby(["match_id", "innings"], sort=False).agg(
        tot_runs=("total_runs", "sum"),
        tot_wkts=("is_wicket_event", "sum"),
        tot_legal=("is_legal_delivery", "sum"),
    )
    assert (lasts["cum_score_before"] + lasts["total_runs"] == totals["tot_runs"]).all()
    assert (lasts["wickets_before"] + lasts["is_wicket_event"].astype(int) == totals["tot_wkts"]).all()
    assert (lasts["legal_balls_before"] + lasts["is_legal_delivery"].astype(int) == totals["tot_legal"]).all()

    # Verify retired hurt does NOT increment wickets_before on next ball (match 40725, Sanju Samson)
    m40725 = fe_df[(fe_df["match_id"] == 40725) & (fe_df["innings"] == 2)].reset_index(drop=True)
    rh_idx = m40725.index[m40725["is_retired_hurt"]].tolist()
    assert len(rh_idx) == 1
    i = rh_idx[0]
    assert m40725.loc[i + 1, "wickets_before"] == m40725.loc[i, "wickets_before"]


def test_legal_balls_remaining_and_phase_boundaries(fe_df: pd.DataFrame) -> None:
    # Standard 20-over innings starts with 120 legal balls remaining and Powerplay phase
    std = fe_df[fe_df["scheduled_balls_source"] == "standard_20_overs"]
    std_first = std.groupby(["match_id", "innings"]).first()
    assert (std_first["legal_balls_remaining_before"] == 120).all()
    assert (std_first["match_phase"] == "Powerplay").all()

    # Exact standard T20 phase boundaries: <36 Powerplay, 36..89 Middle, >=90 Death
    assert (std.loc[std["legal_balls_before"] < 36, "match_phase"] == "Powerplay").all()
    assert (std.loc[(std["legal_balls_before"] >= 36) & (std["legal_balls_before"] < 90), "match_phase"] == "Middle").all()
    assert (std.loc[std["legal_balls_before"] >= 90, "match_phase"] == "Death").all()

    # Known revised-overs match: IPL 2023 Final (match_id 21586, 15-over chase = 90 balls, revised_target = 171)
    m21586_i2 = fe_df[(fe_df["match_id"] == 21586) & (fe_df["innings"] == 2)].reset_index(drop=True)
    assert m21586_i2.loc[0, "scheduled_legal_balls"] == 90
    assert m21586_i2.loc[0, "legal_balls_remaining_before"] == 90
    assert m21586_i2.loc[0, "target_runs"] == 171
    assert m21586_i2.loc[0, "runs_remaining_before"] == 171
    assert np.isclose(m21586_i2.loc[0, "required_run_rate_before"], 171 * 6.0 / 90.0, atol=1e-3)


def test_dls_unavailable_feature_handling(fe_df: pd.DataFrame) -> None:
    # DLS matches lacking revised_overs & revised_target metadata (e.g., 20182, 23674, 24822, 28334)
    missing_dls_mids = [20182, 23674, 24822, 28334]
    sub = fe_df[(fe_df["match_id"].isin(missing_dls_mids)) & (fe_df["innings"] == 2)]
    assert len(sub) > 0
    assert sub["scheduled_legal_balls"].isna().all()
    assert sub["legal_balls_remaining_before"].isna().all()
    assert sub["target_runs"].isna().all()
    assert sub["runs_remaining_before"].isna().all()
    assert sub["required_run_rate_before"].isna().all()
    assert (sub["match_phase"] == "Unavailable").all()
    assert (~sub["chase_context_available"]).all()

    # Unflagged rain-reduced matches (15795, 31278, 48514): scheduled balls & RRR unavailable, NOT assumed 20 overs
    unflagged_short = fe_df[fe_df["match_id"].isin([15795, 31278, 48514])]
    assert len(unflagged_short) > 0
    assert unflagged_short["scheduled_legal_balls"].isna().all()
    assert unflagged_short["legal_balls_remaining_before"].isna().all()
    assert unflagged_short["required_run_rate_before"].isna().all()
    assert (unflagged_short["match_phase"] == "Unavailable").all()


def test_innings_1_has_no_chase_features(fe_df: pd.DataFrame) -> None:
    inn1 = fe_df[fe_df["innings"] == 1]
    assert inn1["target_runs"].isna().all()
    assert inn1["runs_remaining_before"].isna().all()
    assert inn1["required_run_rate_before"].isna().all()
    assert (~inn1["chase_context_available"]).all()
