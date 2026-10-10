import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, ui
from core.config import BLUE, DROUGHT_COLOURS, DROUGHT_LABELS, DROUGHT_LEVELS, MUN_SHORT, THESIS

ui.header(
    "Interactive companion to the thesis",
    "When Water Flows to the Few",
    "Who holds the rights to water around San Cristóbal de las Casas, and do the people living next to "
    "those concessions have water at home? This tool puts the thesis data on a map, lets you re-run the "
    "model with your own choices, and adds live drought and rain data for the nine municipalities of the "
    "San Cristóbal aquifer area (Chiapas, Mexico).",
)
pts, src = ui.sidebar_status()

rep = data.repda()
ext = rep[rep.vol > 0]
loc = data.localities()
drought, dsrc = data.drought()

# ---- headline numbers -------------------------------------------------------
v = np.sort(ext.vol.values)
n = len(v)
gini = (2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum())
top10 = v[int(np.floor(0.9 * n)):].sum() / v.sum()
has = loc.dropna(subset=["VPH_AGUADV", "VIVPARH_CV"])
share_no_water = 1 - has.VPH_AGUADV.sum() / has.VIVPARH_CV.sum()
latest = drought[drought.date == drought.date.max()]
in_drought = (latest.cat.isin(["D1", "D2", "D3", "D4"])).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Water titles", f"{n:,}", help="REPDA titles with an extraction volume, nine municipalities, September 2026.")
c2.metric("Million m³ per year", f"{ext.vol.sum() / 1e6:,.1f}", help="Total authorised extraction volume.")
c3.metric("Held by the top 10% of titles", f"{top10:.0%}", help=f"Share of the volume held by the largest 10% of titles. Gini coefficient: {gini:.3f}.")
c4.metric("Homes without piped water inside", f"{share_no_water:.0%}",
          help="Share of all dwellings, census 2020, in localities whose data INEGI publishes (small localities are masked). The average locality is far worse off (27%) because the city of San Cristóbal is well served.")

# ---- drought now -------------------------------------------------------------
st.subheader(f"Drought today: {in_drought} of 9 municipalities in drought")
st.caption(f"{dsrc}. Latest assessment: {drought.date.max():%d %B %Y}. "
           "D0 = abnormally dry (a warning, not yet drought); D1–D4 = moderate to exceptional drought.")
lt = latest.assign(municipality=latest.MUN.map(MUN_SHORT),
                   label=latest.cat.map(DROUGHT_LABELS), order=latest.cat.map(DROUGHT_LEVELS.index))
chart = alt.Chart(lt).mark_bar(cornerRadiusEnd=3).encode(
    y=alt.Y("municipality:N", sort=alt.EncodingSortField("order", order="descending"), title=None),
    x=alt.X("order:Q", title="Drought Monitor category", scale=alt.Scale(domain=[0, 5]),
            axis=alt.Axis(values=list(range(6)), labelExpr="['None','D0','D1','D2','D3','D4'][datum.value]")),
    color=alt.Color("cat:N", scale=alt.Scale(domain=DROUGHT_LEVELS, range=[DROUGHT_COLOURS[k] for k in DROUGHT_LEVELS]),
                    legend=None),
    tooltip=["municipality", "label"],
).properties(height=270)
st.altair_chart(chart, use_container_width=True)

# ---- the thesis finding in one paragraph ---------------------------------------
st.subheader("What the thesis model finds")
st.markdown(
    f"""
<div class="card">
Across {THESIS['n']} localities, those with more water concessioned within 2 km have <b>fewer</b> dwellings without
piped water inside (β1 = {THESIS['beta1']}: about 8 percentage points fewer for a locality at the 75th percentile
of concession intensity than for one at the 25th, against an average of 27%). The pattern holds in every alternative specification but is only moderately
strong once spatial correlation and the small number of municipalities are taken into account. It does <b>not</b>
differ with the share of Indigenous-language speakers, and it disappears when water piped to the yard counts as
access. Many concessions are the legal registration of local water systems, so this is an association,
not proof that concessions cause access.
</div>
""", unsafe_allow_html=True)

# ---- how to use ---------------------------------------------------------------------
st.subheader("What you can do here")
a, b, c = st.columns(3)
with a:
    st.markdown("**Map and locality card**  \nClick any locality to see its households, the concessions around it and who holds them.")
    st.page_link("app_pages/p2_map.py", label="Open the map", icon=":material/map:")
with b:
    st.markdown("**Model playground**  \nChange the radius, the sample or the outcome and watch the result hold or break.")
    st.page_link("app_pages/p3_model.py", label="Open the model", icon=":material/tune:")
with c:
    st.markdown("**Priority index**  \nSet your own weights and see which localities come first, and how stable that ranking is.")
    st.page_link("app_pages/p4_index.py", label="Open the index", icon=":material/leaderboard:")

st.divider()
st.caption(
    "Why now: water scarcity is front-page news in Mexico in 2026, from rationing in Guadalajara "
    "([Mexico News Daily, Oct 2026](https://mexiconewsdaily.com/news/jalisco-governor-announces-water-rationing-plan-guadalajara-contamination-crisis/)) "
    "to drought across the Chiapas highlands. All figures on this page are recomputed from the data files each time the app starts."
)
