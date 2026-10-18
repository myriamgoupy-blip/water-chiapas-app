import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, engine, holders, insights, maps, ui
from core.config import THESIS

L = ui.L
pts, pkey = data.active_points()
rep = data.repda()
ext = rep[rep.vol > 0].copy()
loc = engine.table(pkey, pts)
drought, dkey = data.drought()
k, _, _ = insights.current()

# ---- numbers ---------------------------------------------------------------------
v = np.sort(ext.vol.values)
n = len(v)
top10 = v[int(np.floor(0.9 * n)):].sum() / v.sum()
last = drought.date.max()
latest = drought[drought.date == last].set_index("MUN").cat
n_drought = int(latest.isin(["D1", "D2", "D3", "D4"]).sum())
seg = insights.segment_summary(k)
unconn = seg.loc[["outside", "nearby"]]
unconn_share_nowater = float(unconn.share_nowater.sum())
unconn_n = int(unconn.localities.sum())
unconn_people = float(unconn.share_people.sum())

# ---- hero ----------------------------------------------------------------------------
with st.container(key="hero"):
    left, right = st.columns([5, 6], gap="large", vertical_alignment="center")
    with left:
        st.markdown(ui.live_pill(L(f"Datos en vivo · sequía al {last:%d/%m/%Y}", f"Live data · drought as of {last:%d/%m/%Y}"))
                    + " &nbsp;" + '<span class="pill" style="color:#C9B8FF">✦ ' + L("Modelo + IA", "Model + AI") + '</span>',
                    unsafe_allow_html=True)
        st.markdown(f"# {L('¿Quién tiene el agua?', 'Who holds the water?')}")
        st.markdown(
            '<p class="hero-sub">' + L(
                f"Alrededor de San Cristóbal de las Casas, CONAGUA ha otorgado {n:,} títulos que suman "
                f"{ext.vol.sum() / 1e6:,.0f} millones de m³ de agua al año. Aun así, en la localidad promedio "
                "una de cada cuatro viviendas no tiene agua entubada. Esta app muestra dónde, y por qué.",
                f"Around San Cristóbal de las Casas, CONAGUA has granted {n:,} water titles adding up to "
                f"{ext.vol.sum() / 1e6:,.0f} million m³ a year. Yet in the average locality one home in four "
                "has no piped water. This app shows where, and why.") + '</p>', unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        b1.page_link("app_pages/p7_ask.py", label=L("Pregunta a los datos", "Ask the data"), icon=":material/auto_awesome:")
        b2.page_link("app_pages/p2_map.py", label=L("Busca tu localidad", "Find your locality"), icon=":material/map:")
        st.markdown(
            "<p style='margin:.8rem 0 .35rem 0;font-weight:600;color:#DCE5F2'>"
            + L(f"Sequía hoy: {n_drought} de 9 municipios", f"Drought today: {n_drought} of 9 municipalities") + "</p>"
            + " ".join(ui.dchip(latest.get(m, "None"), f"{ui.mun_short(m)} {latest.get(m, 'None').replace('None', '–')}")
                       for m in sorted(latest.index, key=ui.mun_short)),
            unsafe_allow_html=True)
    with right:
        view = loc[loc.lon.notna()].copy()
        view["t1"] = view.NOM_LOC
        view["t2"] = view.MUN.map(ui.mun_name)
        view["t3"] = L("Sin agua entubada: ", "No piped water: ") + view.dep_water.map(
            lambda x: "–" if x != x else f"{x:.0f}%")
        layers = [maps.locality_layer(view, "dep_water", 0, 100, pickable=True, opacity=235)]
        if pts is not None:
            placed = engine.point_arrays(pkey, pts)["placed"].copy()
            placed["t1"] = placed.TITULAR.fillna("").astype(str).str.title()
            placed["t2"] = placed.use.map(ui.use_label)
            placed["t3"] = placed.vol.map(lambda x: f"{x:,.0f} m³/año" if ui.lang() == "ES" else f"{x:,.0f} m³/yr")
            layers.append(maps.concession_layer(placed, radius_m=230, height=2.2))
        st.pydeck_chart(maps.deck(layers, 16.52, -92.45, 8.9, pitch=52, bearing=-18), height=440)
        st.markdown(maps.legend(L("Viviendas sin agua entubada", "Homes without piped water"), "0%", "100%"), unsafe_allow_html=True)

# ---- four numbers ----------------------------------------------------------------------
st.write("")
a, b, c, d = st.columns(4, gap="medium")
with a.container(key="glass_k1"):
    st.markdown(ui.count(n, cls="water") + f'<p class="muted">{L("títulos de agua que autorizan extracción", "water titles that authorise extraction")}</p>',
                unsafe_allow_html=True)
with b.container(key="glass_k2"):
    st.markdown(ui.count(ext.vol.sum() / 1e6, suffix=" M m³", cls="water")
                + f'<p class="muted">{L("de agua concedida al año en los 9 municipios", "of water granted per year in the 9 municipalities")}</p>',
                unsafe_allow_html=True)
with c.container(key="glass_k3"):
    st.markdown(ui.count(100 * top10, suffix="%") + f'<p class="muted">{L("del volumen está en el 10% de los títulos más grandes", "of the volume sits in the largest 10% of titles")}</p>',
                unsafe_allow_html=True)
with d.container(key="glass_k4"):
    st.markdown(ui.count(100 * unconn_share_nowater, suffix="%", cls="homes")
                + f'<p class="muted">{L(f"de las viviendas sin agua están en solo {unconn_n} localidades ({unconn_people:.0%} de la población)", f"of homes without piped water are in just {unconn_n} localities ({unconn_people:.0%} of the population)")}</p>',
                unsafe_allow_html=True)

# ---- what the model found ---------------------------------------------------------------
st.subheader(L("Lo que encontró el modelo", "What the model found"))
f1, f2, f3 = st.columns(3, gap="medium")
cards = [
    (f1, L("Agua registrada y agua en casa van juntas", "Registered water and piped water go together"), L(
        f"En {THESIS['n']} localidades, pasar de poca a mucha agua concedida a menos de 2 km se asocia con unos "
        "8 puntos menos de viviendas sin agua entubada (promedio: 27%).",
        f"Across {THESIS['n']} localities, going from little to much water granted within 2 km goes with about "
        "8 points fewer homes without piped water (average: 27%).")),
    (f2, L("Constante, pero moderado", "Consistent, but moderate"), L(
        "El signo se mantiene en todas las variantes; su solidez depende de cómo se trate la cercanía entre "
        "localidades y el número pequeño de municipios. Es una asociación, no una causa.",
        "The sign holds in every variant; how strong it is depends on how closeness between localities and the "
        "small number of municipalities are handled. An association, not a cause.")),
    (f3, L("El problema está concentrado", "The problem is concentrated"), L(
        f"{unconn_n} localidades pequeñas concentran {unconn_share_nowater:.0%} de las viviendas sin agua. Se dividen en dos "
        "grupos que necesitan respuestas distintas.",
        f"{unconn_n} small localities hold {unconn_share_nowater:.0%} of the homes without piped water. They split into two "
        "groups that need different answers.")),
]
for i, (col, t, x) in enumerate(cards):
    with col.container(key=f"glass_f{i}"):
        st.markdown(f"**{t}**")
        st.markdown(f'<p class="muted" style="font-size:.95rem;color:#C3D0E4">{x}</p>', unsafe_allow_html=True)

# ---- two groups to act on ---------------------------------------------------------------------
st.subheader(L("Dos grupos, dos soluciones", "Two groups, two solutions"))
g1, g2 = st.columns([3, 2], gap="large")
with g1:
    sg = seg.reset_index().assign(
        name=lambda x: x.segment.map({"outside": L("Fuera del sistema formal", "Outside the formal system"),
                                      "nearby": L("Agua cerca que no llega", "Water nearby, not reaching homes"),
                                      "connected": L("Mayormente conectadas", "Mostly connected")}),
        pct=lambda x: 100 * x.share_nowater)
    sg["txt"] = sg.pct.map(lambda x: f"{x:.0f}%") + "  ·  " + sg.localities.astype(str) + L(" localidades", " localities")
    base = alt.Chart(sg).encode(y=alt.Y("name:N", sort=list(sg.name), title=None,
                                        axis=alt.Axis(labelLimit=260, labelFontSize=13, labelColor=ui.INK)))
    bars = base.mark_bar(cornerRadiusEnd=6, height=28).encode(
        x=alt.X("pct:Q", title=L("% de todas las viviendas sin agua entubada", "% of all homes without piped water"),
                scale=alt.Scale(domain=[0, 75])),
        color=alt.Color("segment:N", legend=None, scale=alt.Scale(domain=list(ui.SEG_COLOURS), range=list(ui.SEG_COLOURS.values()))),
        tooltip=[alt.Tooltip("name:N", title=""), alt.Tooltip("pct:Q", format=".1f", title="%"),
                 alt.Tooltip("localities:Q", title=L("localidades", "localities")), alt.Tooltip("people:Q", format=",", title=L("habitantes", "inhabitants"))])
    txt = base.mark_text(align="left", dx=8, fontSize=12, color=ui.MUTED).encode(x="pct:Q", text="txt:N")
    ui.chart(bars + txt, height=170)
with g2:
    o, nb = seg.loc["outside"], seg.loc["nearby"]
    st.markdown(ui.insight(L(
        f"<b>Fuera del sistema</b> ({int(o.localities)} localidades): casi no hay agua concedida cerca (mediana {o.median_vol_pc:.0f} m³ por "
        "habitante). Necesitan una fuente, una red y registrar su derecho de agua.<br><br>"
        f"<b>Agua cerca que no llega</b> ({int(nb.localities)} localidades): hay más agua concedida cerca que en la localidad típica "
        f"(mediana {nb.median_vol_pc:.0f} m³), pero no llega a las viviendas. Necesitan una conexión a un sistema existente.",
        f"<b>Outside the system</b> ({int(o.localities)} localities): almost no water is granted nearby (median {o.median_vol_pc:.0f} m³ per "
        "resident). They need a source, a network and a registered water right.<br><br>"
        f"<b>Water nearby, not reaching homes</b> ({int(nb.localities)} localities): more water is granted nearby than in the typical "
        f"locality (median {nb.median_vol_pc:.0f} m³), but it does not reach homes. They need a connection to an existing system."),
        L("Segmentación del modelo", "Model segmentation")), unsafe_allow_html=True)

# ---- who holds it ----------------------------------------------------------------------
st.subheader(L("¿Quién concentra el agua?", "Who holds the water?"))
ext["htype"] = ext.Titular.map(holders.holder_type)
ht = ext.groupby("htype").agg(vol=("vol", "sum"), titles=("vol", "size")).reset_index()
ht["share"] = ht.vol / ht.vol.sum()
ht["label"] = ht.htype.map(ui.holder_label)
ht["txt"] = ht.share.map(lambda x: f"{x:.0%}") + " (" + ht.titles.astype(str) + L(" títulos)", " titles)")
ht = ht.sort_values("vol", ascending=False)
col1, col2 = st.columns([3, 2], gap="large")
with col1:
    base = alt.Chart(ht).encode(y=alt.Y("label:N", sort=list(ht.label), title=None,
                                        axis=alt.Axis(labelLimit=260, labelFontSize=13, labelColor=ui.INK)))
    bars = base.mark_bar(cornerRadiusEnd=6, height=24, color=ui.WATER).encode(
        x=alt.X("vol:Q", title=L("Millones de m³ al año", "Million m³ per year"),
                scale=alt.Scale(domain=[0, float(ht.vol.max()) * 1.32]),
                axis=alt.Axis(labelExpr="datum.value / 1e6", grid=True)),
        tooltip=[alt.Tooltip("label:N", title=""), alt.Tooltip("vol:Q", format=",.0f", title="m³/año"),
                 alt.Tooltip("titles:Q", title=L("títulos", "titles"))])
    txt = base.mark_text(align="left", dx=8, fontSize=12, color=ui.MUTED).encode(x="vol:Q", text="txt:N")
    ui.chart((bars + txt), height=240)
with col2:
    st.markdown(
        '<p class="lead">' + L(
            f"Los sistemas municipales de agua tienen {ht.set_index('htype').share.get('utility', 0):.0%} del volumen. "
            "Unas pocas concesiones muy grandes, sobre todo las de Comitán y San Cristóbal, pesan más que cientos "
            "de concesiones pequeñas. La industria, incluida la embotelladora, tiene menos del 1%.",
            f"Municipal water systems hold {ht.set_index('htype').share.get('utility', 0):.0%} of the volume. "
            "A few very large titles, above all those of Comitán and San Cristóbal, outweigh hundreds of small ones. "
            "Industry, the bottling plant included, holds less than 1%.") + '</p>'
        f'<p class="muted">{L("Tipo de titular estimado a partir del nombre registrado en el REPDA.", "Holder type estimated from the name registered in REPDA.")}</p>',
        unsafe_allow_html=True)

# ---- explore ------------------------------------------------------------------------------
st.subheader(L("Explora", "Explore"))
EXPLORE = [
    ("app_pages/p7_ask.py", ":material/auto_awesome:", L("Pregunta", "Ask"),
     L("Pregunta en tus palabras; el asistente consulta los datos por ti.", "Ask in your own words; the assistant queries the data for you.")),
    ("app_pages/p2_map.py", ":material/map:", L("Mapa", "Map"),
     L("Abre la ficha de cualquier localidad: viviendas, agua concedida cerca, quién la tiene y localidades parecidas.",
       "Open the record of any locality: homes, water granted nearby, who holds it and similar localities.")),
    ("app_pages/p3_model.py", ":material/tune:", L("Modelo", "Model"),
     L("Vuelve a estimar el modelo de la tesis y mira dónde el modelo se equivoca más.",
       "Re-estimate the thesis model and see where it is most surprised.")),
    ("app_pages/p4_index.py", ":material/leaderboard:", L("Prioridades", "Priorities"),
     L("Decide qué pesa más y obtén una lista de dónde actuar primero, con su solidez.",
       "Decide what matters most and get a list of where to act first, with how solid it is.")),
    ("app_pages/p5_climate.py", ":material/rainy:", L("Sequía y lluvia", "Drought & rain"),
     L("Sigue la sequía oficial y la lluvia frente a lo normal, municipio por municipio.",
       "Follow the official drought and rain against normal, municipality by municipality.")),
    ("app_pages/p6_data.py", ":material/database:", L("Datos", "Data"),
     L("Fuentes, definiciones y la lista de títulos mal ubicados o sin ubicar en el registro.",
       "Sources, definitions and the list of misplaced or unlocated titles in the register.")),
]
cols = st.columns(3, gap="medium")
for i, (page, icon, title, text) in enumerate(EXPLORE):
    with cols[i % 3].container(key=f"explore_{i}"):
        st.page_link(page, label=title, icon=icon)
        st.markdown(f'<p class="muted" style="margin-top:-.3rem">{text}</p>', unsafe_allow_html=True)
