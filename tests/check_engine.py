"""Check that the app's fast NumPy engine gives exactly the thesis numbers (Notebook 4, statsmodels).

Run from the repository root:  pip install statsmodels patsy && python tests/check_engine.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import data, engine, fastols  # noqa: E402
import reference_statsmodels as ref  # noqa: E402

loc = data.localities()
loc["intensity"] = loc.intensity_2km_thesis
d = fastols.centre(data.sample(loc))
for m in ["M1", "M2", "M3"]:
    f, r = fastols.Fit(d, m), ref.fit(d, m)
    for p in fastols.TERMS[m] + ["log_pop", "school"]:
        assert np.isclose(f.params[p], r.params[p]) and np.isclose(f.bse[p], r.bse[p]), (m, p)
f = fastols.Fit(d)
Dm = engine.loc_distances()[np.ix_(d.index.values, d.index.values)]
print("n =", f.n, "| beta1 =", round(f.params["int_c"], 3), "(thesis: -2.195)")
print("Conley p (5/10/20 km):", [round(float(f.conley(Dm, c)[1]["int_c"]), 3) for c in (5, 10, 20)], "(thesis: 0.032 / 0.056 / 0.044)")
print("wild bootstrap p, beta1 / beta3:", round(f.wild_p(d.MUN.values, "int_c"), 3), "/",
      round(f.wild_p(d.MUN.values, "int_c:ind_c"), 3), "(thesis: 0.154 / 0.799)")
print("All coefficients and standard errors identical to statsmodels.")
