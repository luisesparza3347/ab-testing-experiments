# Marketplace interference simulation engine for Part 2.
# Regions have buyers who share a fixed daily supply. A discount raises how many buyers want to buy,
# and when demand exceeds supply the units go to a random subset of them.
# Each run builds one world, computes the true global treatment effect on it, and runs the
# user-level, cluster-by-region, and switchback designs on the same buyers.
# Everything is simulated as counts per region-day, which is exactly equivalent to simulating buyers.

import numpy as np
import pandas as pd
from scipy import stats

DAYS = 14
REGIONS = 50
ALPHA = 0.05
DESIGNS = ["user_level", "cluster", "switchback"]


def to_daily(p, days=DAYS):
    return 1 - (1 - p) ** (1 / days)


def beta_params(mean, sd):
    k = mean * (1 - mean) / sd**2 - 1
    return mean * k, (1 - mean) * k


def draw_regions(rng, p0, lift, spread_rel, regions=REGIONS):
    if spread_rel == 0:
        p0_r = np.full(regions, p0)
    else:
        a, b = beta_params(p0, spread_rel * p0)
        p0_r = rng.beta(a, b, regions)
    p1_r = np.minimum(p0_r + lift, 1.0)
    return to_daily(p0_r), to_daily(p1_r)


def supply_levels(n, q0, q1, eps):
    q0, q1 = np.atleast_1d(q0), np.atleast_1d(q1)

    loose = stats.binom.isf(eps, n, q1).astype(int)
    for _ in range(5):
        loose = np.where(stats.binom.sf(loose, n, q1) > eps, loose + 1, loose)

    k = stats.binom.ppf(eps, n, q0).astype(int)
    for _ in range(5):
        k = np.where((k >= 0) & (stats.binom.cdf(k, n, q0) > eps), k - 1, k)
    tight = np.maximum(k + 1, 1)

    band = np.round(np.linspace(n * q0, n * q1, 5, axis=1)).astype(int)
    return np.column_stack([tight, band, loose])


def draw_world(rng, n, q0, q1, supply):
    shape = (len(q0), DAYS)
    anyway = rng.binomial(n, np.broadcast_to(q0[:, None], shape))
    extra_p = np.where(q0 < 1, (q1 - q0) / (1 - q0), 0.0)
    discount_only = rng.binomial(n - anyway, np.broadcast_to(extra_p[:, None], shape))
    s = np.broadcast_to(supply[:, None], shape)
    conv0 = np.minimum(anyway, s)
    conv1 = np.minimum(anyway + discount_only, s)
    return anyway, discount_only, conv0, conv1


def user_level(rng, n, anyway, discount_only, supply):
    n_treat = n // 2
    n_ctrl = n - n_treat
    anyway_t = rng.hypergeometric(n_treat, n_ctrl, anyway)
    discount_t = rng.hypergeometric(n_treat - anyway_t, n_ctrl - (anyway - anyway_t), discount_only)
    demand_t = anyway_t + discount_t
    demand_c = anyway - anyway_t
    units = np.minimum(demand_t + demand_c, supply[:, None])
    conv_t = rng.hypergeometric(demand_t, demand_c, units)
    conv_c = units - conv_t

    buyer_days_t = n_treat * anyway.size
    buyer_days_c = n_ctrl * anyway.size
    rate_t = conv_t.sum() / buyer_days_t
    rate_c = conv_c.sum() / buyer_days_c
    est = rate_t - rate_c
    se = np.sqrt(rate_t * (1 - rate_t) / buyer_days_t + rate_c * (1 - rate_c) / buyer_days_c)
    return _result(est, se, stats.norm.ppf(1 - ALPHA / 2), lambda z: 2 * stats.norm.sf(abs(z)))


