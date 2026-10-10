"""When Water Flows to the Few — interactive companion to the thesis.

Run locally with:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="When Water Flows to the Few", page_icon="💧", layout="wide")

pages = [
    st.Page("app_pages/p1_overview.py", title="Overview", icon=":material/water_drop:", default=True),
    st.Page("app_pages/p2_map.py", url_path="map", title="Map and locality card", icon=":material/map:"),
    st.Page("app_pages/p3_model.py", url_path="model", title="Model playground", icon=":material/tune:"),
    st.Page("app_pages/p4_index.py", url_path="index", title="Priority index", icon=":material/leaderboard:"),
    st.Page("app_pages/p5_climate.py", url_path="climate", title="Drought and rain (live)", icon=":material/rainy:"),
    st.Page("app_pages/p6_data.py", url_path="data", title="Data, methods and refresh", icon=":material/database:"),
]
st.navigation(pages).run()
