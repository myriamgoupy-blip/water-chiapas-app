import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from core import data, geo, index, ui
from core.config import DROUGHT_LABELS, MUNS, USE_COLOURS

ui.header("Explore", "Map and locality card",
          "Each grey-to-blue dot is a census locality; coloured dots are registered water concessions. "
          "Click a locality (or pick it from the list) to open its card.")
pts, src = ui.sidebar_status()

# ---------------------------------------------------------------- settings
with st.sidebar:
    st.markdown("**Map settings**")
    colour_by = st.selectbox("Colour localities by", [
        "Dwellings without piped water inside (%)", "Concession intensity (2 km)",
        "Indigenous-language speakers (%)", "Priority index (default weights)", "Altitude (m)"])
    radius = st.slider("Radius for the card (km)", 0.5, 5.0, 2.0, 0.5,
                       help="Concessions within this distance are listed on the card. The thesis uses 2 km.")
    show_pts = st.checkbox("Show concession points", True, disabled=pts is None)
    show_flagged = st.checkbox("Also show points that failed the location check", False, disabled=pts is None)
    muns = st.multiselect("Municipalities", list(MUNS), default=list(MUNS), format_func=ui.mun_name)

loc = data.with_intensity(pts, 2)
placed = data.placed_points(pts) if pts is not None else None
drought, dsrc = data.drought()
latest_d = drought[drought.date == drought.date.max()].set_index("MUN").cat

# default priority index, for colouring and for the card
idx_base = loc.dropna(subset=["dep_water", "dep_drain", "school", "indig", "intensity"])
comp = index.components(idx_base, index.drought_pressure(drought))
loc["priority"] = index.score(comp, index.DEFAULT_WEIGHTS).reindex(loc.index)
loc["priority_rank"] = loc.priority.rank(ascending=False, method="min")

# ---------------------------------------------------------------- selection (map click or list)
ev = st.session_state.get("deckmap")
try:
    objs = ev["selection"]["objects"].get("localities", []) if ev else []
except (KeyError, TypeError, AttributeError):
    objs = []
if objs:
    o = objs[0]
    if (o.get("MUN"), o.get("LOC")) != st.session_state.get("_last_click"):
        st.session_state["_last_click"] = (o.get("MUN"), o.get("LOC"))
        st.session_state["card_mun"] = int(o["MUN"])
        st.session_state["card_loc"] = int(o["LOC"])

view = loc[loc.MUN.isin(muns) & loc.lon.notna()].copy()

c1, c2 = st.columns([1, 2])
with c1:
    mun_opts = sorted(view.MUN.unique(), key=ui.mun_name)
    if st.session_state.get("card_mun") not in mun_opts:
        st.session_state["card_mun"] = 78 if 78 in mun_opts else mun_opts[0]
    sel_mun = st.selectbox("Municipality", mun_opts, format_func=ui.mun_name, key="card_mun")
with c2:
    opts = view[view.MUN == sel_mun].sort_values("POBTOT", ascending=False)
    names = dict(zip(opts.LOC, opts.NOM_LOC + " (" + opts.POBTOT.map(ui.fmt_int) + " inhabitants)"))
    if st.session_state.get("card_loc") not in names:
        st.session_state["card_loc"] = int(opts.LOC.iloc[0])
    sel_loc = st.selectbox("Locality (largest first)", list(names), format_func=names.get, key="card_loc")

row = loc[(loc.MUN == sel_mun) & (loc.LOC == sel_loc)].iloc[0]

# ---------------------------------------------------------------- colours
LO, HI = np.array([228, 227, 222]), np.array([13, 71, 161])
col_map = {"Dwellings without piped water inside (%)": ("dep_water", 0, 100),
           "Concession intensity (2 km)": ("intensity", 0, float(np.nanmax(loc.intensity)) if loc.intensity.notna().any() else 1),
           "Indigenous-language speakers (%)": ("indig", 0, 100),
           "Priority index (default weights)": ("priority", float(np.nanmin(loc.priority)), float(np.nanmax(loc.priority))),
           "Altitude (m)": ("ALTITUD", float(np.nanmin(loc.ALTITUD)), float(np.nanmax(loc.ALTITUD)))}
