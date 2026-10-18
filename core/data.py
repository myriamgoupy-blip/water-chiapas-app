"""Loading the bundled data and building the locality table the whole app works from."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st

from . import geo, live
from .config import CACHE, DATA, MUNS, USE_EN

CENSUS_NUM = ["ALTITUD", "POBTOT", "VIVPARH_CV", "TVIVHAB", "VPH_AGUADV", "VPH_AGUAFV", "VPH_DRENAJ",
              "VPH_EXCSA", "VPH_C_ELEC", "P_3YMAS", "P3YM_HLI", "GRAPROES", "P15YM_AN"]


@st.cache_data(show_spinner=False)
def localities():
    """All 985 census localities of the nine municipalities, with the thesis variables.

    INEGI masks small localities with '*'; those become missing and drop out of the model sample.
    """
    loc = pd.read_csv(DATA / "iter2020_localities.csv")
    for c in CENSUS_NUM:
        loc[c] = pd.to_numeric(loc[c], errors="coerce")
    loc["municipality"] = loc.MUN.map(MUNS)
    # VPH_AGUADV = piped water inside the home or in its yard (INEGI); so this is "no piped water at home"
    loc["dep_water"] = 100 * (1 - loc.VPH_AGUADV / loc.VIVPARH_CV)
    loc["dep_drain"] = 100 * (1 - loc.VPH_DRENAJ / loc.VIVPARH_CV)
    loc["dep_toilet"] = 100 * (1 - loc.VPH_EXCSA / loc.VIVPARH_CV)
    loc["indig"] = 100 * loc.P3YM_HLI / loc.P_3YMAS
    loc["log_pop"] = np.log(loc.POBTOT)
    loc["school"] = loc.GRAPROES
    loc = loc.replace([np.inf, -np.inf], np.nan)   # not clipped: keeps the thesis numbers exact
    thesis = pd.read_csv(DATA / "thesis_intensity_2km.csv")
    loc = loc.merge(thesis, on=["MUN", "LOC"], how="left")
    return loc.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def repda():
    """The 1,061 REPDA titles of the nine municipalities (965 with an extraction volume)."""
    r = pd.read_csv(DATA / "repda_titles.csv", dtype=str)
    r["MUN"] = r.MUN.astype(int)
    r["municipality"] = r.MUN.map(MUNS)
    r["vol"] = pd.to_numeric(r["Volumen de extracción de aguas nacionales (m3/año)"].str.replace(" ", "", regex=False),
                             errors="coerce")
    r["key"] = r["Título"].map(geo.title_key)
    r["use"] = r["Uso"].str.strip().map(USE_EN).fillna("Other")
    r["year"] = pd.to_datetime(r["Fecha de registro"], dayfirst=True, errors="coerce").dt.year
    return r


def vol_by_key():
    r = repda()
    return r[r.vol > 0].dropna(subset=["key"]).groupby("key").vol.sum()


def _prepare_points(pts):
    pts = pts.copy()
    pts["FOLIOREG"] = pts.FOLIOREG.astype(str)
    pts["key"] = pts.FOLIOREG.map(geo.title_key)
    pts["VOL_CONS"] = pd.to_numeric(pts.VOL_CONS, errors="coerce").fillna(0)
    pts["MUPIO"] = pd.to_numeric(pts.MUPIO, errors="coerce")
    uso_col = next((c for c in ["uso", "USO_SUB", "USO_SUP", "USO"] if c in pts.columns), None)
    pts["uso"] = pts[uso_col].astype(str).str.strip().str.upper() if uso_col else ""
    if "TITULAR" not in pts.columns:
        pts["TITULAR"] = ""
    if "source" not in pts.columns:
        pts["source"] = ""
    pts["use"] = pts.uso.map(USE_EN).fillna("Other")
    return pts


@st.cache_data(show_spinner=False)
def thesis_points():
    """Bundled LOCREPDA copy (retrieved 28 Sept 2026), used only when CONAGUA's server does not answer."""
    f = DATA / "locrepda_points_qc.csv"
    if not f.exists():
        return None
    return _prepare_points(pd.read_csv(f, dtype={"FOLIOREG": str}))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def live_points():
    """Pull LOCREPDA now, run the same location check, and save a dated copy in data/cache/."""
    raw = live.fetch_locrepda()
    pts = geo.location_check(_prepare_points(raw), localities())
    pulled = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        pts.to_csv(CACHE / "locrepda_points_live.csv", index=False)
    except OSError:
        pass
    return pts, pulled


