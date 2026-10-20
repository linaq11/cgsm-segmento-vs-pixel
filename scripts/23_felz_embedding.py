# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): segmentar sobre el embedding de AlphaEarth, no sobre el RGB.

Las tres primeras componentes principales de AlphaEarth 2025 (ejes calculados con los 20.000 píxeles sin etiqueta de
alphaearth_pool_2025.csv) se exportan desde Earth Engine como imagen de tres bandas de 8 bits en la malla del cubo, y sobre
ella se corre Felzenszwalb con el tamaño mínimo que dio 0,25 ha sobre el RGB (min_size 8). Los bordes siguen así el
significado temático del embedding y no el color. Después 03 clasifica por segmento (--seg felz_ae_025ha).

SALIDAS: datos/alphaearth_2025_pca3_8bit.tif, datos/segmentos_felz_ae_025ha.tif, y las salidas de 03 para felz_ae_025ha
USO: python 23_felz_embedding.py
"""
import importlib.util
import os
import subprocess
import sys

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
F_AE = ["A%02d" % i for i in range(64)]
PCA3 = DATOS / "alphaearth_2025_pca3_8bit.tif"


def exportar_pca3():
    if PCA3.exists():
        print("pca3 ya existe"); return
    import ee, geemap
    from pyproj import CRS
    pool = pd.read_csv(AQUI / "alphaearth_pool_2025.csv")[F_AE].to_numpy(np.float64)
    mu = pool.mean(0); C = np.cov((pool - mu).T); w, V = np.linalg.eigh(C); orden = np.argsort(w)[::-1][:3]; V3 = V[:, orden]
    proy = (pool - mu) @ V3; lo, hi = np.percentile(proy, 1, axis=0), np.percentile(proy, 99, axis=0)
    print("PCA: varianza explicada por 3 componentes %.1f %%" % (100 * w[orden].sum() / w.sum()), flush=True)
    ee.Initialize(project="basic-buttress-338101")
    ae = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("2025-01-01", "2026-01-01").mosaic().select(F_AE)
    centrado = ae.subtract(ee.Image.constant(list(map(float, mu))))
    bandas = []
    for i in range(3):
        pc = centrado.multiply(ee.Image.constant(list(map(float, V3[:, i])))).reduce(ee.Reducer.sum())
        bandas.append(pc.subtract(float(lo[i])).divide(float(hi[i] - lo[i])).multiply(254).add(1).clamp(1, 255).rename("pc%d" % (i + 1)))
    ref = ee.Image("projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/202512").getInfo()["bands"][0]; tr, dims = ref["crs_transform"], ref["dimensions"]
    WKT = CRS.from_epsg(9377).to_wkt(version="WKT1_GDAL"); x0, y0 = tr[2], tr[5]; x1, y1 = x0 + dims[0] * tr[0], y0 + dims[1] * tr[4]
    region = ee.Geometry.Rectangle([x0 + 1, y1 + 1, x1 - 1, y0 - 1], WKT, False)
    AOI = ee.FeatureCollection("projects/basic-buttress-338101/assets/AOI_tesis_CGSM_v1").geometry()
    img = ee.Image.cat(bandas).toUint8().updateMask(ee.Image.constant(1).clip(AOI).mask())
    geemap.download_ee_image(img, str(PCA3), region=region, crs=WKT, crs_transform=tr, scale=10, dtype="uint8")
    with rasterio.open(PCA3, "r+") as r:
        r.crs = rasterio.crs.CRS.from_epsg(9377)
    print("pca3 escrito", flush=True)


def segmentar():
    out = DATOS / "segmentos_felz_ae_025ha.tif"
    if out.exists():
        print("segmentos ya existen"); return
    spec = importlib.util.spec_from_file_location("f13", AQUI / "13_felzenszwalb.py"); f13 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f13)
    f13.RGB = PCA3
    dom = f13.dominio(); f13.segmentar("felz_ae_025ha", 8, dom)


if __name__ == "__main__":
    exportar_pca3(); segmentar()
    r = subprocess.run([sys.executable, "-X", "utf8", str(AQUI / "03_clasificar_segmentos.py"), "--seg", "felz_ae_025ha"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in r.stdout.splitlines() if "macro-F1" in l or "segmento" in l.lower()[:20]), flush=True)
    if r.returncode: print(r.stderr[-1500:])
