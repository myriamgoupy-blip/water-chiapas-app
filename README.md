# Ojo de Agua: interactive companion to *When Water Flows to the Few*

A Streamlit app that goes with the MSc thesis *When Water Flows to the Few* (ESCP Business School, 2026). It covers water concessions, household water access and drought in the nine municipalities around the San Cristóbal de las Casas aquifer (Chiapas, Mexico).

The app opens in Spanish, with English one click away (ES / EN at the top). To open it in English by default, change `default="ES"` to `default="EN"` in `app.py`.

The app has a light and a dark theme. It follows the visitor's system setting; anyone can switch with the three-dot menu at the top right (System / Light / Dark). Both themes are set in `.streamlit/config.toml`.

| Page | What the user can do |
|---|---|
| Inicio / Home | Who holds the water, today's drought, the model's findings and the two groups of localities to act on |
| Pregunta / Ask | Ask questions in plain language. The assistant runs the app's own analyses and answers with their figures (Claude with an API key; built-in answers without one) |
| Mapa / Map | 3D map of concessions and localities; open any locality's record, its group, what the model expected and the most similar localities |
| Modelo / Model | Re-estimate the thesis model instantly, check the radius curve and see where the model is most surprised (residuals) |
| Prioridades / Priorities | Set six weights, rank the 538 localities, see each locality's group and test the stability of the top 20 |
| Sequía y lluvia / Drought & rain | Official drought status per municipality, its history since 2003, rain against normal and the 7-day forecast |
| Datos / Data | Sources, definitions, limits and the list of register entries to review |

The app always uses the latest data: it reads LOCREPDA from CONAGUA once a day and the Drought Monitor every 12 hours, and falls back on the copies in `data/` when a source does not answer.

## Switching on the AI assistant (optional)

The Ask page works without any key (built-in answers to common questions). To let Claude answer any question:

1. Create an API key at console.anthropic.com (pay as you go; a question costs a few cents).
2. In Streamlit Community Cloud, open the app → **Settings** → **Secrets**, and paste:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ANTHROPIC_MODEL = "claude-sonnet-5"
   ```
3. Save. The Ask page then shows "Claude connected".

Claude never produces the numbers itself: it chooses which of the app's functions to call (look up a locality, rank localities, summarise municipalities, re-estimate the model, read the drought, check the register) and writes the answer from what they return.

The model is computed with NumPy in milliseconds, so every control answers instantly. `tests/check_engine.py` shows that it gives exactly the thesis numbers (statsmodels, Notebook 4).

---

## 1. The bundled data

`data/locrepda_points_qc.csv` is the LOCREPDA copy of 28 September 2026 used in the thesis. The app uses it only when CONAGUA's server does not answer; otherwise it reads the register live. With the thesis data, the Model page's default settings give exactly the thesis result (β1 = −2.195, n = 538).

Optional: run `python scripts/build_rain_normals.py` once and commit `data/rain_normals_1991_2020.csv`. The rain comparison then loads instantly instead of asking for a one-off download.

## 2. Publish it free on Streamlit Community Cloud (about 10 minutes)

1. Create a free account at github.com.
2. Click **New repository**. Name it, for example, `water-chiapas-app`, set it to **Public**, and create it.
3. Click **uploading an existing file**. Drag in everything inside this folder (`app.py`, `requirements.txt`, `README.md`, and the folders `core`, `app_pages`, `data`, `scripts`, `static`, `tests`, `.streamlit`). Then click **Commit changes**.
   - The `.streamlit` folder is hidden on a Mac. Press Cmd + Shift + . in Finder to show it.
4. Go to **share.streamlit.io** and sign in with GitHub.
5. Click **Create app**, then **Deploy a public app from GitHub**. Pick the repository, branch `main`, main file `app.py`, and choose a short URL such as `water-chiapas.streamlit.app`.
6. Click **Deploy**. The first build takes 2–4 minutes.
7. Check the result:
   - Open **Model**. With the default settings it should say *Same as in the thesis* (if CONAGUA has not changed the register).
   - Open **Drought and rain**. If it offers to build the rain averages, click the button once.

Put the app's URL in the thesis (Chapter 7 and the appendix) and on the defence slides.

If the app has had no visitors for a while, it goes to sleep, and the first visitor clicks "Yes, get this app back up" to wake it. Open it yourself the morning of the defence.

## 3. Run it on a computer

```
pip install -r requirements.txt
streamlit run app.py
```

## Data sources and versions

| Source | Use | Version bundled | Live? |
|---|---|---|---|
| REPDA, Public Register of Water Rights (CONAGUA) | Titles, holders, uses, volumes | Sept 2026 extracts for the 9 municipalities | No (REPDA has no open API) |
| LOCREPDA, CONAGUA ArcGIS server | Coordinates of concession points | Thesis snapshot, 28 Sept 2026 (`data/locrepda_points_qc.csv`) | Yes: read daily, bundled copy as fallback |
| ITER 2020, INEGI census | Household water, drainage, language, schooling, locality coordinates | Chiapas file trimmed to the 9 municipalities | No (census) |
| Drought Monitor, CONAGUA–SMN (`MunicipiosSequia.xlsx`) | Drought category every 15 days since 2003 | Copy up to 15 Sept 2026, from a public GitHub mirror of the SMN file | Yes: tries the official SMN file every 12 hours, bundled copy as fallback |
| Open-Meteo (ERA5 reanalysis and forecast models) | Rain against the 1991–2020 normal, soil moisture, 7-day forecast | None | Yes |

If the official SMN site is down on the day of the defence, the app shows the bundled copy and says so. To refresh that copy, replace `data/drought_monitor_snapshot.csv` with the latest `MunicipiosSequia.xlsx` values.

## How the numbers are built

The code in `core/` repeats the thesis notebooks line for line:

- `geo.py`: location check, REPDA–LOCREPDA matching on the number after "CHS", and intensity = log(1 + m³ per resident within the radius);
- `fastols.py` and `engine.py`: OLS with municipality fixed effects in NumPy; HC1, Conley and restricted wild cluster bootstrap (Webb weights); distances precomputed once so the pages answer instantly;
- `index.py`: priority index and rank-stability check;
- `ui.py` and `maps.py`: colours (for both light and dark themes), type and the 3D map layers. Fonts (Bricolage Grotesque, OFL licence) are served from `static/fonts`.
- `live.py`: clients for LOCREPDA, the Drought Monitor and Open-Meteo. Each one fails gracefully: when a source is down, the page explains it and falls back to the bundled data.

All model results are associations, not causal effects. Census figures date from 2020, so households may have gained or lost access since.
