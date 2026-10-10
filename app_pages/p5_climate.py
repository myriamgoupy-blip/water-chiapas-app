import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, live, ui
from core.config import (AQUA, BLUE, DROUGHT_COLOURS, DROUGHT_LABELS, DROUGHT_LEVELS, GREY,
                         MUN_SHORT, MUNS, ORANGE)

ui.header("Live conditions", "Drought and rain",
          "Water rights are granted on paper; whether there is water to share depends on rain. This page "
          "brings in the official drought assessment for each municipality and rainfall from weather "
          "reanalysis and forecast models, refreshed every time the app is used.")
ui.sidebar_status()

# ================================================================ drought monitor
st.subheader("Drought Monitor (CONAGUA – National Meteorological Service)")
drought, dsrc = data.drought()
st.caption(f"Source: {dsrc}. A new assessment is published around the 15th and the last day of each month.")

with st.expander("Have a newer file? Upload MunicipiosSequia.xlsx"):
    up = st.file_uploader("MunicipiosSequia.xlsx from smn.conagua.gob.mx", type=["xlsx"])
    if up is not None:
        try:
            st.session_state["drought_upload"] = live.parse_drought_xlsx(up.getvalue())
            st.success("File read. All pages now use it.")
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not read this file: {e}")

end = drought.date.max()
latest = drought[drought.date == end].set_index("MUN").cat
streak = {}
for m, g in drought.sort_values("date").groupby("MUN"):
    s = 0
    for c in g.cat.values[::-1]:
        if c == "None":
            break
        s += 1
    streak[m] = s
ordered = sorted(MUNS, key=lambda x: MUN_SHORT[x])
for i in range(0, 9, 3):
    for col, m in zip(st.columns(3), ordered[i:i + 3]):
        c = latest.get(m, "None")
        col.markdown(f"{ui.pill(c if c != 'None' else 'none', DROUGHT_COLOURS[c], '#fff' if c in ('D2', 'D3', 'D4') else '#0b0b0b')} "
                     f"**{MUNS[m]}** <span class='note'>· {DROUGHT_LABELS[c].lower()} · dry for {streak[m]} assessments</span>",
                     unsafe_allow_html=True)
st.caption(f"Status on {end:%d %B %Y}. 'Dry for n assessments' counts consecutive fortnights at D0 or worse.")

period = st.radio("Period", ["Last 2 years", "Last 5 years", "Since 2003"], horizontal=True)
start = {"Last 2 years": end - pd.DateOffset(years=2), "Last 5 years": end - pd.DateOffset(years=5),
         "Since 2003": drought.date.min()}[period]
h = drought.sort_values(["MUN", "date"]).copy()
h["end"] = h.groupby("MUN").date.shift(-1).fillna(h.date + pd.Timedelta(days=15))
h = h[h.date >= start].assign(municipality=lambda x: x.MUN.map(MUN_SHORT), label=lambda x: x.cat.map(DROUGHT_LABELS))
heat = alt.Chart(h).mark_rect().encode(
    x=alt.X("date:T", title=None), x2="end:T",
    y=alt.Y("municipality:N", title=None, axis=alt.Axis(labelOverlap=False)),
    color=alt.Color("cat:N", title="Category", scale=alt.Scale(domain=DROUGHT_LEVELS,
                    range=[DROUGHT_COLOURS[k] for k in DROUGHT_LEVELS]),
                    legend=alt.Legend(orient="bottom", labelExpr="{'None':'No drought','D0':'D0 abnormally dry','D1':'D1 moderate','D2':'D2 severe','D3':'D3 extreme','D4':'D4 exceptional'}[datum.label]")),
    tooltip=["municipality", alt.Tooltip("date:T", format="%d %b %Y"), "label"],
).properties(height=320)
st.altair_chart(heat, use_container_width=True)

yr = drought.assign(year=drought.date.dt.year, dry=drought.cat.isin(["D1", "D2", "D3", "D4"]))
yr = yr.groupby("year").dry.mean().reset_index()
yr["partial"] = np.where(yr.year == end.year, f"{end.year} (to {end:%d %b})", "Full year")
bar = alt.Chart(yr).mark_bar(color=ORANGE).encode(
    x=alt.X("year:O", title=None), y=alt.Y("dry:Q", title="In drought (D1+)", axis=alt.Axis(format="%")),
    opacity=alt.condition(alt.datum.year == end.year, alt.value(1), alt.value(0.55)),
    tooltip=["year", alt.Tooltip("dry:Q", format=".0%"), "partial"])
st.altair_chart(bar.properties(height=220), use_container_width=True)
st.caption("All nine municipalities together. The current year is drawn darker and is not yet complete.")

# ================================================================ rain
st.subheader("Rain compared with normal")
st.caption("Rain at each municipal seat from the ERA5 reanalysis (Copernicus/ECMWF) via Open-Meteo, compared with "
           "the 1991–2020 average for the same days of the year. ERA5 runs about five days behind real time.")
