"""Ojo de Agua: interactive companion to the MSc thesis "When Water Flows to the Few".

Run locally with:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Ojo de Agua · Chiapas", page_icon=":material/water_drop:", layout="wide")

from core import ui  # noqa: E402  (after set_page_config)
from core.config import DEFAULT_LANG  # noqa: E402

# Keep the language across a theme switch (the page reloads with ?lang=..)
if "lang_choice" not in st.session_state and st.query_params.get("lang") in ("ES", "EN"):
    st.session_state["lang_choice"] = st.query_params.get("lang")

ui.inject_css()
L = ui.L

pages = [
    st.Page("app_pages/p1_overview.py", title=L("Inicio", "Home"), icon=":material/water_drop:", default=True),
    st.Page("app_pages/p7_ask.py", url_path="ask", title=L("Pregunta", "Ask"), icon=":material/auto_awesome:"),
    st.Page("app_pages/p2_map.py", url_path="map", title=L("Mapa", "Map"), icon=":material/map:"),
    st.Page("app_pages/p3_model.py", url_path="model", title=L("Modelo", "Model"), icon=":material/tune:"),
    st.Page("app_pages/p4_index.py", url_path="index", title=L("Prioridades", "Priorities"), icon=":material/leaderboard:"),
    st.Page("app_pages/p5_climate.py", url_path="climate", title=L("Sequía y lluvia", "Drought & rain"), icon=":material/rainy:"),
    st.Page("app_pages/p6_data.py", url_path="data", title=L("Datos", "Data"), icon=":material/database:"),
]
nav = st.navigation(pages, position="top")

with st.container(key="brandbar", horizontal=True, vertical_alignment="center"):
    st.markdown(
        '<div class="brand"><svg width="28" height="28" viewBox="0 0 26 26" aria-hidden="true"><defs>'
        '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2E86DE"/>'
        '<stop offset="1" stop-color="#8B5CF6"/></linearGradient></defs>'
        '<path d="M13 2 C13 2 4 12 4 17 a9 9 0 0 0 18 0 C22 12 13 2 13 2z" fill="url(#g)"/>'
        '<circle cx="13" cy="17" r="3.2" fill="#fff"/><circle cx="13" cy="17" r="1.5" fill="#E0457B"/></svg>'
        f'Ojo de Agua<small>{L("Agua y concesiones en Chiapas", "Water and concessions in Chiapas")}</small></div>',
        unsafe_allow_html=True)
    lang_kw = {} if "lang_choice" in st.session_state else {"default": DEFAULT_LANG}
    st.segmented_control("Idioma / Language", ["ES", "EN"], required=True,
                         key="lang_choice", label_visibility="collapsed", width="content", **lang_kw)
    dark = ui.theme_type() == "dark"
    if st.button(L("Modo claro", "Light mode") if dark else L("Modo oscuro", "Dark mode"),
                 icon=":material/light_mode:" if dark else ":material/dark_mode:",
                 key="theme_btn", type="tertiary"):
        ui.switch_theme("Light" if dark else "Dark")

if ui.theme_file_missing():
    st.warning(L("Falta el archivo de temas .streamlit/config.toml en el repositorio de GitHub: la app no puede "
                 "mostrar sus modos claro y oscuro. Súbelo (ver README).",
                 "The theme file .streamlit/config.toml is missing from the GitHub repository, so the app cannot "
                 "show its light and dark modes. Upload it (see README)."), icon=":material/warning:")

nav.run()

st.markdown(
    '<div class="footer">' + L(
        "Fuentes: CONAGUA (REPDA, LOCREPDA y Monitor de Sequía), INEGI (Censo 2020), Open-Meteo (ERA5). "
        "Herramienta de la tesis de maestría <i>When Water Flows to the Few</i>, ESCP Business School, 2026. "
        "Los resultados del modelo son asociaciones, no efectos causales. Modo claro u oscuro: botón junto a ES / EN.",
        "Sources: CONAGUA (REPDA, LOCREPDA and Drought Monitor), INEGI (2020 Census), Open-Meteo (ERA5). "
        "Tool from the MSc thesis <i>When Water Flows to the Few</i>, ESCP Business School, 2026. "
        "Model results are associations, not causal effects. Light or dark mode: button next to ES / EN.") + '</div>',
    unsafe_allow_html=True)
