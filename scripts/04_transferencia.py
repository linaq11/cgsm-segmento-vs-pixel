# -*- coding: utf-8 -*-
r"""Transferencia temporal 2021 → 2025 por pixel: entrenar con las 600 etiquetas debiles de WorldCover 2021
(Informe 1) y evaluar sobre la muestra propia de 2025, con las mismas tres entradas.

CLASES. El Informe 1 tiene cuatro (manglar, agua, humedal_herbaceo, otro); la muestra 2025 tiene seis. Para
evaluar se agrupa la referencia 2025 a las cuatro de 2021: manglar_intacto y manglar_degradado → manglar;
agua, humedal_herbaceo y otro iguales. vegetacion_flotante no tiene clase en 2021 (en WorldCover es agua o
humedal) y se EXCLUYE de la evaluacion; se reporta aparte que clase le asigna el modelo de 2021.

COMPARACION. Para cada entrada: (a) modelo 2021 → 2025 (transferencia, sin reentrenar); (b) modelo 2025 con
validacion cruzada congelada, con las predicciones OOF de 01 agrupadas a cuatro clases (lo que se obtiene
entrenando en el mismo anio); la diferencia (a) − (b) es la degradacion por transferencia, que Ball et al.
(2026) situan entre 9 y 14 %.

SALIDAS: transferencia_2021_2025_resumen.csv, transferencia_2021_2025_clases.csv, transferencia_2021_2025_flotante.csv
USO: python 04_transferencia.py
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

AQUI = Path(__file__).resolve().parent
INF1 = AQUI.parent / "informe1" / "linea_base_2021" / "variables_puntos.csv"
AE21 = AQUI.parent.parent / "AVANCE TESIS" / "PILOTO_BENCHMARK" / "alphaearth2021_etiquetas.csv"
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
F_S2, F_AE, BRAZOS = v01.F_S2, v01.F_AE, v01.BRAZOS
SEMILLA = 20261007
A4 = {"manglar_intacto": "manglar", "manglar_degradado": "manglar", "agua": "agua", "humedal_herbaceo": "humedal_herbaceo", "otro": "otro"}
CLASES4 = ["agua", "humedal_herbaceo", "manglar", "otro"]


def main():
    t21 = pd.read_csv(INF1); a21 = pd.read_csv(AE21)
    assert len(t21) == len(a21) == 600
    assert np.allclose(t21.lon.values, a21.lon.values) and np.allclose(t21.lat.values, a21.lat.values), "las dos tablas de 2021 no estan alineadas"
    for a in F_AE:
        t21[a] = a21[a].values
    t21 = t21.rename(columns={c: c.replace("hum_", "humeda_", 1) for c in t21.columns if c.startswith("hum_")})   # prefijo de 2021 → el de 2025
    faltan = [c for c in F_S2 if c not in t21]
    assert not faltan, "variables 2021 que faltan: %s" % faltan
    t21 = t21.dropna(subset=F_S2 + F_AE); print("2021: %d puntos con las 94 variables" % len(t21))
    d25 = pd.read_csv(AQUI / "variables_2025_puntos.csv"); oof = pd.read_csv(AQUI / "pixel_2025_oof.csv")
    for c in F_S2 + F_AE:
        if d25[c].isna().any(): d25[c] = d25[c].fillna(d25.groupby("clase_final")[c].transform("median"))
    # las reflectancias de 2021 estan en 0-1 y las de 2025 en x10000 (asset del cubo): se igualan; los indices y la fenologia ya son adimensionales
    for c in F_S2:
        if c.split("_")[1].startswith("B"): d25[c] = d25[c] / 10000.0
    ev = d25.clase_final != "vegetacion_flotante"
    y25 = d25.clase_final.map(A4)
    res, cls, flot = [], [], []
    for nombre, cols in BRAZOS.items():
        rf = RandomForestClassifier(n_estimators=500, random_state=SEMILLA, n_jobs=-1).fit(t21[cols].to_numpy(), t21.clase_nombre.to_numpy())
        p21 = rf.predict(d25[cols].to_numpy())
        p25 = oof["oof_" + nombre].map(A4).fillna("vegetacion_flotante").to_numpy()   # predecir flotante en un punto no flotante cuenta como error
        yv, pt, pc = y25[ev].to_numpy(), p21[ev.to_numpy()], p25[ev.to_numpy()]
        ft, fc = f1_score(yv, pt, labels=CLASES4, average="macro"), f1_score(yv, pc, labels=CLASES4, average="macro")
        res.append(dict(entrada=nombre, n_eval=int(ev.sum()), macro_f1_2021_a_2025=round(ft, 3), exactitud_2021_a_2025=round(float((pt == yv).mean()), 3),
                        macro_f1_2025_cv=round(fc, 3), exactitud_2025_cv=round(float((pc == yv).mean()), 3), degradacion=round(ft - fc, 3), degradacion_pct=round(100 * (ft - fc) / fc, 1)))
        for c, a, b in zip(CLASES4, f1_score(yv, pt, labels=CLASES4, average=None), f1_score(yv, pc, labels=CLASES4, average=None)):
            cls.append(dict(entrada=nombre, clase=c, n=int((yv == c).sum()), f1_2021_a_2025=round(a, 3), f1_2025_cv=round(b, 3)))
        vf = pd.Series(p21[~ev.to_numpy()]).value_counts()
        flot.append(dict(entrada=nombre, n_flotante=int((~ev).sum()), **{"a_" + k: int(v) for k, v in vf.items()}))
        print("%-20s 2021→2025 macro-F1 %.3f (exact. %.3f) | 2025 CV %.3f (%.3f) | degradación %+.3f (%+.1f %%) | flotante → %s" % (nombre, ft, (pt == yv).mean(), fc, (pc == yv).mean(), ft - fc, 100 * (ft - fc) / fc, vf.to_dict()), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "transferencia_2021_2025_resumen.csv", index=False)
    pd.DataFrame(cls).to_csv(AQUI / "transferencia_2021_2025_clases.csv", index=False)
    pd.DataFrame(flot).to_csv(AQUI / "transferencia_2021_2025_flotante.csv", index=False)
    print(pd.DataFrame(cls).pivot(index="clase", columns="entrada", values=["f1_2021_a_2025", "f1_2025_cv"]).round(3).to_string())


if __name__ == "__main__":
    main()
