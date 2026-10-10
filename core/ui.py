"""Small shared interface helpers."""
import streamlit as st

from . import data
from .config import MUNS, SNAPSHOTS

CSS = """
<style>
  .block-container {padding-top: 3.2rem; max-width: 1200px;}
  h1, h2, h3 {font-family: Georgia, 'Times New Roman', serif; letter-spacing: -0.01em;}
  .kicker {color:#52514e; font-size:0.85rem; text-transform:uppercase; letter-spacing:.06em; margin-bottom:-.4rem;}
  .note {color:#52514e; font-size:0.88rem;}
  .card {border:1px solid #e4e3de; border-radius:10px; padding:0.9rem 1.1rem; background:#fbfaf7;}
  .pill {display:inline-block; padding:.1rem .55rem; border-radius:999px; font-size:.8rem; font-weight:600;}
  div[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
"""


def header(kicker, title, intro=None):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="kicker">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    if intro:
        st.markdown(intro)


def sidebar_status():
    pts, label = data.active_points()
    with st.sidebar:
        st.markdown("**Data in use**")
        st.caption(f"Concession points: {label}")
        st.caption(f"Water rights register: {SNAPSHOTS['REPDA']}")
        st.caption(f"Households: {SNAPSHOTS['ITER']}")
        st.caption("Thesis: *When Water Flows to the Few* (ESCP MSc, 2026)")
    return pts, label


def pill(text, bg, fg="#0b0b0b"):
    return f'<span class="pill" style="background:{bg};color:{fg}">{text}</span>'


def facts(items, per_row=3):
    """Label-over-value blocks in a grid (labels wrap instead of being cut off like narrow metrics)."""
    cells = "".join(f'<div><div style="color:#52514e;font-size:.8rem;line-height:1.2">{k}</div>'
                    f'<div style="font-size:1.25rem;font-weight:600;margin-bottom:.5rem">{v}</div></div>'
                    for k, v in items)
    return (f'<div style="display:grid;grid-template-columns:repeat({per_row},1fr);gap:.1rem 1rem;'
            f'margin:.4rem 0 .8rem 0">{cells}</div>')


def fmt_int(x):
    return f"{x:,.0f}" if x == x else "–"


def mun_name(m):
    return MUNS.get(int(m), str(m))
