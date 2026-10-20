# -*- coding: utf-8 -*-
r"""Reúne los contrastes segmento − píxel de todos los segmentadores, marca el contraste primario declarado en el
PLAN (SLIC de 1 ha frente a píxel, entrada unión) y aplica Holm sobre la familia completa de contrastes.

ENTRADAS: segmento_2025_pruebas_<seg>.csv y segmento_2025_resumen_<seg>.csv (de 03), pixel_2025_resumen.csv (de 01).
SALIDAS: resumen_segmento_vs_pixel.csv (tabla maestra) y resumen_segmento_vs_pixel.md.
USO: python 05_pruebas_holm.py
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
PRIMARIO = ("slic_fino", "s2_mas_alphaearth")          # SLIC de 1 ha, entrada union


def holm(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p); adj = np.empty(m); run = 0.0
    for k, i in enumerate(o):
        run = max(run, (m - k) * p[i]); adj[i] = min(1.0, run)
    return adj


def main():
    pix = pd.read_csv(AQUI / "pixel_2025_resumen.csv").set_index("brazo")
    filas = []
    for f in sorted(glob.glob(str(AQUI / "segmento_2025_pruebas_*.csv"))):
        seg = Path(f).stem.replace("segmento_2025_pruebas_", "")
        pr = pd.read_csv(f); rs = pd.read_csv(AQUI / ("segmento_2025_resumen_%s.csv" % seg)).set_index("brazo")
        for _, r in pr.iterrows():
            ref = "s2_mas_alphaearth" if r.entrada == "pixel_mas_segmento" else r.entrada
            filas.append(dict(segmentador=seg, entrada=r.entrada, contraste=r.contraste, macro_f1_pixel=pix.loc[ref, "macro_f1_oof"],
                              macro_f1_brazo=rs.loc[r.entrada, "macro_f1_oof"], dif=r.dif_macro_f1, p_permutacion=r.p_permutacion_bloques, p_mcnemar=r.p_mcnemar,
                              primario=(seg == PRIMARIO[0] and r.entrada == PRIMARIO[1])))
    # brazo de voto por mayoria (06), si existe: entra a la misma familia
    fv = AQUI / "voto_2025_pruebas.csv"
    if fv.exists():
        vr = pd.read_csv(AQUI / "voto_2025_resumen.csv").set_index("segmentador")
        for _, r in pd.read_csv(fv).iterrows():
            filas.append(dict(segmentador=r.segmentador, entrada="voto_mayoria_union", contraste=r.contraste, macro_f1_pixel=pix.loc["s2_mas_alphaearth", "macro_f1_oof"],
                              macro_f1_brazo=vr.loc[r.segmentador, "macro_f1_oof"], dif=r.dif_macro_f1, p_permutacion=r.p_permutacion_bloques, p_mcnemar=r.p_mcnemar, primario=False))
    t = pd.DataFrame(filas)
    t["p_holm"] = holm(t.p_permutacion.values)
    t["significativo_holm"] = t.p_holm < 0.05
    t = t.sort_values(["primario", "segmentador", "entrada"], ascending=[False, True, True])
    t.to_csv(AQUI / "resumen_segmento_vs_pixel.csv", index=False)
    md = ["# Segmento frente a píxel: familia de contrastes con Holm", "", "Contraste primario declarado: %s con la entrada %s. Familia: %d contrastes. DMD de la prueba: 0,016 de macro-F1 (potencia 0,80)." % (PRIMARIO[0], PRIMARIO[1], len(t)), "",
          "| Segmentador | Entrada | Contraste | macro-F1 píxel | macro-F1 brazo | Diferencia | p permutación | p Holm | Primario |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        md.append("| %s | %s | %s | %.3f | %.3f | %+.3f | %.4f | %.4f | %s |" % (r.segmentador, r.entrada, r.contraste, r.macro_f1_pixel, r.macro_f1_brazo, r.dif, r.p_permutacion, r.p_holm, "sí" if r.primario else ""))
    open(AQUI / "resumen_segmento_vs_pixel.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
