import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, engine, holders, maps, ui
from core.config import THESIS

L = ui.L
pts, pkey = data.active_points()
rep = data.repda()
ext = rep[rep.vol > 0].copy()
loc = engine.table(pkey, pts)
drought, dkey = data.drought()

# ---- numbers ---------------------------------------------------------------------
v = np.sort(ext.vol.values)
n = len(v)
top10 = v[int(np.floor(0.9 * n)):].sum() / v.sum()
has = loc.dropna(subset=["VPH_AGUADV", "VIVPARH_CV"])
share_no_water = 1 - has.VPH_AGUADV.sum() / has.VIVPARH_CV.sum()
last = drought.date.max()
latest = drought[drought.date == last].set_index("MUN").cat
n_drought = int(latest.isin(["D1", "D2", "D3", "D4"]).sum())

# ---- hero ----------------------------------------------------------------------------
with st.container(key="hero"):
    left, right = st.columns([5, 6], gap="large", vertical_alignment="center")
    with left:
        st.markdown(f"# {L('¿Quién tiene el agua?', 'Who holds the water?')}")
        st.markdown(
            '<p class="hero-sub">' + L(
                f"Alrededor de San Cristóbal de las Casas, CONAGUA ha otorgado {n:,} títulos que suman "
                f"{ext.vol.sum() / 1e6:,.0f} millones de m³ de agua al año. Aun así, en la localidad promedio "
                f"una de cada cuatro viviendas no tiene agua entubada dentro.",
                f"Around San Cristóbal de las Casas, CONAGUA has granted {n:,} water titles adding up to "
                f"{ext.vol.sum() / 1e6:,.0f} million m³ a year. Yet in the average locality one home in four "
                f"has no piped water inside.") + '</p>', unsafe_allow_html=True)
        st.markdown(
            f"<p style='margin:.9rem 0 .35rem 0;font-weight:600'>"
            + L(f"Sequía hoy: {n_drought} de 9 municipios", f"Drought today: {n_drought} of 9 municipalities")
            + f" <span style='font-weight:400;color:#B9C6D8'>({last:%d/%m/%Y})</span></p>"
            + " ".join(ui.dchip(latest.get(m, "None"), f"{ui.mun_short(m)} {latest.get(m, 'None').replace('None', '–')}")
                       for m in sorted(latest.index, key=ui.mun_short)),
            unsafe_allow_html=True)
        st.markdown("<p style='color:#B9C6D8;font-size:.85rem;margin-top:.4rem'>"
                    + L("D0: anormalmente seco. D1: sequía moderada. D2: sequía severa.", "D0: abnormally dry. D1: moderate drought. D2: severe drought.")
                    + "</p>", unsafe_allow_html=True)
    with right:
        view = loc[loc.lon.notna()].copy()
        view["t1"] = view.NOM_LOC
        view["t2"] = view.MUN.map(ui.mun_name)
        view["t3"] = L("Sin agua entubada dentro: ", "No piped water inside: ") + view.dep_water.map(
            lambda x: "–" if x != x else f"{x:.0f}%")
        layers = [maps.locality_layer(view, "dep_water", 0, 100, pickable=True, opacity=235)]
        if pts is not None:
            placed = engine.point_arrays(pkey, pts)["placed"].copy()
            placed["t1"] = placed.TITULAR.fillna("").astype(str).str.title()
            placed["t2"] = placed.use.map(ui.use_label)
            placed["t3"] = placed.vol.map(lambda x: f"{x:,.0f} m³/año" if ui.lang() == "ES" else f"{x:,.0f} m³/yr")
            layers.append(maps.concession_layer(placed, radius_m=230, height=2.2))
        st.pydeck_chart(maps.deck(layers, 16.52, -92.45, 8.9, pitch=50, bearing=-18, dark=True), height=430)

# ---- three numbers -------------------------------------------------------------------
st.write("")
a, b, c = st.columns(3, gap="large")
a.markdown(f'<div class="big water">{ext.vol.sum() / 1e6:,.1f} M m³</div>'
           f'<p class="muted">{L("de agua concesionada al año en los 9 municipios", "of water granted per year in the 9 municipalities")}</p>',
           unsafe_allow_html=True)
b.markdown(f'<div class="big">{top10:.0%}</div>'
           f'<p class="muted">{L("del volumen está en el 10% de los títulos más grandes", "of the volume sits in the largest 10% of titles")}</p>',
           unsafe_allow_html=True)
