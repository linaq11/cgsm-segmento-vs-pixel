# -*- coding: utf-8 -*-
r"""Ablacion de entradas con la muestra 2025 bajo el esquema de CV aprobado (PROTOCOLO,
"Validacion cruzada, puntos dirigidos y reporte", 20-sep-2026).

PREGUNTA. Que aporta cada fuente al clasificador de seis clases: optico de Sentinel-2
(cubo 2025), banda C de Sentinel-1 (orbita 142) y banda L de NISAR (traza 083). La
ablacion principal de la tesis es la de NISAR: O+C+L frente a O+C.

ENTRADAS
  etiquetas_2025.csv            clase_final, lon, lat (720 puntos)
  pliegues_cv.csv               pliegue 1-5 y bloque de 12 km por id (congelado, hash en PROTOCOLO)
  ../../RADAR/clave_muestra2025_puntos.csv   VV, VH (mediana de 61 pasadas S1) y HH, HV
                                (mediana de 12 escenas NISAR), extraidos por clave_vs_muestra2025.py
  cubo s2 2025 en GEE           medianas anuales de B2, B3, B4, B8, B11, B12, NDVI, NDWI, CMRI
                                y minimo, maximo y amplitud de NDVI (12 imagenes mensuales)

ESQUEMA. k = 5 pliegues por bloques de 12 km; al evaluar un pliegue se retiran del
entrenamiento los puntos a menos de BUFER m de cualquier punto de prueba (2,6 km por
defecto; --bufer 0|2600|5200 para la sensibilidad declarada). Random Forest de 500 arboles
con hiperparametros fijos (sin ajuste interno: la pregunta es sobre las entradas, no sobre
el modelo). Predicciones fuera de pliegue (OOF) para cada brazo.

REPORTE (segun el protocolo)
  - macro-F1 OOF por brazo, y pliegue a pliegue (minimo, maximo)
  - F1 por clase con intervalo por remuestreo de bloques (24 bloques, 2000 repeticiones),
    con la proporcion de repeticiones sin la clase
  - prueba principal entre brazos: permutacion pareada en el nivel de bloque sobre la
    diferencia de macro-F1 OOF (2000 permutaciones); McNemar solo como cifra de comparacion
  - manglar_degradado: su F1 se declara de potencia muy baja (protocolo); se reporta igual

SENSIBILIDAD (protocolo): --bufer 0|2600|5200 y --k 10. Con --k 10 los 24 bloques se reparten
en diez pliegues con la misma regla determinista de 32_esquema_cv.py (de mayor a menor numero
de puntos, cada bloque al pliegue mas vacio).

SERIE TEMPORAL (--serie): brazo Os = las 6 bandas medianas mas NDVI y NDWI de cada uno de los
12 meses de 2025 (24 variables; un mes sin dato en un punto se rellena con la mediana anual
de ese punto, y se reporta cuantos). Brazos Os, Os+C, Os+L, Os+C+L; contrastes Os vs O,
Os+C+L vs Os+C, Os+C vs Os.

USO: python 40_ablacion_entradas.py [--bufer 2600] [--k 5] [--serie] [--sin-gee]
Salidas: ablacion_2025_rasgos.csv (cache de rasgos), ablacion_2025_oof.csv,
         ablacion_2025_resumen.csv, ablacion_2025_clases.csv, ablacion_2025_pruebas.csv
         (con sufijo _bufer0, _bufer5200, _k10 o _serie segun la corrida)
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

AQUI = Path(__file__).resolve().parent
RADAR = AQUI.parent.parent / "RADAR" / "clave_muestra2025_puntos.csv"
RAIZ = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/"
SEMILLA = 20261007
OPT = ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI", "NDWI", "CMRI", "ndvi_min", "ndvi_max", "ndvi_amp"]
BANDA_C = ["VV", "VH", "VVmVH"]
BANDA_L = ["HH", "HV", "HHmHV"]
BRAZOS = {"O": OPT, "C": BANDA_C, "L": BANDA_L, "O+C": OPT + BANDA_C, "O+L": OPT + BANDA_L,
          "C+L": BANDA_C + BANDA_L, "O+C+L": OPT + BANDA_C + BANDA_L}
CONTRASTES = [("O+C+L", "O+C"), ("O+C", "O"), ("O+L", "O"), ("O+C+L", "O"), ("C+L", "C")]
N_REP = 2000


def rasgos_optico(d):
    """Medianas anuales 2025 del cubo S2 y estadisticos de NDVI, por tandas de 100 puntos."""
    import ee
    ee.Initialize(project="basic-buttress-338101")
    col = ee.ImageCollection([ee.Image(RAIZ + "2025%02d" % m) for m in range(1, 13)])
    ndvi = col.select("NDVI")
    st = ee.Image.cat(col.select(["B2", "B3", "B4", "B8", "B11", "B12", "NDVI", "NDWI", "CMRI"]).median(),
                      ndvi.min().rename("ndvi_min"), ndvi.max().rename("ndvi_max"))
    out = []
    for k in range(0, len(d), 100):
        s = d.iloc[k:k + 100]
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([float(r.lon), float(r.lat)]), {"id": int(r.id)})
                                   for r in s.itertuples()])
        out += [f["properties"] for f in st.reduceRegions(fc, ee.Reducer.first(), 10, tileScale=4)
                .getInfo()["features"]]
        print("  S2 %d / %d" % (min(k + 100, len(d)), len(d)), flush=True)
    g = pd.DataFrame(out)
    g["ndvi_amp"] = g.ndvi_max - g.ndvi_min
    return g


MESES = ["%02d" % m for m in range(1, 13)]
SERIE = ["ndvi_" + m for m in MESES] + ["ndwi_" + m for m in MESES]


def rasgos_serie(d):
    """NDVI y NDWI de cada mes de 2025 por punto (sin rellenar; el relleno se hace en cargar)."""
    import ee
    ee.Initialize(project="basic-buttress-338101")
    st = ee.Image.cat([ee.Image(RAIZ + "2025" + m).select(["NDVI", "NDWI"]).rename(["ndvi_" + m, "ndwi_" + m])
                       for m in MESES])
    out = []
    for k in range(0, len(d), 100):
        s = d.iloc[k:k + 100]
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([float(r.lon), float(r.lat)]), {"id": int(r.id)})
                                   for r in s.itertuples()])
        out += [f["properties"] for f in st.reduceRegions(fc, ee.Reducer.first(), 10, tileScale=4)
                .getInfo()["features"]]
        print("  S2 serie %d / %d" % (min(k + 100, len(d)), len(d)), flush=True)
    return pd.DataFrame(out)


def pliegues_k(p, k):
    """Reparte los bloques de 12 km en k pliegues con la regla de 32_esquema_cv.py."""
    n = p.bloque12.value_counts().sort_index().sort_values(ascending=False, kind="stable")
    carga, asign = np.zeros(k, int), {}
    for b, c in n.items():
        f = int(np.argmin(carga))
        asign[b], carga[f] = f + 1, carga[f] + c
    return p.bloque12.map(asign)


def cargar(sin_gee, k, serie):
    e = pd.read_csv(AQUI / "etiquetas_2025.csv")[["id", "lon", "lat", "clase_final", "borde"]]
    p = pd.read_csv(AQUI / "pliegues_cv.csv")
    if k != 5:
        p["pliegue"] = pliegues_k(p, k)
    r = pd.read_csv(RADAR)[["id"] + BANDA_C + BANDA_L]
    cache = AQUI / "ablacion_2025_rasgos.csv"
    if cache.exists() or sin_gee:
        o = pd.read_csv(cache)
    else:
        o = rasgos_optico(e)
        o.to_csv(cache, index=False, lineterminator="\n")
    d = e.merge(p, on="id").merge(r, on="id").merge(o, on="id")
    if serie:
        cache_s = AQUI / "ablacion_2025_rasgos_serie.csv"
        if cache_s.exists() or sin_gee:
            s = pd.read_csv(cache_s)
        else:
            s = rasgos_serie(e)
            s.to_csv(cache_s, index=False, lineterminator="\n")
        d = d.merge(s, on="id")
        faltan = d[SERIE].isna().sum().sum()
        print("serie: %d valores mes-punto sin dato de %d (%.1f %%), rellenados con la mediana anual del punto"
              % (faltan, len(d) * len(SERIE), 100 * faltan / (len(d) * len(SERIE))), flush=True)
        for m in MESES:
            d["ndvi_" + m] = d["ndvi_" + m].fillna(d.NDVI)
            d["ndwi_" + m] = d["ndwi_" + m].fillna(d.NDWI)
    assert len(d) == 720, len(d)
    return d


def oof(d, cols, bufer):
    """Predicciones fuera de pliegue con bufer espacial alrededor de la prueba."""
    x, y = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values)
    XY = np.c_[x, y]
    X, Y = d[cols].to_numpy(), d.clase_final.to_numpy()
    pred = np.empty(len(d), dtype=object)
    for k in sorted(d.pliegue.unique()):
        te, tr = (d.pliegue == k).to_numpy(), (d.pliegue != k).to_numpy(copy=True)
        if bufer > 0:
            tr &= cKDTree(XY[te]).query(XY)[0] >= bufer
        rf = RandomForestClassifier(n_estimators=500, random_state=SEMILLA, n_jobs=-1)
        rf.fit(X[tr], Y[tr])
        pred[te] = rf.predict(X[te])
    return pred


def macro(y, p, clases):
    return f1_score(y, p, labels=clases, average="macro", zero_division=0)


def permutacion_bloques(y, pa, pb, bloques, clases, rng):
    """Permutacion pareada: en cada bloque se intercambian las predicciones de los dos brazos
    con probabilidad 1/2; estadistico = diferencia de macro-F1 OOF."""
    obs = macro(y, pa, clases) - macro(y, pb, clases)
    ub = np.unique(bloques)
    dist = np.empty(N_REP)
    for i in range(N_REP):
        swap = np.isin(bloques, ub[rng.random(len(ub)) < 0.5])
        a, b = np.where(swap, pb, pa), np.where(swap, pa, pb)
        dist[i] = macro(y, a, clases) - macro(y, b, clases)
    return obs, float((np.abs(dist) >= abs(obs) - 1e-12).mean())


def mcnemar(y, pa, pb):
    from scipy.stats import binomtest
    b, c = int(((pa == y) & (pb != y)).sum()), int(((pa != y) & (pb == y)).sum())
    return b, c, (binomtest(b, b + c).pvalue if b + c else 1.0)


def main():
    bufer = int(sys.argv[sys.argv.index("--bufer") + 1]) if "--bufer" in sys.argv else 2600
    k = int(sys.argv[sys.argv.index("--k") + 1]) if "--k" in sys.argv else 5
    serie = "--serie" in sys.argv
    d = cargar("--sin-gee" in sys.argv, k, serie)
    clases = sorted(d.clase_final.unique())
    y, bloques = d.clase_final.to_numpy(), d.bloque12.to_numpy()
    print("puntos %d | clases %s | bufer %d m | k %d" % (len(d), d.clase_final.value_counts().to_dict(), bufer, k), flush=True)
    brazos, contrastes = dict(BRAZOS), list(CONTRASTES)
    if serie:
        OS = ["B2", "B3", "B4", "B8", "B11", "B12"] + SERIE
        brazos = {"O": OPT, "Os": OS, "O+C": OPT + BANDA_C, "Os+C": OS + BANDA_C, "Os+L": OS + BANDA_L,
                  "Os+C+L": OS + BANDA_C + BANDA_L}
        contrastes = [("Os", "O"), ("Os+C+L", "Os+C"), ("Os+C", "Os"), ("Os+L", "Os"), ("Os+C", "O+C")]
    BRAZOS.clear(); BRAZOS.update(brazos)

    P = {}
    for nombre, cols in BRAZOS.items():
        P[nombre] = oof(d, cols, bufer)
        print("  %-6s macro-F1 OOF %.3f" % (nombre, macro(y, P[nombre], clases)), flush=True)
    sal = d[["id", "bloque12", "pliegue", "clase_final", "borde"]].copy()
    for n in P:
        sal["pred_" + n.replace("+", "")] = P[n]

    rng = np.random.default_rng(SEMILLA)
    ub = np.unique(bloques)
    resumen, por_clase = [], []
    for n, p in P.items():
        porpl = [macro(y[d.pliegue == k], p[d.pliegue == k], clases) for k in sorted(d.pliegue.unique())]
        boot = []
        for _ in range(N_REP):
            idx = np.concatenate([np.where(bloques == b)[0] for b in rng.choice(ub, len(ub))])
            boot.append(f1_score(y[idx], p[idx], labels=clases, average=None, zero_division=0))
        boot = np.array(boot)
        resumen.append(dict(brazo=n, variables=len(BRAZOS[n]), macro_f1=round(macro(y, p, clases), 3),
                            macro_f1_min_pliegue=round(min(porpl), 3), macro_f1_max_pliegue=round(max(porpl), 3),
                            exactitud=round((y == p).mean(), 3)))
        for j, c in enumerate(clases):
            f = f1_score(y, p, labels=[c], average="macro", zero_division=0)
            sin = [(y[np.concatenate([np.where(bloques == b)[0] for b in rng.choice(ub, len(ub))])] == c).sum() == 0
                   for _ in range(200)]
            por_clase.append(dict(brazo=n, clase=c, n=int((y == c).sum()), f1=round(f, 3),
                                  ic95_bajo=round(np.percentile(boot[:, j], 2.5), 3),
                                  ic95_alto=round(np.percentile(boot[:, j], 97.5), 3),
                                  rep_sin_clase=round(float(np.mean(sin)), 3)))
    pruebas = []
    for a, b in contrastes:
        obs, pperm = permutacion_bloques(y, P[a], P[b], bloques, clases, rng)
        nb, nc, pmc = mcnemar(y, P[a], P[b])
        pruebas.append(dict(contraste="%s vs %s" % (a, b), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pperm, 3),
                            mcnemar_solo_a=nb, mcnemar_solo_b=nc, p_mcnemar=round(pmc, 3)))
    R, C, T = pd.DataFrame(resumen), pd.DataFrame(por_clase), pd.DataFrame(pruebas)
    suf = ("" if bufer == 2600 else "_bufer%d" % bufer) + ("" if k == 5 else "_k%d" % k) + ("_serie" if serie else "")
    sal.to_csv(AQUI / ("ablacion_2025_oof%s.csv" % suf), index=False, lineterminator="\n")
    R.to_csv(AQUI / ("ablacion_2025_resumen%s.csv" % suf), index=False, lineterminator="\n")
    C.to_csv(AQUI / ("ablacion_2025_clases%s.csv" % suf), index=False, lineterminator="\n")
    T.to_csv(AQUI / ("ablacion_2025_pruebas%s.csv" % suf), index=False, lineterminator="\n")
    print("\n" + R.to_string(index=False))
    print("\n" + C.pivot(index="clase", columns="brazo", values="f1")[list(BRAZOS)].to_string())
    print("\n" + T.to_string(index=False))
    print("\nLectura: la ablacion de NISAR es O+C+L frente a O+C; p de permutacion por bloques es la "
          "prueba principal (24 bloques); McNemar solo para comparar cifras.")


if __name__ == "__main__":
    main()
