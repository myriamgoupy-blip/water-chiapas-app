"""Shared constants: study area, file paths, colours, thesis reference values."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "cache"          # written at run time (live pulls); safe to delete

MUNS = {
    78: "San Cristóbal de las Casas", 111: "Zinacantán", 23: "Chamula", 93: "Tenejapa",
    38: "Huixtán", 94: "Teopisca", 7: "Amatenango del Valle", 24: "Chanal",
    19: "Comitán de Domínguez",
}
MUN_SHORT = {78: "San Cristóbal", 111: "Zinacantán", 23: "Chamula", 93: "Tenejapa", 38: "Huixtán",
             94: "Teopisca", 7: "Amatenango", 24: "Chanal", 19: "Comitán"}

# Thesis main specification (Notebook 4, run of 10 Oct 2026). Used to show a "matches the thesis" badge.
THESIS = dict(radius_km=2, min_pop=100, dv="dep_water", model="M3", n=538, beta1=-2.195)

# Data snapshot dates shown in the interface
SNAPSHOTS = {
    "REPDA": "September 2026 (public REPDA consultation, 9 municipal extracts)",
    "ITER": "Census 2020 (INEGI ITER, Chiapas)",
    "LOCREPDA": "28 September 2026 (thesis snapshot)",
    "Drought monitor": "bundled copy up to 15 September 2026",
}

# Palette (same as the thesis figures)
BLUE, ORANGE, AQUA, GREY, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#b4b2a9", "#0b0b0b", "#52514e"

USE_EN = {
    "PUBLICO URBANO": "Public-urban", "AGRICOLA": "Agricultural", "SERVICIOS": "Services",
    "DIFERENTES USOS": "Multiple uses", "INDUSTRIAL": "Industrial", "DOMÉSTICO": "Domestic",
    "DOMESTICO": "Domestic", "ACUACULTURA": "Aquaculture", "PECUARIO": "Livestock",
    "GENERACION DE ENERGIA ELÉCTRICA": "Electricity", "GENERACION DE ENERGIA ELECTRICA": "Electricity",
}
USE_COLOURS = {  # RGB for the map
    "Public-urban": [42, 120, 214], "Agricultural": [27, 175, 122], "Industrial": [235, 104, 52],
    "Services": [150, 90, 200], "Multiple uses": [120, 120, 120], "Other": [180, 178, 169],
}

DROUGHT_LEVELS = ["None", "D0", "D1", "D2", "D3", "D4"]
DROUGHT_LABELS = {
    "None": "No drought", "D0": "Abnormally dry", "D1": "Moderate drought",
    "D2": "Severe drought", "D3": "Extreme drought", "D4": "Exceptional drought",
}
DROUGHT_COLOURS = {"None": "#e4e3de", "D0": "#f6e27f", "D1": "#f2b45a", "D2": "#eb6834",
                   "D3": "#c0392b", "D4": "#6e1a12"}

LOCREPDA_URL = "https://sigagis.conagua.gob.mx/ArcGIS/rest/services/LocREPDA/MapServer"
DROUGHT_URL = ("https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/"
               "MunicipiosSequia.xlsx")
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
