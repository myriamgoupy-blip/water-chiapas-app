"""'Ask Ojo de Agua': a data assistant grounded in the app's own analyses.

The assistant never invents numbers: every figure comes from one of the tools below, which read the same
tables as the pages. With an Anthropic API key (Streamlit secret ANTHROPIC_API_KEY), Claude chooses the
tools and writes the answer. Without a key, the same tools answer a set of common questions directly.
"""
import json
import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from . import data, engine, insights, ui
from .config import MUNS, THESIS

DEFAULT_MODEL = "claude-sonnet-5"


# ---------------------------------------------------------------- helpers
def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _mun_code(name):
    if name in (None, "", "all"):
        return None
    n = _norm(name)
    for code, full in MUNS.items():
        if n.strip() and (n.strip() in _norm(full) or _norm(full).startswith(n.strip())):
            return code
    return None


SEG_NAMES = {"connected": "mostly connected", "outside": "outside the formal water system",
             "nearby": "water granted nearby but not reaching homes"}


def _r(x, d=1):
    return None if x is None or x != x else round(float(x), d)


# ---------------------------------------------------------------- tools (each returns plain JSON-able data)
def tool_find_locality(name, municipality=None):
    k, pts, pkey = insights.current()
    loc = engine.table(pkey, pts)
    pool = loc if _mun_code(municipality) is None else loc[loc.MUN == _mun_code(municipality)]
    n = _norm(name).strip()
    hit = pool[pool.NOM_LOC.map(_norm).str.contains(re.escape(n), na=False)] if n else pool.iloc[0:0]
    if hit.empty:
        words = [w for w in n.split() if len(w) > 3]
        if words:
            hit = pool[pool.NOM_LOC.map(_norm).apply(lambda s: all(w in s for w in words))]
    if hit.empty:
        return {"found": False, "message": f"No locality matching '{name}'."}
    row = hit.sort_values("POBTOT", ascending=False).iloc[0]
    out = {"found": True, "locality": row.NOM_LOC, "municipality": MUNS[int(row.MUN)],
           "inhabitants": int(row.POBTOT) if row.POBTOT == row.POBTOT else None,
           "inhabited_homes": int(row.VIVPARH_CV) if row.VIVPARH_CV == row.VIVPARH_CV else None,
           "pct_homes_without_piped_water": _r(row.dep_water), "pct_homes_without_drainage": _r(row.dep_drain),
           "pct_indigenous_language": _r(row.indig), "years_of_schooling": _r(row.school),
           "other_matches": [f"{r.NOM_LOC} ({MUNS[int(r.MUN)]})" for _, r in hit.iloc[1:6].iterrows()]}
    if row.name in k.index:
        r = k.loc[row.name]
        out.update({"water_granted_within_2km_m3_per_year": _r(r.vol2, 0),
                    "water_granted_within_2km_m3_per_resident": _r(r.vol_pc, 0),
                    "segment": SEG_NAMES[r.segment], "segment_key": r.segment, "priority_rank_of_538": int(r.priority_rank),
                    "priority_score": _r(r.priority), "model_predicted_pct_without_water": _r(r.predicted),
                    "model_surprise_points": _r(r.surprise)})
        if pts is not None:
            from . import geo
            placed = engine.point_arrays(pkey, pts)["placed"]
            near = geo.concessions_near(row.lon, row.lat, placed, 2.0)
            if near is not None and len(near):
                top = near.groupby("TITULAR").vol.sum().sort_values(ascending=False)
                out["largest_holders_within_2km"] = [{"holder": str(h).title(), "share": _r(v / top.sum() * 100, 0)}
                                                     for h, v in top.head(3).items()]
    else:
        out["note"] = "Not in the model sample (100 inhabitants or fewer, or masked census data)."
    return out


def tool_rank_localities(by="priority", municipality=None, segment=None, n=10):
    k, _, _ = insights.current()
    x = k if _mun_code(municipality) is None else k[k.MUN == _mun_code(municipality)]
    if segment in ("outside", "nearby", "connected"):
        x = x[x.segment == segment]
    col, asc = {"priority": ("priority", False), "no_water": ("dep_water", False),
                "water_nearby": ("vol_pc", False), "surprise": ("surprise", False),
                "population": ("POBTOT", False)}.get(by, ("priority", False))
    x = x.sort_values([col, "POBTOT"], ascending=[asc, False]).head(int(min(max(n, 1), 25)))
    return {"ranked_by": by, "municipality": municipality or "all", "segment": segment or "all",
            "localities": [{"locality": r.NOM_LOC, "municipality": MUNS[int(r.MUN)], "inhabitants": int(r.POBTOT),
                            "pct_without_piped_water": _r(r.dep_water, 0), "water_within_2km_m3_per_resident": _r(r.vol_pc, 0),
                            "segment": SEG_NAMES[r.segment], "segment_key": r.segment, "priority_rank": int(r.priority_rank),
                            "model_surprise_points": _r(r.surprise, 0)} for _, r in x.iterrows()]}


