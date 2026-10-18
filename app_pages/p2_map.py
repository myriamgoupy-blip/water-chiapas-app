import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, engine, geo, index, insights, maps, ui
from core.config import MUNS

L = ui.L
pts, pkey = data.active_points()
loc = engine.table(pkey, pts)
drought, _ = data.drought()
latest = drought[drought.date == drought.date.max()].set_index("MUN").cat

k, _, _ = insights.current()
ui.page_title(L("Agua concedida y hogares sin agua", "Water granted and homes without water"),
              L("Compara, localidad por localidad, el agua que el Estado concede y las viviendas que no la reciben.",
                "Compare, locality by locality, the water the State grants and the homes that do not receive it."))
ui.guide([
    (L("Elige una localidad", "Pick a locality"), L("Escribe su nombre o tócala en el mapa.", "Type its name or tap it on the map.")),
    (L("Lee el mapa", "Read the map"), L("Columnas azules: agua concedida (altura = volumen). Círculos: localidades (color = lo que elijas). Anillo: el radio.",
                                         "Blue columns: water granted (height = volume). Circles: localities (colour = what you choose). Ring: the radius.")),
    (L("Lee la ficha", "Read the record"), L("Quién tiene el agua cerca, a qué grupo pertenece la localidad y qué localidades se le parecen.",
                                             "Who holds the water nearby, which group the locality belongs to and which localities are like it.")),
])

# ---------------------------------------------------------------- selection from a map click
ev = st.session_state.get("deckmap")
try:
    objs = ev["selection"]["objects"].get("localities", []) if ev else []
except (KeyError, TypeError, AttributeError):
    objs = []
if objs and (objs[0].get("MUN"), objs[0].get("LOC")) != st.session_state.get("_last_click"):
    o = objs[0]
    st.session_state["_last_click"] = (o.get("MUN"), o.get("LOC"))
    st.session_state["card_mun"] = int(o["MUN"])
    st.session_state[f"card_loc_{int(o['MUN'])}"] = int(o["LOC"])

# ---------------------------------------------------------------- controls
COLOUR = {
    "dep_water": (L("Viviendas sin agua entubada", "Homes without piped water"), "%"),
    "indig": (L("Hablantes de lengua indígena", "Indigenous-language speakers"), "%"),
    "priority": (L("Índice de prioridad", "Priority index"), ""),
    "intensity": (L("Intensidad de concesiones (2 km)", "Concession intensity (2 km)"), ""),
    "segment": (L("Grupo (modelo)", "Group (model)"), ""),
}
with st.container(key="panel_map"):
    c1, c2, c3 = st.columns([2, 3, 2])
    view = loc[loc.lon.notna()]
    mun_opts = sorted(view.MUN.unique(), key=ui.mun_name)
    st.session_state.setdefault("card_mun", 23)
    sel_mun = c1.selectbox(L("Municipio", "Municipality"), mun_opts, format_func=ui.mun_name, key="card_mun")
    opts = view[view.MUN == sel_mun].sort_values("POBTOT", ascending=False)
    names = dict(zip(opts.LOC, opts.NOM_LOC + L(" (", " (") + opts.POBTOT.map(ui.num) + L(" hab.)", " inhabitants)")))
    loc_key = f"card_loc_{sel_mun}"
    if st.session_state.get(loc_key) not in names:
        st.session_state[loc_key] = int(opts.LOC.iloc[0])
    sel_loc = c2.selectbox(L("Localidad (busca por nombre)", "Locality (type to search)"), list(names),
                           format_func=names.get, key=loc_key)
    radius = c3.slider(L("Radio (km)", "Radius (km)"), 0.5, 5.0, 2.0, 0.5,
                       help=L("Concesiones contadas alrededor de la localidad. La tesis usa 2 km.",
                              "Concessions counted around the locality. The thesis uses 2 km."))
    colour_by = st.pills(L("Colorear localidades por", "Colour localities by"), list(COLOUR), default="dep_water",
                         format_func=lambda k: COLOUR[k][0], required=True, key="map_colour")
    d2, d3, d4, _ = st.columns([1, 1.3, 1.8, 3])
    three_d = d2.toggle("3D", True)
    by_use = d3.toggle(L("Por uso", "By use"), False, disabled=pts is None)
    flagged = d4.toggle(L("Puntos descartados", "Rejected points"), False, disabled=pts is None,
                        help=L("Puntos cuya ubicación no pasó la revisión (municipio equivocado o a más de 10 km).",
                               "Points whose location failed the check (wrong municipality or over 10 km away)."))