c.markdown(f'<div class="big homes">{share_no_water:.0%}</div>'
           f'<p class="muted">{L("de todas las viviendas no tiene agua entubada dentro (27% en la localidad promedio)", "of all homes have no piped water inside (27% in the average locality)")}</p>',
           unsafe_allow_html=True)

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
    bars = base.mark_bar(cornerRadiusEnd=6, height=26, color=ui.WATER).encode(
        x=alt.X("vol:Q", title=L("Millones de m³ al año", "Million m³ per year"),
                scale=alt.Scale(domain=[0, float(ht.vol.max()) * 1.32]),
                axis=alt.Axis(labelExpr="datum.value / 1e6", grid=True)),
        tooltip=[alt.Tooltip("label:N", title=""), alt.Tooltip("vol:Q", format=",.0f", title="m³/año"),
                 alt.Tooltip("titles:Q", title=L("títulos", "titles"))])
    txt = base.mark_text(align="left", dx=8, fontSize=12, color=ui.MUTED).encode(x="vol:Q", text="txt:N")
    ui.chart((bars + txt), height=250)
with col2:
    st.markdown(
        '<p class="lead">' + L(
            f"Los sistemas municipales de agua tienen {ht.set_index('htype').share.get('utility', 0):.0%} del volumen. "
            "Unas pocas concesiones muy grandes, sobre todo las de Comitán y San Cristóbal, pesan más que cientos "
            "de concesiones pequeñas de comités comunitarios.",
            f"Municipal water systems hold {ht.set_index('htype').share.get('utility', 0):.0%} of the volume. "
            "A few very large titles, above all those of Comitán and San Cristóbal, outweigh hundreds of small "
            "community-committee titles.") + '</p>'
        f'<p class="muted">{L("Tipo de titular estimado a partir del nombre registrado en el REPDA.", "Holder type estimated from the name registered in REPDA.")}</p>',
        unsafe_allow_html=True)

# ---- what the thesis finds ------------------------------------------------------------
st.subheader(L("Lo que encontramos", "What we found"))
f1, f2, f3 = st.columns(3, gap="large")
f1.markdown("**" + L("Más agua concesionada cerca, menos viviendas sin agua", "More water granted nearby, fewer homes without water") + "**  \n" + L(
    f"En {THESIS['n']} localidades, pasar de poca a mucha agua concesionada a menos de 2 km se asocia con unos "
    "8 puntos porcentuales menos de viviendas sin agua entubada (promedio: 27%).",
    f"Across {THESIS['n']} localities, going from little to much water granted within 2 km goes with about "
    "8 percentage points fewer homes without piped water (average: 27%)."))
f2.markdown("**" + L("Constante, pero moderado", "Consistent, but moderate") + "**  \n" + L(
    "El signo se mantiene en todas las variantes. Su solidez estadística depende de cómo se trate la cercanía "
    "entre localidades y el número pequeño de municipios.",
    "The sign holds in every variant. How strong it is statistically depends on how closeness between "
    "localities and the small number of municipalities are handled."))
f3.markdown("**" + L("Igual en localidades indígenas", "The same in Indigenous localities") + "**  \n" + L(
    "La relación no cambia con la proporción de hablantes de lengua indígena. Desaparece si el agua entubada "
    "hasta el patio cuenta como acceso.",
    "The relationship does not change with the share of Indigenous-language speakers. It disappears if water "
    "piped to the yard counts as access."))
st.markdown('<p class="muted" style="margin-top:.6rem">' + L(
    "Es una asociación, no una causa: muchas concesiones son el registro legal de los propios sistemas de agua de las localidades.",
    "This is an association, not a cause: many concessions are the legal registration of the localities' own water systems.")
    + '</p>', unsafe_allow_html=True)

st.write("")
p1, p2, p3 = st.columns(3)
p1.page_link("app_pages/p2_map.py", label=L("Busca tu localidad en el mapa", "Find your locality on the map"), icon=":material/map:")
p2.page_link("app_pages/p3_model.py", label=L("Pon a prueba el modelo", "Put the model to the test"), icon=":material/tune:")
p3.page_link("app_pages/p4_index.py", label=L("Decide dónde actuar primero", "Decide where to act first"), icon=":material/leaderboard:")
