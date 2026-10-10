"""Look and language of the app: Spanish first, English on request.

Colour code used everywhere (the app's identity):
  blue  = water granted by concession     magenta = homes without piped water
"""
import altair as alt
import numpy as np
import streamlit as st

from .config import DROUGHT_COLOURS, DROUGHT_LABELS, DROUGHT_LABELS_ES, MUN_SHORT, MUNS

# ---------------------------------------------------------------- palette
NIGHT = "#1B2448"      # hero, headings
INK = "#1E2433"        # body text
MUTED = "#5A6378"      # secondary text, axes
LINE = "#DCE3EB"       # gridlines, borders
MIST = "#F2F5F8"       # app background
PANEL = "#E7EDF3"      # control panels
WATER = "#1f6fb2"      # water granted
WATER_SOFT = "#8DBBE3"
HOMES = "#C2185B"      # homes without water
PINE = "#2f8f5b"
MAIZE = "#d49a1e"
HOMES_RAMP = [(0.0, (247, 228, 237)), (0.35, (229, 139, 176)), (0.7, (194, 24, 91)), (1.0, (110, 11, 51))]
WATER_RGB = (31, 111, 178)

MAP_LIGHT = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
MAP_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


# ---------------------------------------------------------------- language
def lang():
    return st.session_state.get("lang_choice") or "ES"


def L(es, en):
    """Pick the text for the current language."""
    return en if lang() == "EN" else es


def num(x, d=0):
    if x != x:
        return "–"
    return f"{x:,.{d}f}"


def mun_name(m):
    return MUNS.get(int(m), str(m))


def mun_short(m):
    return MUN_SHORT.get(int(m), str(m))


def dlabel(cat):
    return L(DROUGHT_LABELS_ES.get(cat, cat), DROUGHT_LABELS.get(cat, cat))


def dchip(cat, text=None):
    fg = "#fff" if cat in ("D2", "D3", "D4") else INK
    return chip(text or (cat if cat != "None" else L("Sin sequía", "None")), DROUGHT_COLOURS.get(cat, "#DCE3EB"), fg)


def source_label(key):
    if key == "thesis":
        return L("instantánea de la tesis (28 sep 2026)", "thesis snapshot (28 Sep 2026)")
    if key.startswith("live:"):
        return L(f"consulta en vivo a CONAGUA ({key[5:]})", f"live pull from CONAGUA ({key[5:]})")
    if key.startswith("upload:"):
        return L(f"archivo cargado ({key[7:]})", f"uploaded file ({key[7:]})")
    return L("sin puntos de concesión cargados", "no concession points loaded")


def drought_source(key, last):
    d = last.strftime("%d/%m/%Y")
    return {
        "official": L(f"Monitor de Sequía de CONAGUA–SMN, descargado ahora (último corte: {d})",
                      f"CONAGUA–SMN Drought Monitor, downloaded now (latest assessment: {d})"),
        "upload": L(f"Monitor de Sequía, archivo cargado (último corte: {d})",
                    f"Drought Monitor, uploaded file (latest assessment: {d})"),
    }.get(key, L(f"Monitor de Sequía, copia incluida en la app (último corte: {d}); el sitio oficial no respondió",
                 f"Drought Monitor, copy bundled with the app (latest assessment: {d}); the official site did not answer"))


HOLDER_TYPES = {
    "utility": ("Sistemas municipales de agua", "Municipal water systems"),
    "community": ("Ejidos y comités comunitarios", "Ejidos and community committees"),
    "irrigation": ("Unidades de riego", "Irrigation units"),
    "company": ("Empresas y sociedades", "Companies"),
    "individual": ("Personas físicas", "Private individuals"),
    "government": ("Gobierno e instituciones", "Government and institutions"),
}


def holder_label(k):
    es, en = HOLDER_TYPES.get(k, (k, k))
    return L(es, en)


USE_ES = {"Public-urban": "Público urbano", "Agricultural": "Agrícola", "Services": "Servicios",
          "Multiple uses": "Usos múltiples", "Industrial": "Industrial", "Domestic": "Doméstico",
          "Aquaculture": "Acuacultura", "Livestock": "Pecuario", "Electricity": "Generación eléctrica",
          "Other": "Otro"}


def use_label(u):
    return L(USE_ES.get(u, u), u)


