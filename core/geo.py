"""Distances, the LOCREPDA location check, and concession intensity around localities.

The logic is copied from the thesis notebooks (LOCREPDA_linkage and Notebook 4) so that the app
reproduces the thesis numbers exactly.
"""
import re
import numpy as np
import pandas as pd


def hav(lon1, lat1, lon2, lat2):
    """Great-circle distance in km (works on broadcast arrays)."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def title_key(s):
    """The number after 'CHS' identifies a title in both REPDA and LOCREPDA (e.g. 6CHS100043 = A6CHS100043)."""
    m = re.search(r"CHS(\d+)", str(s))
    return m[1] if m else None


def location_check(pts, loc, max_km=10):
    """Flag LOCREPDA points whose coordinates are missing or implausible (Section 4.3 of the thesis).

    - no_coords: missing or zero coordinates
    - wrong_municipality: the nearest census locality belongs to another municipality
    - far_from_own_localities: more than `max_km` km from every locality of its own municipality
    """
    pts = pts.copy()
    L = loc.dropna(subset=["lon", "lat"])
    L_lon, L_lat, L_mun = L.lon.values, L.lat.values, L.MUN.values
    ok = pts.LONDEC.notna() & pts.LATDEC.notna() & (pts.LONDEC != 0) & (pts.LATDEC != 0)
    lon = pts.LONDEC.fillna(0).values[:, None]
    lat = pts.LATDEC.fillna(0).values[:, None]
    D = hav(lon, lat, L_lon[None, :], L_lat[None, :])
    D[~ok.values] = np.inf
    near = D.argmin(axis=1)
    pts["near_mun"] = L_mun[near]
    pts["near_km"] = np.where(ok, D[np.arange(len(pts)), near], np.nan)
    own = np.where(L_mun[None, :] == pts.MUPIO.values[:, None], D, np.inf)
    pts["own_km"] = np.where(ok, own.min(axis=1), np.nan)
    pts["flag"] = np.select(
        [~ok, pts.near_mun != pts.MUPIO, pts.own_km > max_km],
        ["no_coords", "wrong_municipality", "far_from_own_localities"], default="ok")
    return pts


def place_volumes(pts, vol_by_key, add_missing_title=False):
    """Attach REPDA volumes to LOCREPDA points (Notebook 4, section 2).

    A title's REPDA volume is split across its points in proportion to LOCREPDA's per-point
    volumes (equal shares if those are missing). Only points that pass the location check are kept.
    """
    p = pts[pts.key.isin(vol_by_key.index)].copy()
    tot = p.groupby("key").VOL_CONS.transform("sum")
    n = p.groupby("key").VOL_CONS.transform("size")
    p["share"] = np.where(tot > 0, p.VOL_CONS / tot, 1 / n)
    p["vol"] = p.share * p.key.map(vol_by_key)
    if add_missing_title and "156910" not in set(p.key) and "156910" in vol_by_key.index:
        host = p[p.key == "100687"].copy()
        host["key"] = "156910"
        host["vol"] = host.share * vol_by_key["156910"]
        p = pd.concat([p, host], ignore_index=True)
    return p[p.flag == "ok"].reset_index(drop=True)


def volume_around(loc, placed, radius_km=2, measure="buffer"):
    """Concessioned volume (m³/yr) within `radius_km` of each locality, or assigned to it ('nearest')."""
    ok = loc.lon.notna() & loc.lat.notna()
    D = hav(loc.lon.fillna(0).values[:, None], loc.lat.fillna(0).values[:, None],
            placed.LONDEC.values[None, :], placed.LATDEC.values[None, :])
    D[~ok.values] = np.inf
    if measure == "buffer":
        v = (D <= radius_km).astype(float) @ placed.vol.values
    else:  # each point goes to the nearest locality of its own municipality
        own = np.where(loc.MUN.values[:, None] == placed.MUPIO.values[None, :], D, np.inf)
        v = np.bincount(own.argmin(axis=0), weights=placed.vol.values, minlength=len(loc))
    return pd.Series(v, index=loc.index)


def intensity(loc, placed, radius_km=2, measure="buffer", per_capita=True):
    """Intensity = log(1 + m³ per resident per year) around each locality (the thesis IV)."""
    v = volume_around(loc, placed, radius_km, measure)
    return np.log1p(v / loc.POBTOT) if per_capita else np.log1p(v)


def concessions_near(lon, lat, placed, radius_km):
    """Concession points within `radius_km` of one location, nearest first."""
    if placed is None or placed.empty:
        return placed
    d = hav(lon, lat, placed.LONDEC.values, placed.LATDEC.values)
    out = placed.assign(dist_km=d)
    return out[out.dist_km <= radius_km].sort_values("dist_km")
