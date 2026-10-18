"""Map layers shared by the pages: water granted rises as blue columns, homes without water glow magenta."""
import numpy as np
import pandas as pd
import pydeck as pdk

from . import ui

USE_RGB = {"Public-urban": [46, 134, 222], "Agricultural": [18, 165, 120]}
OTHER_RGB = [228, 155, 15]


def locality_layer(df, value, vmin, vmax, layer_id="localities", pickable=True, opacity=215, rgb=None):
    """Localities as discs: size = population, colour = value on the magenta ramp (grey when masked).
    `rgb` (n x 3) overrides the colours, e.g. for the segments."""
    if rgb is None:
        t = ((df[value] - vmin) / (vmax - vmin if vmax > vmin else 1)).clip(0, 1)
        rgb = ui.ramp_rgb(t.values)
    rgb = np.array(rgb, dtype=int)
    masked = df[value].isna().values
    rgb[masked] = [175, 184, 198]
    d = df.assign(r=rgb[:, 0], g=rgb[:, 1], b=rgb[:, 2], a=np.where(masked, 120, opacity),
                  size=np.sqrt(df.POBTOT.fillna(1).clip(lower=1)) * 7 + 140)
    cols = ["lon", "lat", "r", "g", "b", "a", "size", "MUN", "LOC"] + [c for c in ["t1", "t2", "t3"] if c in d]
    return pdk.Layer("ScatterplotLayer", id=layer_id, data=d[cols], get_position="[lon, lat]",
                     get_fill_color="[r, g, b, a]", get_radius="size", radius_min_pixels=2.5, radius_max_pixels=24,
                     stroked=True, get_line_color=[255, 255, 255, 170], line_width_min_pixels=0.6,
                     pickable=pickable, auto_highlight=pickable)


def concession_layer(placed, by_use=False, radius_m=80, height=1.0, pickable=True):
    """Concession points as columns: height grows with the square root of the volume."""
    p = placed.copy()
    p["rgb"] = [USE_RGB.get(u, OTHER_RGB) if by_use else list(ui.WATER_RGB) for u in p.use]
    p["elev"] = np.sqrt(p.vol.clip(lower=0)) * height
    cols = ["LONDEC", "LATDEC", "rgb", "elev"] + [c for c in ["t1", "t2", "t3"] if c in p]
    return pdk.Layer("ColumnLayer", id="concessions", data=p[cols], get_position="[LONDEC, LATDEC]",
                     get_elevation="elev", elevation_scale=1, radius=radius_m, disk_resolution=12,
                     get_fill_color="rgb", extruded=True, pickable=pickable, auto_highlight=pickable,
                     coverage=1)


def ring_layer(lon, lat, radius_km):
    return pdk.Layer("ScatterplotLayer", id="ring", data=pd.DataFrame([{"lon": lon, "lat": lat}]),
                     get_position="[lon, lat]", get_radius=radius_km * 1000, filled=True, stroked=True,
                     get_fill_color=[224, 69, 123, 28], get_line_color=[224, 69, 123, 240], line_width_min_pixels=2.5)


def deck(layers, lat, lon, zoom, pitch=45, bearing=-12, dark=False, tooltip=True):
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom, pitch=pitch, bearing=bearing),
        map_style=None,   # follows the light or dark theme
        tooltip={"html": "<b>{t1}</b><br/>{t2}<br/>{t3}",
                 "style": {"fontSize": "13px", "backgroundColor": "#14213D", "color": "#FFFFFF",
                           "borderRadius": "8px", "padding": "8px 10px"}} if tooltip else False,
    )


def legend(value_label, lo, hi, radius_km=None, by_use=False):
    L = ui.L
    parts = [f'<span><span class="ramp"></span>&nbsp; {value_label}: {lo} → {hi}</span>']
    if by_use:
        parts.append('<span><span class="dot" style="background:#2E86DE"></span> ' + L("Público urbano", "Public-urban") +
                     '</span><span><span class="dot" style="background:#12A578"></span> ' + L("Agrícola", "Agricultural") +
                     '</span><span><span class="dot" style="background:#E49B0F"></span> ' + L("Otros usos", "Other uses") + '</span>')
    else:
        parts.append('<span><span class="tower"></span>&nbsp; ' +
                     L("Concesión de agua (altura = volumen)", "Water concession (height = volume)") + '</span>')
    if radius_km:
        parts.append('<span><span class="dot" style="background:transparent;border:2px solid #E0457B"></span> ' +
                     L(f"{radius_km:g} km alrededor de la localidad", f"{radius_km:g} km around the locality") + '</span>')
    return '<div class="legend">' + "".join(parts) + '</div>'
