"""Clients for the live sources. Every function raises on failure; the pages catch and fall back.

- LOCREPDA (CONAGUA ArcGIS server): concession points with coordinates.
- Drought Monitor (CONAGUA–SMN): municipal drought category every 15 days since 2003.
- Open-Meteo: ERA5 reanalysis (archive) and forecast models. Free, no key, non-commercial use.
"""
import io
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import urllib3

from .config import (DROUGHT_URL, LOCREPDA_URL, MUNS, OPEN_METEO_ARCHIVE,
                     OPEN_METEO_FORECAST)

UA = {"User-Agent": "Mozilla/5.0 (thesis research app; ESCP MSc)"}
TZ = "America/Mexico_City"


# ---------------------------------------------------------------- LOCREPDA
def _arcgis(layer, params, timeout=25):
    # The CONAGUA server's certificate chain is incomplete, so certificate checks are disabled
    # for this host only (read-only public data).
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    p = {"f": "json", **params}
    r = requests.get(f"{LOCREPDA_URL}/{layer}/query", params=p, headers=UA, timeout=timeout, verify=False)
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        raise RuntimeError(js["error"])
    return js


def _fetch_layer(layer, where, chunk=200):
    """All records of one layer. The server (ArcGIS 10.0x) ignores paging, so: ask for the IDs, then fetch by ID."""
    ids = _arcgis(layer, {"where": where, "returnIdsOnly": "true"}).get("objectIds") or []
    rows = []
    ids = sorted(ids)
    for i in range(0, len(ids), chunk):
        js = _arcgis(layer, {"objectIds": ",".join(map(str, ids[i:i + chunk])),
                             "outFields": "*", "returnGeometry": "false"})
        rows += [f["attributes"] for f in js.get("features", [])]
    df = pd.DataFrame(rows)
    id_col = next((c for c in ["FID", "OBJECTID"] if c in df.columns), None)
    return df.drop_duplicates(subset=id_col) if id_col else df.drop_duplicates()


def _first(df, prefixes, default=None):
    for p in prefixes:
        for c in df.columns:
            if c.upper() == p or c.upper().startswith(p):
                return c
    return default


def fetch_locrepda():
    """Groundwater (layer 1) and surface water (layer 2) points in the nine municipalities, harmonised."""
    where = f"ESTADO=7 AND MUPIO IN ({','.join(map(str, MUNS))})"
    out = []
    for layer, source in [(1, "subterranea"), (2, "superficial")]:
        df = _fetch_layer(layer, where)
        if df.empty:
            continue
        uso = _first(df, ["USO_SUB", "USO_SUP", "USO"])
        h = pd.DataFrame({
            "FOLIOREG": df["FOLIOREG"].astype(str),
            "TITULAR": df.get("TITULAR"),
            "MUPIO": df["MUPIO"],
            "uso": df[uso] if uso else "",
            "VOL_CONS": df.get("VOL_CONS"),
            "LONDEC": pd.to_numeric(df["LONDEC"], errors="coerce"),
            "LATDEC": pd.to_numeric(df["LATDEC"], errors="coerce"),
            "source": source,
        })
        for extra in ["NOM_LOCAL", "NOMFUENTE"]:
            if extra in df.columns:
                h[extra] = df[extra]
        out.append(h)
    if not out:
        raise RuntimeError("LOCREPDA returned no points")
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- Drought monitor
def parse_drought_xlsx(content):
    """Turn MunicipiosSequia.xlsx (bytes) into a long table for the nine municipalities."""
    d = pd.read_excel(io.BytesIO(content), sheet_name=0)
    cols = {str(c).strip().upper(): c for c in d.columns}
    if "CVE_CONCATENADA" in cols:
        cve = pd.to_numeric(d[cols["CVE_CONCATENADA"]], errors="coerce")
    else:
        cve = pd.to_numeric(d[cols["CVE_ENT"]], errors="coerce") * 1000 + pd.to_numeric(d[cols["CVE_MUN"]], errors="coerce")
    d = d.assign(_cve=cve)
    d = d[d._cve.isin([7000 + m for m in MUNS])]
    date_cols = [c for c in d.columns if isinstance(c, (pd.Timestamp, date)) or
                 (isinstance(c, str) and pd.to_datetime(c, errors="coerce", dayfirst=False) is not pd.NaT
                  and c[:2].isdigit())]
    if not date_cols or d.empty:
        raise ValueError("Unexpected drought file layout")
    lg = d.melt(id_vars=["_cve"], value_vars=date_cols, var_name="date", value_name="cat")
    lg["MUN"] = (lg._cve - 7000).astype(int)
    lg["NOMBRE_MUN"] = lg.MUN.map(MUNS)
    lg["date"] = pd.to_datetime(lg["date"])
    lg["cat"] = lg["cat"].fillna("None").astype(str).str.strip().replace({"": "None", "nan": "None"})
    return lg[["MUN", "NOMBRE_MUN", "date", "cat"]].sort_values(["MUN", "date"]).reset_index(drop=True)


def fetch_drought_official(timeout=60):
    r = requests.get(DROUGHT_URL, headers=UA, timeout=timeout)
    r.raise_for_status()
    return parse_drought_xlsx(r.content)