row = loc[(loc.MUN == sel_mun) & (loc.LOC == sel_loc)].iloc[0]

# ---------------------------------------------------------------- map
if colour_by == "priority":
    base = loc.dropna(subset=["dep_water", "dep_drain", "school", "indig", "intensity"])
    loc["priority"] = index.score(index.components(base, index.drought_pressure(drought)), index.DEFAULT_WEIGHTS).reindex(loc.index)
loc["segment"] = k.segment.reindex(loc.index)
view = loc[loc.lon.notna()].copy()
label, unit = COLOUR[colour_by]
seg_rgb = None
if colour_by == "segment":
    hexrgb = {s_: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for s_, c in ui.SEG_COLOURS.items()}
    seg_rgb = np.array([hexrgb.get(s_, (40, 50, 70)) for s_ in view.segment.fillna("none")])
    view["segment_txt"] = view.segment.map({"outside": L("fuera del sistema", "outside the system"),
                                            "nearby": L("agua cerca que no llega", "water nearby, not reaching homes"),
                                            "connected": L("mayormente conectada", "mostly connected")}).fillna(L("fuera de la muestra", "not in the model sample"))
    vmin, vmax = 0, 1
else:
    vmin, vmax = (0, 100) if unit == "%" else (float(view[colour_by].min()), float(view[colour_by].max()))
view["t1"] = view.NOM_LOC
view["t2"] = view.MUN.map(ui.mun_name) + ", " + view.POBTOT.map(ui.num) + L(" hab.", " inhabitants")
if colour_by == "segment":
    view["t3"] = label + ": " + view.segment_txt
    layers = [maps.locality_layer(view, "dep_water", 0, 100, rgb=seg_rgb), maps.ring_layer(row.lon, row.lat, radius)]
else:
    view["t3"] = label + ": " + view[colour_by].map(lambda x: L("sin dato", "masked") if x != x else f"{x:,.0f}{unit}"
                                                    if unit else f"{x:,.1f}")
    layers = [maps.locality_layer(view, colour_by, vmin, vmax), maps.ring_layer(row.lon, row.lat, radius)]
placed = None
if pts is not None:
    placed = engine.point_arrays(pkey, pts)["placed"].copy()
    placed["t1"] = placed.TITULAR.fillna("").astype(str).str.title()
    placed["t2"] = placed.use.map(ui.use_label) + ", " + placed.source.map(
        {"subterranea": L("agua subterránea", "groundwater"), "superficial": L("agua superficial", "surface water")}).fillna("")
    placed["t3"] = placed.vol.map(lambda x: f"{x:,.0f} m³/" + L("año", "yr"))
    layers.append(maps.concession_layer(placed, by_use=by_use, radius_m=60 if radius <= 2 else 95, height=2.0))
    if flagged:
        bad = pts[(pts.flag != "ok") & pts.LONDEC.notna() & (pts.LONDEC != 0)].copy()
        bad["t1"] = bad.TITULAR.fillna("").astype(str).str.title()
        bad["t2"] = L("Ubicación descartada: ", "Location rejected: ") + bad.flag.str.replace("_", " ")
        bad["t3"] = ""
        import pydeck as pdk
        layers.append(pdk.Layer("ScatterplotLayer", id="flagged", data=bad[["LONDEC", "LATDEC", "t1", "t2", "t3"]],
                                get_position="[LONDEC, LATDEC]", get_fill_color=[212, 154, 30, 230], get_radius=160,
                                radius_min_pixels=4, stroked=True, get_line_color=[255, 255, 255], pickable=True))
