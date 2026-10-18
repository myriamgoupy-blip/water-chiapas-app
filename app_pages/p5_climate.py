import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, live, ui
from core.config import DROUGHT_COLOURS, DROUGHT_LEVELS, MUN_SHORT, MUNS

L = ui.L
drought, dkey = data.drought()
last = drought.date.max()
latest = drought[drought.date == last].set_index("MUN").cat
order = sorted(MUNS, key=lambda m: MUN_SHORT[m])

ui.page_title(L("Sequía y lluvia, en vivo", "Drought and rain, live"),
              L("Las concesiones se otorgan en papel; que haya agua para repartir depende de la lluvia. "
                "Esta página se actualiza sola con los datos oficiales de sequía y con la lluvia de los últimos meses.",
                "Concessions are granted on paper; whether there is water to share depends on the rain. "
                "This page updates itself with official drought data and recent rainfall."))

# ================================================================ drought status
streak = {}
for m, g in drought.sort_values("date").groupby("MUN"):
    s = 0
    for c in g.cat.values[::-1]:
        if c == "None":
            break
        s += 1
    streak[m] = s
n_d = int(latest.isin(["D1", "D2", "D3", "D4"]).sum())
st.subheader(L(f"Hoy: {n_d} de 9 municipios en sequía", f"Today: {n_d} of 9 municipalities in drought"))
tiles = []
for m in order:
    c = latest.get(m, "None")
    weeks = streak[m] * 15 / 30
    tiles.append(
        f'<div style="background:#fff;border:1px solid {ui.LINE};border-left:6px solid {DROUGHT_COLOURS[c]};'
        f'border-radius:12px;padding:.6rem .8rem">'
        f'<div style="font-weight:700;color:{ui.NIGHT}">{MUNS[m]}</div>'
        f'<div style="margin:.25rem 0">{ui.dchip(c, ui.dlabel(c))}</div>'
        f'<div class="muted">' + (L(f"Seco desde hace {weeks:.1f} meses", f"Dry for {weeks:.1f} months") if streak[m] else
                                   L("Sin sequía", "No drought")) + '</div></div>')
st.markdown('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:.6rem">'
            + "".join(tiles) + '</div>', unsafe_allow_html=True)
st.caption(ui.drought_source(dkey, last))


@st.fragment
def history():
    period = st.segmented_control(L("Periodo", "Period"), ["2", "5", "all"], default="2", required=True,
                                  format_func={"2": L("2 años", "2 years"), "5": L("5 años", "5 years"),
                                               "all": L("Desde 2003", "Since 2003")}.get, key="c_period")
    start = drought.date.min() if period == "all" else last - pd.DateOffset(years=int(period))
    h = drought.sort_values(["MUN", "date"]).copy()
    h["end"] = h.groupby("MUN").date.shift(-1).fillna(h.date + pd.Timedelta(days=15))
    h = h[h.date >= start].assign(municipality=lambda x: x.MUN.map(MUN_SHORT), label=lambda x: x.cat.map(ui.dlabel))
    labels = {k: ui.dlabel(k) for k in DROUGHT_LEVELS}
    heat = alt.Chart(h).mark_rect(cornerRadius=2).encode(
        x=alt.X("date:T", title=None, axis=ui.date_axis("month")), x2="end:T",
        y=alt.Y("municipality:N", title=None, sort=[MUN_SHORT[m] for m in order], axis=alt.Axis(labelColor=ui.INK, labelFontSize=12)),
        color=alt.Color("cat:N", title=None, scale=alt.Scale(domain=DROUGHT_LEVELS, range=[DROUGHT_COLOURS[k] for k in DROUGHT_LEVELS]),
                        legend=alt.Legend(orient="top", labelExpr="{" + ",".join(f"'{k}':'{v}'" for k, v in labels.items()) + "}[datum.label]")),
        tooltip=[alt.Tooltip("municipality:N", title=""), alt.Tooltip("date:T", format="%d/%m/%Y", title=L("fecha", "date")),
                 alt.Tooltip("label:N", title="")])
    ui.chart(heat, height=290)

    yr = drought.assign(year=drought.date.dt.year, dry=drought.cat.isin(["D1", "D2", "D3", "D4"]))
    yr = yr.groupby("year").dry.mean().reset_index()
    bars = alt.Chart(yr).mark_bar(cornerRadiusEnd=4, color=DROUGHT_COLOURS["D1"]).encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0, labelExpr="datum.value % 5 == 0 ? datum.value : ''")),
        y=alt.Y("dry:Q", title=L("Tiempo en sequía (D1 o más)", "Time in drought (D1 or worse)"), axis=alt.Axis(format="%")),
        opacity=alt.condition(alt.datum.year == last.year, alt.value(1), alt.value(0.6)),
        tooltip=[alt.Tooltip("year:O", title=""), alt.Tooltip("dry:Q", format=".0%", title="")])
    ui.chart(bars, height=200)
    st.markdown('<p class="muted">' + L(f"Los nueve municipios juntos. {last.year} aún no termina.",
                                        f"All nine municipalities together. {last.year} is not over yet.") + '</p>',
                unsafe_allow_html=True)