def tool_municipality_summary(municipality=None):
    k, _, _ = insights.current()
    t = insights.municipality_table(k)
    drought, _ = data.drought()
    latest = drought[drought.date == drought.date.max()].set_index("MUN").cat
    code = _mun_code(municipality)
    if code is not None:
        t = t[t.MUN == code]
    rows = [{"municipality": MUNS[int(r.MUN)], "localities_in_sample": int(r.localities), "inhabitants": int(r.people),
             "pct_homes_without_piped_water": _r(r.pct_no_water), "localities_mostly_without_pipes": int(r.unconnected),
             "of_which_water_granted_nearby": int(r.nearby), "of_which_outside_the_system": int(r.outside),
             "median_m3_per_resident_within_2km": _r(r.median_vol_pc, 0), "localities_with_no_concession_within_2km": int(r.none_2km),
             "localities_in_priority_top20": int(r.top20), "drought_today": latest.get(int(r.MUN), "None")}
            for _, r in t.iterrows()]
    seg = insights.segment_summary(k)
    return {"municipalities": rows, "drought_date": str(drought.date.max().date()),
            "segments_all_nine": {s: {"localities": int(seg.loc[s, "localities"]), "inhabitants": int(seg.loc[s, "people"]),
                                      "share_of_homes_without_piped_water_pct": _r(100 * seg.loc[s, "share_nowater"])}
                                  for s in seg.index}}


def tool_model_result(radius_km=2.0, min_inhabitants=100, model="M3"):
    pts, pkey = data.active_points()
    radius_km = float(min(max(radius_km, 0.5), 10.0))
    d, fit, Dm = engine.run_model(pkey, pts, model if model in ("M1", "M2", "M3") else "M3", "dep_water",
                                  radius_km, "buffer", True, False, int(min_inhabitants))
    _, cp, _ = fit.conley(Dm, 10)
    q25, q75 = d.intensity.quantile([.25, .75])
    b1 = float(fit.params["int_c"])
    return {"model": model, "radius_km": radius_km, "localities": int(fit.n), "beta1": round(b1, 3),
            "p_robust": round(float(fit.pvalues["int_c"]), 3), "p_conley_10km": round(float(cp["int_c"]), 3),
            "effect_25th_to_75th_percentile_points": round(b1 * (q75 - q25), 1),
            "mean_pct_without_water": round(float(d.dep_water.mean()), 1),
            "thesis_reference": {"beta1": THESIS["beta1"], "p_robust": 0.003, "p_conley_10km": 0.056,
                                 "p_cluster_bootstrap": 0.154, "localities": 538},
            "reading": "Negative beta1: localities with more water granted nearby have fewer homes without piped water. "
                       "Association, not cause."}


def tool_drought_status():
    drought, key = data.drought()
    last = drought.date.max()
    latest = drought[drought.date == last].set_index("MUN").cat
    return {"assessment_date": str(last.date()), "source": key,
            "by_municipality": {MUNS[int(m)]: c for m, c in latest.items()},
            "scale": "None, D0 abnormally dry, D1 moderate, D2 severe, D3 extreme, D4 exceptional drought"}


def tool_register_issues():
    pts, pkey = data.active_points()
    if pts is None:
        return {"available": False}
    rep = data.repda()
    ext = rep[rep.vol > 0]
    ok = set(pts[pts.flag == "ok"].key)
    missing = ext[~ext.key.isin(ok)]
    bad = pts[pts.flag != "ok"]
    return {"points": int(len(pts)), "misplaced_points": int(len(bad)), "extractive_titles": int(len(ext)),
            "titles_without_valid_location": int(len(missing)),
            "share_of_volume_without_valid_location_pct": round(100 * missing.vol.sum() / ext.vol.sum(), 1),
            "largest_unlocated": [{"title": r["Título"], "holder": str(r.Titular).title(), "m3_per_year": int(r.vol)}
                                  for _, r in missing.nlargest(3, "vol").iterrows()],
            "example": "Both points of the Coca-Cola bottler (Inmuebles del Golfo) are placed about 100 km west of San Cristóbal."}


