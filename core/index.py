"""A transparent water-priority index: weighted average of 0–1 components, with a rank-stability check.

This is a decision-support tool, not a result of the thesis model: the weights are value judgements,
which is why the user sets them and why the Monte Carlo check shows how much the ranking depends on them.
"""
import numpy as np
import pandas as pd

COMPONENTS = {
    "water": ("Households without piped water", "Share of dwellings without piped water inside the dwelling or in its yard (census 2020)."),
    "drain": ("Households without drainage", "Share of dwellings not connected to any drainage (census 2020)."),
    "mismatch": ("Water claimed nearby, not reaching homes", "Concession intensity around the locality (rescaled 0–1) × share of dwellings without piped water. High when a lot of water is concessioned nearby but households still lack it."),
    "school": ("Low schooling", "Average years of schooling, reversed and rescaled 0–1 (fewest years = 1)."),
    "drought": ("Drought pressure (live)", "Average Drought Monitor category of the municipality over the last 12 months (no drought = 0, D0 = 0.2 … D4 = 1)."),
    "indig": ("Indigenous-language speakers", "Share of the population aged 3+ speaking an Indigenous language. Off by default: including it is a political choice the user should make knowingly."),
}
DEFAULT_WEIGHTS = {"water": 0.30, "drain": 0.20, "mismatch": 0.20, "school": 0.15, "drought": 0.15, "indig": 0.0}
CAT_SCORE = {"None": 0.0, "D0": 0.2, "D1": 0.4, "D2": 0.6, "D3": 0.8, "D4": 1.0}


def drought_pressure(drought, months=12, mode="average"):
    """Category score per municipality: mean over the last `months` months, or the latest value."""
    end = drought.date.max()
    if mode == "latest":
        recent = drought[drought.date == end]
    else:
        recent = drought[drought.date > end - pd.DateOffset(months=months)]
    return recent.assign(s=recent.cat.map(CAT_SCORE).fillna(0)).groupby("MUN").s.mean()


def _rescale(s):
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0


def components(d, drought_by_mun):
    c = pd.DataFrame(index=d.index)
    c["water"] = d.dep_water.clip(0, 100) / 100
    c["drain"] = d.dep_drain.clip(0, 100) / 100
    c["mismatch"] = _rescale(d.intensity) * c.water
    c["school"] = 1 - _rescale(d.school)
    c["drought"] = d.MUN.map(drought_by_mun).fillna(0)
    c["indig"] = d.indig.clip(0, 100) / 100
    return c.fillna(0)


def score(comp, weights):
    w = pd.Series(weights, dtype=float).reindex(comp.columns).fillna(0)
    if w.sum() <= 0:
        return pd.Series(0.0, index=comp.index)
    return 100 * (comp @ w) / w.sum()


def rank_stability(comp, weights, draws=500, concentration=20, top=20, seed=1):
    """Re-rank under random weights centred on the chosen ones (Dirichlet), to show how robust the ranking is.

    Returns, per locality: median rank, 5th–95th percentile of its rank, and how often it is in the top `top`.
    """
    w = pd.Series(weights, dtype=float).reindex(comp.columns).fillna(0)
    active = w[w > 0]
    if active.empty:
        return None
    rng = np.random.default_rng(seed)
    alpha = concentration * active.values / active.sum() + 1e-3
    W = rng.dirichlet(alpha, size=draws)                         # draws x k
    S = comp[active.index].values @ W.T                          # n x draws
    ranks = (-S).argsort(axis=0).argsort(axis=0) + 1             # 1 = highest priority
    return pd.DataFrame({
        "median_rank": np.median(ranks, axis=1),
        "rank_p5": np.percentile(ranks, 5, axis=1),
        "rank_p95": np.percentile(ranks, 95, axis=1),
        f"top{top}_share": (ranks <= top).mean(axis=1),
    }, index=comp.index)
