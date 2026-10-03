# Loads the Hillstrom email dataset and checks it matches what we expect.
# No by-arm outcome stats here, that happens only after the design doc is committed.

import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOCAL_COPY = DATA_DIR / "hillstrom.csv"
RAW_CSV_URL = "https://raw.githubusercontent.com/joelcarlson/MineThatData/master/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"

EXPECTED_COLUMNS = [
    "recency", "history_segment", "history", "mens", "womens",
    "zip_code", "newbie", "channel", "segment", "visit", "conversion", "spend",
]
EXPECTED_ARMS = {"Mens E-Mail", "Womens E-Mail", "No E-Mail"}
EXPECTED_ROW_COUNT = 64000


def _fetch_via_sklift() -> pd.DataFrame:
    from sklift.datasets import fetch_hillstrom

    bunch = fetch_hillstrom(target_col="all")
    df = bunch.data.copy()
    df[bunch.target_name] = bunch.target
    df["segment"] = bunch.treatment
    return df


def _fetch_via_raw_csv() -> pd.DataFrame:
    return pd.read_csv(RAW_CSV_URL)


def _validate(df: pd.DataFrame) -> None:
    missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
    assert not missing_cols, f"missing expected columns: {missing_cols}"

    assert len(df) == EXPECTED_ROW_COUNT, f"expected {EXPECTED_ROW_COUNT} rows, got {len(df)}"

    arms = set(df["segment"].unique())
    assert arms == EXPECTED_ARMS, f"unexpected arm labels: {arms}"

    outcome_cols = ["visit", "conversion", "spend"]
    nulls = df[outcome_cols].isnull().sum()
    assert nulls.sum() == 0, f"nulls found in outcome columns: {nulls[nulls > 0].to_dict()}"

    assert df["visit"].isin([0, 1]).all(), "visit should be 0/1"
    assert df["conversion"].isin([0, 1]).all(), "conversion should be 0/1"
    assert (df["spend"] >= 0).all(), "spend should be non-negative"
    assert df["spend"].min() >= 0 and np.isfinite(df["spend"]).all(), "spend has non-finite values"


def load_hillstrom(force_refetch: bool = False) -> pd.DataFrame:
    if LOCAL_COPY.exists() and not force_refetch:
        df = pd.read_csv(LOCAL_COPY)
        _validate(df)
        return df

    try:
        df = _fetch_via_sklift()
    except Exception:
        df = _fetch_via_raw_csv()

    _validate(df)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(LOCAL_COPY, index=False)
    return df


if __name__ == "__main__":
    data = load_hillstrom()
    print(f"loaded {len(data)} rows, columns: {list(data.columns)}")
