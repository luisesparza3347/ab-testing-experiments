# Tests for the sanity check helpers in src/checks.py.
# Each test uses a tiny made-up input whose answer can be worked out by hand.

import pandas as pd
import pytest

from checks import balance_table, smd, srm_test


def test_srm_equal_counts_give_zero_chi2():
    result = srm_test(pd.Series({"A": 100, "B": 100, "C": 100}))
    assert result["chi2"] == 0
    assert result["dof"] == 2
    assert result["p_value"] == pytest.approx(1.0)


def test_srm_hand_computed_example():
    # expected 100 each, chi2 = 10^2/100 + 10^2/100 = 2.0 on 1 df, p = 0.1573
    result = srm_test(pd.Series({"A": 110, "B": 90}))
    assert result["chi2"] == pytest.approx(2.0)
    assert result["dof"] == 1
    assert result["p_value"] == pytest.approx(0.1573, abs=1e-4)


def test_smd_known_value():
    # means 2 and 3, both variances 1, so pooled SD 1 and SMD -1
    assert smd(pd.Series([1, 2, 3]), pd.Series([2, 3, 4])) == pytest.approx(-1.0)


def test_balance_table_flags_only_the_big_gap():
    df = pd.DataFrame({
        "arm": ["A"] * 4 + ["B"] * 4,
        "same": [0, 1, 0, 1, 0, 1, 0, 1],
        "gap": [0, 0, 0, 1, 1, 1, 1, 0],
    })
    table = balance_table(df, "arm", ["same", "gap"]).set_index("covariate")
    assert len(table) == 2
    assert table.loc["same", "smd"] == pytest.approx(0.0)
    assert not table.loc["same", "flagged"]
    assert table.loc["gap", "flagged"]
