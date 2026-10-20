# -*- coding: utf-8 -*-
r"""Exploratorio: propagación de etiquetas sobre el embedding AlphaEarth 2025 (semisupervisado), decisión de Lina 2026-10-19.

Pregunta: ¿el embedding fundacional, sin Random Forest, separa las clases cuando las 720 etiquetas se propagan a un
conjunto de píxeles sin etiqueta? Dos brazos, mismo esquema OOF que la CV congelada (k = 5 bloques de 12 km, búfer de
2,6 km, contraste de permutación por bloques y McNemar frente al píxel con entrada unión):
  - knn_alphaearth: k vecinos (k = 10) solo con los puntos etiquetados de entrenamiento (control sin propagación).
  - propagacion_alphaearth: LabelSpreading (kernel knn, 10 vecinos, alpha 0,2) con los puntos de entrenamiento como
    etiquetados y un conjunto de 20.000 píxeles del AOI muestreados en Earth Engine más los puntos de prueba como no
    etiquetados.
El conjunto sin etiqueta se descarga una vez (alphaearth_pool_2025.csv, 4 lotes de 5.000 con semillas fijas).

SALIDAS: alphaearth_pool_2025.csv, propagacion_2025_{resumen,pruebas,oof}.csv
USO: python 10_propagacion_alphaearth.py
"""
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
F_AE = ["A%02d" % i for i in range(64)]
BUFER, VECINOS, ALPHA = 2600, 10, 0.2
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)


def pool_gee():
    f = AQUI / "alphaearth_pool_2025.csv"
    if f.exists():
        return pd.read_csv(f)
    import ee
    ee.Initialize(project="basic-buttress-338101")
    g = json.load(open(AQUI.parent.parent / "AVANCE TESIS" / "AOI" / "AOI_tesis_CGSM_v1.geojson", encoding="utf-8"))
    import geopandas as gpd
    aoi = gpd.read_file(AQUI.parent.parent / "AVANCE TESIS" / "AOI" / "AOI_tesis_CGSM_v1.geojson").to_crs(4326)
    region = ee.Geometry(aoi.geometry.iloc[0].__geo_interface__)
    ae = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("2025-01-01", "2026-01-01").mosaic().select(F_AE)
    filas = []
    for semilla in (1, 2, 3, 4):
        t0 = time.time()
        fc = ae.sample(region=region, scale=10, numPixels=5000, seed=abl.SEMILLA + semilla, geometries=False).getInfo()["features"]
        filas += [x["properties"] for x in fc]
        print("lote %d: %d píxeles en %.0f s" % (semilla, len(fc), time.time() - t0), flush=True)
    p = pd.DataFrame(filas)[F_AE].dropna(); p.to_csv(f, index=False)
    return p


def main():
    from pyproj import Transformer
    from scipy.spatial import cKDTree
    from sklearn.metrics import f1_score
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.semi_supervised import LabelSpreading
    pool = pool_gee(); print("conjunto sin etiqueta:", len(pool), flush=True)
    v = pd.read_csv(AQUI / "variables_2025_puntos.csv")
    d = pd.read_csv(AQUI / "pixel_2025_oof.csv").merge(v[["id", "lon", "lat"] + F_AE], on="id")
    assert len(d) == 720 and d[F_AE].notna().all().all()
    xu, yu = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values); XY = np.c_[xu, yu]
    X, Y = d[F_AE].to_numpy(np.float32), d.clase_final.to_numpy()
    Xp = pool[F_AE].to_numpy(np.float32)
    preds = {"knn_alphaearth": np.empty(len(d), dtype=object), "propagacion_alphaearth": np.empty(len(d), dtype=object)}
    cidx = {c: i for i, c in enumerate(CLASES)}
    for k in sorted(d.pliegue.unique()):
        te, tr = (d.pliegue == k).to_numpy(), (d.pliegue != k).to_numpy(copy=True)
        tr &= cKDTree(XY[te]).query(XY)[0] >= BUFER
        knn = KNeighborsClassifier(n_neighbors=VECINOS).fit(X[tr], Y[tr]); preds["knn_alphaearth"][te] = knn.predict(X[te])
        Xs = np.vstack([X[tr], Xp, X[te]]); ys = np.r_[[cidx[c] for c in Y[tr]], -np.ones(len(Xp) + te.sum(), int)]
        ls = LabelSpreading(kernel="knn", n_neighbors=VECINOS, alpha=ALPHA, max_iter=100).fit(Xs, ys)
        preds["propagacion_alphaearth"][te] = np.array([CLASES[i] for i in ls.transduction_[-te.sum():]], dtype=object)
        print("pliegue %d: knn %.3f | propagación %.3f (%d entrenamiento, %d prueba)" % (k, abl.macro(Y[te], preds["knn_alphaearth"][te], CLASES), abl.macro(Y[te], preds["propagacion_alphaearth"][te], CLASES), tr.sum(), te.sum()), flush=True)
    bloques, pp = d.bloque12.to_numpy(), d.oof_s2_mas_alphaearth.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    res, pr = [], []
    for brazo, pred in preds.items():
        por_pl = [abl.macro(Y[d.pliegue == k], pred[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=brazo, macro_f1_oof=round(abl.macro(Y, pred, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((pred == Y).mean()), 3),
                        **{"f1_" + c: round(x, 3) for c, x in zip(CLASES, f1_score(Y, pred, labels=CLASES, average=None, zero_division=0))}))
        obs, pv = abl.permutacion_bloques(Y, pred, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(Y, pred, pp)
        pr.append(dict(brazo=brazo, entrada="alphaearth 2025 (64)", contraste=brazo + " − pixel union", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        print("%-24s OOF macro-F1 %.3f (pliegues %.3f a %.3f) | − pixel %+.3f, p %.3f | McNemar p %.3f" % (brazo, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv, pm), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "propagacion_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "propagacion_2025_pruebas.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=Y, pliegue=d.pliegue, oof_pixel_union=pp, **{"oof_" + b: p for b, p in preds.items()})).to_csv(AQUI / "propagacion_2025_oof.csv", index=False)


if __name__ == "__main__":
    main()
