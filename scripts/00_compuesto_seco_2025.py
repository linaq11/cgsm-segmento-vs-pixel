# -*- coding: utf-8 -*-
r"""Compuesto de estacion seca 2025 del cubo, como GeoTIFF local, para segmentarlo con SAM.

Mediana de los compuestos mensuales de enero a marzo de 2025 de la coleccion s2 del cubo
(projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2), bandas B4, B3, B2 y B8
(reflectancia x10000, uint16), en la malla exacta del cubo (EPSG:9377, 10 m, 7150 x 6022).
La estacion seca se elige porque es la de menor nubosidad y la misma que usan los
compuestos de clasificacion del contrato del cubo (epoca P2/P3).

Salida: datos/s2_2025_seca.tif (4 bandas) y datos/s2_2025_seca_rgb.tif (RGB uint8 con
estiramiento fijo 0-3000 y gamma 1/1,5, el mismo de las laminas del visor), que es lo que
entra a SAM.

USO: python 00_compuesto_seco_2025.py
"""
import os

import ee
import geemap
import numpy as np
import rasterio
from pyproj import CRS

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.join(AQUI, "datos"); os.makedirs(SAL, exist_ok=True)
PROYECTO = "basic-buttress-338101"
RAIZ = "projects/%s/assets/cgsm_datacube_v1" % PROYECTO
ee.Initialize(project=PROYECTO)
WKT = CRS.from_epsg(9377).to_wkt(version="WKT1_GDAL")

ref = ee.Image(RAIZ + "/s2/202512"); b0 = ref.getInfo()["bands"][0]
tr, dims = b0["crs_transform"], b0["dimensions"]
x0, y0 = tr[2], tr[5]; x1, y1 = x0 + dims[0] * tr[0], y0 + dims[1] * tr[4]
region = ee.Geometry.Rectangle([x0 + 1, y1 + 1, x1 - 1, y0 - 1], WKT, False)

col = ee.ImageCollection([ee.Image(RAIZ + "/s2/2025%02d" % m) for m in (1, 2, 3)]).select(["B4", "B3", "B2", "B8"])
img = col.median().toUint16()
tif = os.path.join(SAL, "s2_2025_seca.tif")
if not os.path.exists(tif):
    geemap.download_ee_image(img, tif, region=region, crs=WKT, crs_transform=tr, scale=10, dtype="uint16")
with rasterio.open(tif) as src:
    print("descargado:", src.width, "x", src.height, src.count, "bandas", src.crs)
    a = src.read(); prof = src.profile
rgb = np.clip(a[:3].astype("float32") / 3000.0, 0, 1) ** (1 / 1.5)
rgb = (rgb * 255).astype("uint8")
prof.update(count=3, dtype="uint8", nodata=None, compress="deflate")
with rasterio.open(os.path.join(SAL, "s2_2025_seca_rgb.tif"), "w", **prof) as dst:
    dst.write(rgb); dst.descriptions = ("R B4", "G B3", "B B2")
validos = (a[0] > 0).mean()
print("RGB escrito; pixeles con dato %.1f %%" % (100 * validos))
