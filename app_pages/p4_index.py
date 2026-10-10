import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from core import data, index, ui
from core.config import BLUE, MUN_SHORT, MUNS, ORANGE

ui.header("Decide", "Priority index",
          "If a water authority had to choose where to act first, which localities would come up? You set what "
          "matters and how much; the index ranks localities and then checks how much that ranking depends on "
          "your exact weights. The weights are value judgements, not results of the thesis model.")
pts, src = ui.sidebar_status()

for _k, _v in index.DEFAULT_WEIGHTS.items():
    st.session_state.setdefault(f"w_{_k}", int(round(_v * 100)))

with st.sidebar:
    st.markdown("**Index settings**")
    min_pop = st.select_slider("Minimum inhabitants", [0, 50, 100, 250, 500, 1000], value=100)
    dmode = st.radio("Drought component uses", ["average", "latest"],
                     format_func={"average": "Average of the last 12 months", "latest": "Latest assessment only"}.get)
    muns = st.multiselect("Municipalities", list(MUNS), default=list(MUNS), format_func=ui.mun_name)
    if st.button("Reset weights"):
        for k, v in index.DEFAULT_WEIGHTS.items():
            st.session_state[f"w_{k}"] = int(round(v * 100))

st.markdown("#### 1. Set the weights")
weights = {}
cols = st.columns(3)
for i, (k, (label, helptext)) in enumerate(index.COMPONENTS.items()):
    with cols[i % 3]:
        weights[k] = st.slider(label, 0, 100, step=5, key=f"w_{k}", help=helptext) / 100
tot = sum(weights.values())
if tot == 0:
    st.warning("All weights are zero. Move at least one slider.")
    st.stop()
st.caption("Weights are rescaled to sum to 100%: " +
           " · ".join(f"{index.COMPONENTS[k][0].lower()} {v / tot:.0%}" for k, v in weights.items() if v > 0))

loc = data.with_intensity(pts, 2)
drought, dsrc = data.drought()
d = loc.dropna(subset=["dep_water", "dep_drain", "school", "indig", "intensity"])
d = d[(d.POBTOT > min_pop) & d.MUN.isin(muns)].copy()
if len(d) < 5:
    st.error("Too few localities with these filters.")
    st.stop()
comp = index.components(d, index.drought_pressure(drought, mode=dmode))
d["index"] = index.score(comp, weights)
d["rank"] = d["index"].rank(ascending=False, method="min").astype(int)
d = d.sort_values("rank")

st.markdown(f"#### 2. The ranking ({len(d)} localities)")
tab_t, tab_m = st.tabs(["Table", "Map"])
with tab_t:
    show = d.head(40)
    tbl = pd.DataFrame({
        "Rank": show["rank"], "Locality": show.NOM_LOC, "Municipality": show.MUN.map(MUNS),
        "Inhabitants": show.POBTOT, "Index": show["index"],
        "No piped water inside %": show.dep_water, "No drainage %": show.dep_drain,
        "Indigenous %": show.indig, "Schooling (yrs)": show.school,
    })
    st.dataframe(tbl, hide_index=True, use_container_width=True, height=470, column_config={
        "Index": st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100, width="medium"),
        "Schooling (yrs)": st.column_config.NumberColumn(format="%.1f"),
        "Inhabitants": st.column_config.NumberColumn(format="%d"),
        **{c: st.column_config.NumberColumn(format="%.0f") for c in ["No piped water inside %", "No drainage %", "Indigenous %"]}})
    st.download_button("Download the full ranking (CSV)",
                       pd.concat([d[["rank", "MUN", "LOC", "NOM_LOC", "POBTOT", "index"]].assign(municipality=d.MUN.map(MUNS)),
                                  comp.loc[d.index].add_prefix("component_")], axis=1).to_csv(index=False),
                       "priority_index.csv", "text/csv")
with tab_m:
    t = ((d["index"] - d["index"].min()) / max(d["index"].max() - d["index"].min(), 1e-9)).values[:, None]
    lo, hi = np.array([246, 226, 127]), np.array([192, 57, 43])
    rgb = (lo + (hi - lo) * t).astype(int)
    m = d.assign(r=rgb[:, 0], g=rgb[:, 1], b=rgb[:, 2], size=np.sqrt(d.POBTOT) * 6 + 120,
                 t1=d.NOM_LOC, t2="Rank " + d["rank"].astype(str) + " · index " + d["index"].round(0).astype(int).astype(str),
                 t3=d.MUN.map(MUNS))
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", data=m[["lon", "lat", "r", "g", "b", "size", "t1", "t2", "t3"]],
                          get_position="[lon, lat]", get_fill_color="[r, g, b, 220]", get_radius="size",
                          radius_min_pixels=2, radius_max_pixels=16, pickable=True)],
        initial_view_state=pdk.ViewState(latitude=16.55, longitude=-92.45, zoom=8.6),
        map_style=None, tooltip={"html": "<b>{t1}</b><br/>{t2}<br/>{t3}"}), height=470)
    st.caption("Yellow = lower priority, red = higher. Dot size = population.")

st.markdown("#### 3. How stable is this ranking?")
st.markdown("The weights are a choice. Here the index is recomputed 500 times with weights drawn at random "
            "around yours (each draw keeps roughly your priorities but shifts them). A locality that stays near "
            "the top in most draws is a robust priority; one whose rank swings widely depends on your exact weights.")
top_n = st.slider("Look at the top", 10, 50, 20, 5)
rs = index.rank_stability(comp, weights, top=top_n)
top = d.head(top_n).join(rs)
top["label"] = top["rank"].astype(str) + ". " + top.NOM_LOC + " (" + top.MUN.map(MUN_SHORT) + ")"
order = list(top.label)
base = alt.Chart(top).encode(y=alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=320, labelOverlap=False)))
ch = (base.mark_rule(color=BLUE, strokeWidth=3, opacity=0.5).encode(
          x=alt.X("rank_p5:Q", title="Rank across 500 weight draws (5th–95th percentile; dot = median)"), x2="rank_p95:Q")
      + base.mark_circle(size=70, color=BLUE).encode(
          x="median_rank:Q", tooltip=["NOM_LOC", "median_rank", "rank_p5", "rank_p95",
                                      alt.Tooltip(f"top{top_n}_share:Q", format=".0%", title=f"share of draws in top {top_n}")])
      + alt.Chart(pd.DataFrame({"x": [top_n]})).mark_rule(color=ORANGE, strokeDash=[4, 3]).encode(x="x:Q"))
st.altair_chart(ch.properties(height=max(260, 22 * top_n)), use_container_width=True)
robust = (top[f"top{top_n}_share"] >= 0.8).sum()
st.caption(f"{robust} of these {top_n} localities stay in the top {top_n} in at least 80% of the draws. "
           "Orange line: the top-N cut-off.")

with st.expander("How each component is measured"):
    for k, (label, helptext) in index.COMPONENTS.items():
        st.markdown(f"- **{label}.** {helptext}")
    st.markdown(f"Index = weighted average of the components × 100. Drought source: {dsrc}. "
                "Localities whose census figures INEGI masks are left out.")
