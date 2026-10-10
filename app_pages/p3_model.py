import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, model, ui
from core.config import BLUE, MUNS, ORANGE, THESIS

ui.header("Test it yourself", "Model playground",
          "The thesis asks whether localities with more water concessioned around them have better or worse "
          "access to piped water, and whether that differs in more Indigenous localities. Change any choice "
          "below and the model re-runs on the spot.")
pts, src = ui.sidebar_status()
snap = pts is None
if snap:
    st.info("Concession points are not loaded, so the playground uses the thesis intensity values (2 km, per "
            "resident). Radius and measure choices unlock once the points are loaded on the *Data* page.")

# ---------------------------------------------------------------- choices
with st.container(border=True):
    a, b, c, d_ = st.columns(4)
    with a:
        mname = st.radio("Model", ["M1", "M2", "M3"], index=2, horizontal=True,
                         help="M1: intensity only. M2: + Indigenous share. M3: + their interaction (the thesis model).")
        dv = st.radio("Outcome", ["dep_water", "dep_water_lot"], horizontal=False,
                      format_func={"dep_water": "No piped water inside the dwelling",
                                   "dep_water_lot": "No piped water even to the yard"}.get)
    with b:
        radius = st.select_slider("Radius (km)", [0.5, 1, 1.5, 2, 3, 4, 5, 7.5, 10], value=2, disabled=snap)
        measure = st.radio("Count concessions", ["buffer", "nearest"], disabled=snap,
                           format_func={"buffer": "Within the radius", "nearest": "Only those assigned to the locality"}.get)
    with c:
        min_pop = st.select_slider("Minimum inhabitants", [0, 50, 100, 250, 500, 1000], value=100,
                                   help="The thesis keeps localities with more than 100 inhabitants.")
        per_capita = st.toggle("Per resident", True, disabled=snap, help="Off: total volume, ignoring population.")
        add_title = st.toggle("Add Comitán title", False, disabled=snap,
                              help="Title 11CHS156910 (8.1 million m³/yr) has no coordinates; this places it on the "
                                   "wells of the same water committee's other title.")
    with d_:
        conley_cut = st.select_slider("Spatial correlation distance (km)", [5, 10, 20], value=10,
                                      help="Conley standard errors let errors be correlated between localities closer than this.")
        do_wild = st.toggle("Wild bootstrap", False,
                            help="The most conservative test: nine municipalities as clusters, 999 resamples.")

if snap and min_pop < 100:
    st.warning("Without the concession points only the thesis sample (more than 100 inhabitants) is available.")
    min_pop = 100

loc = data.with_intensity(pts, radius, measure, per_capita, add_title)
d = model.centre(data.sample(loc, dv, min_pop))
if len(d) < 30:
    st.error("Too few localities for this choice.")
    st.stop()
res = model.fit(d, mname, dv)
cse, cp, cV = model.conley(d, res, conley_cut, mname, dv)
wild = {}
if do_wild:
    with st.spinner("Resampling municipalities…"):
        wild["int_c"] = model.wild_cluster_p(d, "int_c", mname, dv, B=999)
        if mname == "M3":
            wild["int_c:ind_c"] = model.wild_cluster_p(d, "int_c:ind_c", mname, dv, B=999)

is_thesis = radius == 2 and measure == "buffer" and per_capita and not add_title \
    and min_pop == 100 and dv == "dep_water" and mname == "M3"
if is_thesis:
    ok = abs(res.params["int_c"] - THESIS["beta1"]) < 0.0015 and len(d) == THESIS["n"]
    st.success(f"These are the thesis settings (Table 6.6). β1 = {res.params['int_c']:.3f}, n = {len(d)}"
               + (" — identical to the thesis." if ok else
                  f" — differs from the thesis value ({THESIS['beta1']}) because the concession points differ ({src})."))

# ---------------------------------------------------------------- headline
b1, p_r, p_c = res.params["int_c"], res.pvalues["int_c"], cp["int_c"]
q25, q75 = d.intensity.quantile([.25, .75])
iqr_eff = b1 * (q75 - q25)
k1, k2, k3, k4 = st.columns(4)
k1.metric("β1: concession intensity", f"{b1:+.2f} pp", help="Change in % of dwellings lacking water per +1 intensity "
          "(about 2.7× more water per resident nearby), at an average Indigenous share.")
k2.metric("p, robust (HC1)", f"{p_r:.3f}")
k3.metric(f"p, spatial (Conley {conley_cut} km)", f"{p_c:.3f}")
k4.metric("p, wild cluster bootstrap", f"{wild['int_c']:.3f}" if "int_c" in wild else "off")