zoom = 13.0 - np.log2(max(radius, 0.5))
deck = maps.deck(layers, float(row.lat), float(row.lon), float(zoom), pitch=50 if three_d else 0,
                 bearing=-15 if three_d else 0)
st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key="deckmap", height=560)
if colour_by == "segment":
    st.markdown('<div class="legend">' + "".join(
        f'<span><span class="dot" style="background:{ui.SEG_COLOURS[s_]}"></span> {t}</span>' for s_, t in [
            ("outside", L("Fuera del sistema formal", "Outside the formal system")),
            ("nearby", L("Agua cerca que no llega", "Water nearby, not reaching homes")),
            ("connected", L("Mayormente conectada", "Mostly connected"))]) + '</div>', unsafe_allow_html=True)
else:
    lo, hi = ("0%", "100%") if unit == "%" else (f"{vmin:.0f}", f"{vmax:.0f}")
    st.markdown(maps.legend(label, lo, hi, radius, by_use), unsafe_allow_html=True)
ui.explain(L("<b>Qué buscar:</b> círculos muy coloreados sin columnas cerca son localidades fuera del sistema formal; "
             "círculos coloreados rodeados de columnas altas son localidades con agua concedida cerca que no llega a las casas. "
             "El modo «Grupo (modelo)» los separa directamente.",
             "<b>What to look for:</b> strongly coloured circles with no columns nearby are localities outside the formal system; "
             "coloured circles surrounded by tall columns have water granted nearby that does not reach homes. "
             "The «Group (model)» colour separates them directly."))

# ---------------------------------------------------------------- the card
def pct(x):
    return L("sin dato", "masked") if x != x else f"{x:.0f}%"


near = geo.concessions_near(row.lon, row.lat, placed, radius) if placed is not None else None
vol_near = float(near.vol.sum()) if near is not None else np.nan
per_res = vol_near / row.POBTOT if row.POBTOT and vol_near == vol_near else np.nan
cat = latest.get(int(row.MUN), "None")