# ---------------------------------------------------------------- Open-Meteo
def _as_list(js):
    return js if isinstance(js, list) else [js]


def _coords(points):
    return {"latitude": ",".join(f"{p['lat']:.4f}" for p in points),
            "longitude": ",".join(f"{p['lon']:.4f}" for p in points)}


def fetch_forecast(points, past_days=92, forecast_days=7, timeout=60):
    """Daily rain/temperature and daily-mean soil moisture, last `past_days` days and next week."""
    p = {**_coords(points), "timezone": TZ, "past_days": past_days, "forecast_days": forecast_days,
         "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,et0_fao_evapotranspiration",
         "hourly": "soil_moisture_9_to_27cm,soil_moisture_27_to_81cm"}
    r = requests.get(OPEN_METEO_FORECAST, params=p, headers=UA, timeout=timeout)
    r.raise_for_status()
    daily, soil = [], []
    for pt, js in zip(points, _as_list(r.json())):
        dd = pd.DataFrame(js["daily"]).rename(columns={"time": "date"})
        dd["MUN"] = pt["MUN"]
        daily.append(dd)
        hh = pd.DataFrame(js["hourly"]).rename(columns={"time": "ts"})
        hh["date"] = pd.to_datetime(hh.ts).dt.date.astype(str)
        hh = hh.drop(columns="ts").groupby("date").mean(numeric_only=True).reset_index()
        hh["MUN"] = pt["MUN"]
        soil.append(hh)
    daily = pd.concat(daily, ignore_index=True)
    daily["date"] = pd.to_datetime(daily.date)
    soil = pd.concat(soil, ignore_index=True)
    soil["date"] = pd.to_datetime(soil.date)
    return daily, soil


def fetch_recent_rain(points, days=90, lag_days=6, timeout=60):
    """ERA5 daily rain for the last `days` days ending `lag_days` ago (ERA5 runs about 5 days behind)."""
    end = date.today() - timedelta(days=lag_days)
    start = end - timedelta(days=days - 1)
    p = {**_coords(points), "timezone": TZ, "start_date": start.isoformat(), "end_date": end.isoformat(),
         "daily": "precipitation_sum"}
    r = requests.get(OPEN_METEO_ARCHIVE, params=p, headers=UA, timeout=timeout)
    r.raise_for_status()
    out = []
    for pt, js in zip(points, _as_list(r.json())):
        dd = pd.DataFrame(js["daily"]).rename(columns={"time": "date"})
        dd["MUN"] = pt["MUN"]
        out.append(dd)
    out = pd.concat(out, ignore_index=True)
    out["date"] = pd.to_datetime(out.date)
    return out


def fetch_rain_normals(points, start="1991-01-01", end="2020-12-31", timeout=180, progress=None):
    """Average rain for each calendar day, 1991–2020 (WMO standard period), per municipal seat.

    One request per location keeps each response small. This is the heaviest call in the app,
    so the result is saved to disk and reused (see data/cache and scripts/build_rain_normals.py).
    """
    out = []
    for i, pt in enumerate(points):
        out.append(fetch_rain_normal_one(pt, start, end, timeout))
        if progress:
            progress((i + 1) / len(points))
    return pd.concat(out, ignore_index=True)


def fetch_rain_normal_one(pt, start="1991-01-01", end="2020-12-31", timeout=180, tries=4, wait=20):
    """Daily rain averages for one location. Open-Meteo counts 30 years as many calls, so a
    'too many requests' (429) answer is likely on the free tier: wait and try again."""
    p = {"latitude": f"{pt['lat']:.4f}", "longitude": f"{pt['lon']:.4f}", "timezone": TZ,
         "start_date": start, "end_date": end, "daily": "precipitation_sum"}
    for attempt in range(tries):
        r = requests.get(OPEN_METEO_ARCHIVE, params=p, headers=UA, timeout=timeout)
        if r.status_code == 429 and attempt < tries - 1:
            time.sleep(wait * (attempt + 1))
            continue
        r.raise_for_status()
        break
    dd = pd.DataFrame(r.json()["daily"]).rename(columns={"time": "date"})
    dd["date"] = pd.to_datetime(dd.date)
    dd["mmdd"] = dd.date.dt.strftime("%m-%d")
    clim = dd.groupby("mmdd").precipitation_sum.mean().reset_index(name="rain_normal_mm")
    clim["MUN"] = pt["MUN"]
    return clim


def window_anomaly(recent, normals, days):
    """Rain over the last `days` days of `recent` vs the 1991–2020 average for the same calendar days."""
    rows = []
    for mun, g in recent.groupby("MUN"):
        g = g.sort_values("date").tail(days)
        mmdd = g.date.dt.strftime("%m-%d")
        nm = normals[normals.MUN == mun].set_index("mmdd").rain_normal_mm
        normal = nm.reindex(mmdd).fillna(nm.reindex(mmdd.replace("02-29", "02-28"))).sum()
        obs = g.precipitation_sum.sum()
        rows.append({"MUN": mun, "observed_mm": obs, "normal_mm": normal,
                     "pct_of_normal": 100 * obs / normal if normal > 0 else np.nan,
                     "from": g.date.min(), "to": g.date.max()})
    return pd.DataFrame(rows)
