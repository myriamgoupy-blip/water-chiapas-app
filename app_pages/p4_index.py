import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from core import data, engine, index, maps, ui
from core.config import MUNS

L = ui.L
pts, pkey = data.active_points()
loc = engine.table(pkey, pts)
drought, _ = data.drought()

NAMES = {
    "water": (L("Viviendas sin agua entubada", "Homes without piped water"),
              L("Porcentaje de viviendas sin agua entubada dentro (censo 2020).", "Share of homes without piped water inside (2020 census).")),
    "drain": (L("Viviendas sin drenaje", "Homes without drainage"),
              L("Porcentaje de viviendas sin conexión a drenaje.", "Share of homes with no drainage connection.")),
    "mismatch": (L("Agua concedida cerca que no llega", "Water granted nearby that doesn't arrive"),
                 L("Alto cuando hay mucha agua concesionada a menos de 2 km y aun así faltan conexiones en las viviendas.",
                   "High when a lot of water is granted within 2 km and homes still lack connections.")),
    "school": (L("Baja escolaridad", "Low schooling"),
               L("Años promedio de escolaridad, invertidos (menos años = más prioridad).", "Average years of schooling, reversed (fewer years = higher priority).")),
    "drought": (L("Sequía (en vivo)", "Drought (live)"),
                L("Categoría del Monitor de Sequía del municipio (sin sequía = 0, D4 = 1).", "The municipality's Drought Monitor category (no drought = 0, D4 = 1).")),
    "indig": (L("Hablantes de lengua indígena", "Indigenous-language speakers"),
              L("Apagado por defecto: incluirlo es una decisión política que conviene tomar a conciencia.",
                "Off by default: including it is a political choice to make knowingly.")),
}

ui.page_title(L("¿Dónde actuar primero?", "Where to act first?"),
              L("Tú decides qué pesa más. El índice ordena las localidades al instante y luego comprueba si ese orden "
                "depende demasiado de tus pesos exactos.",
                "You decide what matters most. The index ranks localities instantly, then checks whether that order "
                "depends too much on your exact weights."))

for k, v in index.DEFAULT_WEIGHTS.items():
    st.session_state.setdefault(f"w_{k}", int(round(v * 100)))


def reset():
    for k, v in index.DEFAULT_WEIGHTS.items():
        st.session_state[f"w_{k}"] = int(round(v * 100))


