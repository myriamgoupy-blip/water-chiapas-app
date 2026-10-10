"""The thesis model (Notebook 4): OLS with municipality fixed effects and three kinds of p-values."""
import numpy as np
import pandas as pd
import patsy
import statsmodels.formula.api as smf
from scipy import stats

from core.geo import hav

FORMULAS = {
    "M1": "{dv} ~ int_c + log_pop + school + C(MUN)",
    "M2": "{dv} ~ int_c + ind_c + log_pop + school + C(MUN)",
    "M3": "{dv} ~ int_c * ind_c + log_pop + school + C(MUN)",
}
LABELS = {"int_c": "Concession intensity (β1)", "ind_c": "Indigenous share (β2)",
          "int_c:ind_c": "Intensity × Indigenous share (β3)", "log_pop": "Log population",
          "school": "Years of schooling"}


def centre(d):
    d = d.copy()
    d["int_c"] = d.intensity - d.intensity.mean()
    d["ind_c"] = d.indig - d.indig.mean()
    return d


def fit(d, model="M3", dv="dep_water"):
    return smf.ols(FORMULAS[model].format(dv=dv), data=d).fit(cov_type="HC1")


def wild_cluster_p(d, param, model="M3", dv="dep_water", B=999, seed=42):
    """Restricted wild cluster bootstrap-t p-value (Webb weights), clusters = municipalities."""
    y, X = patsy.dmatrices(FORMULAS[model].format(dv=dv), d, return_type="dataframe")
    j = list(X.columns).index(param)
    g = pd.factorize(d.loc[X.index, "MUN"])[0]
    G = g.max() + 1
    Xv, yv = X.values, y.values.ravel()
    n, k = Xv.shape
    A = np.linalg.pinv(Xv.T @ Xv)

    def t_stats(Y):
        b = A @ (Xv.T @ Y)
        e = Y - Xv @ b
        aX = Xv @ A[j]
        sg = np.vstack([(aX[g == c, None] * e[g == c]).sum(0) for c in range(G)])
        se = np.sqrt((G / (G - 1)) * ((n - 1) / (n - k)) * (sg ** 2).sum(0))
        return b[j] / se

    t0 = t_stats(yv[:, None])[0]
    Xr = np.delete(Xv, j, axis=1)
    br = np.linalg.lstsq(Xr, yv, rcond=None)[0]
    fr = Xr @ br
    ur = yv - fr
    rng = np.random.default_rng(seed)
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
    W = rng.choice(webb, size=(G, B))[g]
    tb = t_stats(fr[:, None] + ur[:, None] * W)
    return float((np.abs(tb) >= abs(t0)).mean())


def conley(d, res, cut_km=10, model="M3", dv="dep_water"):
    """Conley (1999) spatial HAC standard errors with a Bartlett (linearly declining) kernel."""
    _, X = patsy.dmatrices(FORMULAS[model].format(dv=dv), d, return_type="dataframe")
    Xv = X.values
    A = np.linalg.inv(Xv.T @ Xv)
    n, k = Xv.shape
    e = res.resid.values
    dd = d.loc[X.index]
    Dm = hav(dd.lon.values[:, None], dd.lat.values[:, None], dd.lon.values[None, :], dd.lat.values[None, :])
    K = np.clip(1 - Dm / cut_km, 0, None)
    S = Xv * e[:, None]
    V = A @ (S.T @ K @ S) @ A * (n / (n - k))
    se = pd.Series(np.sqrt(np.diag(V)), index=X.columns)
    p = pd.Series(2 * (1 - stats.norm.cdf(np.abs(res.params / se))), index=X.columns)
    return se, p, pd.DataFrame(V, index=X.columns, columns=X.columns)


def morans_i(d, res, cut_km=5):
    Dm = hav(d.lon.values[:, None], d.lat.values[:, None], d.lon.values[None, :], d.lat.values[None, :])
    W = ((Dm > 0) & (Dm <= cut_km)).astype(float)      # binary neighbours, as in Notebook 4 cell 20
    e = (res.resid - res.resid.mean()).values
    return float((len(e) / W.sum()) * (e @ W @ e) / (e @ e))


def marginal_effects(res, mean_indig, V=None, shares=None):
    """Association between +1 intensity and deprivation at each Indigenous share, with a 95% CI."""
    V = res.cov_params() if V is None else V
    shares = np.linspace(0, 100, 101) if shares is None else np.asarray(shares, dtype=float)
    c = shares - mean_indig
    est = res.params["int_c"] + c * res.params["int_c:ind_c"]
    se = np.sqrt(V.loc["int_c", "int_c"] + c ** 2 * V.loc["int_c:ind_c", "int_c:ind_c"]
                 + 2 * c * V.loc["int_c", "int_c:ind_c"])
    return pd.DataFrame({"indig": shares, "effect": est, "low": est - 1.96 * se, "high": est + 1.96 * se, "se": se})


def stars(p):
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "†" if p < .1 else ""
