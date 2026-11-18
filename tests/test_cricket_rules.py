"""Automated tests for cricket scoring rules in data/processed/clean_deliveries.csv."""

from pathlib import Path
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def deliveries() -> pd.DataFrame:
    df = pd.read_csv(
        PROCESSED_DIR / "clean_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    for col in [
        "is_wide", "is_overstep_noball", "is_other_noball", "is_noball",
        "is_byes", "is_legbyes", "is_penalty_extra", "is_legal_delivery",
        "is_batter_ball_faced", "is_wicket_event", "is_retired_hurt",
        "is_bowler_wicket", "is_run_out", "is_retired_out", "is_obstructing_field",
        "is_super_over", "is_primary_eligible",
    ]:
        df[col] = df[col].astype(str).str.lower().eq("true")
    return df


def test_total_runs_calculation(deliveries: pd.DataFrame) -> None:
    expected = deliveries["runs"] + deliveries["extras1_runs"] + deliveries["extras_2_runs"]
    assert (deliveries["total_runs"] == expected).all()
    assert (deliveries["total_runs"] >= 0).all()


def test_legal_delivery_classification(deliveries: pd.DataFrame) -> None:
    non_legal = deliveries["extras_type"].isin(["wide", "Overstep", "other"])
    assert (deliveries["is_legal_delivery"] == (~non_legal)).all()
    # Penalty, byes, legbyes, None must be legal deliveries
    legal_types = deliveries["extras_type"].isin(["None", "byes", "legbyes", "Penalty"])
    assert deliveries.loc[legal_types, "is_legal_delivery"].all()
    # Six-legal-ball over rule: only documented exception is match 41509, inn 1, over 12
    over_legal = deliveries.groupby(["match_id", "innings", "overid"])["is_legal_delivery"].sum()
    gt6 = over_legal[over_legal > 6]
    assert list(gt6.index) == [(41509, 1, 12)]
    assert int(gt6.iloc[0]) == 7


def test_batter_runs_and_balls_faced(deliveries: pd.DataFrame) -> None:
    assert (deliveries["batter_runs"] == deliveries["runs"]).all()
    # Wides do NOT count as batter balls faced; no-balls DO count
    assert (~deliveries.loc[deliveries["is_wide"], "is_batter_ball_faced"]).all()
    assert deliveries.loc[deliveries["is_noball"], "is_batter_ball_faced"].all()
    assert deliveries.loc[deliveries["is_legal_delivery"], "is_batter_ball_faced"].all()
    # Wides have 0 batter runs
    assert (deliveries.loc[deliveries["is_wide"], "batter_runs"] == 0).all()


def test_bowler_conceded_runs_rules_and_reconciliation(deliveries: pd.DataFrame) -> None:
    # Byes, leg-byes, and penalty runs must NOT be charged to bowler
    excl_mask = deliveries["is_byes"] | deliveries["is_legbyes"] | deliveries["is_penalty_extra"]
    assert (deliveries.loc[excl_mask, "bowler_conceded_runs"] == 0).all()

    # Wides charge all wide runs to bowler
    wides = deliveries[deliveries["is_wide"]]
    assert (wides["bowler_conceded_runs"] == (wides["extras1_runs"] + wides["extras_2_runs"])).all()

    # No-balls charge batter runs + extras1_runs (NB penalty), excluding extras_2_runs (byes/legbyes off NB)
    nb = deliveries[deliveries["is_noball"]]
    assert (nb["bowler_conceded_runs"] == (nb["runs"] + nb["extras1_runs"])).all()

    # Exact accounting identity across every single delivery
    assert (
        (deliveries["bowler_conceded_runs"] + deliveries["non_bowler_extras_runs"])
        == deliveries["total_runs"]
    ).all()


def test_wicket_and_bowler_wicket_rules(deliveries: pd.DataFrame) -> None:
    # Bowler wickets strictly limited to Caught, Bowled, LBW, Stump, Hit Wicket
    bw_types = set(deliveries.loc[deliveries["is_bowler_wicket"], "dismissal_type_std"].dropna().unique())
    assert bw_types.issubset({"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"})

    # Run-outs, Retired Out, Obstructing the field must NEVER be bowler wickets
    non_bw = deliveries["is_run_out"] | deliveries["is_retired_out"] | deliveries["is_obstructing_field"]
    assert (~deliveries.loc[non_bw, "is_bowler_wicket"]).all()

    # Retired hurt events must NEVER be team wickets or bowler wickets
    rh = deliveries[deliveries["is_retired_hurt"]]
    assert len(rh) == 11  # 11 in primary IPL/T20I (12th is in excluded comp 2670)
    assert (~rh["is_wicket_event"]).all()
    assert (~rh["is_bowler_wicket"]).all()

    # Spelling normalization preserved raw dismissal_type while fixing dismissal_type_std
    assert (deliveries["dismissal_type_std"] == "Obstracting the field").sum() == 0
    assert (deliveries["dismissal_type"] == "Obstracting the field").sum() == 1
    excl = pd.read_csv(
        PROCESSED_DIR / "excluded_competition_deliveries.csv",
        low_memory=False,
        keep_default_na=False,
        na_values=[""],
    )
    assert (excl["dismissal_type"] == "Obstracting the field").sum() == 1
    assert (excl["dismissal_type_std"] == "Obstracting the field").sum() == 0
