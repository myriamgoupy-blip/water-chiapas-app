"""Look and language of the app: Spanish first, English on request.

Colour code used everywhere (the app's identity):
  blue  = water granted by concession     magenta = homes without piped water
"""
import altair as alt
import numpy as np
import streamlit as st

from .config import DEFAULT_LANG, DROUGHT_COLOURS, DROUGHT_LABELS, DROUGHT_LABELS_ES, MUN_SHORT, MUNS

# ---------------------------------------------------------------- palette
# The app follows the viewer's light or dark theme (Settings menu, or the system setting). Text in custom
# blocks inherits the theme's text colour; the accents below are mid-tones that stay readable on both.
NEUTRAL = "#6F7F98"    # chart labels, rules and secondary marks (readable on white and on dark blue)
NIGHT = NEUTRAL        # kept for older calls: secondary chart marks
INK = NEUTRAL
MUTED = NEUTRAL
LINE = "#CBD5E1"
PANEL = "transparent"
DARK_TEXT = "#0B1220"  # text on light chips (drought colours)
WATER = "#2E86DE"      # water granted
WATER_SOFT = "#7FB2E8"
HOMES = "#E0457B"      # homes without water
PINE = "#12A578"
MAIZE = "#E49B0F"
AI = "#8B5CF6"         # model and machine-learning results
HOMES_RAMP = [(0.0, (148, 163, 184)), (0.35, (214, 120, 170)), (0.7, (224, 69, 123)), (1.0, (150, 20, 70))]
WATER_RGB = (46, 134, 222)
SEG_COLOURS = {"connected": "#94A3B8", "nearby": "#E49B0F", "outside": "#E0457B"}

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
# Every colour below either inherits the theme's text colour (currentColor) or is a mid-tone accent,
# so the same CSS reads well in the light and in the dark theme.
CSS = f"""
<style>
@property --n {{ syntax: '<integer>'; initial-value: 0; inherits: false; }}
.stApp {{background-image:
   radial-gradient(1000px 420px at 10% -10%, rgba(46,134,222,.10), transparent 60%),
   radial-gradient(800px 380px at 95% 0%, rgba(139,92,246,.08), transparent 60%);}}
.block-container {{padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1220px;}}
h1 {{letter-spacing: -0.025em; line-height: 1.05;}}
h2, h3, h4 {{letter-spacing: -0.01em;}}
p, li {{max-width: 80ch;}}

/* brand bar */
.st-key-brandbar {{border-bottom: 1px solid color-mix(in srgb, currentColor 14%, transparent); padding-bottom: .45rem; margin-bottom: .7rem;}}
.brand {{display:flex; align-items:center; gap:.6rem; font-family:'Bricolage Grotesque', sans-serif;
        font-weight:700; font-size:1.3rem; letter-spacing:-0.01em;}}
.brand small {{font-family:'Source Sans', sans-serif; font-weight:400; opacity:.78; font-size:.9rem; margin-left:.3rem;}}
.pill {{display:inline-flex; align-items:center; gap:.45rem; padding:.22rem .75rem; border-radius:999px; font-size:.8rem;
       font-weight:600; letter-spacing:.02em; border:1px solid color-mix(in srgb, currentColor 22%, transparent);
       background: color-mix(in srgb, currentColor 5%, transparent);}}
.pill.ai {{color:{AI}; border-color: color-mix(in srgb, {AI} 45%, transparent); background: color-mix(in srgb, {AI} 10%, transparent);}}
.live {{width:.5rem; height:.5rem; border-radius:50%; background:{PINE}; animation: pulse 2s infinite;}}
@keyframes pulse {{0% {{box-shadow:0 0 0 0 rgba(18,165,120,.55);}} 70% {{box-shadow:0 0 0 9px rgba(18,165,120,0);}}
                   100% {{box-shadow:0 0 0 0 rgba(18,165,120,0);}}}}

/* hero */
.st-key-hero {{border-radius: 26px; padding: 1.7rem 1.8rem 1.5rem 1.8rem;
  background: linear-gradient(135deg, rgba(46,134,222,.10), rgba(139,92,246,.07) 50%, rgba(224,69,123,.06));
  border: 1px solid color-mix(in srgb, currentColor 13%, transparent);}}
.st-key-hero h1 {{font-size: clamp(2.4rem, 5vw, 3.7rem);}}
.st-key-hero h1 .accent {{color:{WATER};}}
.hero-sub {{font-size:1.14rem; line-height:1.6; max-width: 48ch;}}

/* cards, panels, results */
[class*="st-key-glass"], [class*="st-key-panel"], [class*="st-key-result"], [class*="st-key-explore"] {{
  background: color-mix(in srgb, currentColor 3.5%, transparent); border:1px solid color-mix(in srgb, currentColor 13%, transparent);
  border-radius:18px; padding: 1rem 1.15rem .8rem 1.15rem;}}
[class*="st-key-result"] {{border-color: color-mix(in srgb, {WATER} 55%, transparent);
  background: color-mix(in srgb, {WATER} 6%, transparent);}}
[class*="st-key-explore"] {{min-height: 128px; transition: border-color .2s, transform .2s;}}
[class*="st-key-explore"]:hover {{border-color: {WATER}; transform: translateY(-2px);}}
[class*="st-key-glass_k"] {{min-height: 150px;}}
.st-key-hero [data-testid="stPageLink"] a {{border:1px solid color-mix(in srgb, {WATER} 60%, transparent); border-radius:999px;
  padding:.35rem .95rem; background: color-mix(in srgb, {WATER} 10%, transparent); width:fit-content;}}
.st-key-hero [data-testid="stPageLink"] a:hover {{border-color:{WATER};}}

.lead {{font-size:1.08rem; line-height:1.6; max-width:74ch;}}
.muted {{opacity:.8; font-size:.93rem; line-height:1.5;}}
.big {{font-family:'Bricolage Grotesque', sans-serif; font-weight:800; font-size:2.7rem; line-height:1;}}
.big.water {{color:{WATER};}} .big.homes {{color:{HOMES};}} .big.ai {{color:{AI};}}
.count {{animation: countup 1.8s cubic-bezier(.2,.7,.2,1) forwards; counter-reset: n var(--n);}}
.count::after {{content: counter(n);}}
@keyframes countup {{from {{--n: 0;}} to {{--n: var(--to);}}}}

.chip {{display:inline-flex; align-items:center; gap:.35rem; padding:.2rem .68rem; border-radius:999px;
       font-size:.82rem; font-weight:600; white-space:nowrap;}}
.chip.soft {{background: color-mix(in srgb, currentColor 9%, transparent); border:1px solid color-mix(in srgb, currentColor 18%, transparent);}}
.dot {{width:.62rem; height:.62rem; border-radius:50%; display:inline-block;}}
.legend {{display:flex; flex-wrap:wrap; gap:1.2rem; align-items:center; font-size:.88rem; opacity:.85; margin:.4rem 0 0 0;}}
.ramp {{display:inline-block; width:120px; height:10px; border-radius:6px;
        background:linear-gradient(90deg, rgb(148,163,184), rgb(214,120,170), rgb(224,69,123), rgb(150,20,70));}}
.tower {{display:inline-block; width:9px; height:18px; border-radius:2px 2px 0 0; background:{WATER};}}
.factgrid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.3rem 1.2rem; margin:.3rem 0 .4rem 0;}}
.factgrid .k {{opacity:.78; font-size:.85rem; line-height:1.2;}}
.factgrid .v {{font-family:'Bricolage Grotesque', sans-serif; font-size:1.45rem; font-weight:700; margin-bottom:.45rem;}}
.factgrid .v.homes {{color:{HOMES};}} .factgrid .v.water {{color:{WATER};}}
.sentence {{font-size:1.06rem; line-height:1.6; border-left:3px solid {HOMES}; padding:.2rem 0 .2rem .9rem;}}

/* page guide: three numbered steps */
.guide {{display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin:.2rem 0 1.1rem 0;}}
.guide .step {{border:1px solid color-mix(in srgb, currentColor 13%, transparent); border-radius:14px; padding:.7rem .85rem;
               background: color-mix(in srgb, currentColor 3%, transparent); font-size:.93rem; line-height:1.45;}}
.guide .n {{display:inline-flex; width:1.5rem; height:1.5rem; border-radius:50%; align-items:center; justify-content:center;
            font-weight:700; font-size:.8rem; margin-right:.45rem; color:#fff; background:{WATER};}}
.guide .t {{font-weight:700;}}

/* explanation under a map or chart */
.explain {{display:flex; gap:.55rem; align-items:flex-start; font-size:.92rem; line-height:1.5; margin:.45rem 0 .25rem 0; opacity:.88;}}
.explain .i {{flex:0 0 auto; width:1.25rem; height:1.25rem; border-radius:50%; border:1.5px solid currentColor; display:inline-flex;
             align-items:center; justify-content:center; font-size:.72rem; font-weight:700; margin-top:.12rem;}}

/* model and machine-learning results */
.insight {{border-radius:16px; padding:.85rem 1rem .85rem 1rem; margin:.5rem 0 .8rem 0; line-height:1.6;
          background: color-mix(in srgb, {AI} 8%, transparent); border:1px solid color-mix(in srgb, {AI} 40%, transparent);}}
.insight .tag {{display:block; font-size:.74rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase;
               color:{AI}; margin-bottom:.3rem;}}
.segtag {{display:inline-flex; align-items:center; gap:.4rem; padding:.22rem .75rem; border-radius:999px; font-size:.82rem;
         font-weight:700; color:#fff;}}

[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"] p, [data-testid="stMetricLabel"] p {{color:inherit !important; opacity:.88;}}
[data-testid="stTooltipIcon"] svg {{opacity:.8;}}
/* Streamlit Cloud adds Share / star / edit / GitHub buttons at the top right: hidden for a cleaner header */
[data-testid="stToolbarActions"] {{display:none !important;}}
.st-key-theme_btn button {{white-space:nowrap;}}
.footer {{opacity:.85; font-size:.84rem; border-top:1px solid color-mix(in srgb, currentColor 14%, transparent);
         padding-top:.8rem; margin-top:2.4rem;}}
@media (max-width: 760px) {{ .factgrid {{grid-template-columns:repeat(2,1fr);}} .big {{font-size:2.1rem;}}
                             .guide {{grid-template-columns:1fr;}} }}
</style>
"""


