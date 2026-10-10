# Sanity check helpers for the Hillstrom experiment.
# SRM chi-square test on arm counts, and standardized mean differences for covariate balance.
# The notebooks show the math behind each of these at least once before relying on them.

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def srm_test(counts: pd.Series, expected_shares: dict | None = None) -> dict:
    n_total = counts.sum()
    if expected_shares is None:
        expected_shares = {arm: 1 / len(counts) for arm in counts.index}
    expected = pd.Series({arm: n_total * share for arm, share in expected_shares.items()})[counts.index]
    chi2 = (((counts - expected) ** 2) / expected).sum()
    dof = len(counts) - 1
    p_value = stats.chi2.sf(chi2, dof)
    return {"chi2": chi2, "dof": dof, "p_value": p_value, "expected": expected}


def smd(a: pd.Series, b: pd.Series) -> float:
    pooled_sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (a.mean() - b.mean()) / pooled_sd


def balance_table(df: pd.DataFrame, arm_col: str, covariates: list[str], threshold: float = 0.1) -> pd.DataFrame:
    rows = []
    for arm_a, arm_b in combinations(sorted(df[arm_col].unique()), 2):
        a = df[df[arm_col] == arm_a]
        b = df[df[arm_col] == arm_b]
        for cov in covariates:
            value = smd(a[cov], b[cov])
            rows.append({
                "pair": f"{arm_a} vs {arm_b}",
                "covariate": cov,
                "mean_a": a[cov].mean(),
                "mean_b": b[cov].mean(),
                "smd": value,
                "flagged": abs(value) >= threshold,
            })
    return pd.DataFrame(rows)
