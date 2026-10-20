# -*- coding: utf-8 -*-
r"""Clasificacion por segmento frente a por pixel, con las mismas entradas, puntos, pliegues y motor.

COMO. Para cada uno de los 720 puntos se toma el segmento que lo contiene (SAM o SLIC, datos/segmentos_*.tif),
se vectoriza ese segmento y se agregan dentro de el las 94 variables del Informe 1 (media y desviacion) desde
Earth Engine: los 12 compuestos mensuales de 2025 del cubo (de los que salen las 30 espectrales, calculadas
sobre las medias por segmento igual que 01 las calcula por pixel) y AlphaEarth 2025 (64). El clasificador
es el mismo Random Forest, con los mismos pliegues y bufer; la unidad de decision cambia porque las
variables describen el segmento y no el pixel. Un punto cuyo segmento es 0 (SAM no lo cubrio) conserva sus
variables por pixel y se cuenta.

BRAZOS: pixel (01) frente a segmento, para s2_multitemporal, alphaearth y union; dos segmentadores.
PRUEBAS (PLAN): permutacion pareada por bloques de la diferencia segmento − pixel con la misma entrada;
McNemar como cifra; F1 por clase; bordes (borde_final) frente a interior.

SALIDAS (informe2/): segmentos_puntos_<seg>.csv, segmento_2025_resumen.csv, segmento_2025_clases.csv,
segmento_2025_pruebas.csv, segmento_2025_bordes.csv, segmento_2025_oof.csv
USO: python 03_clasificar_segmentos.py [--seg sam|slic] [--sin-gee]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
RAIZ = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/"
BANDAS = ["B2", "B3", "B4", "B8", "B11", "B12"]
MESES = ["2025%02d" % m for m in range(1, 13)]
F_AE = ["A%02d" % i for i in range(64)]
spec = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec); spec.loader.exec_module(abl)
spec1 = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec1); spec1.loader.exec_module(v01)          # construir, F_S2, BRAZOS, CONTRASTES
F_S2 = v01.F_S2


def poligonos_de_puntos(seg_tif, d):
    """Segmento de cada punto (id de segmento y poligono en EPSG:9377)."""
    from pyproj import Transformer
    with rasterio.open(seg_tif) as src:
        seg = src.read(1); tr = src.transform; crs = src.crs
        x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
        fil, col = rasterio.transform.rowcol(tr, x, y)
        fil = np.clip(fil, 0, seg.shape[0] - 1); col = np.clip(col, 0, seg.shape[1] - 1)
        ids = seg[fil, col].astype("int64")
        polis = {}
        for sid in np.unique(ids[ids > 0]):
            m = (seg == sid).astype("uint8")
            geoms = [shape(g) for g, v in features.shapes(m, mask=m.astype(bool), transform=tr)]
            polis[int(sid)] = unary_union(geoms)
    return ids, polis, crs


def agregar_gee(ids, polis):
    """Media y desviacion de las 72 bandas mensuales y de AlphaEarth dentro de cada segmento."""
    import ee
    from pyproj import Transformer
    ee.Initialize(project="basic-buttress-338101")
    t = Transformer.from_crs(9377, 4326, always_xy=True)
    fs = []
    for sid, g in polis.items():
        gj = mapping(g); gj = json.loads(json.dumps(gj))
        def tr(coords):
            return [[list(t.transform(x, y)) for x, y in ring] for ring in coords]
        if gj["type"] == "Polygon": geom = ee.Geometry.Polygon(tr(gj["coordinates"]))
        else: geom = ee.Geometry.MultiPolygon([tr(p) for p in gj["coordinates"]])
        fs.append(ee.Feature(geom, {"sid": sid}))
    fc = ee.FeatureCollection(fs)
    pila = ee.Image.cat([ee.Image(RAIZ + m).select(BANDAS).rename([m + "_" + b for b in BANDAS]) for m in MESES])
    ae = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("2025-01-01", "2026-01-01").mosaic().select(F_AE)
    img = pila.addBands(ae)
    filas = []
    for i in range(0, len(fs), 100):
        sub = ee.FeatureCollection(fs[i:i + 100])
        r = img.reduceRegions(sub, ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True), 10, tileScale=4).getInfo()["features"]
        for f in r:
            filas.append(dict(sid=f["properties"]["sid"], area_ha=round(polis[f["properties"]["sid"]].area / 1e4, 2), **{k: v for k, v in f["properties"].items() if k != "sid"}))
        print("   segmentos agregados: %d de %d" % (min(i + 100, len(fs)), len(fs)), flush=True)
    return pd.DataFrame(filas)


def variables_segmento(agg):
    """De las medias mensuales por segmento a las 30 espectrales (mismo construir de 01) + sd de los indices + AlphaEarth media y sd."""
    raw = pd.DataFrame({"id": agg.sid})
    for m in MESES:
        for b in BANDAS:
            raw[m + "_" + b] = agg[m + "_" + b + "_mean"]
    v = v01.construir(raw).rename(columns={"id": "sid"})
    for a in F_AE:
        v[a] = agg[a + "_mean"].values; v[a + "_sd"] = agg[a + "_stdDev"].values
    for b in BANDAS:                      # heterogeneidad interna del segmento en la estacion seca
        v["sd_seca_" + b] = np.nanmean(np.stack([agg["2025%02d_%s_stdDev" % (m, b)].values for m in (1, 2, 3)]), axis=0)
    v["area_ha"] = agg.area_ha.values
    return v


def main():
    segn = sys.argv[sys.argv.index("--seg") + 1] if "--seg" in sys.argv else "sam"
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv")
    ids, polis, crs = poligonos_de_puntos(DATOS / ("segmentos_%s.tif" % segn), d)
    d["sid"] = ids
    print("%s: %d puntos con segmento, %d sin (id 0); segmentos distintos %d; puntos que comparten segmento %d" % (segn, (ids > 0).sum(), (ids == 0).sum(), len(polis), int((d[d.sid > 0].sid.duplicated()).sum())), flush=True)
    cache = AQUI / ("segmentos_puntos_%s.csv" % segn)
    if cache.exists() or "--sin-gee" in sys.argv:
        vs = pd.read_csv(cache)
    else:
        vs = variables_segmento(agregar_gee(ids, polis)); vs.to_csv(cache, index=False, lineterminator="\n")
    F_SD = ["sd_seca_" + b for b in BANDAS] + [a + "_sd" for a in F_AE]
    # tabla por punto con variables de segmento; sin segmento -> variables de pixel y sd 0
    seg_cols = F_S2 + F_AE
    ds = d[["id", "lon", "lat", "clase_final", "borde_final", "bloque12", "pliegue", "sid"]].merge(vs, on="sid", how="left")
    sin = ds.sid == 0
    for c in seg_cols:
        ds.loc[sin, c] = d.loc[sin, c].values
    for c in F_SD + ["area_ha"]:
        ds[c] = ds[c].fillna(0.0)
    for c in seg_cols:
        if ds[c].isna().any(): ds[c] = ds[c].fillna(ds.groupby("clase_final")[c].transform("median"))
    clases = sorted(d.clase_final.unique()); y, bloques = d.clase_final.to_numpy(), d.bloque12.to_numpy()
    rng = np.random.default_rng(abl.SEMILLA)
    pix = pd.read_csv(AQUI / "pixel_2025_oof.csv")
    # contexto como rasgo (auditoría, punto 1): el pixel conserva sus 94 variables y anade las de su segmento
    for c in seg_cols:
        ds["seg_" + c] = ds[c].values; ds[c] = d[c].values
    F_SEG = ["seg_" + c for c in seg_cols]
    # brazos por segmento (variables del segmento) y brazo pixel + segmento
    brazos = {"s2_multitemporal": ["seg_" + c for c in F_S2], "alphaearth": ["seg_" + c for c in F_AE], "s2_mas_alphaearth": F_SEG,
              "s2_mas_alphaearth_mas_sd": F_SEG + F_SD,
              "pixel_mas_segmento": F_S2 + F_AE + F_SEG + F_SD}
    res, cls, pr, bor, oofs = [], [], [], [], {}
    from sklearn.metrics import f1_score
    for nombre, cols in brazos.items():
        pred = abl.oof(ds, cols, 2600); oofs[nombre] = pred
        por_pl = [abl.macro(y[ds.pliegue == k], pred[ds.pliegue == k], clases) for k in sorted(ds.pliegue.unique())]
        res.append(dict(segmentador=segn, brazo=nombre, unidad="pixel + segmento" if nombre == "pixel_mas_segmento" else "segmento", n_vars=len(cols), macro_f1_oof=round(abl.macro(y, pred, clases), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((pred == y).mean()), 3)))
        for c, f in zip(clases, f1_score(y, pred, labels=clases, average=None, zero_division=0)):
            cls.append(dict(segmentador=segn, brazo=nombre, clase=c, f1_segmento=round(f, 3)))
        print("%-26s segmento macro-F1 OOF %.3f (pliegues %.3f a %.3f)" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl)), flush=True)
        ref = "s2_mas_alphaearth" if nombre == "pixel_mas_segmento" else nombre
        if "oof_" + ref in pix:
            pp = pix["oof_" + ref].to_numpy()
            obs, pv = abl.permutacion_bloques(y, pred, pp, bloques, clases, rng); mb, mc, pm = abl.mcnemar(y, pred, pp)
            pr.append(dict(segmentador=segn, entrada=nombre, contraste=("pixel+segmento − pixel" if nombre == "pixel_mas_segmento" else "segmento − pixel"), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
            print("   segmento − pixel: %+.3f, p permutación %.3f, McNemar %d/%d p %.3f" % (obs, pv, mb, mc, pm), flush=True)
            for grupo, m in (("borde", (d.borde_final == "si").to_numpy()), ("interior", (d.borde_final == "no").to_numpy())):
                bor.append(dict(segmentador=segn, entrada=nombre, grupo=grupo, n=int(m.sum()), macro_f1_pixel=round(abl.macro(y[m], pp[m], clases), 3), macro_f1_segmento=round(abl.macro(y[m], pred[m], clases), 3),
                                exactitud_pixel=round(float((pp[m] == y[m]).mean()), 3), exactitud_segmento=round(float((pred[m] == y[m]).mean()), 3)))
    sufijo = "_" + segn
    pd.DataFrame(res).to_csv(AQUI / ("segmento_2025_resumen%s.csv" % sufijo), index=False)
    pd.DataFrame(cls).to_csv(AQUI / ("segmento_2025_clases%s.csv" % sufijo), index=False)
    pd.DataFrame(pr).to_csv(AQUI / ("segmento_2025_pruebas%s.csv" % sufijo), index=False)
    pd.DataFrame(bor).to_csv(AQUI / ("segmento_2025_bordes%s.csv" % sufijo), index=False)
    o = ds[["id", "clase_final", "borde_final", "bloque12", "pliegue", "sid", "area_ha"]].copy()
    for k, v in oofs.items(): o["oof_seg_" + k] = v
    o.to_csv(AQUI / ("segmento_2025_oof%s.csv" % sufijo), index=False)
    print(pd.DataFrame(bor).to_string(index=False))


if __name__ == "__main__":
    main()