PAGE_PATHS = ["", "ask", "map", "model", "index", "climate", "data"]


def switch_theme(target):
    """Switch the viewer to the light or dark theme.

    Streamlit keeps each viewer's choice in the browser (the same setting as the three-dot menu). The script
    writes that choice for every page of the app and reloads the page, keeping the language in the URL.
    """
    st.html(f"""<script>
(function () {{
  const pages = {PAGE_PATHS!r};
  const segs = window.location.pathname.split('/');
  const last = segs[segs.length - 1];
  if (last === '' || pages.includes(last)) segs.pop();
  const base = segs.join('/');
  const value = JSON.stringify('{target}');
  const paths = new Set([base || '/']);
  pages.forEach(p => paths.add(base + '/' + p));
  paths.forEach(p => {{ try {{ window.localStorage.setItem('stActiveTheme-' + p + '-v2', value); }} catch (e) {{}} }});
  const u = new URL(window.location.href);
  u.searchParams.set('lang', '{lang()}');
  window.location.replace(u.toString());
}})();
</script>""", unsafe_allow_javascript=True)


def theme_file_missing():
    """True when .streamlit/config.toml (the light and dark themes) was not deployed with the app."""
    try:
        return st.get_option("theme.dark.backgroundColor") is None
    except Exception:  # noqa: BLE001
        return True