# ---------------------------------------------------------------- CSS
CSS = f"""
<style>
.block-container {{padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1180px;}}
h1 {{letter-spacing: -0.02em; line-height: 1.05; color: {NIGHT};}}
h2, h3 {{letter-spacing: -0.01em; color: {NIGHT};}}
p, li {{max-width: 78ch;}}

/* brand bar */
.st-key-brandbar {{border-bottom: 1px solid {LINE}; padding-bottom: .4rem; margin-bottom: .6rem;}}
.brand {{display:flex; align-items:center; gap:.55rem; font-family:'Bricolage Grotesque', sans-serif;
        font-weight:700; font-size:1.25rem; color:{NIGHT}; letter-spacing:-0.01em;}}
.brand small {{font-family:'Source Sans', sans-serif; font-weight:400; color:{MUTED}; font-size:.85rem;
              letter-spacing:0; margin-left:.4rem;}}

/* hero: night-blue panel with contour lines (highlands and ripples) */
.st-key-hero {{background-color:{NIGHT};
  background-image: repeating-radial-gradient(circle at 85% 30%, rgba(141,187,227,.10) 0 1px, transparent 1px 26px),
                    repeating-radial-gradient(circle at 10% 120%, rgba(229,139,176,.08) 0 1px, transparent 1px 34px);
  border-radius: 22px; padding: 1.6rem 1.7rem 1.4rem 1.7rem; color:#fff;}}
.st-key-hero h1, .st-key-hero p, .st-key-hero span, .st-key-hero div {{color:#fff;}}
.st-key-hero h1 {{font-size: clamp(2.4rem, 5vw, 3.6rem);}}
.hero-sub {{font-size:1.12rem; line-height:1.5; color:#D9E3F0 !important; max-width: 46ch;}}

/* control panels */
[class*="st-key-panel"] {{background:{PANEL}; border-radius:16px; padding: .9rem 1.1rem .6rem 1.1rem;}}

/* result highlight */
[class*="st-key-result"] {{background:#fff; border-radius:18px; padding:1.1rem 1.3rem; border:1px solid {LINE};}}

.lead {{font-size:1.08rem; line-height:1.55; color:{INK}; max-width:72ch;}}
.muted {{color:{MUTED}; font-size:.9rem;}}
.big {{font-family:'Bricolage Grotesque', sans-serif; font-weight:700; font-size:2.6rem; line-height:1; color:{NIGHT};}}
.big.water {{color:{WATER};}} .big.homes {{color:{HOMES};}}
.chip {{display:inline-flex; align-items:center; gap:.35rem; padding:.18rem .65rem; border-radius:999px;
       font-size:.82rem; font-weight:600; white-space:nowrap;}}
.dot {{width:.62rem; height:.62rem; border-radius:50%; display:inline-block;}}
.legend {{display:flex; flex-wrap:wrap; gap:1.2rem; align-items:center; font-size:.86rem; color:{MUTED}; margin:.35rem 0 0 0;}}
.ramp {{display:inline-block; width:120px; height:10px; border-radius:6px;
        background:linear-gradient(90deg, rgb(247,228,237), rgb(229,139,176), rgb(194,24,91), rgb(110,11,51));}}
.tower {{display:inline-block; width:9px; height:18px; border-radius:2px 2px 0 0; background:{WATER};
         box-shadow: 3px 0 0 rgba(31,111,178,.45);}}
.factgrid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.3rem 1.2rem; margin:.3rem 0 .4rem 0;}}
.factgrid .k {{color:{MUTED}; font-size:.82rem; line-height:1.2;}}
.factgrid .v {{font-family:'Bricolage Grotesque', sans-serif; font-size:1.45rem; font-weight:700; color:{NIGHT};
               margin-bottom:.45rem;}}
.factgrid .v.homes {{color:{HOMES};}} .factgrid .v.water {{color:{WATER};}}
.sentence {{font-size:1.06rem; line-height:1.55; border-left:4px solid {HOMES}; padding:.2rem 0 .2rem .9rem;}}
.footer {{color:{MUTED}; font-size:.82rem; border-top:1px solid {LINE}; padding-top:.8rem; margin-top:2.2rem;}}
@media (max-width: 640px) {{ .factgrid {{grid-template-columns:repeat(2,1fr);}} .big {{font-size:2rem;}} }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def page_title(title, lead=None):
    st.title(title)
    if lead:
        st.markdown(f'<p class="lead">{lead}</p>', unsafe_allow_html=True)


def chip(text, bg, fg=INK):
    return f'<span class="chip" style="background:{bg};color:{fg}">{text}</span>'


def facts(items):
    """items: (label, value, css-class) triples, shown as a grid."""
    cells = "".join(f'<div><div class="k">{k}</div><div class="v {c}">{v}</div></div>' for k, v, c in items)
    return f'<div class="factgrid">{cells}</div>'


# ---------------------------------------------------------------- colour scales
def ramp_rgb(t, stops=HOMES_RAMP):
    """Interpolate a 0–1 array along colour stops -> (n, 3) uint8."""
    t = np.clip(np.nan_to_num(np.asarray(t, dtype=float), nan=0.0), 0, 1)
    xs = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=float)
    return np.stack([np.interp(t, xs, cols[:, i]) for i in range(3)], axis=1).astype(int)


# ---------------------------------------------------------------- charts
def chart(ch, height=300):
    """Apply the app's chart style and draw."""
    ch = ch.properties(height=height).configure(
        font="Source Sans", background="transparent", padding={"left": 4, "right": 8, "top": 6, "bottom": 4},
    ).configure_axis(
        labelColor=MUTED, titleColor=MUTED, gridColor=LINE, domain=False, tickColor=LINE,
        labelFontSize=12, titleFontSize=12, titleFontWeight=600, labelPadding=6,
    ).configure_view(stroke=None).configure_legend(
        labelColor=INK, titleColor=MUTED, orient="top", labelFontSize=12, titleFontSize=12, symbolType="circle",
    ).configure_title(font="Bricolage Grotesque", fontSize=15, color=NIGHT, anchor="start")
    st.altair_chart(ch, width="stretch", theme=None)


def gradient(color, top_opacity=0.35):
    """Vertical fade from transparent (bottom) to the colour (top), for area fills."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                        stops=[alt.GradientStop(color=f"rgba({r},{g},{b},0)", offset=0),
                               alt.GradientStop(color=f"rgba({r},{g},{b},{top_opacity})", offset=1)])


MONTHS = {"ES": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
          "EN": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]}


def date_axis(kind="day", **kw):
    """Date labels in the app's language ('day' = 12 sep, 'month' = sep, with the year in January)."""
    m = "[" + ",".join(f"'{x}'" for x in MONTHS[lang()]) + "]"
    expr = (f"date(datum.value) + ' ' + {m}[month(datum.value)]" if kind == "day" else
            f"month(datum.value) == 0 ? '' + year(datum.value) : {m}[month(datum.value)]")
    return alt.Axis(labelExpr=expr, **kw)