def tool_thesis_facts():
    return {"concessions": "965 extractive titles, 71.2 million m3 a year in 9 municipalities; Gini 0.859; top 10% of titles hold 78%; "
                           "public-urban 64.9%, agriculture 31.6%, industry 0.6% (Coca-Cola bottler 419,774 m3 a year).",
            "official_balance": "Registered groundwater in San Cristóbal is about a third of the official extraction figure: no hidden over-extraction.",
            "model": "OLS with municipality fixed effects on 538 localities; outcome % of homes without piped water; intensity = "
                     "log(1 + m3 granted within 2 km per resident). beta1 = -2.195 (robust p 0.003, Conley 10 km p 0.056, "
                     "cluster bootstrap p 0.154): consistent but moderate. No difference with the Indigenous share (beta3 p 0.74).",
            "segments": "137 localities with at least half of homes without piped water hold 65% of such homes: 85 outside the system "
                        "(no water granted nearby), 52 with water granted nearby that does not reach homes.",
            "data_dates": "REPDA cut-off 30 June 2026; census 2020; thesis results checked on 18 October 2026; the app uses live data."}


TOOLS = {
    "find_locality": (tool_find_locality, "Look up one locality by name: population, homes without piped water and drainage, "
                      "Indigenous share, schooling, water granted within 2 km, segment, priority rank and how it compares with the model.",
                      {"name": {"type": "string", "description": "Locality name, accents optional"},
                       "municipality": {"type": "string", "description": "Optional municipality name"}}, ["name"]),
    "rank_localities": (tool_rank_localities, "Rank localities of the model sample by priority, share without piped water, "
                        "water granted nearby, model surprise (worse than predicted) or population, optionally within a municipality or segment.",
                        {"by": {"type": "string", "enum": ["priority", "no_water", "water_nearby", "surprise", "population"]},
                         "municipality": {"type": "string"}, "segment": {"type": "string", "enum": ["outside", "nearby", "connected"]},
                         "n": {"type": "integer", "minimum": 1, "maximum": 25}}, []),
    "municipality_summary": (tool_municipality_summary, "Summary for one or all nine municipalities: homes without piped water, "
                             "unconnected localities by segment, water granted nearby, top-20 priorities, today's drought.",
                             {"municipality": {"type": "string", "description": "Leave empty for all nine"}}, []),
    "model_result": (tool_model_result, "Re-estimate the thesis model with another radius, minimum population or version (M1, M2, M3).",
                     {"radius_km": {"type": "number"}, "min_inhabitants": {"type": "integer"},
                      "model": {"type": "string", "enum": ["M1", "M2", "M3"]}}, []),
    "drought_status": (tool_drought_status, "Latest official Drought Monitor category of each municipality.", {}, []),
    "register_issues": (tool_register_issues, "Problems found in CONAGUA's concession register: misplaced points and titles without location.", {}, []),
    "thesis_facts": (tool_thesis_facts, "Key results and methods of the thesis, with their dates.", {}, []),
}


def run_tool(name, args):
    fn = TOOLS[name][0]
    try:
        return fn(**(args or {}))
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def tool_specs():
    return [{"name": n, "description": desc, "input_schema": {"type": "object", "properties": props, "required": req}}
            for n, (_, desc, props, req) in TOOLS.items()]


# ---------------------------------------------------------------- Claude
def api_key():
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # noqa: BLE001  (no secrets file)
        return None


def model_name():
    try:
        return st.secrets.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    except Exception:  # noqa: BLE001
        return DEFAULT_MODEL


SYSTEM = """You are the assistant of Ojo de Agua, a web application that accompanies an MSc thesis (ESCP Business School, 2026)
on water concessions and household water access in nine municipalities of the Chiapas highlands, Mexico.
Rules:
- Use the tools for every number. Never invent or estimate figures; if a tool cannot answer, say so.
- Write in a plain, professional register: no emojis or decorative symbols.
- Answer in {lang}. Be concise: at most about 130 words, plain language, short paragraphs or a short list.
- The model shows associations, not causes. Say so when you discuss the model.
- When useful, end with one line telling the user which page of the app to open (Map, Model, Priorities, Drought & rain, Data).
- Segments: 'outside the formal water system' (no water granted nearby, needs a source and a network) and
  'water nearby, not reaching homes' (needs a connection to an existing system)."""