var, vmin, vmax = col_map[colour_by]
t = ((view[var] - vmin) / (vmax - vmin if vmax > vmin else 1)).clip(0, 1)
rgb = np.where(t.notna().values[:, None], LO + (HI - LO) * t.fillna(0).values[:, None], [200, 200, 200])
view["r"], view["g"], view["b"] = rgb[:, 0].astype(int), rgb[:, 1].astype(int), rgb[:, 2].astype(int)
view["a"] = np.where(view[var].isna(), 90, 215)
view["size"] = np.sqrt(view.POBTOT.fillna(1).clip(lower=1)) * 6 + 120
view["value_txt"] = view[var].map(lambda x: "masked" if x != x else f"{x:,.1f}")
view["mun_name"] = view.MUN.map(MUNS)
view["t1"] = view.NOM_LOC
view["t2"] = view.mun_name + " · " + view.POBTOT.map(ui.fmt_int) + " inhabitants"
view["t3"] = colour_by + ": " + view.value_txt

layers = [pdk.Layer("ScatterplotLayer", id="localities",
                    data=view[["MUN", "LOC", "t1", "t2", "t3", "lon", "lat", "r", "g", "b", "a", "size"]],
                    get_position="[lon, lat]", get_fill_color="[r, g, b, a]", get_radius="size",
                    radius_min_pixels=2, radius_max_pixels=18, pickable=True, auto_highlight=True,
                    stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=0.5)]
if show_pts and placed is not None and not placed.empty:
    pp = placed[placed.MUPIO.isin(muns)].copy()
    pp["rgb"] = pp.use.map(lambda u: USE_COLOURS.get(u, USE_COLOURS["Other"]))
    pp["rad"] = np.sqrt(pp.vol.clip(lower=1)) * 1.2 + 40
    pp["t1"] = pp.TITULAR.fillna("").astype(str)
    pp["t2"] = pp.use + " · " + pp.source.replace({"subterranea": "groundwater", "superficial": "surface water"})
    pp["t3"] = pp.vol.map(lambda x: f"{x:,.0f} m³/yr")
    layers.append(pdk.Layer("ScatterplotLayer", id="concessions",
                            data=pp[["LONDEC", "LATDEC", "rgb", "rad", "t1", "t2", "t3"]],
                            get_position="[LONDEC, LATDEC]", get_fill_color="rgb", get_radius="rad", opacity=0.75,
                            radius_min_pixels=2, radius_max_pixels=25, pickable=True))
if show_flagged and pts is not None:
    bad = pts[(pts.flag != "ok") & pts.LONDEC.notna() & (pts.LONDEC != 0)].copy()
    bad["t1"] = bad.TITULAR.fillna("").astype(str)
    bad["t2"] = "Failed the location check: " + bad.flag.str.replace("_", " ")
    bad["t3"] = "Registered in " + bad.MUPIO.map(lambda m: MUNS.get(int(m), "?") if m == m else "?")
    layers.append(pdk.Layer("ScatterplotLayer", id="flagged", data=bad[["LONDEC", "LATDEC", "t1", "t2", "t3"]],
                            get_position="[LONDEC, LATDEC]", get_fill_color=[235, 104, 52, 230], get_radius=250,
                            radius_min_pixels=3, pickable=True))
layers.append(pdk.Layer("ScatterplotLayer", id="ring", data=pd.DataFrame([{"lon": row.lon, "lat": row.lat}]),
                        get_position="[lon, lat]", get_radius=radius * 1000, filled=False, stroked=True,
                        get_line_color=[235, 104, 52], line_width_min_pixels=2))

