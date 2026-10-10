import numpy as np
import pandas as pd
import streamlit as st

from core import data, geo, model, ui
from core.config import MUNS, SNAPSHOTS

ui.header("Behind the numbers", "Data, methods and refresh",
          "Where every number in this app comes from, how the main variables are built, and a button to "
          "pull the concession register again from CONAGUA so the analysis can be re-run on today's data.")
pts, src = ui.sidebar_status()

# ================================================================ sources
st.subheader("Sources")
drought, dsrc = data.drought()
normals = data.rain_normals()
src_tbl = pd.DataFrame([
    ["REPDA – Public Register of Water Rights (CONAGUA)", "Every water title: holder, use, authorised volume, date",
     SNAPSHOTS["REPDA"], "Bundled"],
    ["LOCREPDA – geolocated REPDA (CONAGUA ArcGIS server)", "Coordinates of concession wells and intakes",
     src, "Bundled or live"],
    ["ITER 2020 – Census localities (INEGI)", "Households with/without piped water, drainage, language, schooling",
     SNAPSHOTS["ITER"], "Bundled"],
    ["Drought Monitor (CONAGUA–SMN)", "Drought category per municipality every 15 days since 2003",
     dsrc, "Live, with bundled fallback"],
    ["ERA5 reanalysis and forecast models (via Open-Meteo)", "Daily rain, soil moisture, 7-day forecast",
     "1991–2020 averages " + ("ready" if normals is not None else "not built yet") + "; recent data on request", "Live"],
], columns=["Source", "What it provides", "Version in use", "Mode"])
st.markdown("| " + " | ".join(src_tbl.columns) + " |\n|" + "---|" * len(src_tbl.columns) + "\n" +
            "\n".join("| " + " | ".join(map(str, r)) + " |" for r in src_tbl.values))

# ================================================================ refresh LOCREPDA
st.subheader("Concession points: thesis snapshot or today's register")
tp = data.thesis_points()
st.markdown(
    "The thesis analysis uses LOCREPDA as downloaded on 28 September 2026. CONAGUA keeps updating it, so you "
    "can pull it again now. The same location check is applied (points with missing coordinates, in the wrong "
    "municipality or over 10 km from any locality of their municipality are set aside), and every page then "
    "uses the version you choose below.")
c1, c2 = st.columns(2)
with c1:
    if st.button("Pull the current register from CONAGUA", type="primary"):
        st.session_state["_nonce"] = st.session_state.get("_nonce", 0) + 1
        try:
            live_pts, stamp = data.live_points(st.session_state["_nonce"])
            st.session_state["alt_points"] = (live_pts, f"LOCREPDA live pull ({stamp})")
            st.session_state["points_source"] = "alt"
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"CONAGUA's server did not answer ({type(e).__name__}: {str(e)[:120]}). It is often slow; "
                     "try again in a few minutes. The app keeps using the version below.")
with c2:
    up = st.file_uploader("…or upload a points file (locrepda_points_qc.csv)", type=["csv"])
    if up is not None:
        try:
            raw = pd.read_csv(up, dtype={"FOLIOREG": str})
            p = data._prepare_points(raw)
            if "flag" not in p.columns:
                p = geo.location_check(p, data.localities())
            st.session_state["alt_points"] = (p, f"uploaded file {up.name}")
            st.session_state["points_source"] = "alt"
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not read the file: {e}")

options = []
if tp is not None:
    options.append("thesis")
if st.session_state.get("alt_points") is not None:
    options.append("alt")
if options:
    labels = {"thesis": "Thesis snapshot (28 Sept 2026)",
              "alt": st.session_state["alt_points"][1] if st.session_state.get("alt_points") else ""}
    cur = st.session_state.get("points_source", "thesis")
    choice = st.radio("Use in the app", options, index=options.index(cur) if cur in options else 0,
                      format_func=labels.get, horizontal=True)
    if choice != cur:
        st.session_state["points_source"] = choice
        st.rerun()
else:
    st.warning("No concession points are loaded yet. Pull the register or upload the thesis file "
               "(locrepda_points_qc.csv). Until then the map has no concession dots and the model uses the "
               "thesis 2 km values only.")

