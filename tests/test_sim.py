# Tests for the simulation engine in src/sim.py.
# Mechanics only, on small made-up inputs. These never run a real scenario
# and never check bias, power, or coverage numbers from the simulation itself.

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import sim


def test_to_daily_converts_back_to_two_week_rate():
    q = sim.to_daily(0.05)
    assert 1 - (1 - q) ** sim.DAYS == pytest.approx(0.05)


def test_beta_params_recover_mean_and_sd():
    a, b = sim.beta_params(0.3, 0.05)
    assert a / (a + b) == pytest.approx(0.3)
    assert np.sqrt(a * b / ((a + b) ** 2 * (a + b + 1))) == pytest.approx(0.05)


def test_no_spread_gives_every_region_the_same_rate():
    q0, q1 = sim.draw_regions(np.random.default_rng(0), 0.01, 0.005, 0)
    assert len(q0) == sim.REGIONS
    assert np.allclose(q0, sim.to_daily(0.01))
    assert np.allclose(q1, sim.to_daily(0.015))


def test_supply_levels_are_ordered_and_meet_eps():
    n, eps = 1000, 1e-6
    q0, q1 = np.array([0.01, 0.02]), np.array([0.02, 0.03])
    levels = sim.supply_levels(n, q0, q1, eps)
    assert levels.shape == (2, 7)
    assert np.all(levels[:, 0] >= 1)
    assert np.all(np.diff(levels, axis=1) >= 0)
    assert np.all(stats.binom.sf(levels[:, -1], n, q1) <= eps)


def test_world_never_sells_more_than_supply():
    q0, q1 = np.full(5, 0.05), np.full(5, 0.10)
    supply = np.array([1, 3, 5, 10, 100])
    _, _, conv0, conv1 = sim.draw_world(np.random.default_rng(0), 200, q0, q1, supply)
    assert conv0.shape == (5, sim.DAYS)
    assert np.all(conv0 <= supply[:, None])
    assert np.all(conv1 <= supply[:, None])
    assert np.all(conv1 >= conv0)


@pytest.mark.parametrize("design", [sim.cluster, sim.switchback])
def test_zero_se_is_marked_degenerate(design):
    conv = np.ones((sim.REGIONS, sim.DAYS), dtype=int)
    result = design(np.random.default_rng(0), 100, conv, conv)
    assert result["degenerate"]
    assert result["se"] == 0
    assert not result["reject"]


def test_same_seed_gives_identical_run():
    args = dict(n=2000, p0=0.01, lift=0.005, spread_rel=0.2, level=3, eps=1e-6)
    first = sim.run_once(np.random.default_rng(123), **args)
    second = sim.run_once(np.random.default_rng(123), **args)
    assert pd.Series(first).equals(pd.Series(second))


def test_summarize_hand_counted_table():
    # true effect 1 in every run, errors 0.5, -0.5, 0, 1, so bias 0.25
    # intervals are est +/- 0.6, so only the run with error 1 misses, coverage 0.75
    est = [1.5, 0.5, 1.0, 2.0]
    per_run = pd.DataFrame({"gte": [1.0] * 4})
    for design in sim.DESIGNS:
        per_run[f"{design}_est"] = est
        per_run[f"{design}_lo"] = [e - 0.6 for e in est]
        per_run[f"{design}_hi"] = [e + 0.6 for e in est]
        per_run[f"{design}_se"] = 0.3
        per_run[f"{design}_reject"] = [True, False, True, True]
        per_run[f"{design}_degenerate"] = False
    summary = sim.summarize(per_run).set_index("design")
    for design in sim.DESIGNS:
        row = summary.loc[design]
        assert row["runs"] == 4
        assert row["bias"] == pytest.approx(0.25)
        assert row["coverage"] == pytest.approx(0.75)
        assert row["power"] == pytest.approx(0.75)
        assert row["degenerate_runs"] == 0
