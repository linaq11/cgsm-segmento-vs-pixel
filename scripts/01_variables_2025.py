# -*- coding: utf-8 -*-
r"""Variables por punto para el Informe 2: las mismas entradas del Informe 1, pero de 2025 y sobre la
muestra de referencia propia de 720 puntos, mas la linea base por pixel con el esquema de validacion
congelado de la muestra (PROTOCOLO, k = 5 por bloques de 12 km, bufer 2,6 km).

ENTRADAS
  MUESTRA_2025/etiquetas_2025.csv   id, lon, lat, clase_final, borde_final
  MUESTRA_2025/pliegues_cv.csv      bloque12 y pliegue (congelados)
  cubo s2 2025 (GEE)                12 compuestos mensuales, B2 B3 B4 B8 B11 B12 x10000
  GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL 2025   A00-A63

VARIABLES (identicas a linea_base_2021.py / representaciones_2021.py)
  seca   : mediana ene-mar por banda, 6 bandas + NDVI, NDWI, MNDWI recalculados  (9)
  humeda : mediana sep-nov                                                       (9)
  fenologia : min, max, amp, sd de NDVI, NDWI y MNDWI en los 12 meses             (12)
  alphaearth : A00-A63                                                           (64)
BRAZOS por pixel: s2_multitemporal (30), alphaearth (64), union (94). Motor: el de
MUESTRA_2025/40_ablacion_entradas.py (RF 500 arboles, semilla 20261007, OOF con bufer,
permutacion pareada por bloques, 2000 repeticiones).

SALIDAS (informe2/)
  variables_2025_puntos.csv      720 x (id, clase_final, borde_final, bloque12, pliegue, 94 variables)
  pixel_2025_resumen.csv         macro-F1 OOF por brazo, con minimo y maximo por pliegue
  pixel_2025_clases.csv          F1 por clase y brazo
  pixel_2025_pruebas.csv         contrastes pareados por bloques
  pixel_2025_oof.csv             predicciones OOF por brazo (para el analisis de bordes y de segmentos)
USO: python 01_variables_2025.py [--sin-gee]
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
RAIZ = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/"
BANDAS = ["B2", "B3", "B4", "B8", "B11", "B12"]
MESES = ["2025%02d" % m for m in range(1, 13)]
F_AE = ["A%02d" % i for i in range(64)]
N_REP = 2000

spec = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec); spec.loader.exec_module(abl)        # oof, macro, permutacion_bloques, mcnemar


def indices(v, pref, b):
    b2, b3, b4, b8, b11 = (b[pref + x] for x in ("B2", "B3", "B4", "B8", "B11"))
    v[pref + "NDVI"] = (b8 - b4) / (b8 + b4)
    v[pref + "NDWI"] = (b3 - b8) / (b3 + b8)
    v[pref + "MNDWI"] = (b3 - b11) / (b3 + b11)


def muestrear_gee(e):
    import ee
    ee.Initialize(project="basic-buttress-338101")
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in e.itertuples()])
    pila = ee.Image.cat([ee.Image(RAIZ + m).select(BANDAS).rename([m + "_" + b for b in BANDAS]) for m in MESES])
    ae = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("2025-01-01", "2026-01-01").mosaic().select(F_AE)
    r = pila.addBands(ae).reduceRegions(fc, ee.Reducer.first(), 10).getInfo()["features"]
    return pd.DataFrame([dict(id=f["properties"]["id"], **{k: f["properties"].get(k) for k in [m + "_" + b for m in MESES for b in BANDAS] + F_AE}) for f in r])


def construir(raw):
    """De 72 columnas mensuales a las 30 variables espectrales, como construir_variables de linea_base_2021.py."""
    v = pd.DataFrame({"id": raw.id})
    meses = {"seca": ["202501", "202502", "202503"], "humeda": ["202509", "202510", "202511"]}
    for est, ms in meses.items():
        med = {}
        for b in BANDAS:
            med[est + "_" + b] = np.nanmedian(np.stack([raw[m + "_" + b].astype(float) for m in ms]), axis=0)
            v[est + "_" + b] = med[est + "_" + b]
        indices(v, est + "_", med)
    serie = {}
    for c in ("NDVI", "NDWI", "MNDWI"):
        filas = []
        for m in MESES:
            b = {m + "_" + x: raw[m + "_" + x].astype(float) for x in BANDAS}
            t = {}
            indices(t, m + "_", b); filas.append(np.asarray(t[m + "_" + c]))
        s = np.stack(filas)
        with np.errstate(all="ignore"):
            v["fen_" + c + "_min"] = np.nanmin(s, axis=0); v["fen_" + c + "_max"] = np.nanmax(s, axis=0)
            v["fen_" + c + "_amp"] = v["fen_" + c + "_max"] - v["fen_" + c + "_min"]; v["fen_" + c + "_sd"] = np.nanstd(s, axis=0)
    return v


F_S2 = ["%s_%s" % (e, b) for e in ("seca", "humeda") for b in BANDAS + ["NDVI", "NDWI", "MNDWI"]] + ["fen_%s_%s" % (c, s) for c in ("NDVI", "NDWI", "MNDWI") for s in ("min", "max", "amp", "sd")]
BRAZOS = {"s2_multitemporal": F_S2, "alphaearth": F_AE, "s2_mas_alphaearth": F_S2 + F_AE}
CONTRASTES = [("alphaearth", "s2_multitemporal"), ("s2_mas_alphaearth", "s2_multitemporal"), ("s2_mas_alphaearth", "alphaearth")]


def main():
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat", "clase_final", "borde_final"]]
    p = pd.read_csv(MUESTRA / "pliegues_cv.csv")
    salida = AQUI / "variables_2025_puntos.csv"
    if salida.exists() or "--sin-gee" in sys.argv:
        d = pd.read_csv(salida)
    else:
        raw = muestrear_gee(e)
        v = construir(raw).merge(raw[["id"] + F_AE], on="id")
        d = e.merge(p, on="id").merge(v, on="id")
        d.to_csv(salida, index=False, lineterminator="\n")
    assert len(d) == 720, len(d)
    ok = d[F_S2 + F_AE].notna().all(axis=1)
    print("puntos con las 94 variables: %d de 720" % ok.sum(), flush=True)
    for c in F_S2 + F_AE:                      # imputacion minima, declarada: mediana de la clase
        if d[c].isna().any():
            d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    clases = sorted(d.clase_final.unique()); y, bloques = d.clase_final.to_numpy(), d.bloque12.to_numpy()
    rng = np.random.default_rng(abl.SEMILLA)
    oofs, res, cls = {}, [], []
    for nombre, cols in BRAZOS.items():
        pred = abl.oof(d, cols, 2600); oofs[nombre] = pred
        por_pl = [abl.macro(y[d.pliegue == k], pred[d.pliegue == k], clases) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, n_vars=len(cols), macro_f1_oof=round(abl.macro(y, pred, clases), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3),
                        exactitud=round(float((pred == y).mean()), 3)))
        from sklearn.metrics import f1_score
        for c, f in zip(clases, f1_score(y, pred, labels=clases, average=None, zero_division=0)):
            cls.append(dict(brazo=nombre, clase=c, f1=round(f, 3), n=int((y == c).sum())))
        print("%-20s macro-F1 OOF %.3f (pliegues %.3f a %.3f)" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl)), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "pixel_2025_resumen.csv", index=False)
    pd.DataFrame(cls).to_csv(AQUI / "pixel_2025_clases.csv", index=False)
    pr = []
    for a, b in CONTRASTES:
        obs, pv = abl.permutacion_bloques(y, oofs[a], oofs[b], bloques, clases, rng); mb, mc, pm = abl.mcnemar(y, oofs[a], oofs[b])
        pr.append(dict(contraste="%s − %s" % (a, b), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        print("  %s: %+.3f, p permutación %.3f, McNemar %d/%d p %.3f" % (pr[-1]["contraste"], obs, pv, mb, mc, pm), flush=True)
    pd.DataFrame(pr).to_csv(AQUI / "pixel_2025_pruebas.csv", index=False)
    o = d[["id", "clase_final", "borde_final", "bloque12", "pliegue"]].copy()
    for k, v in oofs.items(): o["oof_" + k] = v
    o.to_csv(AQUI / "pixel_2025_oof.csv", index=False)


if __name__ == "__main__":
    main()
