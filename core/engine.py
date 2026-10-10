"""Precomputed distances and fast recomputation, so the pages answer instantly.

Distances between all localities and all concession points are computed once per data source and
kept in memory; changing the radius is then a single matrix product.
"""
import numpy as np
import pandas as pd
import streamlit as st

from . import data, fastols, geo


@st.cache_resource(show_spinner=False)
def loc_distances():
    """Locality-to-locality distances (km); missing coordinates are infinitely far."""
    loc = data.localities()
    ok = (loc.lon.notna() & loc.lat.notna()).values
    lon, lat = loc.lon.fillna(0).values, loc.lat.fillna(0).values
    D = geo.hav(lon[:, None], lat[:, None], lon[None, :], lat[None, :])
    D[~ok, :] = np.inf
    D[:, ~ok] = np.inf
    return D


@st.cache_resource(show_spinner=False)
def point_arrays(points_key, _pts, add_title=False):
    """Placed concession points and their distances to every locality (cached per data source)."""
    placed = geo.place_volumes(_pts, data.vol_by_key(), add_title)
    loc = data.localities()
    ok = (loc.lon.notna() & loc.lat.notna()).values
    D = geo.hav(loc.lon.fillna(0).values[:, None], loc.lat.fillna(0).values[:, None],
                placed.LONDEC.values[None, :], placed.LATDEC.values[None, :])
    D[~ok, :] = np.inf
    own = np.where(loc.MUN.values[:, None] == placed.MUPIO.values[None, :], D, np.inf)
    return {"placed": placed, "D": D, "vol": placed.vol.values, "nearest": own.argmin(axis=0)}


def volume_around(points_key, pts, radius_km=2.0, measure="buffer", add_title=False):
    loc = data.localities()
    pa = point_arrays(points_key, pts, add_title)
    if measure == "buffer":
        v = (pa["D"] <= radius_km) @ pa["vol"]
    else:
        v = np.bincount(pa["nearest"], weights=pa["vol"], minlength=len(loc))
    return pd.Series(v, index=loc.index)


def intensity(points_key, pts, radius_km=2.0, measure="buffer", per_capita=True, add_title=False):
    loc = data.localities()
    if pts is None:
        return loc["intensity_2km_thesis"]
    v = volume_around(points_key, pts, radius_km, measure, add_title)
    return np.log1p(v / loc.POBTOT) if per_capita else np.log1p(v)


def table(points_key, pts, radius_km=2.0, measure="buffer", per_capita=True, add_title=False):
    loc = data.localities().copy()
    loc["intensity"] = intensity(points_key, pts, radius_km, measure, per_capita, add_title).values
    return loc


def run_model(points_key, pts, model="M3", dv="dep_water", radius_km=2.0, measure="buffer",
              per_capita=True, add_title=False, min_pop=100):
    """Sample, fit and the sample's distance matrix."""
    loc = table(points_key, pts, radius_km, measure, per_capita, add_title)
    d = fastols.centre(data.sample(loc, dv, min_pop))
    fit = fastols.Fit(d, model, dv)
    Dm = loc_distances()[np.ix_(d.index.values, d.index.values)]
    return d, fit, Dm


@st.cache_data(show_spinner=False, max_entries=64)
def radius_sweep(points_key, _pts, model, dv, measure, per_capita, add_title, min_pop, cut_km):
    """β1 and its Conley interval at every radius from 0.5 to 10 km."""
    rows = []
    for r in np.arange(0.5, 10.01, 0.5):
        d, fit, Dm = run_model(points_key, _pts, model, dv, float(r), "buffer", per_capita, add_title, min_pop)
        se, p, _ = fit.conley(Dm, cut_km)
        b = fit.params["int_c"]
        rows.append({"radius": float(r), "beta1": b, "low": b - 1.96 * se["int_c"],
                     "high": b + 1.96 * se["int_c"], "p": p["int_c"]})
    return pd.DataFrame(rows)