def ask_claude(history, on_tool=None):
    """history: list of {'role', 'content'} with plain text. Returns (answer, tool_calls)."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key())
    msgs = [{"role": m["role"], "content": m["content"]} for m in history]
    calls = []
    for _ in range(6):
        resp = client.messages.create(model=model_name(), max_tokens=900,
                                      system=SYSTEM.format(lang="Spanish" if ui.lang() == "ES" else "English"),
                                      tools=tool_specs(), messages=msgs)
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
            return text, calls
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if getattr(b, "type", "") == "tool_use":
                if on_tool:
                    on_tool(b.name, b.input)
                out = run_tool(b.name, b.input)
                calls.append((b.name, b.input))
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)})
        msgs.append({"role": "user", "content": results})
    return ui.L("No pude terminar la respuesta. Intenta con una pregunta más concreta.",
                "I could not finish the answer. Try a more specific question."), calls


# ---------------------------------------------------------------- offline answers (no API key)
def offline_answer(q):
    """Answer common questions with the same tools and fixed wording. Returns (markdown, tool_calls)."""
    L = ui.L
    nq = _norm(q)
    calls = []

    seg_l = {"connected": L("mayormente conectada", "mostly connected"),
             "outside": L("fuera del sistema formal", "outside the formal system"),
             "nearby": L("agua cerca que no llega", "water nearby, not reaching homes")}

    def call(tool, **a):
        calls.append((tool, a))
        return run_tool(tool, a)

    mun = next((n for code, n in MUNS.items() if _norm(n).split()[0] in nq.split()), None)
    if any(w in nq for w in ["drought", "sequia", "dry", "rain", "lluvia"]):
        r = call("drought_status")
        lines = [f"- **{m}**: {c}" for m, c in r["by_municipality"].items()]
        return L(f"Monitor de Sequía, corte del {r['assessment_date']}:\n", f"Drought Monitor, assessment of {r['assessment_date']}:\n") \
            + "\n".join(lines) + "\n\n" + L("Abre **Sequía y lluvia** para ver la historia.", "Open **Drought & rain** for the history."), calls
    if any(w in nq for w in ["register", "registro", "misplaced", "error", "repda", "locrepda", "coca"]):
        r = call("register_issues")
        return L(f"De {r['points']} puntos de LOCREPDA, **{r['misplaced_points']}** están fuera de su municipio, y "
                 f"**{r['titles_without_valid_location']}** títulos ({r['share_of_volume_without_valid_location_pct']}% del volumen) "
                 "no tienen una ubicación válida. Los dos puntos de la embotelladora de Coca-Cola aparecen ~100 km al oeste. "
                 "Abre **Datos** para descargar la lista.",
                 f"Of {r['points']} LOCREPDA points, **{r['misplaced_points']}** lie outside their municipality, and "
                 f"**{r['titles_without_valid_location']}** titles ({r['share_of_volume_without_valid_location_pct']}% of the volume) "
                 "have no valid location. Both points of the Coca-Cola bottler appear about 100 km to the west. "
                 "Open **Data** to download the list."), calls
    if any(w in nq for w in ["surpris", "unexpected", "worse than", "inesperad", "sorpres"]):
        r = call("rank_localities", by="surprise", n=5)
        lines = [f"- **{x['locality']}** ({x['municipality']}): {x['pct_without_piped_water']:.0f}% " + L("sin agua; el modelo esperaba", "without water; the model expected")
                 + f" ~{round(x['pct_without_piped_water'] - x['model_surprise_points'])}%" for x in r["localities"]]
        return L("Localidades con muchas más viviendas sin agua de lo que predice el modelo:\n",
                 "Localities with many more homes without water than the model predicts:\n") + "\n".join(lines), calls
    if any(w in nq for w in ["model", "modelo", "beta", "significant", "radius", "radio", "how sure", "robust"]):
        r = call("model_result")
        return L(f"Con los ajustes de la tesis ({r['localities']} localidades, 2 km), β1 = **{r['beta1']}**: pasar del percentil 25 al 75 "
                 f"de agua concedida cerca se asocia con **{abs(r['effect_25th_to_75th_percentile_points'])} puntos menos** de viviendas sin "
                 f"agua entubada (promedio {r['mean_pct_without_water']}%). p robusto {r['p_robust']}, p espacial {r['p_conley_10km']}: "
                 "constante pero moderado. Es una asociación, no una causa. Abre **Modelo** para probar otros ajustes.",
                 f"With the thesis settings ({r['localities']} localities, 2 km), β1 = **{r['beta1']}**: going from the 25th to the 75th "
                 f"percentile of water granted nearby goes with **{abs(r['effect_25th_to_75th_percentile_points'])} points fewer** homes "
                 f"without piped water (average {r['mean_pct_without_water']}%). Robust p {r['p_robust']}, spatial p {r['p_conley_10km']}: "
                 "consistent but moderate. An association, not a cause. Open **Model** to try other settings."), calls
    if any(w in nq for w in ["municip", "where", "donde", "least", "most", "worst", "peor", "segment", "group", "grupo"]) and not any(
            w in nq for w in ["priorit", "first", "primero"]):
        r = call("municipality_summary", municipality=mun)
        rows = r["municipalities"]
        lines = [f"- **{x['municipality']}**: {x['pct_homes_without_piped_water']}% " + L("de viviendas sin agua entubada; ", "of homes without piped water; ")
                 + f"{x['localities_mostly_without_pipes']} " + L("localidades mayormente sin red", "localities mostly without pipes")
                 + f" ({x['of_which_outside_the_system']} " + L("fuera del sistema", "outside the system") + f", {x['of_which_water_granted_nearby']} "
                 + L("con agua cerca", "with water nearby") + ")" for x in rows[:9]]
        s = r["segments_all_nine"]
        tail = L(f"\n\nEn total, las localidades **fuera del sistema** concentran {s['outside']['share_of_homes_without_piped_water_pct']}% "
                 f"de las viviendas sin agua y las de **agua cerca que no llega** {s['nearby']['share_of_homes_without_piped_water_pct']}%.",
                 f"\n\nOverall, localities **outside the system** hold {s['outside']['share_of_homes_without_piped_water_pct']}% of homes "
                 f"without piped water, and those with **water nearby, not reaching homes** {s['nearby']['share_of_homes_without_piped_water_pct']}%.")
        return "\n".join(lines) + (tail if not mun else ""), calls
    if any(w in nq for w in ["priorit", "first", "primero", "top", "act", "actuar", "where to"]):
        r = call("rank_localities", by="priority", municipality=mun, n=5)
        lines = [f"{i}. **{x['locality']}** ({x['municipality']}, {x['inhabitants']} " + L("hab.", "inhabitants") + f"): "
                 f"{x['pct_without_piped_water']:.0f}% " + L("sin agua entubada", "without piped water") + f", {seg_l[x['segment_key']]}"
                 for i, x in enumerate(r["localities"], 1)]
        return L("Primeras prioridades con los pesos por defecto:\n", "Top priorities with the default weights:\n") + "\n".join(lines) \
            + "\n\n" + L("Abre **Prioridades** para cambiar los pesos.", "Open **Priorities** to change the weights."), calls
    # otherwise: try a locality name
    words = [w for w in nq.split() if len(w) > 3 and w not in {"what", "about", "tell", "locality", "localidad", "dime", "sobre", "como", "esta", "water"}]
    for w in [" ".join(words)] + words:
        if not w:
            continue
        r = call("find_locality", name=w)
        if r.get("found"):
            seg = seg_l.get(r.get("segment_key"), "")
            txt = L(f"**{r['locality']}** ({r['municipality']}): {r['inhabitants']} habitantes; **{r['pct_homes_without_piped_water']}%** de las "
                    f"viviendas sin agua entubada y {r['pct_homes_without_drainage']}% sin drenaje.",
                    f"**{r['locality']}** ({r['municipality']}): {r['inhabitants']} inhabitants; **{r['pct_homes_without_piped_water']}%** of homes "
                    f"without piped water and {r['pct_homes_without_drainage']}% without drainage.")
            if "water_granted_within_2km_m3_per_year" in r:
                txt += " " + L(f"A menos de 2 km se conceden {r['water_granted_within_2km_m3_per_year']:,.0f} m³ al año. Grupo: {seg}. "
                               f"Prioridad n.º {r['priority_rank_of_538']} de 538.",
                               f"Within 2 km, {r['water_granted_within_2km_m3_per_year']:,.0f} m³ a year are granted. Segment: {seg}. "
                               f"Priority rank {r['priority_rank_of_538']} of 538.")
            return txt + "\n\n" + L("Abre **Mapa** para ver su ficha.", "Open **Map** to see its record."), calls
    calls.clear()
    r = call("thesis_facts")
    return L("Puedo responder sobre una localidad (escribe su nombre), los municipios, las prioridades, el modelo, la sequía o los "
             "errores del registro. Por ejemplo: «¿Dónde actuar primero en Chamula?»",
             "I can answer about a locality (type its name), the municipalities, priorities, the model, drought or errors in the "
             "register. For example: \"Where should we act first in Chamula?\""), calls
