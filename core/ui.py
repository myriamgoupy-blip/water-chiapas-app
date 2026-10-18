"""Look and language of the app: Spanish first, English on request.

Colour code used everywhere (the app's identity):
  blue  = water granted by concession     magenta = homes without piped water
"""
import altair as alt
import numpy as np
import streamlit as st

from .config import DEFAULT_LANG, DROUGHT_COLOURS, DROUGHT_LABELS, DROUGHT_LABELS_ES, MUN_SHORT, MUNS

# ---------------------------------------------------------------- palette (dark "data lab")
BG = "#070D1A"         # app background
SURFACE = "#0E1729"    # cards
NIGHT = "#F4F8FF"      # headings, strongest marks (light on dark)
INK = "#DCE5F2"        # body text
MUTED = "#8C9DB8"      # secondary text, axes
LINE = "#22304D"       # gridlines, borders
MIST = BG
PANEL = "#101B31"      # control panels
DARK_TEXT = "#0B1220"  # text on light chips
WATER = "#38B6FF"      # water granted (cyan)
WATER_SOFT = "#2C6FA8"
HOMES = "#FF4F93"      # homes without water (neon magenta)
PINE = "#34D399"
MAIZE = "#FBBF24"
AI = "#A78BFA"         # AI and machine-learning features (violet)
HOMES_RAMP = [(0.0, (58, 74, 104)), (0.35, (150, 58, 128)), (0.7, (255, 79, 147)), (1.0, (255, 176, 210))]
WATER_RGB = (56, 182, 255)
SEG_COLOURS = {"connected": "#3B4A66", "nearby": "#FBBF24", "outside": "#FF4F93"}

MAP_LIGHT = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
MAP_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


# ---------------------------------------------------------------- language
def lang():
    return st.session_state.get("lang_choice") or DEFAULT_LANG


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
    fg = "#fff" if cat in ("D2", "D3", "D4", "None") else DARK_TEXT
    return chip(text or (cat if cat != "None" else L("Sin sequía", "None")), DROUGHT_COLOURS.get(cat, "#DCE3EB"), fg)


def source_label(key):
    if key.startswith("live:"):
        return L(f"LOCREPDA en vivo desde CONAGUA (leído el {key[5:]})", f"LOCREPDA live from CONAGUA (read {key[5:]})")
    if key == "bundled":
        return L("copia incluida en la app (28 sep 2026): el servidor de CONAGUA no respondió",
                 "copy bundled with the app (28 Sep 2026): CONAGUA's server did not answer")
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
@property --n {{ syntax: '<integer>'; initial-value: 0; inherits: false; }}
.stApp {{background:
   radial-gradient(1100px 520px at 12% -8%, rgba(56,182,255,.13), transparent 60%),
   radial-gradient(900px 480px at 92% 2%, rgba(167,139,250,.12), transparent 60%),
   {BG};}}
.block-container {{padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1220px;}}
h1 {{letter-spacing: -0.025em; line-height: 1.04; color: {NIGHT};}}
h2, h3, h4 {{letter-spacing: -0.01em; color: {NIGHT};}}
p, li {{max-width: 80ch;}}

/* brand bar */
.st-key-brandbar {{border-bottom: 1px solid {LINE}; padding-bottom: .45rem; margin-bottom: .7rem;}}
.brand {{display:flex; align-items:center; gap:.6rem; font-family:'Bricolage Grotesque', sans-serif;
        font-weight:700; font-size:1.3rem; color:{NIGHT}; letter-spacing:-0.01em;}}
.brand small {{font-family:'Source Sans', sans-serif; font-weight:400; color:{MUTED}; font-size:.86rem; margin-left:.3rem;}}
.pill {{display:inline-flex; align-items:center; gap:.4rem; padding:.2rem .7rem; border-radius:999px; font-size:.78rem;
       font-weight:600; letter-spacing:.02em; border:1px solid {LINE}; background:rgba(16,27,49,.75); color:{INK};}}
.live {{width:.5rem; height:.5rem; border-radius:50%; background:{PINE}; box-shadow:0 0 0 0 rgba(52,211,153,.7);
       animation: pulse 2s infinite;}}
@keyframes pulse {{0% {{box-shadow:0 0 0 0 rgba(52,211,153,.6);}} 70% {{box-shadow:0 0 0 9px rgba(52,211,153,0);}}
                   100% {{box-shadow:0 0 0 0 rgba(52,211,153,0);}}}}

/* hero */
.st-key-hero {{position:relative; border-radius: 26px; padding: 1.7rem 1.8rem 1.5rem 1.8rem;
  background: linear-gradient(135deg, rgba(56,182,255,.10), rgba(167,139,250,.08) 45%, rgba(255,79,147,.07)), {SURFACE};
  border: 1px solid rgba(120,160,230,.18); box-shadow: 0 30px 80px -30px rgba(56,182,255,.25);}}
