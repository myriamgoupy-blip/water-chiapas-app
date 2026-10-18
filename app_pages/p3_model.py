import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import data, engine, fastols, ui
from core.config import MUNS, THESIS

L = ui.L
pts, pkey = data.active_points()
snap = pts is None

ui.page_title(L("¿Más agua concedida, más acceso?", "More water granted, better access?"),
              L("Este es el modelo de la tesis. Cambia cualquier opción y se vuelve a estimar al instante.",
                "This is the thesis model. Change any option and it is re-estimated instantly."))
if snap:
    st.info(L("Sin los puntos de concesión, el modelo usa los valores de la tesis (radio de 2 km). "
              "Carga los puntos en la página Datos para cambiar el radio.",
              "Without the concession points the model uses the thesis values (2 km radius). "
              "Load the points on the Data page to change the radius."))


def badge(p):
    if p < 0.05:
        return ui.chip(f"p = {p:.3f}", "#D7EFE2", "#1D5E3B")
    if p < 0.10:
        return ui.chip(f"p = {p:.3f}", "#FBEFD2", "#7A5A0E")
    return ui.chip(f"p = {p:.3f}", "#E7EDF3", ui.MUTED)


@st.fragment
def playground():
    # ------------------------------------------------------------ controls
    with st.container(key="panel_model"):
        a, b = st.columns([1, 1])
        dv = "dep_water"
        mname = a.pills(L("Modelo", "Model"), ["M1", "M2", "M3"], default="M3", required=True, key="m_model",
                        format_func={"M1": L("Solo intensidad", "Intensity only"),
                                     "M2": L("+ lengua indígena", "+ Indigenous share"),
                                     "M3": L("+ interacción (tesis)", "+ interaction (thesis)")}.get)
        b.markdown('<p class="muted" style="margin-top:1.9rem">' + L(
            "Resultado: % de viviendas sin agua entubada (ni dentro ni en el patio), censo 2020.",
            "Outcome: % of homes without piped water (neither inside nor in the yard), 2020 census.") + '</p>',
            unsafe_allow_html=True)
        c, d, e = st.columns([2, 2, 1.4])
        radius = c.slider(L("Radio alrededor de cada localidad (km)", "Radius around each locality (km)"),
                          0.5, 10.0, 2.0, 0.5, disabled=snap, key="m_radius")
        min_pop = d.select_slider(L("Habitantes mínimos", "Minimum inhabitants"), [0, 50, 100, 250, 500, 1000],
                                  value=100, key="m_minpop",
                                  help=L("La tesis usa localidades de más de 100 habitantes.",
                                         "The thesis uses localities with more than 100 inhabitants."))
        cut = e.pills(L("Correlación espacial", "Spatial correlation"), [5, 10, 20], default=10, required=True,
                      format_func=lambda x: f"{x} km", key="m_cut",
                      help=L("Distancia hasta la que los errores de localidades vecinas pueden estar relacionados (Conley).",
                             "Distance up to which errors of neighbouring localities may be related (Conley)."))
        f, g, h, i = st.columns(4)
        measure = f.toggle(L("Solo concesiones asignadas", "Assigned concessions only"), False, disabled=snap, key="m_nearest",
                           help=L("Cuenta solo las concesiones cuya localidad más cercana es esta.",
                                  "Counts only concessions whose nearest locality is this one."))
        per_capita = g.toggle(L("Por habitante", "Per resident"), True, disabled=snap, key="m_pc")
        add_title = h.toggle(L("Ubicar título de Comitán", "Place Comitán title"), False, disabled=snap, key="m_title",
                             help=L("El título 11CHS156910 (8.1 millones de m³) no tiene coordenadas; esta opción lo ubica en los pozos del mismo comité.",
                                    "Title 11CHS156910 (8.1 million m³) has no coordinates; this places it on the same committee's wells."))
        do_wild = i.toggle(L("Bootstrap por municipio", "Cluster bootstrap"), True, key="m_wild",
                           help=L("La prueba más exigente: remuestrea los 9 municipios 9,999 veces.",
                                  "The strictest test: resamples the 9 municipalities 9,999 times."))
    if snap and min_pop < 100:
        min_pop = 100
    meas = "nearest" if measure else "buffer"

    # ------------------------------------------------------------ estimate
    d, fit, Dm = engine.run_model(pkey, pts, mname, dv, radius, meas, per_capita, add_title, min_pop)
    cse, cp, _ = fit.conley(Dm, cut)
    wild = {}
    if do_wild:
        wild["int_c"] = fit.wild_p(d.MUN.values, "int_c")
        if mname == "M3":
            wild["int_c:ind_c"] = fit.wild_p(d.MUN.values, "int_c:ind_c")
    b1 = fit.params["int_c"]
    ps = [fit.pvalues["int_c"], cp["int_c"]] + ([wild["int_c"]] if wild else [])
    is_thesis = (radius == 2 and meas == "buffer" and per_capita and not add_title and min_pop == 100
                 and dv == "dep_water" and mname == "M3")

    # ------------------------------------------------------------ result
    if max(ps) < 0.05:
        verdict, vcol = L("Sólido en las tres pruebas", "Holds in all three tests"), "#1D5E3B"
    elif min(ps) < 0.05:
        verdict, vcol = L("Moderado: significativo en algunas pruebas", "Moderate: significant in some tests"), "#7A5A0E"
    elif min(ps) < 0.10:
        verdict, vcol = L("Débil: apenas al límite", "Weak: borderline at best"), "#7A5A0E"
    else:
        verdict, vcol = L("No se distingue de cero", "Not distinguishable from zero"), ui.MUTED
    with st.container(key="result_model"):
        r1, r2 = st.columns([2, 3], gap="large", vertical_alignment="center")
        with r1:
            delta = b1 - THESIS["beta1"]
            st.markdown(f'<p class="muted" style="margin:0">{L("Efecto de la intensidad (β1)", "Effect of intensity (β1)")}</p>'
                        f'<div class="big {"water" if b1 < 0 else "homes"}">{b1:+.2f} <span style="font-size:1.1rem">pp</span></div>'
                        f'<p class="muted" style="margin:.2rem 0 0 0">'
                        + (L("Igual que en la tesis", "Same as in the thesis") if abs(delta) < 0.0015
                           else L(f"{delta:+.2f} frente a la tesis ({THESIS['beta1']})", f"{delta:+.2f} vs the thesis ({THESIS['beta1']})"))
                        + f' &nbsp;n = {fit.n}</p>', unsafe_allow_html=True)
        with r2:
            st.markdown(f'<p style="font-weight:700;color:{vcol};font-size:1.1rem;margin:0 0 .4rem 0">{verdict}</p>'
                        + f'<p style="margin:.1rem 0">{L("Errores robustos", "Robust errors")} {badge(ps[0])} &nbsp; '
                        + f'{L("Espacial", "Spatial")} ({cut} km) {badge(ps[1])} &nbsp; '
                        + (f'{L("Bootstrap", "Bootstrap")} {badge(wild["int_c"])}' if wild else "") + '</p>',
                        unsafe_allow_html=True)
        q25, q75 = d.intensity.quantile([.25, .75])
        out = L("sin agua entubada", "without piped water")
        direction = L("menos" if b1 < 0 else "más", "fewer" if b1 < 0 else "more")
        weak = min(ps) >= 0.10
        where = ("a menos de " + format(radius, "g") + " km" if meas == "buffer" else "asignada",
                 "within " + format(radius, "g") + " km" if meas == "buffer" else "assigned to them")
        if weak:
            txt = L(f"Con estos ajustes, tener más agua concesionada {where[0]} no se asocia de forma clara con más o menos "
                    f"viviendas {out} ({b1 * (q75 - q25):+.1f} puntos del percentil 25 al 75 de intensidad).",
                    f"With these settings, more water granted {where[1]} shows no clear link with more or fewer homes "
                    f"{out} ({b1 * (q75 - q25):+.1f} points from the 25th to the 75th percentile of intensity).")
        else:
            txt = L(f"Las localidades con más agua concesionada {where[0]} tienen <b>{direction}</b> viviendas {out}: "
                    f"del percentil 25 al 75 de intensidad, {b1 * (q75 - q25):+.1f} puntos porcentuales (promedio {d[dv].mean():.0f}%).",
                    f"Localities with more water granted {where[1]} have <b>{direction}</b> homes {out}: from the 25th "
                    f"to the 75th percentile of intensity, {b1 * (q75 - q25):+.1f} percentage points (average {d[dv].mean():.0f}%).")
        if mname == "M3":
            p3 = min(fit.pvalues["int_c:ind_c"], cp["int_c:ind_c"])
            txt += " " + (L("La relación cambia con la proporción indígena.", "The relationship changes with the Indigenous share.")
                          if p3 < 0.05 else
                          L("No cambia con la proporción de hablantes de lengua indígena.",
                            "It does not change with the share of Indigenous-language speakers."))
        st.markdown(f'<p class="lead" style="margin-top:.7rem">{txt}</p>', unsafe_allow_html=True)
        if is_thesis:
            st.markdown('<p class="muted" style="margin:0">' + L(
                "Estos son los ajustes de la tesis (cuadro 6.6). Asociación, no causa.",
                "These are the thesis settings (Table 6.6). Association, not cause.") + '</p>', unsafe_allow_html=True)

    # ------------------------------------------------------------ the radius curve
    if not snap:
        st.markdown(f"#### {L('¿Es 2 km una elección afortunada?', 'Is 2 km a lucky choice?')}")
        sw = engine.radius_sweep(pkey, pts, mname, dv, "buffer", per_capita, add_title, min_pop, cut)
        base = alt.Chart(sw).encode(x=alt.X("radius:Q", title=L("Radio (km)", "Radius (km)"),
                                             scale=alt.Scale(domain=[0.5, 10], nice=False)))
        band = base.mark_area(opacity=0.22, color=ui.WATER, interpolate="monotone").encode(
            y=alt.Y("low:Q", title=L("β1 e intervalo de 95%", "β1 and 95% interval")), y2="high:Q")
        line = base.mark_line(color=ui.WATER, strokeWidth=3, interpolate="monotone").encode(y="beta1:Q")
        dots = base.mark_circle(size=55, color=ui.WATER, stroke="white", strokeWidth=1.5).encode(
            y="beta1:Q", tooltip=[alt.Tooltip("radius:Q", title="km"), alt.Tooltip("beta1:Q", format=".2f", title="β1"),
                                  alt.Tooltip("p:Q", format=".3f", title="p (Conley)")])
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=ui.MUTED, strokeDash=[3, 3]).encode(y="y:Q")
        cur = sw[np.isclose(sw.radius, radius)]
        mark = alt.Chart(cur).mark_point(size=260, shape="circle", filled=False, color=ui.HOMES, strokeWidth=3).encode(
            x="radius:Q", y="beta1:Q")
        ui.chart(band + zero + line + dots + mark, height=280)
        st.markdown('<p class="muted">' + L(
            f"Cada punto vuelve a estimar el modelo con otro radio; la banda es el intervalo con errores espaciales ({cut} km). "
            "El círculo magenta es tu radio actual. Por debajo de cero: más agua concedida, menos viviendas sin agua.",
            f"Each point re-estimates the model with another radius; the band is the interval with spatial errors ({cut} km). "
            "The magenta circle is your current radius. Below zero: more water granted, fewer homes without water.")
            + '</p>', unsafe_allow_html=True)

    # ------------------------------------------------------------ two views of the data
    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.markdown(f"#### {L('Los datos, sin controles', 'The raw data')}")
        bins = d.assign(bin=pd.qcut(d.intensity.rank(method="first"), 10, labels=False))
        bs = bins.groupby("bin").agg(intensity=("intensity", "mean"), y=(dv, "mean"), n=(dv, "size")).reset_index()
        pts_ch = alt.Chart(d).mark_circle(size=22, opacity=0.28, color=ui.HOMES).encode(
            x=alt.X("intensity:Q", title=L("Intensidad: log(1 + m³ por habitante)", "Intensity: log(1 + m³ per resident)")),
            y=alt.Y(f"{dv}:Q", title=L("% de viviendas sin agua", "% of homes without water"), scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("NOM_LOC:N", title=""), alt.Tooltip(f"{dv}:Q", format=".0f", title="%")])
        area = alt.Chart(bs).mark_area(color=ui.gradient(ui.WATER), interpolate="monotone").encode(x="intensity:Q", y="y:Q")
        ln = alt.Chart(bs).mark_line(color=ui.WATER, strokeWidth=3, interpolate="monotone",
                                     point=alt.OverlayMarkDef(size=70, color=ui.WATER, stroke="white", strokeWidth=1.5)).encode(
            x="intensity:Q", y="y:Q", tooltip=[alt.Tooltip("y:Q", format=".1f", title=L("promedio %", "mean %")), "n"])
        ui.chart(pts_ch + area + ln, height=300)
        st.markdown('<p class="muted">' + L("Puntos: cada localidad. Línea: promedio por décimo de intensidad.",
                                            "Dots: each locality. Line: average by tenth of intensity.") + '</p>', unsafe_allow_html=True)
    with g2:
        st.markdown(f"#### {L('¿Cambia en localidades indígenas?', 'Does it differ in Indigenous localities?')}")
        if mname == "M3":
            me = fastols.marginal_effects(fit, d.indig.mean())
            base = alt.Chart(me).encode(x=alt.X("indig:Q", title=L("Hablantes de lengua indígena (%)", "Indigenous-language speakers (%)")))
            band = base.mark_area(opacity=0.22, color=ui.WATER).encode(
                y=alt.Y("low:Q", title=L("Efecto de +1 de intensidad (pp)", "Effect of +1 intensity (pp)")), y2="high:Q")
            line = base.mark_line(color=ui.WATER, strokeWidth=3).encode(
                y="effect:Q", tooltip=[alt.Tooltip("indig:Q", title="%"), alt.Tooltip("effect:Q", format=".2f", title="pp")])
            zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=ui.MUTED, strokeDash=[3, 3]).encode(y="y:Q")
            rug = alt.Chart(d.assign(_y=float(me.low.min()))).mark_tick(color=ui.HOMES, opacity=0.35, thickness=1.2, size=12).encode(
                x="indig:Q", y="_y:Q")
            ui.chart(band + zero + line + rug, height=300)
            st.markdown('<p class="muted">' + L(
                "Línea plana: el efecto es el mismo en todas. Marcas magenta: dónde están las localidades (la mayoría por encima de 80%).",
                "A flat line: the effect is the same everywhere. Magenta ticks: where the localities are (most above 80%).")
                + '</p>', unsafe_allow_html=True)
        else:
            st.markdown(L("Elige el modelo **+ interacción** para ver esta gráfica.", "Choose the **+ interaction** model to see this chart."))

    # ------------------------------------------------------------ details
    with st.expander(L("Tabla completa de coeficientes", "Full coefficient table")):
        names = {"int_c": L("Intensidad (β1)", "Intensity (β1)"), "ind_c": L("Lengua indígena (β2)", "Indigenous share (β2)"),
                 "int_c:ind_c": L("Intensidad × lengua indígena (β3)", "Intensity × Indigenous share (β3)"),
                 "log_pop": L("Log población", "Log population"), "school": L("Escolaridad", "Schooling")}
        rows = [p for p in names if p in fit.params]
        tab = pd.DataFrame({
            L("Coeficiente", "Coefficient"): [names[p] for p in rows],
            L("Estimación", "Estimate"): [f"{fit.params[p]:.3f}" for p in rows],
            L("Error robusto", "Robust SE"): [f"{fit.bse[p]:.3f}" for p in rows],
            L("p robusto", "p robust"): [f"{fit.pvalues[p]:.3f}" for p in rows],
            f"p Conley {cut} km": [f"{cp[p]:.3f}" for p in rows],
            "p bootstrap": [f"{wild[p]:.3f}" if p in wild else "" for p in rows],
        })
        st.dataframe(tab, hide_index=True)
        st.caption(L(f"MCO con efectos fijos por municipio; n = {fit.n}; R² = {fit.rsquared:.3f}.",
                     f"OLS with municipality fixed effects; n = {fit.n}; R² = {fit.rsquared:.3f}."))
    with st.expander(L("Diagnósticos", "Diagnostics")):
        mi = {c: fastols.morans_i(Dm, fit.e, c) for c in [2, 5, 10]}
        st.markdown(L("I de Moran de los residuos: ", "Moran's I of the residuals: ")
                    + ", ".join(f"{v:.2f} ({c} km)" for c, v in mi.items()) + ". "
                    + L("Valores positivos indican que localidades vecinas comparten carencias no explicadas; por eso importan las pruebas espacial y bootstrap.",
                        "Positive values mean neighbouring localities share unexplained deprivation, which is why the spatial and bootstrap tests matter."))
        loo = []
        for m in sorted(d.MUN.unique()):
            ff = fastols.Fit(fastols.centre(d[d.MUN != m]), mname, dv)
            loo.append({L("Sin el municipio", "Without"): MUNS[m], "n": ff.n, "β1": f'{ff.params["int_c"]:.3f}',
                        L("p robusto", "p robust"): f'{ff.pvalues["int_c"]:.3f}'})
        st.dataframe(pd.DataFrame(loo), hide_index=True)
        st.download_button(L("Descargar los datos del modelo (CSV)", "Download the model data (CSV)"),
                           d.to_csv(index=False), "model_dataset_app.csv", "text/csv")


playground()
