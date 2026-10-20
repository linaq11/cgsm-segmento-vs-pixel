# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): contexto multiescala como rasgo.

Hasta ahora cada escala de contexto entró sola (píxel + medias de su segmento a una escala). Aquí el píxel recibe a la vez
las medias de sus celdas de 0,25, 1 y 4 ha (SLIC) o de sus objetos de Felzenszwalb de 0,25 y 1 ha más la celda SLIC de 4
ha, reutilizando las tablas por segmento ya agregadas en Earth Engine por 03 (segmentos_puntos_<seg>.csv). Misma CV
congelada, contraste de permutación frente al píxel unión (0,591), bordes e interior.

SALIDAS: multiescala_2025_{resumen,pruebas,bordes,oof}.csv
USO: python 21_contexto_multiescala.py
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
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
BUFER = 2600
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)
F_S2, F_AE = v01.F_S2, v01.F_AE
SEGC = F_S2 + F_AE


def ids_en_puntos(seg_tif, d):
    from pyproj import Transformer
    with rasterio.open(seg_tif) as src:
        tr = src.transform; H, W = src.height, src.width
        x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
        fil, col = rasterio.transform.rowcol(tr, x, y); fil = np.clip(fil, 0, H - 1); col = np.clip(col, 0, W - 1)
        seg = src.read(1)
    return seg[fil, col].astype("int64")


def contexto(d, segn, pref):
    ids = ids_en_puntos(DATOS / ("segmentos_%s.tif" % segn), d)
    vs = pd.read_csv(AQUI / ("segmentos_puntos_%s.csv" % segn))
    if "sid" in vs.columns and vs.sid.nunique() < len(vs):
        vs = vs.drop_duplicates("sid")
    t = pd.DataFrame({"sid": ids}).merge(vs[["sid"] + SEGC], on="sid", how="left")
    for c in SEGC:                                   # sin segmento o sin agregacion: la variable del pixel
        t[c] = t[c].fillna(pd.Series(d[c].values))
    t.columns = ["sid"] + [pref + c for c in SEGC]
    return t.drop(columns="sid")


def main():
    from sklearn.metrics import f1_score
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv").merge(pd.read_csv(AQUI / "pixel_2025_oof.csv")[["id", "oof_s2_mas_alphaearth"]], on="id")
    for c in SEGC:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    partes = {"c025_": "slic_025ha", "c1_": "slic_fino", "c4_": "slic_4ha", "f025_": "felz_025ha", "f1_": "felz_1ha"}
    for pref, segn in partes.items():
        d = pd.concat([d.reset_index(drop=True), contexto(d, segn, pref).reset_index(drop=True)], axis=1)
    for c in d.columns:
        if d[c].dtype != object and d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median")).fillna(d[c].median())
    y = d.clase_final.to_numpy(); bloques = d.bloque12.to_numpy(); pp = d.oof_s2_mas_alphaearth.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    borde = d.borde_final.astype(str).str.lower().isin(["si", "sí", "true", "1"]).to_numpy()
    def cols(*prefs): return SEGC + [p + c for p in prefs for c in SEGC]
    brazos = {"pixel_mas_slic_025_1_4": cols("c025_", "c1_", "c4_"), "pixel_mas_felz_025_1_mas_slic_4": cols("f025_", "f1_", "c4_"), "pixel_mas_slic_025_1": cols("c025_", "c1_"), "pixel_mas_felz_025_1": cols("f025_", "f1_")}
    res, pr, bor, oofs = [], [], [], {}
    for nombre, cc in brazos.items():
        p = abl.oof(d, cc, BUFER); oofs[nombre] = p
        por_pl = [abl.macro(y[d.pliegue == k], p[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, n_vars=len(cc), macro_f1_oof=round(abl.macro(y, p, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((p == y).mean()), 3),
                        **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y, p, labels=CLASES, average=None, zero_division=0))}))
        obs, pv = abl.permutacion_bloques(y, p, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y, p, pp)
        pr.append(dict(brazo=nombre, contraste=nombre + " − pixel union", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        for g, m in (("borde", borde), ("interior", ~borde)):
            bor.append(dict(brazo=nombre, grupo=g, n=int(m.sum()), macro_f1_pixel=round(abl.macro(y[m], pp[m], CLASES), 3), macro_f1_brazo=round(abl.macro(y[m], p[m], CLASES), 3)))
        print("%-34s OOF macro-F1 %.3f (pliegues %.3f a %.3f) | − pixel union %+.3f (p %.3f) | borde %.3f interior %.3f | humedal %.2f" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv, bor[-2]["macro_f1_brazo"], bor[-1]["macro_f1_brazo"], res[-1]["f1_humedal_herbaceo"]), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "multiescala_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "multiescala_2025_pruebas.csv", index=False); pd.DataFrame(bor).to_csv(AQUI / "multiescala_2025_bordes.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y, pliegue=d.pliegue, oof_pixel_union=pp, **{"oof_" + n: p for n, p in oofs.items()})).to_csv(AQUI / "multiescala_2025_oof.csv", index=False)


if __name__ == "__main__":
    main()