normals = data.rain_normals()
if normals is None:
    st.info("The 1991–2020 rain averages have not been built yet on this server. This is a one-off download "
            "(about a minute); afterwards the comparison loads instantly.")
    if st.button("Build the 1991–2020 rain averages now"):
        bar_ = st.progress(0.0, "Downloading 30 years of daily rain for 9 locations…")
        try:
            normals = data.build_rain_normals(progress=lambda f: bar_.progress(f))
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Open-Meteo could not be reached ({type(e).__name__}). Try again later.")
if normals is not None:
    try:
        recent = data.recent_rain()
        rows = []
        for days in (30, 90):
            a = live.window_anomaly(recent, normals, days).assign(window=f"Last {days} days")
            rows.append(a)
        an = pd.concat(rows).assign(municipality=lambda x: x.MUN.map(MUN_SHORT))
        rule = alt.Chart(pd.DataFrame({"x": [100]})).mark_rule(color="#52514e", strokeDash=[4, 3]).encode(x="x:Q")
        xmax = max(150, float(an.pct_of_normal.max()) * 1.05)
        for col, (win, g) in zip(st.columns(2), an.groupby("window", sort=False)):
            ch = alt.Chart(g).mark_bar().encode(
                y=alt.Y("municipality:N", title=None, axis=alt.Axis(labelOverlap=False)),
                x=alt.X("pct_of_normal:Q", title="Rain as % of the 1991–2020 average", scale=alt.Scale(domain=[0, xmax])),
                color=alt.condition(alt.datum.pct_of_normal < 100, alt.value(ORANGE), alt.value(BLUE)),
                tooltip=["municipality", alt.Tooltip("observed_mm:Q", format=".0f", title="observed (mm)"),
                         alt.Tooltip("normal_mm:Q", format=".0f", title="normal (mm)"),
                         alt.Tooltip("pct_of_normal:Q", format=".0f", title="% of normal")])
            col.markdown(f"**{win}**")
            col.altair_chart((ch + rule).properties(height=250), use_container_width=True)
        w = an[an.window == "Last 90 days"]
        st.caption(f"Window ends {w['to'].max():%d %b %Y}. Orange = below normal. Over the last 90 days the nine seats "
                   f"received between {w.pct_of_normal.min():.0f}% and {w.pct_of_normal.max():.0f}% of their usual rain.")
    except Exception as e:  # noqa: BLE001
        st.warning(f"Live rain data could not be loaded right now ({type(e).__name__}). The drought monitor above is unaffected.")

st.subheader("Last three months and the week ahead")
pick = st.selectbox("Municipality", sorted(MUNS, key=lambda x: MUN_SHORT[x]), format_func=ui.mun_name,
                    index=sorted(MUNS, key=lambda x: MUN_SHORT[x]).index(78))
try:
    daily, soil = data.forecast()
    today = pd.Timestamp.today().normalize()
    dd = daily[daily.MUN == pick].assign(when=lambda x: np.where(x.date > today, "Forecast", "Past days"))
    rain = alt.Chart(dd).mark_bar().encode(
        x=alt.X("date:T", title=None), y=alt.Y("precipitation_sum:Q", title="Rain (mm/day)"),
        color=alt.Color("when:N", title=None, scale=alt.Scale(domain=["Past days", "Forecast"], range=[BLUE, GREY]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("date:T", format="%d %b"), alt.Tooltip("precipitation_sum:Q", format=".1f")])
    st.altair_chart(rain.properties(height=220), use_container_width=True)
    ss = soil[soil.MUN == pick].melt(id_vars=["date", "MUN"], var_name="layer", value_name="m3m3")
    ss["layer"] = ss.layer.map({"soil_moisture_9_to_27cm": "9–27 cm", "soil_moisture_27_to_81cm": "27–81 cm"})
    sm = alt.Chart(ss).mark_line(strokeWidth=2).encode(
        x=alt.X("date:T", title=None), y=alt.Y("m3m3:Q", title="Soil moisture (m³/m³)", scale=alt.Scale(zero=False)),
        color=alt.Color("layer:N", title="Depth", scale=alt.Scale(range=[AQUA, "#0d6b4a"]), legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("date:T", format="%d %b"), "layer", alt.Tooltip("m3m3:Q", format=".3f")])
    st.altair_chart(sm.properties(height=200), use_container_width=True)
    nxt = dd[dd.date > today].precipitation_sum.sum()
    last30 = dd[(dd.date <= today) & (dd.date > today - pd.Timedelta(days=30))].precipitation_sum.sum()
    st.caption(f"{MUNS[pick]}: {last30:.0f} mm in the last 30 days; {nxt:.0f} mm forecast for the next 7 days. "
               "Source: Open-Meteo forecast API (national weather-service models). Soil moisture is modelled, not measured.")
except Exception as e:  # noqa: BLE001
    st.warning(f"Weather data could not be loaded right now ({type(e).__name__}). Open-Meteo may be busy; try again in a minute.")