def cached_live_points():
    """A previously pulled live copy on disk, if any (survives app reruns, not redeploys)."""
    f = CACHE / "locrepda_points_live.csv"
    if not f.exists():
        return None, None
    stamp = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return _prepare_points(pd.read_csv(f, dtype={"FOLIOREG": str})), stamp


@st.cache_resource(show_spinner=False)
def _live_failures():
    return {}


def active_points():
    """The concession points the app uses, always the live version when CONAGUA answers.

    Order: LOCREPDA pulled live (cached 24 h), else the last live copy on disk, else the copy bundled
    with the app (retrieved 28 Sept 2026). A failed pull is not retried for 30 minutes, so a slow
    CONAGUA server does not slow every page. Returns (points or None, key): "live:<time>" or "bundled".
    """
    fails = _live_failures()
    if datetime.now(timezone.utc).timestamp() - fails.get("t", 0) > 1800:
        try:
            with st.spinner(L_("Leyendo LOCREPDA en el servidor de CONAGUA…", "Reading LOCREPDA from CONAGUA's server…")):
                pts, stamp = live_points()
            if pts is not None and len(pts):
                return pts, f"live:{stamp}"
        except Exception:  # noqa: BLE001
            fails["t"] = datetime.now(timezone.utc).timestamp()
    lp, stamp = cached_live_points()
    if lp is not None:
        return lp, f"live:{stamp}"
    tp = thesis_points()
    if tp is not None:
        return tp, "bundled"
    return None, "none"


def L_(es, en):
    from core.ui import L
    return L(es, en)


@st.cache_data(show_spinner=False)
def drought_snapshot():
    d = pd.read_csv(DATA / "drought_monitor_snapshot.csv", parse_dates=["date"])
    d["cat"] = d["cat"].fillna("None")
    return d


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _drought_auto():
    try:
        return live.fetch_drought_official(), "official"
    except Exception:
        return drought_snapshot(), "bundled"


def drought():
    """Drought monitor history for the nine municipalities.

    Uses the official file if reachable (refreshed every 12 hours), else the bundled copy.
    """
    return _drought_auto()


def sample(loc, dv="dep_water", min_pop=100):
    """Model sample: complete cases with more than `min_pop` inhabitants (Notebook 4)."""
    d = loc.dropna(subset=[dv, "intensity", "indig", "log_pop", "school"])
    return d[d.POBTOT > min_pop].copy()




def municipal_seats():
    """Coordinates of the nine municipal seats (locality 1), used for weather requests."""
    loc = localities()
    s = loc[loc.LOC == 1][["MUN", "lat", "lon", "ALTITUD"]]
    return [dict(MUN=int(r.MUN), lat=float(r.lat), lon=float(r.lon)) for r in s.itertuples()]


NORMALS_FILE = "rain_normals_1991_2020.csv"


def rain_normals():
    """Daily rain climatology 1991–2020 per municipal seat: bundled file, else a copy built at run time."""
    for f in [DATA / NORMALS_FILE, CACHE / NORMALS_FILE]:
        if f.exists():
            return pd.read_csv(f, dtype={"mmdd": str})
    return None


def build_rain_normals(progress=None):
    """Download the averages one municipality at a time, keeping each one on disk, so that if
    Open-Meteo stops answering halfway a second click only fetches the missing ones."""
    CACHE.mkdir(parents=True, exist_ok=True)
    seats = municipal_seats()
    done = []
    for i, pt in enumerate(seats):
        f = CACHE / f"rain_normal_{pt['MUN']}.csv"
        if f.exists():
            part = pd.read_csv(f, dtype={"mmdd": str})
        else:
            part = live.fetch_rain_normal_one(pt)
            part.to_csv(f, index=False)
        done.append(part)
        if progress:
            progress((i + 1) / len(seats))
    nm = pd.concat(done, ignore_index=True)
    nm.to_csv(CACHE / NORMALS_FILE, index=False)
    return nm


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def recent_rain():
    return live.fetch_recent_rain(municipal_seats())


@st.cache_data(ttl=3600, show_spinner=False)
def forecast():
    return live.fetch_forecast(municipal_seats())
