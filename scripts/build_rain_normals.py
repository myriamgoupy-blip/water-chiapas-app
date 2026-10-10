"""One-off: download 1991–2020 daily rain for the nine municipal seats and save the daily averages.

Run once from the repository root (locally or in Colab), then commit the file it writes:
    python scripts/build_rain_normals.py
It writes data/rain_normals_1991_2020.csv. The app works without it (it can build the same file
from the Drought and rain page), but bundling it makes that page load instantly for the jury.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import live  # noqa: E402
from core.config import DATA  # noqa: E402

loc = pd.read_csv(DATA / "iter2020_localities.csv")
seats = loc[loc.LOC == 1]

points = [dict(MUN=int(r.MUN), lat=float(r.lat), lon=float(r.lon)) for r in seats.itertuples()]
nm = live.fetch_rain_normals(points, progress=lambda f: print(f"{f:.0%}", end=" ", flush=True))
nm.to_csv(DATA / "rain_normals_1991_2020.csv", index=False)
print("\nSaved", DATA / "rain_normals_1991_2020.csv", nm.shape)
