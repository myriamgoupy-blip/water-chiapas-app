import pandas as pd
import streamlit as st

from core import data, engine, fastols, geo, ui
from core.config import MUNS

L = ui.L
ui.page_title(L("Los datos detrás de la app", "The data behind the app"),
              L("De dónde sale cada cifra, cómo se construyen las variables y qué registros conviene revisar.",
                "Where every number comes from, how the variables are built, and which register entries need review."),
              kicker=L("Transparencia", "Transparency"))

drought, dkey = data.drought()
pts, pkey = data.active_points()
normals = data.rain_normals()

# ================================================================ sources
st.subheader(L("Fuentes", "Sources"))
rows = [
    (L("REPDA, Registro Público de Derechos de Agua (CONAGUA)", "REPDA, Public Register of Water Rights (CONAGUA)"),
     L("Cada título: titular, uso, volumen, fecha", "Every title: holder, use, volume, date"),
     L("Consulta de septiembre de 2026", "September 2026 extract")),
    (L("LOCREPDA, REPDA georreferenciado (CONAGUA)", "LOCREPDA, geolocated REPDA (CONAGUA)"),
     L("Ubicación de pozos y tomas", "Location of wells and intakes"), ui.source_label(pkey)),
    (L("Censo 2020, ITER (INEGI)", "2020 Census, ITER (INEGI)"),
     L("Agua, drenaje, lengua indígena y escolaridad por localidad", "Water, drainage, language and schooling by locality"),
     L("Chiapas, 9 municipios", "Chiapas, 9 municipalities")),
    (L("Monitor de Sequía (CONAGUA–SMN)", "Drought Monitor (CONAGUA–SMN)"),
     L("Categoría de sequía por municipio cada 15 días desde 2003", "Drought category per municipality every 15 days since 2003"),
     ui.drought_source(dkey, drought.date.max())),
    ("Open-Meteo (ERA5)", L("Lluvia diaria, humedad del suelo, pronóstico", "Daily rain, soil moisture, forecast"),
     L("En vivo; promedios 1991–2020 ", "Live; 1991–2020 averages ") + (L("listos", "ready") if normals is not None else L("pendientes", "pending"))),
]
st.markdown(f"| {L('Fuente', 'Source')} | {L('Qué aporta', 'What it provides')} | {L('Versión en uso', 'Version in use')} |\n|---|---|---|\n"
            + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows))

# ================================================================ concession points in use
st.subheader(L("Puntos de concesión en uso", "Concession points in use"))
st.markdown(L("La app lee LOCREPDA en el servidor de CONAGUA cada día y aplica la misma revisión de ubicaciones que la tesis. "
              "Si el servidor no responde, usa la copia incluida (28 de septiembre de 2026).",
              "The app reads LOCREPDA from CONAGUA's server every day and applies the same location check as the thesis. "
              "If the server does not answer, it uses the bundled copy (28 September 2026)."))
st.caption(L("Fuente actual: ", "Current source: ") + ui.source_label(pkey) + ".")
pts, pkey = data.active_points()
if pts is not None:
    rep = data.repda()
    ext = rep[rep.vol > 0]
    placed = engine.point_arrays(pkey, pts)["placed"]
    located = ext.key.isin(set(pts[pts.flag == "ok"].key))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(L("Puntos", "Points"), f"{len(pts):,}")
    k2.metric(L("Ubicación válida", "Valid location"), f"{(pts.flag == 'ok').mean():.0%}")
    k3.metric(L("Títulos ubicados", "Titles located"), f"{located.sum()} / {len(ext)}")
    k4.metric(L("Volumen ubicado", "Volume located"), f"{placed.vol.sum() / ext.vol.sum():.0%}")

