# -*- coding: utf-8 -*-
r"""Curva de aprendizaje de la clase humedal herbáceo sobre la muestra de 820 (Informe 2, segunda ronda).

Se quitan al azar puntos de humedal hasta dejar 40, 73 (ronda 1), 90 y 113 (todos), cinco sorteos por tamaño, y se repite
el píxel unión con la misma CV congelada. Se reporta el F1 de humedal, el de degradado y la macro-F1. Además la variante
con humedal y degradado fusionados (cinco clases).

SALIDAS: curva_humedal_820.csv, fusion_humedal_degradado_820.csv
USO: python 25_curva_humedal.py
"""
import importlib.util
import os

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]


def mod(n, f):
    s = importlib.util.spec_from_file_location(n, f); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main():
    from sklearn.metrics import f1_score
    v01 = mod("v01", AQUI / "01_variables_2025.py"); abl = mod("abl", MUESTRA / "40_ablacion_entradas.py")
    COLS = v01.F_S2 + v01.F_AE
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv")
    for c in COLS:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    hum = d.index[d.clase_final == "humedal_herbaceo"].to_numpy(); rng = np.random.default_rng(20261019); filas = []
    for n in (40, 73, 90, 113):
        for r in range(5 if n < len(hum) else 1):
            keep = np.ones(len(d), bool); keep[rng.choice(hum, len(hum) - n, replace=False)] = False
            dd = d[keep].reset_index(drop=True); p = abl.oof(dd, COLS, 2600); y = dd.clase_final.to_numpy()
            f = f1_score(y, p, labels=CLASES, average=None)
            filas.append(dict(n_humedal=n, sorteo=r, f1_humedal=round(f[1], 3), f1_degradado=round(f[2], 3), macro_f1=round(abl.macro(y, p, CLASES), 3)))
        print("n %d: %s" % (n, filas[-1]), flush=True)
    pd.DataFrame(filas).to_csv(AQUI / "curva_humedal_820.csv", index=False)
    dd = d.copy(); dd["clase_final"] = dd.clase_final.replace({"humedal_herbaceo": "humedal_o_degradado", "manglar_degradado": "humedal_o_degradado"})
    C5 = ["agua", "humedal_o_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]; p = abl.oof(dd, COLS, 2600); y = dd.clase_final.to_numpy()
    f = f1_score(y, p, labels=C5, average=None)
    pd.DataFrame([dict(macro_f1=round(abl.macro(y, p, C5), 3), exactitud=round(float((p == y).mean()), 3), **{"f1_" + c: round(x, 3) for c, x in zip(C5, f)})]).to_csv(AQUI / "fusion_humedal_degradado_820.csv", index=False)
    print("fusión: macro-F1 %.3f exactitud %.3f" % (abl.macro(y, p, C5), (p == y).mean()), flush=True)


if __name__ == "__main__":
    main()