def cluster(rng, n, conv0, conv1):
    regions = conv0.shape[0]
    treated = np.zeros(regions, dtype=bool)
    treated[rng.permutation(regions)[: regions // 2]] = True
    rate_t = conv1[treated].sum(axis=1) / (DAYS * n)
    rate_c = conv0[~treated].sum(axis=1) / (DAYS * n)
    est = rate_t.mean() - rate_c.mean()
    v_t = rate_t.var(ddof=1) / len(rate_t)
    v_c = rate_c.var(ddof=1) / len(rate_c)
    se = np.sqrt(v_t + v_c)
    if se == 0:
        return _result(est, 0.0, np.nan, None)
    df = (v_t + v_c) ** 2 / (v_t**2 / (len(rate_t) - 1) + v_c**2 / (len(rate_c) - 1))
    return _result(est, se, stats.t.ppf(1 - ALPHA / 2, df), lambda t: 2 * stats.t.sf(abs(t), df))


def switchback(rng, n, conv0, conv1):
    regions = conv0.shape[0]
    order = rng.random((regions, DAYS)).argsort(axis=1)
    treated = np.zeros((regions, DAYS), dtype=bool)
    np.put_along_axis(treated, order[:, : DAYS // 2], True, axis=1)
    rate_t = np.where(treated, conv1, 0).sum(axis=1) / (DAYS // 2 * n)
    rate_c = np.where(~treated, conv0, 0).sum(axis=1) / ((DAYS - DAYS // 2) * n)
    diffs = rate_t - rate_c
    est = diffs.mean()
    se = diffs.std(ddof=1) / np.sqrt(regions)
    if se == 0:
        return _result(est, 0.0, np.nan, None)
    df = regions - 1
    return _result(est, se, stats.t.ppf(1 - ALPHA / 2, df), lambda t: 2 * stats.t.sf(abs(t), df))


def _result(est, se, crit, p_from_stat):
    if se == 0:
        return {"est": est, "se": 0.0, "lo": est, "hi": est, "p": 1.0, "reject": False, "degenerate": True}
    p = p_from_stat(est / se)
    return {"est": est, "se": se, "lo": est - crit * se, "hi": est + crit * se,
            "p": p, "reject": p < ALPHA, "degenerate": False}


def run_once(rng, n, p0, lift, spread_rel, level, eps):
    q0, q1 = draw_regions(rng, p0, lift, spread_rel)
    supply = supply_levels(n, q0, q1, eps)[:, level]
    anyway, discount_only, conv0, conv1 = draw_world(rng, n, q0, q1, supply)
    gte = (conv1.sum() - conv0.sum()) / (conv0.size * n)
    out = {"gte": gte}
    results = {
        "user_level": user_level(rng, n, anyway, discount_only, supply),
        "cluster": cluster(rng, n, conv0, conv1),
        "switchback": switchback(rng, n, conv0, conv1),
    }
    for design, res in results.items():
        for key, val in res.items():
            out[f"{design}_{key}"] = val
    return out


def run_scenario(n, p0, lift, spread_rel, level, eps, runs, scenario_seed):
    seeds = scenario_seed.spawn(runs)
    rows = [run_once(np.random.default_rng(s), n, p0, lift, spread_rel, level, eps) for s in seeds]
    return pd.DataFrame(rows)


def summarize(per_run):
    runs = len(per_run)
    rows = []
    for design in DESIGNS:
        err = per_run[f"{design}_est"] - per_run["gte"]
        covered = (per_run[f"{design}_lo"] <= per_run["gte"]) & (per_run["gte"] <= per_run[f"{design}_hi"])
        power = per_run[f"{design}_reject"].mean()
        coverage = covered.mean()
        rows.append({
            "design": design,
            "runs": runs,
            "mean_gte": per_run["gte"].mean(),
            "mean_est": per_run[f"{design}_est"].mean(),
            "bias": err.mean(),
            "bias_mcse": err.std(ddof=1) / np.sqrt(runs),
            "power": power,
            "power_mcse": np.sqrt(power * (1 - power) / runs),
            "coverage": coverage,
            "coverage_mcse": np.sqrt(coverage * (1 - coverage) / runs),
            "degenerate_runs": int(per_run[f"{design}_degenerate"].sum()),
        })
    return pd.DataFrame(rows)