# ================================================================ titles to review
if pts is not None:
    st.subheader(L("Títulos por revisar", "Titles to review"))
    st.markdown(L("Dos listas para quien revisa el registro: los puntos que LOCREPDA ubica donde no pueden estar, "
                  "y los títulos con volumen en el REPDA que LOCREPDA no ubica en ningún punto.",
                  "Two lists for anyone reviewing the register: points that LOCREPDA places where they cannot be, "
                  "and titles with a volume in REPDA that LOCREPDA does not place anywhere."))
    bad = pts[pts.flag != "ok"].copy()
    bad = pd.DataFrame({
        L("Título", "Title"): bad.FOLIOREG, L("Titular", "Holder"): bad.TITULAR.astype(str).str.title(),
        L("Municipio registrado", "Registered municipality"): bad.MUPIO.map(MUNS), L("Uso", "Use"): bad.use,
        L("Volumen LOCREPDA (m³/año)", "LOCREPDA volume (m³/yr)"): bad.VOL_CONS.round(0),
        L("Longitud", "Longitude"): bad.LONDEC.round(3), L("Latitud", "Latitude"): bad.LATDEC.round(3),
        L("Distancia a su municipio (km)", "Distance to its municipality (km)"): bad.get("own_km", pd.Series(dtype=float)).round(1),
    }).sort_values(L("Distancia a su municipio (km)", "Distance to its municipality (km)"), ascending=False)
    miss = ext[~located]
    miss = pd.DataFrame({
        L("Título", "Title"): miss["Título"], L("Titular", "Holder"): miss.Titular.astype(str).str.strip().str.title(),
        L("Municipio", "Municipality"): miss.municipality, L("Uso", "Use"): miss.use,
        L("Volumen REPDA (m³/año)", "REPDA volume (m³/yr)"): miss.vol.round(0), L("Año de registro", "Year registered"): miss.year,
    }).sort_values(L("Volumen REPDA (m³/año)", "REPDA volume (m³/yr)"), ascending=False)
    t1, t2 = st.tabs([L(f"Mal ubicados ({len(bad)})", f"Misplaced ({len(bad)})"),
                      L(f"Sin ubicar ({len(miss)})", f"Not located ({len(miss)})")])
    with t1:
        st.dataframe(bad, hide_index=True, height=320,
                     column_config={L("Volumen LOCREPDA (m³/año)", "LOCREPDA volume (m³/yr)"): st.column_config.NumberColumn(format="localized")})
    with t2:
        st.caption(L(f"{len(miss)} títulos suman {miss.iloc[:, 4].sum() / ext.vol.sum():.0%} del volumen concesionado.",
                     f"{len(miss)} titles add up to {miss.iloc[:, 4].sum() / ext.vol.sum():.0%} of the concessioned volume."))
        st.dataframe(miss, hide_index=True, height=320,
                     column_config={L("Volumen REPDA (m³/año)", "REPDA volume (m³/yr)"): st.column_config.NumberColumn(format="localized"),
                                    L("Año de registro", "Year registered"): st.column_config.NumberColumn(format="%d")})
    both = pd.concat([bad.assign(**{L("Problema", "Issue"): L("Ubicación imposible", "Impossible location")}),
                      miss.assign(**{L("Problema", "Issue"): L("Sin ubicar en LOCREPDA", "Not located in LOCREPDA")})], ignore_index=True)
    st.download_button(L("Descargar los títulos por revisar (CSV)", "Download the titles to review (CSV)"),
                       both.to_csv(index=False), "titles_to_review.csv", "text/csv", icon=":material/download:")

# ================================================================ methods
st.subheader(L("Cómo se construyen las variables", "How the variables are built"))
st.markdown(L("""
- **Viviendas sin agua**: % de viviendas particulares habitadas que no disponen de agua entubada en el ámbito de la vivienda, es decir, ni dentro ni en el patio (1 − VPH_AGUADV / VIVPARH_CV, censo 2020).
- **Lengua indígena**: % de personas de 3 años y más que hablan una lengua indígena (P3YM_HLI / P_3YMAS).
- **Intensidad de concesiones**: cada título del REPDA se une a sus puntos de LOCREPDA por el número que sigue a "CHS". Su volumen se reparte entre sus puntos y se suma el de todos los puntos dentro del radio, por habitante, en escala log(1 + m³).
- **Modelo**: mínimos cuadrados con efectos fijos por municipio, controlando por población (log) y escolaridad. Tres pruebas: errores robustos (HC1), errores espaciales de Conley y bootstrap restringido por municipio (pesos de Webb).
- **Índice de prioridad**: promedio ponderado de componentes entre 0 y 1, con pesos elegidos por quien usa la app.
""", """
- **Homes without water**: % of private inhabited homes with no piped water at home, neither inside nor in the yard (1 − VPH_AGUADV / VIVPARH_CV, 2020 census).
- **Indigenous share**: % of people aged 3 and over who speak an Indigenous language (P3YM_HLI / P_3YMAS).
- **Concession intensity**: each REPDA title is matched to its LOCREPDA points on the number after "CHS". Its volume is split across its points; the volume of all points within the radius is summed, per resident, on a log(1 + m³) scale.
- **Model**: least squares with municipality fixed effects, controlling for log population and schooling. Three tests: robust errors (HC1), Conley spatial errors, and a restricted wild cluster bootstrap by municipality (Webb weights).
- **Priority index**: a weighted average of 0–1 components, with weights chosen by the user.
"""))
st.subheader(L("Límites", "Limits"))
st.markdown(L("""
- El censo es de 2020; las concesiones y la sequía son más recientes.
- El ITER no separa el agua dentro de la vivienda del agua en el patio: solo dice si hay agua entubada en la vivienda o el terreno.
- INEGI no publica los datos de las localidades muy pequeñas: 133 de 985 no se pueden analizar.
- Algunas coordenadas de LOCREPDA están mal por kilómetros; esos puntos se descartan, no se mueven.
- Una concesión es un derecho a extraer, no una medición de lo extraído ni de dónde se entrega.
- Los resultados son asociaciones: muchas concesiones son los propios sistemas de agua de las localidades vecinas.
""", """
- The census dates from 2020; concessions and drought are more recent.
- ITER does not separate water inside the home from water in the yard: it only says whether there is piped water on the premises.
- INEGI does not publish data for very small localities: 133 of 985 cannot be analysed.
- Some LOCREPDA coordinates are wrong by kilometres; those points are set aside, not moved.
- A concession is a right to extract, not a measure of what is extracted or where it is delivered.
- Results are associations: many concessions are the water systems of the neighbouring localities themselves.
"""))

loc = engine.table(pkey, pts)
keep = ["MUN", "municipality", "LOC", "NOM_LOC", "lon", "lat", "ALTITUD", "POBTOT", "dep_water",
        "dep_drain", "indig", "school", "intensity", "intensity_2km_thesis"]
st.download_button(L("Descargar las 985 localidades (CSV)", "Download all 985 localities (CSV)"),
                   loc[keep].to_csv(index=False), "localities_app.csv", "text/csv", icon=":material/download:")
