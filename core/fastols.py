"""The thesis model in plain NumPy, so that every slider move re-estimates it in milliseconds.

Same specification and the same numbers as Notebook 4 (statsmodels OLS with HC1 errors):
    deprivation ~ intensity_c [* indigenous_c] + log_pop + school + municipality fixed effects
Checked against statsmodels in tests: identical coefficients, standard errors and p-values.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

TERMS = {"M1": ["int_c"], "M2": ["int_c", "ind_c"], "M3": ["int_c", "ind_c", "int_c:ind_c"]}


def centre(d):
    d = d.copy()
    d["int_c"] = d.intensity - d.intensity.mean()
    d["ind_c"] = d.indig - d.indig.mean()
    return d


def design(d, model="M3"):
    mun = d.MUN.values
    cols, names = [np.ones(len(d))], ["Intercept"]
    for lv in np.unique(mun)[1:]:                       # treatment coding, first municipality = reference
        cols.append((mun == lv).astype(float))
        names.append(f"MUN[{lv}]")
    for term in TERMS[model]:
        cols.append(d.int_c.values * d.ind_c.values if term == "int_c:ind_c" else d[term].values)
        names.append(term)
    for c in ["log_pop", "school"]:
        cols.append(d[c].values)
        names.append(c)
    return np.column_stack(cols), names


class Fit:
    """Coefficients, HC1 covariance and the pieces the other tests need."""

    def __init__(self, d, model="M3", dv="dep_water"):
        X, names = design(d, model)
        y = d[dv].values.astype(float)
        n, k = X.shape
        A = np.linalg.inv(X.T @ X)
        b = A @ (X.T @ y)
        e = y - X @ b
        V = A @ (X.T @ (X * (e ** 2)[:, None])) @ A * (n / (n - k))
        self.X, self.y, self.A, self.e, self.n, self.k, self.names = X, y, A, e, n, k, names
        self.params = pd.Series(b, index=names)
        self.cov = pd.DataFrame(V, index=names, columns=names)
        self.bse = pd.Series(np.sqrt(np.diag(V)), index=names)
        self.pvalues = pd.Series(2 * norm.sf(np.abs(b / self.bse.values)), index=names)
        yc = y - y.mean()
        self.rsquared = 1 - (e @ e) / (yc @ yc)
        self.model, self.dv = model, dv

    def conley(self, Dm, cut_km):
        """Conley (1999) spatial HAC errors, Bartlett kernel. Dm: distances (km) between the sample's localities."""
        K = np.clip(1 - Dm / cut_km, 0, None)
        S = self.X * self.e[:, None]
        V = self.A @ (S.T @ K @ S) @ self.A * (self.n / (self.n - self.k))
        V = pd.DataFrame(V, index=self.names, columns=self.names)
        se = pd.Series(np.sqrt(np.diag(V.values)), index=self.names)
        p = pd.Series(2 * norm.sf(np.abs(self.params / se)), index=self.names)
        return se, p, V

    def wild_p(self, clusters, param, B=9999, seed=42):
        """Restricted wild cluster bootstrap-t p-value (Webb weights), as in Notebook 4."""
        X, y, A = self.X, self.y, self.A
        j = self.names.index(param)
        g = pd.factorize(clusters)[0]
        G = g.max() + 1
        n, k = X.shape
        onehot = np.zeros((G, n))
        onehot[g, np.arange(n)] = 1.0
        aX = X @ A[j]
        factor = (G / (G - 1)) * ((n - 1) / (n - k))

        def t_stats(Y):
            b = A @ (X.T @ Y)
            e = Y - X @ b
            sg = onehot @ (aX[:, None] * e)
            return b[j] / np.sqrt(factor * (sg ** 2).sum(0))

        t0 = t_stats(y[:, None])[0]
        Xr = np.delete(X, j, axis=1)
        br = np.linalg.lstsq(Xr, y, rcond=None)[0]
        fr = Xr @ br
        ur = y - fr
        rng = np.random.default_rng(seed)
        webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
        W = rng.choice(webb, size=(G, B))[g]
        tb = t_stats(fr[:, None] + ur[:, None] * W)
        return float((np.abs(tb) >= abs(t0)).mean())


def marginal_effects(fit, mean_indig, V=None, shares=None):
    V = fit.cov if V is None else V
    shares = np.linspace(0, 100, 101) if shares is None else np.asarray(shares, dtype=float)
    c = shares - mean_indig
    est = fit.params["int_c"] + c * fit.params["int_c:ind_c"]
    se = np.sqrt(V.loc["int_c", "int_c"] + c ** 2 * V.loc["int_c:ind_c", "int_c:ind_c"]
                 + 2 * c * V.loc["int_c", "int_c:ind_c"])
    return pd.DataFrame({"indig": shares, "effect": est, "low": est - 1.96 * se, "high": est + 1.96 * se})


def morans_i(Dm, resid, cut_km=5):
    W = ((Dm > 0) & (Dm <= cut_km)).astype(float)       # binary neighbours, as in Notebook 4
    e = resid - resid.mean()
    return float((len(e) / W.sum()) * (e @ W @ e) / (e @ e))
