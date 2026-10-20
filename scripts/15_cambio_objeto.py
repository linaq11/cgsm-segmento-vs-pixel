# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): cambio 2021 → 2025 por píxel frente a por objeto.

Un mismo clasificador (RF de 500 árboles en Earth Engine, entrenado con las 600 etiquetas débiles de WorldCover 2021 y
las 94 variables de 2021, cuatro clases: agua, humedal herbáceo, manglar, otro) se aplica a la pila de 2021 y a la de
2025 del cubo, de modo que la diferencia entre fechas no mezcla modelos. El cambio por píxel es el desacuerdo píxel a
píxel; el cambio por objeto usa los segmentos de Felzenszwalb de 1 ha de 2025 y la clase mayoritaria de cada objeto en
cada fecha. Se comparan: área cambiada, fragmentación del cambio (componentes conexas de 4 píxeles o menos, el ruido de
"sal y pimienta") y, en los 591 puntos de 2025 que no son vegetación flotante, el acuerdo con un cambio de referencia
débil: etiqueta WorldCover 2021 en el punto frente a la etiqueta propia de 2025 agrupada a cuatro clases.

SALIDAS: datos/mapa_2021_modelo2021.tif, datos/mapa_2025_modelo2021.tif, cambio_2025_{resumen,transiciones,puntos}.csv
USO: python 15_cambio_objeto.py
"""
import importlib.util
import os

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
INF1 = AQUI.parent / "informe1" / "linea_base_2021" / "variables_puntos.csv"
AE21 = AQUI.parent.parent / "AVANCE TESIS" / "PILOTO_BENCHMARK" / "alphaearth2021_etiquetas.csv"
RAIZ = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/"
BANDAS = ["B2", "B3", "B4", "B8", "B11", "B12"]
F_AE = ["A%02d" % i for i in range(64)]
SEMILLA = 20261007
CLASES4 = ["agua", "humedal_herbaceo", "manglar", "otro"]
A4 = {"manglar_intacto": "manglar", "manglar_degradado": "manglar", "agua": "agua", "humedal_herbaceo": "humedal_herbaceo", "otro": "otro"}
WC4 = {80: "agua", 90: "humedal_herbaceo", 95: "manglar"}          # resto de WorldCover → otro
SEG = DATOS / "segmentos_felz_1ha.tif"
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
F_S2 = v01.F_S2; COLS = F_S2 + F_AE


def pila_gee(anio):
    import ee
    meses = ["%d%02d" % (anio, m) for m in range(1, 13)]
    def ind(img, pref):
        b = {x: img.select(pref + x) for x in BANDAS}
        return ee.Image.cat(b["B8"].subtract(b["B4"]).divide(b["B8"].add(b["B4"])).rename(pref + "NDVI"),
                            b["B3"].subtract(b["B8"]).divide(b["B3"].add(b["B8"])).rename(pref + "NDWI"),
                            b["B3"].subtract(b["B11"]).divide(b["B3"].add(b["B11"])).rename(pref + "MNDWI"))
    mens = {m: ee.Image(RAIZ + m).select(BANDAS).toFloat() for m in meses}
    partes = []
    for est, idx in (("seca", [0, 1, 2]), ("humeda", [8, 9, 10])):
        med = ee.ImageCollection([mens[meses[i]] for i in idx]).median().rename([est + "_" + b for b in BANDAS])
        partes += [med, ind(med, est + "_")]
    for c in ("NDVI", "NDWI", "MNDWI"):
        serie = ee.ImageCollection([ind(mens[m].rename([m + "_" + b for b in BANDAS]), m + "_").select(m + "_" + c).rename(c) for m in meses])
        mn, mx, sd = serie.min(), serie.max(), serie.reduce(ee.Reducer.stdDev())
        partes += [mn.rename("fen_%s_min" % c), mx.rename("fen_%s_max" % c), mx.subtract(mn).rename("fen_%s_amp" % c), sd.rename("fen_%s_sd" % c)]
    ae = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("%d-01-01" % anio, "%d-01-01" % (anio + 1)).mosaic().select(F_AE)
    return ee.Image.cat(partes + [ae]).select(COLS)


def tabla_2021():
    t21 = pd.read_csv(INF1); a21 = pd.read_csv(AE21); assert len(t21) == len(a21) == 600
    for a in F_AE:
        t21[a] = a21[a].values
    t21 = t21.rename(columns={c: c.replace("hum_", "humeda_", 1) for c in t21.columns if c.startswith("hum_")})
    t21 = t21.dropna(subset=COLS).copy()
    for c in F_S2:                                   # reflectancias de 2021 en 0-1 → unidades del cubo (x10000), como la pila
        if c.split("_")[1].startswith("B"): t21[c] = t21[c] * 10000.0
    t21["clase_num"] = t21.clase_nombre.map({c: i + 1 for i, c in enumerate(CLASES4)})
    assert t21.clase_num.notna().all(), t21.clase_nombre.unique()
    return t21


def mapas_gee():
    import ee, geemap
    from pyproj import CRS
    ee.Initialize(project="basic-buttress-338101")
    t21 = tabla_2021(); print("2021: %d puntos de entrenamiento, clases %s" % (len(t21), t21.clase_nombre.value_counts().to_dict()), flush=True)
    fc = ee.FeatureCollection([ee.Feature(None, {**{c: float(r[c]) for c in COLS}, "clase_num": int(r.clase_num)}) for _, r in t21.iterrows()])
    rf = ee.Classifier.smileRandomForest(numberOfTrees=500, seed=SEMILLA).train(fc, "clase_num", COLS)
    ref = ee.Image(RAIZ + "202512").getInfo()["bands"][0]; tr, dims = ref["crs_transform"], ref["dimensions"]
    WKT = CRS.from_epsg(9377).to_wkt(version="WKT1_GDAL")
    x0, y0 = tr[2], tr[5]; x1, y1 = x0 + dims[0] * tr[0], y0 + dims[1] * tr[4]
    region = ee.Geometry.Rectangle([x0 + 1, y1 + 1, x1 - 1, y0 - 1], WKT, False)
    AOI = ee.FeatureCollection("projects/basic-buttress-338101/assets/AOI_tesis_CGSM_v1").geometry()
    for anio in (2021, 2025):
        out = DATOS / ("mapa_%d_modelo2021.tif" % anio)
        if out.exists():
            continue
        img = pila_gee(anio).classify(rf).toUint8().updateMask(ee.Image.constant(1).clip(AOI).mask())
        geemap.download_ee_image(img, str(out), region=region, crs=WKT, crs_transform=tr, scale=10, dtype="uint8")
        with rasterio.open(out, "r+") as r:
            r.crs = rasterio.crs.CRS.from_epsg(9377)
        print("escrito", out.name, flush=True)
    # WorldCover 2021 en los 720 puntos (referencia débil de 2021)
    f = AQUI / "worldcover2021_puntos.csv"
    if not f.exists():
        e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]]
        pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in e.itertuples()])
        wc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
        r = wc.reduceRegions(pts, ee.Reducer.first(), 10).getInfo()["features"]
        pd.DataFrame([dict(id=x["properties"]["id"], wc=x["properties"].get("first")) for x in r]).to_csv(f, index=False)
    return pd.read_csv(f)


def moda_por_segmento(seg, mapa, ncl):
    n = int(seg.max()) + 1; mejor = np.zeros(n, np.int64); cl = np.zeros(n, np.uint8)
    for c in range(1, ncl + 1):
        cnt = np.bincount(seg[(mapa == c) & (seg > 0)], minlength=n); gana = cnt > mejor; cl[gana] = c; mejor[gana] = cnt[gana]
    return cl


def main():
    from pyproj import Transformer
    from rasterio.transform import rowcol
    from scipy.ndimage import label
    from sklearn.metrics import f1_score
    wc = mapas_gee()
    with rasterio.open(DATOS / "mapa_2021_modelo2021.tif") as s:
        m21 = s.read(1); trf = s.transform
    with rasterio.open(DATOS / "mapa_2025_modelo2021.tif") as s:
        m25 = s.read(1)
    with rasterio.open(SEG) as s:
        seg = s.read(1).astype(np.int64)
    dom = (m21 > 0) & (m25 > 0) & (seg > 0)
    cl21, cl25 = moda_por_segmento(seg, np.where(dom, m21, 0), 4), moda_por_segmento(seg, np.where(dom, m25, 0), 4)
    o21, o25 = cl21[seg], cl25[seg]
    camb_px = dom & (m21 != m25); camb_ob = dom & (o21 != o25) & (o21 > 0) & (o25 > 0)
    res = []
    for nombre, cm in (("pixel", camb_px), ("objeto_felz_1ha", camb_ob)):
        lab, n = label(cm); tam = np.bincount(lab.ravel())[1:]
        res.append(dict(unidad=nombre, area_dominio_ha=round(dom.sum() * 0.01), area_cambio_ha=round(cm.sum() * 0.01), fraccion_cambio=round(float(cm.sum() / dom.sum()), 4),
                        componentes=int(n), componentes_le4px=int((tam <= 4).sum()), fraccion_area_cambio_en_le4px=round(float(tam[tam <= 4].sum() / max(tam.sum(), 1)), 4), tamano_mediano_px=float(np.median(tam)) if n else 0))
        print(res[-1], flush=True)
    trans = []
    for a in range(1, 5):
        for b in range(1, 5):
            trans.append(dict(de=CLASES4[a - 1], a=CLASES4[b - 1], area_pixel_ha=round(((m21 == a) & (m25 == b) & dom).sum() * 0.01), area_objeto_ha=round(((o21 == a) & (o25 == b) & dom).sum() * 0.01)))
    pd.DataFrame(trans).to_csv(AQUI / "cambio_2025_transiciones.csv", index=False)
    # puntos: referencia debil de cambio
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat", "clase_final"]].merge(wc, on="id")
    e = e[e.clase_final != "vegetacion_flotante"].copy(); e["ref21"] = e.wc.map(lambda v: WC4.get(int(v), "otro") if pd.notna(v) else np.nan); e["ref25"] = e.clase_final.map(A4)
    e = e.dropna(subset=["ref21"]); e["cambio_ref"] = e.ref21 != e.ref25
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(e.lon.values, e.lat.values); fil, col = rowcol(trf, x, y)
    fil = np.clip(fil, 0, m21.shape[0] - 1); col = np.clip(col, 0, m21.shape[1] - 1)
    e["cambio_pixel"] = camb_px[fil, col]; e["cambio_objeto"] = camb_ob[fil, col]
    e["m21"] = [CLASES4[v - 1] if v > 0 else "sin dato" for v in m21[fil, col]]; e["m25"] = [CLASES4[v - 1] if v > 0 else "sin dato" for v in m25[fil, col]]
    for u in ("pixel", "objeto"):
        p = e["cambio_" + u].to_numpy(); r = e.cambio_ref.to_numpy()
        res_p = dict(unidad=u, n=len(e), prevalencia_cambio_ref=round(float(r.mean()), 3), exactitud=round(float((p == r).mean()), 3), f1_cambio=round(f1_score(r, p), 3), f1_sin_cambio=round(f1_score(~r, ~p), 3),
                     predicho_cambio=int(p.sum()), acuerdo_en_cambio_de_clase=round(float(((e.m21 == e.ref21) & (e.m25 == e.ref25))[p & r].mean()), 3) if (p & r).any() else np.nan)
        res.append(res_p); print(res_p, flush=True)
    pd.DataFrame(res).to_csv(AQUI / "cambio_2025_resumen.csv", index=False); e.to_csv(AQUI / "cambio_2025_puntos.csv", index=False)


if __name__ == "__main__":
    main()
