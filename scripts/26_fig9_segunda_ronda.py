# -*- coding: utf-8 -*-
r"""Figura 9 del Informe 2: segunda ronda. a) curva de aprendizaje de humedal sobre los 820 (informe2_ampliada/curva_humedal_820.csv),
b) macro-F1 de los brazos principales en las dos rondas, leída de los resúmenes reales de informe2/ e informe2_ampliada/.
SALIDA: figuras/fig9_segunda_ronda.png
USO: python 26_fig9_segunda_ronda.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
AMP = AQUI.parent / "informe2_ampliada"
FIG = AQUI / "figuras"


def macro(dirn, archivo, brazo):
    d = pd.read_csv(dirn / archivo); return float(d.loc[d.brazo == brazo, "macro_f1_oof"].iloc[0])


def main():
    c = pd.read_csv(AMP / "curva_humedal_820.csv"); g = c.groupby("n_humedal").agg(["mean", "std"])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.4]})
    for col, nombre, color in (("f1_humedal", "F1 humedal herbáceo", "#b8a63c"), ("f1_degradado", "F1 manglar degradado", "#e6963c"), ("macro_f1", "macro-F1 (6 clases)", "#333333")):
        ax[0].errorbar(g.index, g[col]["mean"], yerr=g[col]["std"].fillna(0), fmt="o-", color=color, capsize=3, label=nombre)
    ax[0].set_xlabel("puntos de humedal herbáceo en la muestra"); ax[0].set_ylabel("F1 fuera de pliegue"); ax[0].set_xticks([40, 73, 90, 113]); ax[0].grid(alpha=0.3); ax[0].legend(fontsize=8); ax[0].set_title("a) Curva de aprendizaje del humedal (820 puntos)", loc="left", fontsize=10)
    ax[0].axvline(73, color="grey", ls=":", lw=0.8); ax[0].text(73.5, 0.05, "ronda 1", fontsize=7, color="grey")
    brazos = [("píxel unión", "pixel_2025_resumen.csv", "s2_mas_alphaearth"), ("SLIC 0,25 ha\nsegmento", "segmento_2025_resumen_slic_025ha.csv", "s2_mas_alphaearth"),
              ("SLIC 0,25 ha\npíxel + contexto", "segmento_2025_resumen_slic_025ha.csv", "pixel_mas_segmento"), ("Felz 1 ha\nsegmento", "segmento_2025_resumen_felz_1ha.csv", "s2_mas_alphaearth"),
              ("píxel + Felz\n0,25 y 1 ha", "multiescala_2025_resumen.csv", "pixel_mas_felz_025_1"), ("filtro 5x5", "filtro5_2025_resumen.csv", "pixel_union_filtro5"),
              ("SLIC 4 ha\nsegmento", "segmento_2025_resumen_slic_4ha.csv", "s2_mas_alphaearth"), ("SLIC 16 ha\nsegmento", "segmento_2025_resumen_slic_16ha.csv", "s2_mas_alphaearth"), ("SAM grueso\nsegmento", "segmento_2025_resumen_sam.csv", "s2_mas_alphaearth")]
    v720 = [macro(AQUI, a, b) for _, a, b in brazos]; v820 = [macro(AMP, a, b) for _, a, b in brazos]; x = np.arange(len(brazos))
    ax[1].bar(x - 0.2, v720, 0.4, color="#7a9cc6", label="ronda 1: 720 puntos"); ax[1].bar(x + 0.2, v820, 0.4, color="#1f4e79", label="ronda 2: 820 puntos")
    ax[1].axhline(v720[0], color="#7a9cc6", ls="--", lw=0.8); ax[1].axhline(v820[0], color="#1f4e79", ls="--", lw=0.8)
    for i, (a, b) in enumerate(zip(v720, v820)):
        ax[1].text(i - 0.2, a + 0.005, "%.2f" % a, ha="center", fontsize=6.5); ax[1].text(i + 0.2, b + 0.005, "%.2f" % b, ha="center", fontsize=6.5)
    ax[1].set_xticks(x); ax[1].set_xticklabels([n.replace("\n", " ") for n, _, _ in brazos], fontsize=7, rotation=28, ha="right"); ax[1].set_ylim(0.3, 0.68); ax[1].set_ylabel("macro-F1 fuera de pliegue"); ax[1].grid(axis="y", alpha=0.3); ax[1].legend(fontsize=8, loc="upper right")
    ax[1].set_title("b) Brazos principales en las dos rondas (líneas: píxel unión)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "fig9_segunda_ronda.png", dpi=170); print("fig9 escrita")


if __name__ == "__main__":
    main()
