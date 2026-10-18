import streamlit as st

from core import assistant, ui

L = ui.L
online = bool(assistant.api_key())

ui.page_title(L("Pregunta a los datos", "Ask the data"),
              L("Escribe una pregunta en tus palabras. El asistente elige qué análisis de la app ejecutar y responde "
                "con sus cifras: nunca inventa números.",
                "Ask a question in your own words. The assistant picks which of the app's analyses to run and answers "
                "with their figures: it never makes numbers up."),
              kicker="✦ " + L("Asistente de IA", "AI assistant"))

status = (ui.live_pill(L(f"Claude conectado · {assistant.model_name()}", f"Claude connected · {assistant.model_name()}")) if online else
          '<span class="pill">◌ ' + L("Modo sin conexión: análisis integrados", "Offline mode: built-in analyses") + '</span>')
st.markdown(status, unsafe_allow_html=True)
ui.guide([
    (L("Pregunta", "Ask"), L("Una localidad, un municipio, dónde actuar, el modelo, la sequía o el registro.",
                             "A locality, a municipality, where to act, the model, drought or the register.")),
    (L("El asistente consulta", "The assistant looks it up"),
     L("Ejecuta las mismas funciones que las páginas de la app y muestra cuáles usó.",
       "It runs the same functions as the app's pages and shows which ones it used.")),
    (L("Comprueba", "Check"), L("Cada respuesta indica qué página abrir para verlo en el mapa o en el modelo.",
                                "Each answer says which page to open to see it on the map or in the model.")),
])

SUGGEST = [
    L("¿Dónde actuar primero en Chamula?", "Where should we act first in Chamula?"),
    L("Háblame de Yalentay", "Tell me about Yalentay"),
    L("¿Qué municipios tienen menos agua entubada?", "Which municipalities have the least piped water?"),
    L("¿Qué tan sólido es el modelo?", "How sure is the model?"),
    L("¿Qué localidades sorprenden al modelo?", "Which localities surprise the model?"),
    L("¿Qué errores tiene el registro de concesiones?", "What is wrong with the concession register?"),
]

st.session_state.setdefault("chat", [])
pick = st.pills(L("Prueba con", "Try"), SUGGEST, key=f"suggest_{len(st.session_state.chat)}", label_visibility="collapsed")
typed = st.chat_input(L("Pregunta sobre el agua en los nueve municipios…", "Ask about water in the nine municipalities…"))
question = typed or pick

TOOL_LABEL = {
    "find_locality": L("Buscando la localidad", "Looking up the locality"),
    "rank_localities": L("Ordenando localidades", "Ranking localities"),
    "municipality_summary": L("Resumiendo municipios", "Summarising municipalities"),
    "model_result": L("Estimando el modelo", "Estimating the model"),
    "drought_status": L("Leyendo el Monitor de Sequía", "Reading the Drought Monitor"),
    "register_issues": L("Revisando el registro", "Checking the register"),
    "thesis_facts": L("Consultando los resultados de la tesis", "Reading the thesis results"),
}


def show_calls(calls):
    if calls:
        st.markdown('<p class="muted" style="margin:.3rem 0 0 0">✦ ' + L("Análisis usados: ", "Analyses used: ")
                    + " · ".join(dict.fromkeys(TOOL_LABEL.get(n, n) for n, _ in calls)) + "</p>", unsafe_allow_html=True)


if not st.session_state.chat:
    with st.chat_message("assistant", avatar="💧"):
        st.markdown(L("Hola. Puedo buscar cualquier localidad, comparar los nueve municipios, decir dónde actuar primero, "
                      "volver a estimar el modelo con otro radio, leer la sequía de hoy o mostrar los errores del registro. "
                      "Elige una pregunta arriba o escribe la tuya.",
                      "Hi. I can look up any locality, compare the nine municipalities, say where to act first, re-estimate "
                      "the model with another radius, read today's drought or show the errors in the register. Pick a "
                      "question above or type your own."))

for m in st.session_state.chat:
    with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "💧"):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            show_calls(m.get("calls"))

if question:
    st.session_state.chat.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="💧"):
        calls = []
        if online:
            with st.status(L("Pensando…", "Thinking…"), expanded=False) as box:
                try:
                    hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat[-8:]]
                    answer, calls = assistant.ask_claude(hist, on_tool=lambda n, a: box.write(f"✦ {TOOL_LABEL.get(n, n)} {a or ''}"))
                    box.update(label=L("Listo", "Done"), state="complete")
                except Exception as e:  # noqa: BLE001
                    box.update(label=L("Claude no respondió: respuesta sin conexión", "Claude did not answer: offline answer"), state="error")
                    answer, calls = assistant.offline_answer(question)
        else:
            answer, calls = assistant.offline_answer(question)
        st.markdown(answer)
        show_calls(calls)
    st.session_state.chat.append({"role": "assistant", "content": answer, "calls": calls})
    st.rerun()

if st.session_state.chat:
    if st.button(L("Nueva conversación", "New conversation"), icon=":material/refresh:"):
        st.session_state.chat = []
        st.rerun()

with st.expander(L("Cómo funciona", "How it works")):
    st.markdown(L(
        "El asistente tiene acceso a siete funciones de la app: buscar una localidad, ordenar localidades, resumir los "
        "municipios, estimar el modelo, leer el Monitor de Sequía, revisar el registro y los resultados de la tesis. "
        "**Con Claude** (Anthropic), un modelo de lenguaje decide qué funciones llamar y redacta la respuesta a partir de lo que "
        "devuelven. **Sin conexión**, la app reconoce las preguntas frecuentes y responde con las mismas funciones. "
        "En ambos casos, cada cifra sale de los datos públicos de la app, no del modelo de lenguaje.",
        "The assistant can use seven of the app's functions: look up a locality, rank localities, summarise the "
        "municipalities, estimate the model, read the Drought Monitor, check the register, and the thesis results. "
        "**With Claude** (Anthropic), a language model decides which functions to call and writes the answer from what they "
        "return. **Offline**, the app recognises common questions and answers them with the same functions. Either way, every "
        "figure comes from the app's public data, not from the language model."))
    if not online:
        st.caption(L("Para activar Claude: en Streamlit Cloud, Settings → Secrets, añade ANTHROPIC_API_KEY = \"…\".",
                     "To switch Claude on: in Streamlit Cloud, Settings → Secrets, add ANTHROPIC_API_KEY = \"…\"."))