@st.fragment
def ranking():
    with st.container(key="panel_index"):
        s1, s2, wv = st.columns([1, 1, 1.1], gap="large")
        weights = {}
        for i, k in enumerate(index.DEFAULT_WEIGHTS):
            col = s1 if i % 2 == 0 else s2
            weights[k] = col.slider(NAMES[k][0], 0, 100, step=5, key=f"w_{k}", help=NAMES[k][1]) / 100
        tot = sum(weights.values())
        with wv:
            if tot > 0:
                w = pd.DataFrame({"c": [NAMES[k][0] for k in weights], "w": [v / tot for v in weights.values()]})
                ch = alt.Chart(w).mark_bar(cornerRadiusEnd=5, height=16, color=ui.NIGHT).encode(
                    y=alt.Y("c:N", sort=list(w.c), title=None, axis=alt.Axis(labelLimit=200, labelColor=ui.INK)),
                    x=alt.X("w:Q", title=L("Peso en el índice", "Weight in the index"), axis=alt.Axis(format="%"),
                            scale=alt.Scale(domain=[0, max(0.5, w.w.max())])))
                t = ch.mark_text(align="left", dx=5, fontSize=12, color=ui.MUTED).encode(text=alt.Text("w:Q", format=".0%"))
                ui.chart(ch + t, height=210)
            o1, o2 = st.columns(2)
            min_pop = o1.select_slider(L("Habitantes mín.", "Min. inhabitants"), [0, 50, 100, 250, 500], value=100, key="i_minpop")
            o2.button(L("Pesos iniciales", "Default weights"), on_click=reset, width="stretch")
    if tot == 0:
        st.warning(L("Todos los pesos están en cero. Sube al menos uno.", "All weights are zero. Raise at least one."))
        return

    d = loc.dropna(subset=["dep_water", "dep_drain", "school", "indig", "intensity"])
    d = d[d.POBTOT > min_pop].copy()
    comp = index.components(d, index.drought_pressure(drought))
    d["index"] = index.score(comp, weights)
    d["rank"] = d["index"].rank(ascending=False, method="min").astype(int)
    d = d.sort_values("rank")

    tab_map, tab_list = st.tabs([L("Mapa", "Map"), L("Lista", "List")])
    with tab_map:
        lo, hi = float(d["index"].min()), float(d["index"].max())
        t = ((d["index"] - lo) / max(hi - lo, 1e-9)).values
        rgb = ui.ramp_rgb(t)
        m = d.assign(r=rgb[:, 0], g=rgb[:, 1], b=rgb[:, 2], elev=(t ** 1.6) * 4500 + 60,
                     t1=d.NOM_LOC, t2=L("Lugar ", "Rank ") + d["rank"].astype(str) + L(" de ", " of ") + str(len(d)),
                     t3=L("Índice ", "Index ") + d["index"].round(0).astype(int).astype(str) + "/100, " + d.MUN.map(ui.mun_short))
        layer = pdk.Layer("ColumnLayer", data=m[["lon", "lat", "r", "g", "b", "elev", "t1", "t2", "t3"]],
                          get_position="[lon, lat]", get_elevation="elev", radius=420, disk_resolution=10,
                          get_fill_color="[r, g, b, 235]", extruded=True, pickable=True, auto_highlight=True)
        st.pydeck_chart(maps.deck([layer], 16.5, -92.45, 9.35, pitch=55, bearing=-20), height=520)
        st.markdown('<div class="legend"><span><span class="ramp"></span>&nbsp; '
                    + L("Prioridad: baja → alta (altura y color)", "Priority: low → high (height and colour)")
                    + '</span></div>', unsafe_allow_html=True)
    with tab_list:
        show = d.head(50)
        st.dataframe(pd.DataFrame({
            "#": show["rank"], L("Localidad", "Locality"): show.NOM_LOC, L("Municipio", "Municipality"): show.MUN.map(MUNS),
            L("Habitantes", "Inhabitants"): show.POBTOT, L("Índice", "Index"): show["index"],
            L("Sin agua %", "No water %"): show.dep_water.round(0), L("Sin drenaje %", "No drainage %"): show.dep_drain.round(0),
            L("Indígena %", "Indigenous %"): show.indig.round(0)}),
            hide_index=True, height=480, column_config={
                L("Índice", "Index"): st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=100, width="medium"),
                L("Habitantes", "Inhabitants"): st.column_config.NumberColumn(format="%d")})
        st.download_button(L("Descargar la lista completa (CSV)", "Download the full list (CSV)"),
                           pd.concat([d[["rank", "MUN", "LOC", "NOM_LOC", "POBTOT", "index"]],
                                      comp.loc[d.index].add_prefix("component_")], axis=1).to_csv(index=False),
                           "priority_index.csv", "text/csv")

    # ------------------------------------------------------------ stability
    st.markdown(f"#### {L('¿Qué tan estable es este orden?', 'How stable is this order?')}")
    top_n = 20
    rs = index.rank_stability(comp, weights, top=top_n)
    top = d.head(top_n).join(rs)
    top["label"] = top["rank"].astype(str) + ". " + top.NOM_LOC + " (" + top.MUN.map(ui.mun_short) + ")"
    sure = (top[f"top{top_n}_share"] >= 0.8).sum()
    st.markdown('<p class="lead">' + L(
        f"Recalculamos el índice 500 veces moviendo un poco tus pesos al azar. <b>{sure} de las {top_n}</b> primeras "
        f"localidades siguen en el top {top_n} en al menos 80% de los casos: son prioridades sólidas.",
        f"We recompute the index 500 times, nudging your weights at random. <b>{sure} of the top {top_n}</b> localities "
        f"stay in the top {top_n} in at least 80% of cases: they are solid priorities.") + '</p>', unsafe_allow_html=True)
    base = alt.Chart(top).encode(y=alt.Y("label:N", sort=list(top.label), title=None,
                                         axis=alt.Axis(labelLimit=320, labelOverlap=False, labelColor=ui.INK)))
    rng = base.mark_bar(height=9, cornerRadius=5, color=ui.WATER_SOFT).encode(
        x=alt.X("rank_p5:Q", title=L("Lugar en las 500 versiones (rango del 90%; punto = mediana)",
                                     "Rank across the 500 versions (90% range; dot = median)")), x2="rank_p95:Q")
    dot = base.mark_circle(size=90, stroke="white", strokeWidth=1.5).encode(
        x="median_rank:Q",
        color=alt.condition(alt.datum[f"top{top_n}_share"] >= 0.8, alt.value(ui.HOMES), alt.value(ui.MUTED)),
        tooltip=[alt.Tooltip("NOM_LOC:N", title=""), alt.Tooltip("median_rank:Q", title=L("mediana", "median")),
                 alt.Tooltip(f"top{top_n}_share:Q", format=".0%", title=f"top {top_n}")])
    cutl = alt.Chart(pd.DataFrame({"x": [top_n + 0.5]})).mark_rule(color=ui.HOMES, strokeDash=[4, 3]).encode(x="x:Q")
    ui.chart(rng + cutl + dot, height=24 * top_n)
    st.markdown('<p class="muted">' + L("Magenta: prioridad sólida (top 20 en 80% o más de las versiones). Gris: depende de los pesos.",
                                        "Magenta: solid priority (top 20 in 80% or more of versions). Grey: depends on the weights.")
                + '</p>', unsafe_allow_html=True)


ranking()