history()

# ================================================================ rain
st.subheader(L("Lluvia frente a lo normal", "Rain compared with normal"))
normals = data.rain_normals()
if normals is None:
    st.info(L("Para comparar con lo normal, la app necesita el promedio de lluvia 1991–2020. Se descarga una sola vez (un minuto).",
              "To compare with normal, the app needs the 1991–2020 rain average. It downloads once (about a minute)."))
    if st.button(L("Descargar promedios 1991–2020", "Download 1991–2020 averages"), type="primary"):
        bar_ = st.progress(0.0)
        try:
            data.build_rain_normals(progress=lambda f: bar_.progress(f))
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(L("Open-Meteo dejó de responder (límite gratuito de consultas grandes). Lo ya descargado se guarda: "
                       "espera un minuto y vuelve a pulsar el botón.",
                       "Open-Meteo stopped answering (free limit on large requests). What was downloaded is kept: "
                       "wait a minute and press the button again."))


@st.fragment
def rain():
    mun = st.pills(L("Municipio", "Municipality"), order, default=78, required=True,
                   format_func=lambda m: MUN_SHORT[m], key="c_mun")
    try:
        recent = data.recent_rain()
    except Exception as e:  # noqa: BLE001
        st.warning(L(f"No se pudo consultar la lluvia ahora ({type(e).__name__}). Inténtalo en un minuto.",
                     f"Rain data could not be loaded right now ({type(e).__name__}). Try again in a minute."))
        return
    if normals is not None:
        an = pd.concat([live.window_anomaly(recent, normals, w).assign(w=w) for w in (30, 90)])
        a90 = an[an.w == 90].assign(m=lambda x: x.MUN.map(MUN_SHORT))
        c1, c2 = st.columns([3, 2], gap="large")
        with c1:
            base = alt.Chart(a90).encode(y=alt.Y("m:N", title=None, sort=[MUN_SHORT[m] for m in order],
                                                 axis=alt.Axis(labelColor=ui.INK, labelFontSize=12)))
            obs = base.mark_bar(height=16, cornerRadiusEnd=5).encode(
                x=alt.X("observed_mm:Q", title=L("Lluvia de los últimos 90 días (mm)", "Rain over the last 90 days (mm)")),
                color=alt.condition(alt.datum.pct_of_normal < 100, alt.value(DROUGHT_COLOURS["D1"]), alt.value(ui.WATER)),
                tooltip=[alt.Tooltip("m:N", title=""), alt.Tooltip("observed_mm:Q", format=".0f", title="mm"),
                         alt.Tooltip("normal_mm:Q", format=".0f", title=L("normal", "normal")),
                         alt.Tooltip("pct_of_normal:Q", format=".0f", title="%")])
            tick = base.mark_tick(thickness=3, size=26, color=ui.NIGHT).encode(x="normal_mm:Q")
            a90["max_mm"] = a90[["observed_mm", "normal_mm"]].max(axis=1)
            a90["pct_txt"] = a90.pct_of_normal.round(0).astype(int).astype(str) + "%"
            lab = alt.Chart(a90).mark_text(align="left", dx=8, fontSize=12, color=ui.MUTED).encode(
                y=alt.Y("m:N", sort=[MUN_SHORT[m] for m in order]), x="max_mm:Q", text="pct_txt:N")
            ui.chart(obs + tick + lab, height=300)
            st.markdown('<p class="muted">' + L(
                f"Barra: lluvia observada ({a90['from'].min():%d/%m} al {a90['to'].max():%d/%m}). Raya oscura: lo normal en esas fechas (1991–2020). "
                "Naranja: por debajo de lo normal.",
                f"Bar: observed rain ({a90['from'].min():%d/%m} to {a90['to'].max():%d/%m}). Dark tick: normal for those dates (1991–2020). "
                "Orange: below normal.") + " " + L(
                "Las cantidades vienen del modelo ERA5, que tiende a sobrestimar la lluvia en zonas de montaña: compara el porcentaje, no los milímetros.",
                "Amounts come from the ERA5 model, which tends to overestimate rain in mountains: compare the percentage, not the millimetres.")
                + '</p>', unsafe_allow_html=True)
        with c2:
            g = recent[recent.MUN == mun].sort_values("date").copy()
            g["obs"] = g.precipitation_sum.cumsum()
            nm = normals[normals.MUN == mun].set_index("mmdd").rain_normal_mm
            g["norm"] = nm.reindex(g.date.dt.strftime("%m-%d").replace("02-29", "02-28")).values.cumsum()
            area = alt.Chart(g).mark_area(color=ui.gradient(ui.WATER, 0.45), line={"color": ui.WATER, "strokeWidth": 3},
                                          interpolate="monotone").encode(
                x=alt.X("date:T", title=None, axis=ui.date_axis("day")),
                y=alt.Y("obs:Q", title=L("Lluvia acumulada (mm)", "Accumulated rain (mm)")),
                tooltip=[alt.Tooltip("date:T", format="%d/%m"), alt.Tooltip("obs:Q", format=".0f", title=L("este año", "this year")),
                         alt.Tooltip("norm:Q", format=".0f", title=L("normal", "normal"))])
            normal = alt.Chart(g).mark_line(color=ui.NIGHT, strokeDash=[5, 4], strokeWidth=2).encode(x="date:T", y="norm:Q")
            ui.chart(area + normal, height=300)
            pct = 100 * g.obs.iloc[-1] / g.norm.iloc[-1] if g.norm.iloc[-1] > 0 else np.nan
            st.markdown('<p class="muted">' + L(
                f"{MUNS[mun]}: {g.obs.iloc[-1]:.0f} mm en 90 días, {pct:.0f}% de lo normal (línea punteada).",
                f"{MUNS[mun]}: {g.obs.iloc[-1]:.0f} mm in 90 days, {pct:.0f}% of normal (dashed line).") + '</p>',
                unsafe_allow_html=True)

    try:
        daily, soil = data.forecast()
    except Exception as e:  # noqa: BLE001
        st.warning(L(f"El pronóstico no está disponible ahora ({type(e).__name__}).",
                     f"The forecast is not available right now ({type(e).__name__})."))
        return
    today = pd.Timestamp.today().normalize()
    dd = daily[(daily.MUN == mun) & (daily.date > today - pd.Timedelta(days=45))].copy()
    dd["when"] = np.where(dd.date > today, L("Pronóstico", "Forecast"), L("Días pasados", "Past days"))
    c3, c4 = st.columns(2, gap="large")
    with c3:
        st.markdown(f"#### {L('Lluvia diaria y próximos 7 días', 'Daily rain and the next 7 days')}")
        bars = alt.Chart(dd).mark_bar(cornerRadiusEnd=3, width={"band": 0.75}).encode(
            x=alt.X("yearmonthdate(date):T", title=None, axis=ui.date_axis("day")),
            y=alt.Y("precipitation_sum:Q", title="mm"),
            color=alt.Color("when:N", title=None, scale=alt.Scale(domain=[L("Días pasados", "Past days"), L("Pronóstico", "Forecast")],
                                                                     range=[ui.WATER, ui.WATER_SOFT])),
            tooltip=[alt.Tooltip("date:T", format="%d/%m"), alt.Tooltip("precipitation_sum:Q", format=".1f", title="mm")])
        ui.chart(bars, height=240)
        nxt = dd[dd.date > today].precipitation_sum.sum()
        st.markdown('<p class="muted">' + L(f"Pronóstico para los próximos 7 días: {nxt:.0f} mm.",
                                            f"Forecast for the next 7 days: {nxt:.0f} mm.") + '</p>', unsafe_allow_html=True)
    with c4:
        st.markdown(f"#### {L('Humedad del suelo', 'Soil moisture')}")
        ss = soil[(soil.MUN == mun) & (soil.date > today - pd.Timedelta(days=45))].melt(
            id_vars=["date", "MUN"], var_name="layer", value_name="v")
        ss["layer"] = ss.layer.map({"soil_moisture_9_to_27cm": "9–27 cm", "soil_moisture_27_to_81cm": "27–81 cm"})
        sm = alt.Chart(ss).mark_line(strokeWidth=3, interpolate="monotone").encode(
            x=alt.X("date:T", title=None, axis=ui.date_axis("day")),
            y=alt.Y("v:Q", title="m³/m³", scale=alt.Scale(zero=False)),
            color=alt.Color("layer:N", title=L("Profundidad", "Depth"), scale=alt.Scale(range=[ui.PINE, ui.NIGHT])),
            tooltip=[alt.Tooltip("date:T", format="%d/%m"), "layer:N", alt.Tooltip("v:Q", format=".3f")])
        sm = sm + alt.Chart(ss[ss.date == ss.date.max()]).mark_circle(size=70, stroke="white", strokeWidth=1.5).encode(
            x="date:T", y="v:Q", color=alt.Color("layer:N", legend=None, scale=alt.Scale(range=[ui.PINE, ui.NIGHT])))
        ui.chart(sm, height=240)
        st.markdown('<p class="muted">' + L("Modelada, no medida (Open-Meteo).", "Modelled, not measured (Open-Meteo).") + '</p>',
                    unsafe_allow_html=True)


rain()
if normals is not None and not (data.DATA / data.NORMALS_FILE).exists():
    st.download_button(L("Descargar el archivo de promedios (súbelo a data/ en GitHub para que sea permanente)",
                         "Download the averages file (upload it to data/ on GitHub to make it permanent)"),
                       normals.to_csv(index=False), data.NORMALS_FILE, "text/csv")
