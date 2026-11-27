# Tests for the data checks in src/load.py.
# Uses a fake 64,000-row table, never the real data or the network, so it runs the same anywhere.
# Checks that good data passes and that each kind of bad data is caught.

import pandas as pd
import pytest

from load import EXPECTED_ARMS, EXPECTED_COLUMNS, EXPECTED_ROW_COUNT, _validate


@pytest.fixture
def valid_df():
    arms = sorted(EXPECTED_ARMS)
    df = pd.DataFrame(0, index=range(EXPECTED_ROW_COUNT), columns=EXPECTED_COLUMNS)
    df["segment"] = [arms[i % 3] for i in range(EXPECTED_ROW_COUNT)]
    df["spend"] = 0.0
    return df


def test_valid_data_passes(valid_df):
    _validate(valid_df)


def test_wrong_arm_label_fails(valid_df):
    valid_df.loc[0, "segment"] = "Kids E-Mail"
    with pytest.raises(AssertionError):
        _validate(valid_df)


def test_null_outcome_fails(valid_df):
    valid_df.loc[0, "spend"] = None
    with pytest.raises(AssertionError):
        _validate(valid_df)


def test_wrong_row_count_fails(valid_df):
    with pytest.raises(AssertionError):
        _validate(valid_df.iloc[:-1])


def test_negative_spend_fails(valid_df):
    valid_df.loc[0, "spend"] = -5.0
    with pytest.raises(AssertionError):
        _validate(valid_df)
