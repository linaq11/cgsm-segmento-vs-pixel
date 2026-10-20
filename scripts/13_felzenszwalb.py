# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): segmentador con bordes adaptativos a 0,25 y 1 ha.

SLICO produjo celdas casi regulares a todas las escalas (Figura 2 del informe), así que los brazos SLIC midieron escala
de agregación y no delimitación. Felzenszwalb y Huttenlocher (2004) construyen regiones por grafo cuyo tamaño sigue el
contraste local, con bordes que se adaptan a la imagen. Se corre por teselas de 1024 px sobre Lab del compuesto RGB de
estación seca (misma entrada que SLIC), con min_size igual al área objetivo en píxeles (25 y 100) y la escala calibrada
en una tesela de calibración para que la mediana del área de los segmentos quede cerca del objetivo. Después se clasifica
con 03 (--seg felz_025ha | felz_1ha) y se compara con píxel y con SLIC a la misma escala.

SALIDAS: datos/segmentos_felz_025ha.tif, datos/segmentos_felz_1ha.tif, felz_calibracion.csv
USO: python 13_felzenszwalb.py
"""
import importlib.util
import os
import time

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from skimage.color import rgb2lab
from skimage.segmentation import felzenszwalb

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
RGB = DATOS / "s2_2025_seca_rgb.tif"
T = 1024
OBJETIVOS = {"felz_025ha": 25, "felz_1ha": 100}   # píxeles de 10 m
ESCALA = 100
MINSIZES = [3, 4, 6, 8, 12, 16, 24, 32, 48]   # la escala apenas mueve la mediana en Lab; el tamaño minimo sí (calibracion del 19-oct)


def dominio():
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        return src.read(1) > 0


def tesela_calibracion(dom):
    """Tesela con más píxeles válidos del complejo occidental (zona de manglar), para calibrar la escala."""
    H, W = dom.shape; mejor, mv = None, -1
    for r0 in range(0, H, T):
        for c0 in range(0, W, T):
            v = dom[r0:min(r0 + T, H), c0:min(c0 + T, W)].sum()
            if v > mv and c0 < W // 2:
                mejor, mv = (r0, c0), v
    return mejor


def calibrar(dom):
    r0, c0 = tesela_calibracion(dom)
    with rasterio.open(RGB) as src:
        rgb = np.moveaxis(src.read(window=Window(c0, r0, T, T)), 0, -1)
    lab = rgb2lab(rgb).astype("float32"); dm = dom[r0:r0 + T, c0:c0 + T]
    filas, eleccion = [], {}
    for nombre, obj in OBJETIVOS.items():
        for ms in MINSIZES:
            seg = felzenszwalb(lab, scale=ESCALA, sigma=0.5, min_size=ms, channel_axis=-1)
            ids, n = np.unique(seg[dm], return_counts=True)
            med = float(np.median(n)); filas.append(dict(objetivo=nombre, min_size=ms, segmentos=len(ids), mediana_px=med, p25=float(np.percentile(n, 25)), p75=float(np.percentile(n, 75))))
            print("%s min_size %d: %d segmentos, mediana %.0f px (objetivo %d)" % (nombre, ms, len(ids), med, obj), flush=True)
        q = [f for f in filas if f["objetivo"] == nombre]
        eleccion[nombre] = min(q, key=lambda f: abs(np.log(f["mediana_px"] / obj)))["min_size"]
    pd.DataFrame(filas).to_csv(AQUI / "felz_calibracion.csv", index=False)
    print("tamaños mínimos elegidos:", eleccion, flush=True)
    return eleccion


def segmentar(nombre, min_size, dom):
    out = DATOS / ("segmentos_%s.tif" % nombre)
    if out.exists():
        print(nombre, "ya existe"); return
    with rasterio.open(RGB) as src:
        prof = src.profile; H, W = src.height, src.width
    seg = np.zeros((H, W), dtype="int32"); desplaz = 0; t0 = time.time()
    with rasterio.open(RGB) as src:
        for r0 in range(0, H, T):
            for c0 in range(0, W, T):
                r1, c1 = min(r0 + T, H), min(c0 + T, W); dm = dom[r0:r1, c0:c1]
                if not dm.any():
                    continue
                rgb = np.moveaxis(src.read(window=Window(c0, r0, c1 - c0, r1 - r0)), 0, -1)
                loc = felzenszwalb(rgb2lab(rgb).astype("float32"), scale=ESCALA, sigma=0.5, min_size=min_size, channel_axis=-1).astype("int32") + 1
                loc += desplaz; desplaz = int(loc.max())
                seg[r0:r1, c0:c1] = np.where(dm, loc, 0)
    u = np.unique(seg[seg > 0]); lut = np.zeros(seg.max() + 1, dtype="int32"); lut[u] = np.arange(1, len(u) + 1); seg = lut[seg]
    areas = np.bincount(seg[seg > 0])[1:] * 0.01
    print("%s: %d segmentos en %.0f s, área mediana %.2f ha (p25 %.2f, p75 %.2f)" % (nombre, len(u), time.time() - t0, np.median(areas), np.percentile(areas, 25), np.percentile(areas, 75)), flush=True)
    prof.update(count=1, dtype="int32", nodata=0, compress="deflate")
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(seg, 1)


if __name__ == "__main__":
    dom = dominio(); ms = calibrar(dom)
    for nombre in OBJETIVOS:
        segmentar(nombre, ms[nombre], dom)
