# Ojo de Agua: interactive companion to *When Water Flows to the Few*

A Streamlit app that goes with the MSc thesis *When Water Flows to the Few* (ESCP Business School, 2026). It covers water concessions, household water access and drought in the nine municipalities around the San Cristóbal de las Casas aquifer (Chiapas, Mexico).

The app opens in Spanish, with English one click away (ES / EN at the top). To open it in English by default, change `default="ES"` to `default="EN"` in `app.py`.

| Page | What the user can do |
|---|---|
| Inicio / Home | See who holds the water, the drought status today, and the thesis findings in three sentences |
| Mapa / Map | Explore a 3D map: blue columns are concessions (height = volume), magenta circles are localities (deeper = more homes without piped water). Tap any locality to open its card |
| Modelo / Model | Re-estimate the thesis model instantly with another radius, sample, outcome or test, and see how β1 changes across every radius from 0.5 to 10 km |
| Prioridades / Priorities | Set six weights, rank the localities on a 3D map, and test how stable the top 20 is under 500 random weightings |
| Sequía y lluvia / Drought & rain | Check the official drought status per municipality, its history since 2003, rain against the 1991–2020 normal, soil moisture and the 7-day forecast |
| Datos / Data | See the sources and definitions, re-query CONAGUA's concession register, and compare it with the thesis snapshot |

The model is computed with NumPy in milliseconds, so every control answers instantly. `tests/check_engine.py` shows that it gives exactly the thesis numbers (statsmodels, Notebook 4).

---|---|
| Overview | See the headline numbers, the drought status today and the thesis finding in one paragraph |
| Map and locality card | Click any of the 985 census localities to see its households, the concessions within a chosen radius and who holds them |
| Model playground | Re-run the thesis model with another radius, sample, outcome or error type, and check whether the result holds |
| Priority index | Set weights for six components, rank the localities, and test how stable the ranking is under 500 random weightings |
| Drought and rain (live) | View CONAGUA's municipal drought monitor since 2003, rain against the 1991–2020 normal, soil moisture and the 7-day forecast |
| Data, methods and refresh | Check the sources and definitions, pull the current LOCREPDA register from CONAGUA, and compare it with the thesis snapshot |

---

## 1. Before publishing: add the thesis points file

Copy **`locrepda_points_qc.csv`** into the `data/` folder. The LOCREPDA_linkage notebook saved this file on 28 September 2026, and it is in your Drive folder `THESIS 2026/Colab Notebooks`.

- **With it:** every page uses the exact thesis data. In the Model playground, the default settings show *"identical to the thesis"* (β1 = −2.195, n = 538).
- **Without it:** the app still runs. The map has no concession dots, and the model can only use the thesis 2 km values. The *Data* page also lets anyone pull today's register or upload the file.

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
   - Open **Model playground**. With the default settings it should say *identical to the thesis*.
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
| LOCREPDA, CONAGUA ArcGIS server | Coordinates of concession points | Thesis snapshot, 28 Sept 2026 (`data/locrepda_points_qc.csv`) | Yes: *Data* page button |
| ITER 2020, INEGI census | Household water, drainage, language, schooling, locality coordinates | Chiapas file trimmed to the 9 municipalities | No (census) |
| Drought Monitor, CONAGUA–SMN (`MunicipiosSequia.xlsx`) | Drought category every 15 days since 2003 | Copy up to 15 Sept 2026, from a public GitHub mirror of the SMN file | Yes: tries the official SMN file first, and accepts an uploaded file |
| Open-Meteo (ERA5 reanalysis and forecast models) | Rain against the 1991–2020 normal, soil moisture, 7-day forecast | None | Yes |

Before the defence, download `MunicipiosSequia.xlsx` from the SMN Drought Monitor page and upload it on the *Drought and rain* page, or replace `data/drought_monitor_snapshot.csv`. This confirms that the bundled values match the official file.

## How the numbers are built

The code in `core/` repeats the thesis notebooks line for line:

- `geo.py`: location check, REPDA–LOCREPDA matching on the number after "CHS", and intensity = log(1 + m³ per resident within the radius);
- `fastols.py` and `engine.py`: OLS with municipality fixed effects in NumPy; HC1, Conley and restricted wild cluster bootstrap (Webb weights); distances precomputed once so the pages answer instantly;
- `index.py`: priority index and rank-stability check;
- `ui.py` and `maps.py`: colours, type and the 3D map layers. Fonts (Bricolage Grotesque, OFL licence) are served from `static/fonts`.
- `live.py`: clients for LOCREPDA, the Drought Monitor and Open-Meteo. Each one fails gracefully: when a source is down, the page explains it and falls back to the bundled data.

All model results are associations, not causal effects. Census figures date from 2020, so households may have gained or lost access since.