.st-key-hero h1 {{font-size: clamp(2.4rem, 5vw, 3.8rem);
  background: linear-gradient(92deg, #FFFFFF 10%, #9ED8FF 55%, #C9B8FF 95%); -webkit-background-clip:text;
  background-clip:text; color: transparent;}}
.hero-sub {{font-size:1.12rem; line-height:1.55; color:#C3D0E4 !important; max-width: 48ch;}}

/* glass cards, panels, results */
[class*="st-key-glass"], [class*="st-key-panel"], [class*="st-key-result"] {{
  background: linear-gradient(180deg, rgba(20,33,60,.72), rgba(14,23,41,.72)); border:1px solid rgba(120,160,230,.14);
  border-radius:18px; padding: 1rem 1.15rem .8rem 1.15rem; backdrop-filter: blur(8px);}}
[class*="st-key-result"] {{border-color: rgba(56,182,255,.35); box-shadow: 0 20px 60px -35px rgba(56,182,255,.45);}}

.lead {{font-size:1.07rem; line-height:1.58; color:{INK}; max-width:74ch;}}
.muted {{color:{MUTED}; font-size:.9rem;}}
.big {{font-family:'Bricolage Grotesque', sans-serif; font-weight:800; font-size:2.7rem; line-height:1; color:{NIGHT};}}
.big.water {{color:{WATER}; text-shadow:0 0 28px rgba(56,182,255,.35);}}
.big.homes {{color:{HOMES}; text-shadow:0 0 28px rgba(255,79,147,.35);}}
.big.ai {{color:{AI};}}
.count {{animation: countup 1.8s cubic-bezier(.2,.7,.2,1) forwards; counter-reset: n var(--n);}}
.count::after {{content: counter(n);}}
@keyframes countup {{from {{--n: 0;}} to {{--n: var(--to);}}}}
.fadeup {{animation: fadeup .9s ease-out both;}}
@keyframes fadeup {{from {{opacity:0; transform: translateY(8px);}} to {{opacity:1; transform:none;}}}}

.chip {{display:inline-flex; align-items:center; gap:.35rem; padding:.18rem .65rem; border-radius:999px;
       font-size:.82rem; font-weight:600; white-space:nowrap;}}
.dot {{width:.62rem; height:.62rem; border-radius:50%; display:inline-block;}}
.legend {{display:flex; flex-wrap:wrap; gap:1.2rem; align-items:center; font-size:.86rem; color:{MUTED}; margin:.4rem 0 0 0;}}
.ramp {{display:inline-block; width:120px; height:10px; border-radius:6px;
        background:linear-gradient(90deg, rgb(58,74,104), rgb(150,58,128), rgb(255,79,147), rgb(255,176,210));}}
.tower {{display:inline-block; width:9px; height:18px; border-radius:2px 2px 0 0; background:{WATER};
         box-shadow: 0 0 10px rgba(56,182,255,.8);}}
.factgrid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.3rem 1.2rem; margin:.3rem 0 .4rem 0;}}
.factgrid .k {{color:{MUTED}; font-size:.82rem; line-height:1.2;}}
.factgrid .v {{font-family:'Bricolage Grotesque', sans-serif; font-size:1.45rem; font-weight:700; color:{NIGHT}; margin-bottom:.45rem;}}
.factgrid .v.homes {{color:{HOMES};}} .factgrid .v.water {{color:{WATER};}}
.sentence {{font-size:1.06rem; line-height:1.55; border-left:3px solid {HOMES}; padding:.2rem 0 .2rem .9rem; color:{INK};}}

/* page guide: three numbered steps */
.guide {{display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin:.2rem 0 1.1rem 0;}}
.guide .step {{border:1px solid rgba(120,160,230,.14); border-radius:14px; padding:.65rem .8rem;
               background:rgba(16,27,49,.55); font-size:.9rem; line-height:1.4; color:{INK};}}
.guide .n {{display:inline-flex; width:1.45rem; height:1.45rem; border-radius:50%; align-items:center; justify-content:center;
            font-weight:700; font-size:.8rem; margin-right:.45rem; color:{DARK_TEXT};
            background:linear-gradient(135deg, {WATER}, {AI});}}
.guide .t {{font-weight:700; color:{NIGHT};}}

/* explanation under a map or chart */
.explain {{display:flex; gap:.55rem; align-items:flex-start; color:{MUTED}; font-size:.88rem; line-height:1.45; margin:.45rem 0 .2rem 0;}}
.explain b {{color:{INK};}}
.explain .i {{flex:0 0 auto; width:1.2rem; height:1.2rem; border-radius:50%; border:1px solid {MUTED}; display:inline-flex;
             align-items:center; justify-content:center; font-size:.72rem; font-weight:700; margin-top:.1rem;}}

/* machine-learning / AI insight */
.insight {{position:relative; border-radius:16px; padding:.85rem 1rem .8rem 1rem; margin:.5rem 0 .8rem 0; color:{INK};
          background: linear-gradient(135deg, rgba(167,139,250,.14), rgba(56,182,255,.08)); line-height:1.55;
          border:1px solid rgba(167,139,250,.35);}}
.insight .tag {{display:flex; align-items:center; gap:.35rem; font-size:.74rem; font-weight:700; letter-spacing:.06em;
               text-transform:uppercase; color:{AI}; margin-bottom:.3rem;}}
.segtag {{display:inline-flex; align-items:center; gap:.4rem; padding:.22rem .7rem; border-radius:999px; font-size:.8rem;
         font-weight:700; border:1px solid currentColor;}}

/* explore cards (home) */
[class*="st-key-explore"] {{border-radius:18px; padding:.95rem 1.05rem .7rem 1.05rem; border:1px solid rgba(120,160,230,.14);
  background: linear-gradient(180deg, rgba(20,33,60,.72), rgba(14,23,41,.72)); transition: border-color .2s, transform .2s;}}
[class*="st-key-explore"] {{min-height: 128px;}}
[class*="st-key-glass_k"] {{min-height: 150px;}}
.st-key-hero [data-testid="stPageLink"] a {{border:1px solid rgba(56,182,255,.45); border-radius:999px; padding:.35rem .9rem;
  background: linear-gradient(90deg, rgba(56,182,255,.18), rgba(167,139,250,.18)); width:fit-content;}}
.st-key-hero [data-testid="stPageLink"] a:hover {{border-color:#38B6FF;}}
[class*="st-key-explore"]:hover {{border-color: rgba(56,182,255,.55); transform: translateY(-2px);}}

.footer {{color:{MUTED}; font-size:.82rem; border-top:1px solid {LINE}; padding-top:.8rem; margin-top:2.4rem;}}
[data-testid="stExpander"] details {{border-color:{LINE}; border-radius:14px; background:rgba(16,27,49,.45);}}
@media (max-width: 760px) {{ .factgrid {{grid-template-columns:repeat(2,1fr);}} .big {{font-size:2.1rem;}}
                             .guide {{grid-template-columns:1fr;}} }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def page_title(title, lead=None, kicker=None):
    if kicker:
        st.markdown(f'<span class="pill">{kicker}</span>', unsafe_allow_html=True)
    st.title(title)
    if lead:
        st.markdown(f'<p class="lead">{lead}</p>', unsafe_allow_html=True)


def guide(steps):
    """Three short numbered steps: (title, text) pairs that say how to use the page."""
    cells = "".join(f'<div class="step"><span class="n">{i}</span><span class="t">{t}</span><br>{x}</div>'
                    for i, (t, x) in enumerate(steps, 1))
    st.markdown(f'<div class="guide">{cells}</div>', unsafe_allow_html=True)


def explain(text):
    """One line under a map or chart: what it shows and how to read it."""
    st.markdown(f'<div class="explain"><span class="i">i</span><div>{text}</div></div>', unsafe_allow_html=True)


def insight(text, tag=None):
    """A result computed by the app's analytics (machine learning or the model), set apart in violet."""
    tag = tag or L("Análisis automático", "Auto-insight")
    return f'<div class="insight"><div class="tag">✦ {tag}</div>{text}</div>'


def count(value, suffix="", prefix="", cls=""):
    """A number that counts up when the page opens (integers only)."""
    v = int(round(value))
    return f'<div class="big {cls}">{prefix}<span class="count" style="--to:{v}"></span>{suffix}</div>'


def live_pill(text):
    return f'<span class="pill"><span class="live"></span>{text}</span>'


def segtag(seg):
    name = {"connected": L("Mayormente conectada", "Mostly connected"),
            "nearby": L("Agua cerca que no llega", "Water nearby, not reaching homes"),
            "outside": L("Fuera del sistema formal", "Outside the formal system")}.get(seg, "–")
    col = {"connected": "#9AA9C2"}.get(seg, SEG_COLOURS.get(seg, MUTED))
    return f'<span class="segtag" style="color:{col}">{name}</span>'


def chip(text, bg, fg=DARK_TEXT):
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
        labelColor=MUTED, titleColor=MUTED, gridColor="#1A2742", domain=False, tickColor=LINE,
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
