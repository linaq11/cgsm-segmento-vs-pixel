# -*- coding: utf-8 -*-
r"""Cuatro compuestos trimestrales de 2025 del cubo (B2, B3, B4, B8, B11, B12, uint16 x10000), en la malla exacta del cubo,
como entrada multitemporal de Prithvi-EO 2.0 (num_frames 4). Misma receta de exportación que 06_mapas.py (rectángulo
exacto contraído 1 m, WKT1_GDAL de 9377, máscara del AOI con imagen constante).

SALIDA: datos/s2_2025_q1.tif ... s2_2025_q4.tif
USO: python 19a_compuestos_trimestrales.py
"""
import importlib.util
import os

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import ee
import geemap
import rasterio
from pyproj import CRS

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
RAIZ = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/"
BANDAS = ["B2", "B3", "B4", "B8", "B11", "B12"]
TRIMESTRES = {1: ["202501", "202502", "202503"], 2: ["202504", "202505", "202506"], 3: ["202507", "202508", "202509"], 4: ["202510", "202511", "202512"]}

ee.Initialize(project="basic-buttress-338101")
ref = ee.Image(RAIZ + "202512").getInfo()["bands"][0]; tr, dims = ref["crs_transform"], ref["dimensions"]
WKT = CRS.from_epsg(9377).to_wkt(version="WKT1_GDAL")
x0, y0 = tr[2], tr[5]; x1, y1 = x0 + dims[0] * tr[0], y0 + dims[1] * tr[4]
region = ee.Geometry.Rectangle([x0 + 1, y1 + 1, x1 - 1, y0 - 1], WKT, False)
AOI = ee.FeatureCollection("projects/basic-buttress-338101/assets/AOI_tesis_CGSM_v1").geometry()
for q, meses in TRIMESTRES.items():
    out = DATOS / ("s2_2025_q%d.tif" % q)
    if out.exists():
        print(out.name, "ya existe"); continue
    img = ee.ImageCollection([ee.Image(RAIZ + m).select(BANDAS).toFloat() for m in meses]).median().toUint16().updateMask(ee.Image.constant(1).clip(AOI).mask())
    geemap.download_ee_image(img, str(out), region=region, crs=WKT, crs_transform=tr, scale=10, dtype="uint16")
    with rasterio.open(out, "r+") as r:
        r.crs = rasterio.crs.CRS.from_epsg(9377)
    with rasterio.open(out) as r:
        print("escrito", out.name, r.shape, r.count, flush=True)