pts, src = data.active_points()
if pts is not None:
    rep = data.repda()
    ext = rep[rep.vol > 0]
    placed = data.placed_points(pts)
    located = ext.key.isin(set(pts[pts.flag == "ok"].key))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Points", f"{len(pts):,}")
    k2.metric("Passing the location check", f"{(pts.flag == 'ok').mean():.0%}")
    k3.metric("REPDA titles placed on the map", f"{located.sum()} of {len(ext)}")
    k4.metric("Share of REPDA volume placed", f"{placed.vol.sum() / ext.vol.sum():.0%}")
    st.dataframe(pts.flag.value_counts().rename_axis("Location check").reset_index(name="Points"),
                 hide_index=True)

    if tp is not None and st.session_state.get("alt_points") is not None:
        st.markdown("**What changed since the thesis snapshot**")
        alt_pts = st.session_state["alt_points"][0]
        a, b = set(tp.FOLIOREG), set(alt_pts.FOLIOREG)
        loc = data.localities()
        res = {}
        for name, p in [("Thesis snapshot", tp), ("Other version", alt_pts)]:
            dd = model.centre(data.sample(data.with_intensity(p, 2)))
            rr = model.fit(dd)
            res[name] = (len(dd), rr.params["int_c"], rr.pvalues["int_c"])
        st.markdown(
            f"- Titles' point records: {len(b - a)} new, {len(a - b)} no longer listed, {len(a & b)} in both.\n"
            f"- Thesis model at 2 km: β1 = {res['Thesis snapshot'][1]:.3f} (snapshot) vs "
            f"{res['Other version'][1]:.3f} (other version; n = {res['Other version'][0]}, robust p = {res['Other version'][2]:.3f}).")
        if b - a:
            new = alt_pts[alt_pts.FOLIOREG.isin(b - a)][["FOLIOREG", "TITULAR", "MUPIO", "uso", "VOL_CONS", "flag"]]
            st.dataframe(new.assign(MUPIO=new.MUPIO.map(lambda m: MUNS.get(int(m), m) if m == m else m)),
                         hide_index=True, use_container_width=True)

# ================================================================ methods
st.subheader("How the main variables are built")
st.markdown("""
- **Water deprivation**: % of private inhabited dwellings *without piped water inside the dwelling*,
  100 × (1 − VPH_AGUADV / VIVPARH_CV), census 2020. The alternative outcome also counts water piped to the yard as access.
- **Indigenous share**: % of people aged 3 and over who speak an Indigenous language (P3YM_HLI / P_3YMAS).
- **Concession intensity**: REPDA titles are matched to LOCREPDA points on the number after "CHS" in the title.
  Each title's current REPDA volume is split across its points; for each locality the volume of all points within
  the radius is summed, divided by population, and logged: log(1 + m³ per resident per year).
- **Model**: OLS with municipality fixed effects and controls for log population and years of schooling.
  Three p-values: heteroskedasticity-robust (HC1), Conley spatial (Bartlett kernel), and a restricted wild cluster
  bootstrap with Webb weights across the nine municipalities.
- **Priority index**: a weighted average of 0–1 components chosen by the user, with a Monte Carlo check of rank stability.
""")
st.subheader("Limits to keep in mind")
st.markdown("""
- Census figures are from 2020; concessions and drought are more recent. Households may have gained or lost access since.
- INEGI masks figures for very small localities, so 133 of 985 localities cannot be analysed.
- Some LOCREPDA coordinates are wrong by kilometres; those points are set aside, not moved. One large title
  (11CHS156910, Comitán) has no coordinates at all.
- A concession is a right to extract, not a measurement of what is extracted or where it is delivered.
- All model results are associations. Many concessions belong to the local water systems that serve the
  localities next to them, which alone can produce the negative association.
""")

st.subheader("Download")
loc = data.with_intensity(pts, 2)
keep = ["MUN", "municipality", "LOC", "NOM_LOC", "lon", "lat", "ALTITUD", "POBTOT", "dep_water", "dep_water_lot",
        "dep_drain", "indig", "school", "intensity", "intensity_2km_thesis"]
st.download_button("All 985 localities with the app's variables (CSV)", loc[keep].to_csv(index=False),
                   "localities_app.csv", "text/csv")
st.caption("Thesis: *When Water Flows to the Few*, MSc in Big Data & Business Analytics, ESCP Business School, 2026.")
