# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): suavizado de probabilidades dentro del objeto en vez de voto duro.

El voto por mayoría (06) pierde la información de las probabilidades. Aquí, para cada pliegue k, el Random Forest de Earth
Engine (mismos puntos de entrenamiento y variables que 06, salida MULTIPROBABILITY) produce las seis probabilidades por
píxel, y para cada punto de prueba se promedian dentro de su objeto (polígono del segmento, como en 03) y se decide por el
máximo. Segmentadores: Felzenszwalb 0,25 ha y SLIC 0,25 ha. Contraste frente al píxel unión (OOF sklearn) y bordes.

SALIDAS: suavizado_prob_<seg>_puntos.csv (probabilidades medias por punto y pliegue), suavizado_2025_{resumen,pruebas,bordes,oof}.csv
USO: python 22_suavizado_prob.py
"""
import importlib.util
import os
import sys

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
BUFER = 2600
SEGS = ["felz_025ha", "slic_025ha"]
for n, f in (("v01", "01_variables_2025.py"), ("m03", "03_clasificar_segmentos.py"), ("m06", "06_mapas.py")):
    spec = importlib.util.spec_from_file_location(n, AQUI / f); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); globals()[n] = mod
abl = m06.abl; COLS = m06.COLS


def probabilidades(segn, d, XY):
    """Probabilidades medias por clase dentro del objeto de cada punto, con el RF del pliegue que no vio al punto."""
    import ee
    from scipy.spatial import cKDTree
    f = AQUI / ("suavizado_prob_%s_puntos.csv" % segn)
    if f.exists():
        return pd.read_csv(f)
    ee.Initialize(project="basic-buttress-338101")
    ids, polis, crs = m03.poligonos_de_puntos(DATOS / ("segmentos_%s.tif" % segn), d)
    from pyproj import Transformer
    tr = Transformer.from_crs(9377, 4326, always_xy=True)
    import shapely.ops as so
    pila = m06.pila_gee()
    filas = []
    for k in sorted(d.pliegue.unique()):
        te, trn = (d.pliegue == k).to_numpy(), (d.pliegue != k).to_numpy(copy=True); trn &= cKDTree(XY[te]).query(XY)[0] >= BUFER
        sub = d[trn]
        fc = ee.FeatureCollection([ee.Feature(None, {**{c: float(r[c]) for c in COLS}, "clase_num": int(r.clase_num)}) for _, r in sub.iterrows()])
        rf = ee.Classifier.smileRandomForest(numberOfTrees=500, seed=abl.SEMILLA).setOutputMode("MULTIPROBABILITY").train(fc, "clase_num", COLS)
        prob = pila.classify(rf).arrayFlatten([["p%d" % c for c in range(1, 7)]])
        feats = []
        for j in np.where(te)[0]:
            sid = int(ids[j])
            g = polis[sid] if sid > 0 else None
            geom = ee.Geometry(so.transform(lambda x, y, z=None: tr.transform(x, y), g).__geo_interface__) if g is not None else ee.Geometry.Point([float(d.lon.values[j]), float(d.lat.values[j])])
            feats.append(ee.Feature(geom, {"id": int(d.id.values[j]), "pliegue": int(k)}))
        r = prob.reduceRegions(ee.FeatureCollection(feats), ee.Reducer.mean(), 10, tileScale=4).getInfo()["features"]
        filas += [dict(id=x["properties"]["id"], pliegue=k, **{"p%d" % c: x["properties"].get("p%d" % c) for c in range(1, 7)}) for x in r]
        print("  %s pliegue %d: %d puntos de prueba" % (segn, k, te.sum()), flush=True)
    t = pd.DataFrame(filas); t.to_csv(f, index=False); return t


def main():
    from pyproj import Transformer
    from sklearn.metrics import f1_score
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv").merge(pd.read_csv(AQUI / "pixel_2025_oof.csv")[["id", "oof_s2_mas_alphaearth"]], on="id")
    for c in COLS:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    d["clase_num"] = d.clase_final.map({c: i + 1 for i, c in enumerate(CLASES)})
    x, y_ = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values); XY = np.c_[x, y_]
    y = d.clase_final.to_numpy(); bloques = d.bloque12.to_numpy(); pp = d.oof_s2_mas_alphaearth.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    borde = d.borde_final.astype(str).str.lower().isin(["si", "sí", "true", "1"]).to_numpy()
    res, pr, bor, oofs = [], [], [], {}
    for segn in SEGS:
        t = probabilidades(segn, d, XY).merge(d[["id"]], on="id", how="right")
        P = t[["p%d" % c for c in range(1, 7)]].to_numpy(float)
        p = np.where(np.isfinite(P).all(1), np.array(CLASES)[np.nan_to_num(P, nan=-1).argmax(1)], pp)
        nombre = "prob_objeto_" + segn; oofs[nombre] = p
        por_pl = [abl.macro(y[d.pliegue == k], p[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, macro_f1_oof=round(abl.macro(y, p, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((p == y).mean()), 3), sin_prob=int((~np.isfinite(P).all(1)).sum()),
                        **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y, p, labels=CLASES, average=None, zero_division=0))}))
        obs, pv = abl.permutacion_bloques(y, p, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y, p, pp)
        pr.append(dict(brazo=nombre, contraste=nombre + " − pixel union", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        for g, mm in (("borde", borde), ("interior", ~borde)):
            bor.append(dict(brazo=nombre, grupo=g, n=int(mm.sum()), macro_f1_pixel=round(abl.macro(y[mm], pp[mm], CLASES), 3), macro_f1_brazo=round(abl.macro(y[mm], p[mm], CLASES), 3)))
        print("%-26s OOF macro-F1 %.3f (pliegues %.3f a %.3f) | − pixel union %+.3f (p %.3f) | borde %.3f interior %.3f | humedal %.2f" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv, bor[-2]["macro_f1_brazo"], bor[-1]["macro_f1_brazo"], res[-1]["f1_humedal_herbaceo"]), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "suavizado_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "suavizado_2025_pruebas.csv", index=False); pd.DataFrame(bor).to_csv(AQUI / "suavizado_2025_bordes.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y, pliegue=d.pliegue, oof_pixel_union=pp, **{"oof_" + n: p for n, p in oofs.items()})).to_csv(AQUI / "suavizado_2025_oof.csv", index=False)


if __name__ == "__main__":
    main()
