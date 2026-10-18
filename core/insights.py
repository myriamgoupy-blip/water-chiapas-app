"""Analytics built on top of the thesis model: segments, model surprises and similar localities.

None of this changes the thesis results. It reuses the same sample, the same intensity measure and
the same fitted model (Notebook 4), and adds three readings of them:

- segments: the three groups of Section 6.6 (mostly connected / outside the system / water nearby);
- surprises: localities with many more homes without piped water than the model predicts (residuals);
- peers: the localities most similar to a given one (k-nearest neighbours on standardised features).
"""
import numpy as np
import pandas as pd
import streamlit as st

from . import data, engine, fastols, index

SEG_ORDER = ["outside", "nearby", "connected"]
PEER_FEATURES = ["log_pop", "school", "indig", "intensity", "ALTITUD"]


def segments(d):
    """Thesis Section 6.6: 'unconnected' = at least half of homes without piped water; split by the
    sample median of water granted within 2 km per resident."""
    vol_pc = np.expm1(d.intensity)
    med = float(np.median(vol_pc))
    seg = np.where(d.dep_water < 50, "connected", np.where(vol_pc >= med, "nearby", "outside"))
    return pd.Series(seg, index=d.index), med


@st.cache_data(show_spinner=False, max_entries=8)
def knowledge(points_key, _pts, drought_last):
    """One table with everything the pages and the assistant need, for the model sample (thesis settings)."""
    drought, _ = data.drought()
    loc = engine.table(points_key, _pts)
    vol2 = engine.volume_around(points_key, _pts, 2.0) if _pts is not None else pd.Series(np.nan, index=loc.index)
    d, fit, _ = engine.run_model(points_key, _pts)            # thesis settings: M3, 2 km, > 100 inhabitants
    k = d.copy()
    k["vol2"] = vol2.reindex(k.index)
    k["vol_pc"] = np.expm1(k.intensity)
    k["segment"], med = segments(k)
    k["predicted"] = (fit.X @ fit.params.values).clip(0, 100)
    k["surprise"] = k.dep_water - k.predicted                  # > 0: more homes without water than expected
    full = loc.dropna(subset=["dep_water", "dep_drain", "school", "indig", "intensity"])
    full = full[full.POBTOT > 100]
    comp = index.components(full, index.drought_pressure(drought))
    score = index.score(comp, index.DEFAULT_WEIGHTS)
    k["priority"] = score.reindex(k.index)
    k["priority_rank"] = k.priority.rank(ascending=False, method="min")
    k.attrs["median_vol_pc"] = med
    k.attrs["beta1"] = float(fit.params["int_c"])
    return k


def current():
    """Knowledge table for the data the app is using now."""
    pts, pkey = data.active_points()
    drought, _ = data.drought()
    return knowledge(pkey, pts, str(drought.date.max().date())), pts, pkey


def peers(k, idx, n=6):
    """The n localities most similar to locality `idx` on size, schooling, language, water nearby and altitude.

    Water access is not used to find them, so the list shows how similar places fare."""
    X = k[PEER_FEATURES].astype(float)
    X = (X - X.mean()) / X.std(ddof=0)
    X = X.fillna(0)
    if idx not in X.index:
        return k.iloc[0:0]
    dist = np.sqrt(((X - X.loc[idx]) ** 2).sum(axis=1))
    out = k.assign(dist=dist).drop(index=idx).nsmallest(n, "dist")
    out["similarity"] = (100 * np.exp(-out.dist / 2)).round(0)
    return out


def surprises(d, fit, n=10):
    """Localities furthest above the model's prediction (more homes without piped water than expected)."""
    pred = (fit.X @ fit.params.values).clip(0, 100)
    s = d.assign(predicted=pred, surprise=d.dep_water.values - pred)
    return s.sort_values("surprise", ascending=False).head(n)


def segment_summary(k):
    homes = k.VIVPARH_CV
    nowater = k.VIVPARH_CV - k.VPH_AGUADV
    g = k.assign(homes=homes, nowater=nowater).groupby("segment").agg(
        localities=("POBTOT", "size"), people=("POBTOT", "sum"), nowater=("nowater", "sum"),
        median_vol_pc=("vol_pc", "median"), top20=("priority_rank", lambda r: int((r <= 20).sum())))
    g["share_people"] = g.people / g.people.sum()
    g["share_nowater"] = g.nowater / g.nowater.sum()
    return g.reindex(SEG_ORDER)


def municipality_table(k):
    rows = []
    for m, x in k.groupby("MUN"):
        homes, nowater = x.VIVPARH_CV.sum(), (x.VIVPARH_CV - x.VPH_AGUADV).sum()
        rows.append({"MUN": m, "localities": len(x), "people": int(x.POBTOT.sum()),
                     "pct_no_water": 100 * nowater / homes, "unconnected": int((x.dep_water >= 50).sum()),
                     "nearby": int((x.segment == "nearby").sum()), "outside": int((x.segment == "outside").sum()),
                     "median_vol_pc": float(x.vol_pc.median()), "none_2km": int((x.vol_pc == 0).sum()),
                     "top20": int((x.priority_rank <= 20).sum())})
    return pd.DataFrame(rows).sort_values("pct_no_water", ascending=False)


def advice(seg, L):
    """What the thesis segmentation suggests for a locality of this group (Chapter 9)."""
    return {
        "outside": L("Sin agua concesionada cerca y sin red: la respuesta probable es una fuente nueva y una red, "
                     "y ayudar a la comunidad a registrar su derecho de agua.",
                     "No water granted nearby and no network: the likely answer is a new source and a network, "
                     "and helping the community register its water right."),
        "nearby": L("Hay agua concesionada cerca pero no llega a las viviendas: la respuesta probable es conectarse a un "
                    "sistema existente y revisar los títulos cercanos, normalmente más barato que una fuente nueva.",
                    "Water is granted nearby but does not reach homes: the likely answer is a connection to an existing "
                    "system and a review of nearby titles, usually cheaper than a new source."),
        "connected": L("La mayoría de las viviendas ya tiene agua entubada: aquí la prioridad está en la calidad, "
                       "la continuidad del servicio o el drenaje.",
                       "Most homes already have piped water: priorities here are quality, continuity of supply or drainage."),
    }.get(seg, "")