ps = [p_r, p_c] + ([wild["int_c"]] if "int_c" in wild else [])
if max(ps) < 0.05:
    strength = "holds under every test shown"
elif min(ps) < 0.05 and max(ps) < 0.2:
    strength = "is significant under some tests but not all, so treat it as moderately supported"
elif min(ps) < 0.1:
    strength = "is weak: at best borderline"
else:
    strength = "is not distinguishable from zero"
direction = ("fewer" if b1 < 0 else "more")
outcome_txt = "without piped water inside" if dv == "dep_water" else "without piped water even to the yard"
reading = (f"**Plain reading.** Among these {len(d)} localities, those with more water concessioned "
           f"{'within ' + format(radius, 'g') + ' km' if measure == 'buffer' else 'assigned to them'} have **{direction}** dwellings "
           f"{outcome_txt}: going from the 25th to the 75th percentile of intensity goes with {iqr_eff:+.1f} percentage points "
           f"(average: {d[dv].mean():.0f}%). The association {strength}.")
if mname == "M3":
    b3, p3 = res.params["int_c:ind_c"], res.pvalues["int_c:ind_c"]
    reading += (f" The interaction (β3 = {b3:+.4f}, robust p = {p3:.2f}, Conley p = {cp['int_c:ind_c']:.2f}) "
                + ("suggests the association changes with the Indigenous share." if min(p3, cp['int_c:ind_c']) < 0.05 else
                   "shows no sign that the association differs between more and less Indigenous localities."))
reading += " This is an association between registered water rights and household access, not a causal effect."
st.markdown(reading)

# ---------------------------------------------------------------- coefficient table
rows = [p for p in ["int_c", "ind_c", "int_c:ind_c", "log_pop", "school"] if p in res.params]
tab = pd.DataFrame({
    "Coefficient": [model.LABELS[p] for p in rows],
    "Estimate": [res.params[p] for p in rows],
    "Robust SE": [res.bse[p] for p in rows],
    "p robust": [res.pvalues[p] for p in rows],
    f"p Conley {conley_cut} km": [cp[p] for p in rows],
})
if wild:
    tab["p wild bootstrap"] = [wild.get(p, np.nan) for p in rows]
st.dataframe(tab, hide_index=True, use_container_width=True,
             column_config={c: st.column_config.NumberColumn(format="%.3f") for c in tab.columns[1:]})
st.caption(f"OLS with municipality fixed effects; n = {int(res.nobs)}; R² = {res.rsquared:.3f}. "
           "Intensity and Indigenous share are centred on their means. Controls: log population, years of schooling.")

# ---------------------------------------------------------------- charts
g1, g2 = st.columns(2)
with g1:
    st.markdown("**What the raw data look like**")
    bins = d.assign(bin=pd.qcut(d.intensity.rank(method="first"), 10, labels=False))
    bs = bins.groupby("bin").agg(intensity=("intensity", "mean"), y=(dv, "mean"), n=(dv, "size")).reset_index()
    pts_ch = alt.Chart(d).mark_circle(size=14, opacity=0.18, color="#8a8983").encode(
        x=alt.X("intensity:Q", title="Concession intensity, log(1 + m³ per resident)"),
        y=alt.Y(f"{dv}:Q", title="% dwellings lacking piped water", scale=alt.Scale(domain=[0, 100])),
        tooltip=["NOM_LOC", alt.Tooltip(f"{dv}:Q", format=".0f"), alt.Tooltip("intensity:Q", format=".2f")])
    bin_ch = alt.Chart(bs).mark_line(point=alt.OverlayMarkDef(size=60), color=BLUE, strokeWidth=2.5).encode(
        x="intensity:Q", y="y:Q", tooltip=[alt.Tooltip("y:Q", title="mean %", format=".1f"), "n"])
    st.altair_chart((pts_ch + bin_ch).properties(height=320), use_container_width=True)
    st.caption("Grey: each locality. Blue: average within each tenth of intensity (no controls).")