def theme_type():
    try:
        return st.context.theme.type or "light"
    except Exception:  # noqa: BLE001
        return "light"


def inject_css():
    """Inject the CSS and pick the chart label colour for the active theme (light or dark)."""
    global NEUTRAL, MUTED, INK, NIGHT
    NEUTRAL = "#C9D4E5" if theme_type() == "dark" else "#3F4D63"
    MUTED = INK = NIGHT = NEUTRAL
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
    return f'<div class="insight"><div class="tag">{tag}</div>{text}</div>'


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
    col = {"connected": "#64748B"}.get(seg, SEG_COLOURS.get(seg, NEUTRAL))
    return f'<span class="segtag" style="background:{col}">{name}</span>'


def chip(text, bg=None, fg=DARK_TEXT):
    if bg is None:
        return f'<span class="chip soft">{text}</span>'
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
    """Draw with the Streamlit theme, so axes and labels follow light or dark mode."""
    dark = theme_type() == "dark"
    label, title = ("#E3EAF5", "#C5D0E0") if dark else ("#1F2A3D", "#3A475C")
    ch = ch.properties(height=height).configure(
        font="Source Sans", padding={"left": 4, "right": 8, "top": 6, "bottom": 4},
    ).configure_axis(domain=False, labelFontSize=12.5, titleFontSize=12.5, titleFontWeight=600, labelPadding=6,
                     labelColor=label, titleColor=title,
    ).configure_view(stroke=None).configure_legend(orient="top", labelFontSize=12.5, titleFontSize=12.5, symbolType="circle",
                                                   labelColor=label, titleColor=title)
    st.altair_chart(ch, width="stretch", theme="streamlit")


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
