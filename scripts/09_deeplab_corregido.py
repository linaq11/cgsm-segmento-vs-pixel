# -*- coding: utf-8 -*-
r"""Exploratorio DeepLabV3+ con etiquetas débiles CORREGIDAS por los puntos propios (decisión de Lina, 2026-10-19).

Igual que 08_deeplab.py, pero la etiqueta de cada pliegue k es el mapa RF del pliegue (mapa_pixel_2025_k<k>.tif) con el
segmento SLIC de 0,25 ha de cada punto de ENTRENAMIENTO (pliegue != k y a más de 2,6 km de los puntos de prueba, mismo
búfer que la CV congelada) pintado con la clase real del punto. Los puntos de prueba nunca se pintan. Pregunta: ¿720
parches limpios bastan para que la red corrija al maestro?

SALIDAS: datos/deeplab/etiqueta_corr_k<k>.tif, mapa_deeplab_kc<k>.tif, deeplab_corr_2025_{resumen,pruebas,oof}.csv
USO: python 09_deeplab_corregido.py [--epocas 15]
"""
import importlib.util
import os
import sys

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m08", AQUI / "08_deeplab.py")
m08 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m08)
DATOS, OUT, MUESTRA, CLASES, abl = m08.DATOS, m08.OUT, m08.MUESTRA, m08.CLASES, m08.abl
BUFER = 2600


def main():
    import rasterio
    from pyproj import Transformer
    from rasterio.transform import rowcol
    from scipy.spatial import cKDTree
    from sklearn.metrics import f1_score
    OUT.mkdir(exist_ok=True)
    img = m08.imagen_8bit()
    d = pd.read_csv(AQUI / "pixel_2025_oof.csv").merge(pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]], on="id")
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        trf = src.transform
    with rasterio.open(DATOS / "segmentos_slic_025ha.tif") as src:
        seg = src.read(1).astype(np.int64)
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
    fil, col = rowcol(trf, x, y); fil = np.clip(fil, 0, 6021); col = np.clip(col, 0, 7149)
    xu, yu = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values); XY = np.c_[xu, yu]
    cnum = np.array([CLASES.index(c) + 1 for c in d.clase_final])
    pred = np.empty(len(d), dtype=object)
    for k in sorted(d.pliegue.unique()):
        te, tr = (d.pliegue == k).to_numpy(), (d.pliegue != k).to_numpy(copy=True)
        tr &= cKDTree(XY[te]).query(XY)[0] >= BUFER
        etiqueta = OUT / ("etiqueta_corr_k%d.tif" % k)
        if not etiqueta.exists():
            with rasterio.open(DATOS / ("mapa_pixel_2025_k%d.tif" % k)) as src:
                lab = src.read(1); prof = src.profile
            lut = np.zeros(int(seg.max()) + 1, dtype=np.uint8)
            sids = seg[fil[tr], col[tr]]; lut[sids[sids > 0]] = cnum[tr][sids > 0]
            pintado = lut[seg]; m = pintado > 0; lab[m] = pintado[m]
            for f, c, cl in zip(fil[tr][sids == 0], col[tr][sids == 0], cnum[tr][sids == 0]):   # sin segmento: ventana 3x3
                lab[max(f - 1, 0):f + 2, max(c - 1, 0):c + 2] = cl
            prof.update(compress="deflate")
            with rasterio.open(etiqueta, "w", **prof) as dst:
                dst.write(lab, 1)
            print("k%d: etiqueta corregida con %d puntos de entrenamiento, %.0f ha pintadas" % (k, tr.sum(), m.sum() * 0.01), flush=True)
        mapa = m08.entrenar_y_predecir("c%d" % k, img, etiqueta)
        with rasterio.open(mapa) as src:
            mk = src.read(1)
        c = mk[fil[te], col[te]]
        pred[te] = np.array([CLASES[v - 1] if 0 < v <= len(CLASES) else "sin dato" for v in c], dtype=object)
        print("pliegue %d: macro-F1 %.3f en %d puntos" % (k, abl.macro(d.clase_final[te].to_numpy(), pred[te], CLASES), te.sum()), flush=True)
    y_ref, bloques, pp = d.clase_final.to_numpy(), d.bloque12.to_numpy(), d.oof_s2_mas_alphaearth.to_numpy()
    rng = np.random.default_rng(abl.SEMILLA)
    por_pl = [abl.macro(y_ref[d.pliegue == k], pred[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
    res = dict(brazo="deeplabv3plus_etiquetas_corregidas", epocas=m08.EPOCAS, macro_f1_oof=round(abl.macro(y_ref, pred, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3),
               exactitud=round(float((pred == y_ref).mean()), 3), **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y_ref, pred, labels=CLASES, average=None, zero_division=0))})
    obs, pv = abl.permutacion_bloques(y_ref, pred, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y_ref, pred, pp)
    pr = dict(brazo=res["brazo"], entrada="s2_2025_seca (4 bandas) + parches de puntos", contraste="deeplab corregido − pixel union", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4))
    pd.DataFrame([res]).to_csv(AQUI / "deeplab_corr_2025_resumen.csv", index=False); pd.DataFrame([pr]).to_csv(AQUI / "deeplab_corr_2025_pruebas.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y_ref, pliegue=d.pliegue, oof_deeplab_corr=pred, oof_pixel_union=pp)).to_csv(AQUI / "deeplab_corr_2025_oof.csv", index=False)
    print("DeepLabV3+ corregido OOF macro-F1 %.3f (pliegues %.3f a %.3f) | − pixel %+.3f, p %.3f | McNemar p %.3f" % (res["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv, pm), flush=True)
    print({c: res["f1_" + c] for c in CLASES})


if __name__ == "__main__":
    main()