st.write("")
left, right = st.columns([5, 4], gap="large")
with left:
    st.markdown(f"## {row.NOM_LOC}")
    st.markdown(f"{MUNS[int(row.MUN)]}, {ui.num(row.ALTITUD)} m {L('de altitud', 'above sea level')} &nbsp; "
                f"{ui.dchip(cat, ui.dlabel(cat))}", unsafe_allow_html=True)
    # one-sentence reading of the card
    if row.dep_water != row.dep_water:
        s = L("INEGI no publica los datos de vivienda de esta localidad porque es muy pequeña.",
              "INEGI does not publish housing data for this locality because it is very small.")
    else:
        s = L(f"En {row.NOM_LOC}, {pct(row.dep_water)} de las viviendas no tiene agua entubada, ni dentro ni en el patio.",
              f"In {row.NOM_LOC}, {pct(row.dep_water)} of homes have no piped water, neither inside nor in the yard.")
    if near is not None:
        if near.empty:
            s += " " + L(f"No hay concesiones registradas a menos de {radius:g} km.",
                         f"There is no registered concession within {radius:g} km.")
        else:
            top = near.assign(TITULAR=near.TITULAR.fillna("").astype(str).str.strip()).groupby("TITULAR").vol.sum().sort_values(ascending=False)
            holder = str(top.index[0]).title()
            s += " " + L(
                f"A menos de {radius:g} km se concesionan {vol_near:,.0f} m³ de agua al año ({per_res:,.0f} m³ por "
                f"habitante)" + (f"; el mayor titular es {holder} ({top.iloc[0] / top.sum():.0%})." if holder else "."),
                f"Within {radius:g} km, {vol_near:,.0f} m³ of water a year are granted ({per_res:,.0f} m³ per "
                f"resident)" + (f"; the largest holder is {holder} ({top.iloc[0] / top.sum():.0%})." if holder else "."))
    st.markdown(f'<p class="sentence">{s}</p>', unsafe_allow_html=True)
    st.markdown(ui.facts([
        (L("Habitantes", "Inhabitants"), ui.num(row.POBTOT), ""),
        (L("Viviendas habitadas", "Inhabited homes"), ui.num(row.VIVPARH_CV), ""),
        (L("Sin agua entubada", "No piped water"), pct(row.dep_water), "homes"),
        (L("Sin drenaje", "No drainage"), pct(row.dep_drain), ""),
        (L("Hablan lengua indígena", "Speak an Indigenous language"), pct(row.indig), ""),
        (L("Años de escolaridad", "Years of schooling"), "–" if row.school != row.school else f"{row.school:.1f}", ""),
    ]), unsafe_allow_html=True)
    if row.name in k.index:
        kr = k.loc[row.name]
        st.markdown(ui.segtag(kr.segment) + "&nbsp; " + ui.chip(L(f"Prioridad n.º {int(kr.priority_rank)} de {len(k)}",
                                                                   f"Priority rank {int(kr.priority_rank)} of {len(k)}")),
                    unsafe_allow_html=True)
        gap = kr.dep_water - kr.predicted
        model_line = L(
            f"Con su agua concedida cerca, su tamaño y su escolaridad, el modelo esperaría {kr.predicted:.0f}% de viviendas sin agua; "
            f"tiene {kr.dep_water:.0f}% ({gap:+.0f} puntos). ",
            f"Given its water granted nearby, its size and its schooling, the model would expect {kr.predicted:.0f}% of homes without "
            f"water; it has {kr.dep_water:.0f}% ({gap:+.0f} points). ")
        st.markdown(ui.insight(model_line + insights.advice(kr.segment, L), L("Lectura del modelo", "Model reading")),
                    unsafe_allow_html=True)
    elif row.dep_water == row.dep_water:
        st.markdown('<p class="muted">' + L("Esta localidad no está en la muestra del modelo (100 habitantes o menos).",
                                            "This locality is not in the model sample (100 inhabitants or fewer).") + '</p>',
                    unsafe_allow_html=True)

with right:
    st.markdown(f"#### {L('Agua concesionada a menos de', 'Water granted within')} {radius:g} km")
    if near is None:
        st.info(L("Los puntos de concesión no están cargados. Ve a la página Datos para cargarlos.",
                  "Concession points are not loaded. Go to the Data page to load them."))
    elif near.empty:
        st.markdown(f'<div class="big water">0 m³</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="big water">{vol_near:,.0f} m³</div><p class="muted">'
                    + L(f"al año, en {len(near)} puntos de {near.key.nunique()} títulos",
                        f"per year, at {len(near)} points of {near.key.nunique()} titles") + '</p>',
                    unsafe_allow_html=True)
        by_holder = near.groupby("TITULAR").agg(vol=("vol", "sum"), dist=("dist_km", "min")).reset_index()
        by_holder["name"] = by_holder.TITULAR.astype(str).str.title().str.slice(0, 38)
        by_holder = by_holder.sort_values("vol", ascending=False).head(8)
        ch = alt.Chart(by_holder).mark_bar(cornerRadiusEnd=5, height=18, color=ui.WATER).encode(
            y=alt.Y("name:N", sort=list(by_holder.name), title=None, axis=alt.Axis(labelLimit=230)),
            x=alt.X("vol:Q", title="m³/" + L("año", "yr"), axis=alt.Axis(format="~s")),
            tooltip=[alt.Tooltip("TITULAR:N", title=""), alt.Tooltip("vol:Q", format=",.0f", title="m³"),
                     alt.Tooltip("dist:Q", format=".2f", title="km")])
        ui.chart(ch, height=max(120, 30 * len(by_holder)))