with g2:
    if mname == "M3":
        st.markdown("**Does it differ with the Indigenous share?**")
        me = model.marginal_effects(res, d.indig.mean())
        band = alt.Chart(me).mark_area(opacity=0.18, color=BLUE).encode(
            x=alt.X("indig:Q", title="Indigenous-language speakers (% aged 3+)"), y=alt.Y("low:Q", title="Effect of +1 intensity (pp)"), y2="high:Q")
        line = alt.Chart(me).mark_line(color=BLUE, strokeWidth=2.5).encode(x="indig:Q", y="effect:Q",
            tooltip=[alt.Tooltip("indig:Q", title="Indigenous %"), alt.Tooltip("effect:Q", format=".2f"),
                     alt.Tooltip("low:Q", format=".2f"), alt.Tooltip("high:Q", format=".2f")])
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#8a8983").encode(y="y:Q")
        rug = alt.Chart(d.assign(_y=float(me.low.min()))).mark_tick(color="#52514e", opacity=0.35, thickness=1, size=10).encode(
            x="indig:Q", y="_y:Q")
        st.altair_chart((band + line + zero + rug).properties(height=320), use_container_width=True)
        st.caption("Below zero: more concessioned water nearby goes with fewer dwellings lacking water. "
                   "Band: 95% interval (robust errors). Ticks: where the localities are; few are below 80%.")
    else:
        st.markdown("**Switch to M3** to see whether the association changes with the Indigenous share.")

if not snap:
    st.markdown("**Is 2 km a lucky choice? β1 at every radius**")

    @st.cache_data(show_spinner="Re-estimating at each radius…")
    def sweep(pts, measure, per_capita, add_title, min_pop, dv, mname, cut):
        out = []
        for r in [0.5, 1, 1.5, 2, 3, 4, 5, 7.5, 10]:
            dd = model.centre(data.sample(data.with_intensity(pts, r, "buffer", per_capita, add_title), dv, min_pop))
            rr = model.fit(dd, mname, dv)
            se, p, _ = model.conley(dd, rr, cut, mname, dv)
            out.append({"radius": r, "beta1": rr.params["int_c"], "low": rr.params["int_c"] - 1.96 * se["int_c"],
                        "high": rr.params["int_c"] + 1.96 * se["int_c"], "p": p["int_c"]})
        return pd.DataFrame(out)

    sw = sweep(pts, measure, per_capita, add_title, min_pop, dv, mname, conley_cut)
    base = alt.Chart(sw).encode(x=alt.X("radius:Q", title="Radius (km)", scale=alt.Scale(type="log", domain=[0.4, 12]),
                                         axis=alt.Axis(values=[0.5, 1, 2, 5, 10])))
    ch = (base.mark_rule(color=BLUE, strokeWidth=2).encode(y=alt.Y("low:Q", title="β1 with 95% interval (Conley)"), y2="high:Q")
          + base.mark_circle(size=80, color=BLUE).encode(y="beta1:Q", tooltip=["radius", alt.Tooltip("beta1:Q", format=".2f"),
                                                                                    alt.Tooltip("p:Q", format=".3f")])
          + alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#8a8983").encode(y="y:Q")
          + alt.Chart(pd.DataFrame({"x": [radius]})).mark_rule(color=ORANGE, strokeDash=[4, 3]).encode(x="x:Q"))
    st.altair_chart(ch.properties(height=260), use_container_width=True)
    st.caption(f"Each point re-estimates {mname} with concessions counted within that radius. Orange line: your current radius. "
               f"Intervals use Conley errors at {conley_cut} km.")

# ---------------------------------------------------------------- diagnostics
with st.expander("Diagnostics: spatial correlation and leaving out one municipality at a time"):
    mi = {c: model.morans_i(d, res, c) for c in [2, 5, 10]}
    st.markdown("Moran's I of the residuals (0 = no spatial pattern): " +
                ", ".join(f"{v:.2f} within {c} km" for c, v in mi.items()) +
                ". Positive values mean neighbouring localities share unexplained deprivation, which is why the "
                "Conley and bootstrap p-values matter more than the robust ones.")
    loo = []
    for m in sorted(d.MUN.unique()):
        rr = model.fit(model.centre(d[d.MUN != m]), mname, dv)
        loo.append({"Municipality left out": MUNS[m], "n": int(rr.nobs), "β1": rr.params["int_c"], "p robust": rr.pvalues["int_c"]})
    st.dataframe(pd.DataFrame(loo), hide_index=True, use_container_width=True,
                 column_config={"β1": st.column_config.NumberColumn(format="%.3f"),
                                "p robust": st.column_config.NumberColumn(format="%.3f")})
    st.download_button("Download the model dataset (CSV)", d.drop(columns=[c for c in d.columns if c.startswith("_")]).to_csv(index=False),
                       "model_dataset_app.csv", "text/csv")