deck = pdk.Deck(
    layers=layers,
    initial_view_state=pdk.ViewState(latitude=float(row.lat), longitude=float(row.lon), zoom=10.2 if radius <= 2 else 9.4),
    map_style=None,
    tooltip={"html": "<b>{t1}</b><br/>{t2}<br/>{t3}",
             "style": {"fontSize": "12px"}},
)
left, right = st.columns([3, 2], gap="large")
with left:
    try:
        st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key="deckmap", height=560)
    except TypeError:  # older Streamlit without map selection
        st.pydeck_chart(deck, height=560)
    st.caption(f"Colour: {colour_by.lower()} (light = low, dark blue = high; pale grey = masked by INEGI). "
               "Concession colours: blue public-urban, green agricultural, orange industrial, purple services, grey other. "
               f"Orange ring = {radius:g} km around the selected locality. Source of points: {src}.")

# ---------------------------------------------------------------- the card
def pct(x):
    return "masked" if x != x else f"{x:.0f}%"

near = geo.concessions_near(row.lon, row.lat, placed, radius) if placed is not None else None
vol_near = float(near.vol.sum()) if near is not None else np.nan
with right:
    st.markdown(f"### {row.NOM_LOC}")
    dcat = latest_d.get(int(row.MUN), "None")
    st.markdown(f"{MUNS[int(row.MUN)]} · {ui.fmt_int(row.ALTITUD)} m above sea level · "
                f"Drought now: **{DROUGHT_LABELS.get(dcat, dcat)}**")
    st.markdown(ui.facts([
        ("Inhabitants", ui.fmt_int(row.POBTOT)),
        ("Homes without piped water inside", pct(row.dep_water)),
        ("…without water even to the yard", pct(row.dep_water_lot)),
        ("Homes without drainage", pct(row.dep_drain)),
        ("Speak an Indigenous language (3+)", pct(row.indig)),
        ("Average years of schooling", "masked" if row.school != row.school else f"{row.school:.1f}"),
    ]), unsafe_allow_html=True)
    if placed is not None:
        per_res = vol_near / row.POBTOT if row.POBTOT else np.nan
        st.markdown(ui.facts([
            (f"Water concessioned within {radius:g} km", f"{vol_near:,.0f} m³/yr"),
            ("Per resident", f"{per_res:,.0f} m³/yr" if per_res == per_res else "–"),
            ("Points / titles", f"{len(near)} / {near.key.nunique()}"),
        ]), unsafe_allow_html=True)
    if row.intensity == row.intensity:
        share_below = (loc.intensity < row.intensity).mean()
        st.markdown(f"Concession intensity (2 km): **{row.intensity:.2f}**, higher than {share_below:.0%} of localities.")
    if row.priority == row.priority:
        st.markdown(f"Priority index (default weights): **{row.priority:.0f}/100**, rank {row.priority_rank:.0f} "
                    f"of {int(loc.priority.notna().sum())} localities with complete data.")

st.markdown(f"#### Concessions within {radius:g} km of {row.NOM_LOC}")
if near is None:
    st.info("Concession points are not loaded, so this list is empty. Go to *Data, methods and refresh* to load the "
            "thesis snapshot or pull the current register from CONAGUA.")
elif near.empty:
    st.write("No located concession within this radius.")
else:
    rep = data.repda()
    titles = rep.dropna(subset=["key"]).drop_duplicates("key").set_index("key")
    tbl = pd.DataFrame({
        "Holder": near.TITULAR, "Use": near.use,
        "Volume at this point (m³/yr)": near.vol.round(0),
        "Distance (km)": near.dist_km.round(2),
        "Water": near.source.replace({"subterranea": "groundwater", "superficial": "surface"}),
        "REPDA title": near.key.map(titles["Título"]),
        "Registered": near.key.map(titles["Fecha de registro"]),
    })
    st.dataframe(tbl, hide_index=True, use_container_width=True,
                 column_config={"Volume at this point (m³/yr)": st.column_config.NumberColumn(format="%d")})
    top = near.groupby("TITULAR").vol.sum().sort_values(ascending=False)
    st.caption(f"{len(near)} points, {near.key.nunique()} titles. Largest holder nearby: {top.index[0]} "
               f"({top.iloc[0] / top.sum():.0%} of the volume within {radius:g} km). Volumes are current REPDA volumes, "
               "split across a title's points.")