if near is not None and not near.empty:
    with st.expander(L(f"Todas las concesiones a menos de {radius:g} km", f"All concessions within {radius:g} km")):
        rep = data.repda()
        titles = rep.dropna(subset=["key"]).drop_duplicates("key").set_index("key")
        st.dataframe(pd.DataFrame({
            L("Titular", "Holder"): near.TITULAR.astype(str).str.title(),
            L("Uso", "Use"): near.use.map(ui.use_label),
            L("Volumen (m³/año)", "Volume (m³/yr)"): near.vol.round(0),
            L("Distancia (km)", "Distance (km)"): near.dist_km.round(2),
            L("Fuente", "Source"): near.source.map({"subterranea": L("subterránea", "groundwater"),
                                                     "superficial": L("superficial", "surface")}),
            L("Título REPDA", "REPDA title"): near.key.map(titles["Título"]),
            L("Registro", "Registered"): near.key.map(titles["Fecha de registro"]),
        }), hide_index=True, column_config={L("Volumen (m³/año)", "Volume (m³/yr)"): st.column_config.NumberColumn(format="%d")})

# ---------------------------------------------------------------- similar localities (k-nearest neighbours)
if row.name in k.index:
    st.markdown(f"#### {L('Localidades parecidas', 'Similar localities')}")
    pr = insights.peers(k, row.name, n=6)
    better = int((pr.dep_water < 50).sum())
    st.markdown('<p class="muted">' + L(
        "Las seis localidades más parecidas por tamaño, escolaridad, lengua, agua concedida cerca y altitud (vecinos más cercanos, "
        "sin usar el acceso al agua). Sirven para comparar: si localidades parecidas tienen agua entubada, vale la pena ver cómo lo lograron.",
        "The six localities most like this one in size, schooling, language, water granted nearby and altitude (nearest neighbours, "
        "without using water access). Use them to compare: if similar localities have piped water, it is worth seeing how they got it.")
        + '</p>', unsafe_allow_html=True)
    seg_txt = {"outside": L("Fuera del sistema", "Outside the system"), "nearby": L("Agua cerca que no llega", "Water nearby, not reaching"),
               "connected": L("Mayormente conectada", "Mostly connected")}
    st.dataframe(pd.DataFrame({
        L("Localidad", "Locality"): pr.NOM_LOC, L("Municipio", "Municipality"): pr.MUN.map(ui.mun_short),
        L("Habitantes", "Inhabitants"): pr.POBTOT.astype(int), L("Sin agua entubada", "No piped water"): pr.dep_water,
        L("Agua a 2 km (m³/hab.)", "Water within 2 km (m³/resident)"): pr.vol_pc.round(0),
        L("Grupo", "Group"): pr.segment.map(seg_txt), L("Similitud", "Similarity"): pr.similarity}),
        hide_index=True, column_config={
            L("Sin agua entubada", "No piped water"): st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
            L("Similitud", "Similarity"): st.column_config.NumberColumn(format="%d%%"),
            L("Agua a 2 km (m³/hab.)", "Water within 2 km (m³/resident)"): st.column_config.NumberColumn(format="localized")})
    if row.dep_water >= 50 and better:
        st.markdown(ui.insight(L(f"{better} de las 6 localidades parecidas tienen agua entubada en la mayoría de sus viviendas. "
                                 "Son buenos casos para comparar qué hicieron distinto.",
                                 f"{better} of the 6 similar localities have piped water in most of their homes. "
                                 "They are good cases to compare what they did differently."), L("Comparación", "Comparison")),
                    unsafe_allow_html=True)

st.caption(L("Puntos de concesión: ", "Concession points: ") + ui.source_label(pkey) + ".")
