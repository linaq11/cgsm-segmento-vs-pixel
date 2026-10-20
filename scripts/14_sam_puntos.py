# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): SAM con los puntos de referencia como indicaciones (one-shot,
Osco et al. 2023), evaluado fuera de pliegue con el esquema congelado.

Para cada uno de los 720 puntos se corre SamPredictor (ViT-H) sobre una ventana de 512 px del compuesto RGB de estación
seca centrada en el punto, con el punto como indicación positiva, y se guardan dos máscaras: la de mayor puntaje de SAM
("mejor") y la más pequeña de las tres ("menor"). Después, por pliegue k (entrenamiento = pliegue != k y a más de 2,6 km
de la prueba):
  - pintura_mejor / pintura_menor: las máscaras de los puntos de ENTRENAMIENTO se pintan con su clase, de mayor a menor
    área (la pequeña queda encima); el punto de prueba toma la clase pintada en su píxel. Sin pintura: decisión por
    píxel (OOF unión), y se reporta la cobertura.
  - objeto_propio: la máscara "mejor" del punto de PRUEBA (solo usa su posición, no su etiqueta) toma la clase
    mayoritaria de los puntos de entrenamiento que caen dentro; sin ninguno, decisión por píxel.
Contraste frente al píxel unión: permutación por bloques y McNemar, como en 03.

SALIDAS: datos/sam_puntos_mascaras.npz, sam_puntos_2025_{resumen,pruebas,oof,cobertura}.csv
Hallazgo del 19-oct: con ventana de 512 px (alcance 2,56 km) y búfer de 2,6 km ninguna máscara de entrenamiento puede
llegar a un punto de prueba (cobertura 4 %), así que la prueba se corre con ventana de 1024 px y, como sensibilidad
declarada en el protocolo, con búfer 0.

USO: python 14_sam_puntos.py [--ventana 1024] [--bufer 2600|0]
"""
import importlib.util
import os
import sys
import time

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
W = int(sys.argv[sys.argv.index("--ventana") + 1]) if "--ventana" in sys.argv else 512
BUFER = int(sys.argv[sys.argv.index("--bufer") + 1]) if "--bufer" in sys.argv else 2600
SUF = "_w%d_b%d" % (W, BUFER)
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)


def puntos():
    from pyproj import Transformer
    from rasterio.transform import rowcol
    d = pd.read_csv(AQUI / "pixel_2025_oof.csv").merge(pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]], on="id")
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        trf = src.transform; H, Wd = src.height, src.width
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
    fil, col = rowcol(trf, x, y); d["fil"] = np.clip(fil, 0, H - 1); d["col"] = np.clip(col, 0, Wd - 1)
    xu, yu = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values); d["xu"], d["yu"] = xu, yu
    return d, (H, Wd)


def mascaras(d, HW):
    """Dos máscaras por punto (mejor y menor), empaquetadas; ventana (r0, c0) por punto."""
    f = DATOS / ("sam_puntos_mascaras_w%d.npz" % W)
    if f.exists():
        z = np.load(f); return z["r0"], z["c0"], z["mejor"], z["menor"], z["area_mejor"], z["area_menor"], z["puntaje"]
    import torch
    from segment_anything import sam_model_registry, SamPredictor
    ruta = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints", "sam_vit_h_4b8939.pth")
    sam = sam_model_registry["vit_h"](checkpoint=ruta).to("cuda" if torch.cuda.is_available() else "cpu"); pr = SamPredictor(sam)
    H, Wd = HW; n = len(d); r0s = np.zeros(n, int); c0s = np.zeros(n, int)
    mejor = np.zeros((n, W * W // 8), np.uint8); menor = np.zeros((n, W * W // 8), np.uint8)
    am = np.zeros(n); an = np.zeros(n); pt = np.zeros(n); t0 = time.time()
    with rasterio.open(DATOS / "s2_2025_seca_rgb.tif") as src:
        for i, (fi, ci) in enumerate(zip(d.fil.values, d.col.values)):
            r0 = int(min(max(fi - W // 2, 0), H - W)); c0 = int(min(max(ci - W // 2, 0), Wd - W)); r0s[i], c0s[i] = r0, c0
            rgb = np.moveaxis(src.read(window=rasterio.windows.Window(c0, r0, W, W)), 0, -1)
            pr.set_image(np.ascontiguousarray(rgb))
            ms, sc, _ = pr.predict(point_coords=np.array([[ci - c0, fi - r0]]), point_labels=np.array([1]), multimask_output=True)
            areas = ms.reshape(3, -1).sum(1); j = int(np.argmax(sc)); k = int(np.argmin(areas))
            mejor[i] = np.packbits(ms[j].ravel()); menor[i] = np.packbits(ms[k].ravel()); am[i], an[i], pt[i] = areas[j], areas[k], sc[j]
            if (i + 1) % 60 == 0:
                print("  %d/%d puntos, %.0f s; área mediana mejor %.1f ha, menor %.1f ha" % (i + 1, n, time.time() - t0, np.median(am[:i + 1]) * 0.01, np.median(an[:i + 1]) * 0.01), flush=True)
    np.savez_compressed(f, r0=r0s, c0=c0s, mejor=mejor, menor=menor, area_mejor=am, area_menor=an, puntaje=pt)
    return r0s, c0s, mejor, menor, am, an, pt


def desempaquetar(fila):
    return np.unpackbits(fila)[:W * W].reshape(W, W).astype(bool)


def main():
    from scipy.spatial import cKDTree
    from sklearn.metrics import f1_score
    d, HW = puntos(); H, Wd = HW
    r0s, c0s, mejor, menor, am, an, pt = mascaras(d, HW)
    print("máscaras: área mediana mejor %.1f ha (p25 %.1f, p75 %.1f), menor %.1f ha; puntaje mediano %.2f" % (np.median(am) * 0.01, np.percentile(am, 25) * 0.01, np.percentile(am, 75) * 0.01, np.median(an) * 0.01, np.median(pt)), flush=True)
    XY = np.c_[d.xu.values, d.yu.values]; y_ref = d.clase_final.to_numpy(); pp = d.oof_s2_mas_alphaearth.to_numpy()
    cnum = np.array([CLASES.index(c) + 1 for c in y_ref]); fil, col = d.fil.values, d.col.values
    preds = {v: pp.copy() for v in ("pintura_mejor", "pintura_menor", "objeto_propio")}; cobertura = {v: np.zeros(len(d), bool) for v in preds}
    for k in sorted(d.pliegue.unique()):
        te, tr = (d.pliegue == k).to_numpy(), (d.pliegue != k).to_numpy(copy=True); tr &= cKDTree(XY[te]).query(XY)[0] >= BUFER
        for nombre, pack, areas in (("pintura_mejor", mejor, am), ("pintura_menor", menor, an)):
            lienzo = np.zeros(HW, np.uint8)
            for i in np.where(tr)[0][np.argsort(-areas[tr])]:          # grandes primero, pequeñas encima
                m = desempaquetar(pack[i]); r0, c0 = r0s[i], c0s[i]
                sub = lienzo[r0:r0 + W, c0:c0 + W]; sub[m] = cnum[i]
            v = lienzo[fil[te], col[te]]; cub = v > 0
            preds[nombre][np.where(te)[0][cub]] = np.array(CLASES)[v[cub] - 1]; cobertura[nombre][te] = cub
        # objeto propio: máscara del punto de prueba, clase mayoritaria de los puntos de entrenamiento dentro
        idx_tr = np.where(tr)[0]
        for j in np.where(te)[0]:
            m = desempaquetar(mejor[j]); r0, c0 = r0s[j], c0s[j]
            dentro = [i for i in idx_tr if r0 <= fil[i] < r0 + W and c0 <= col[i] < c0 + W and m[fil[i] - r0, col[i] - c0]]
            if dentro:
                vals, cnt = np.unique(y_ref[dentro], return_counts=True); preds["objeto_propio"][j] = vals[np.argmax(cnt)]; cobertura["objeto_propio"][j] = True
        print("pliegue %d: cobertura pintura_mejor %.2f, pintura_menor %.2f, objeto_propio %.2f" % (k, cobertura["pintura_mejor"][te].mean(), cobertura["pintura_menor"][te].mean(), cobertura["objeto_propio"][te].mean()), flush=True)
    bloques = d.bloque12.to_numpy(); rng = np.random.default_rng(abl.SEMILLA); res, pr, cob = [], [], []
    for nombre, pred in preds.items():
        por_pl = [abl.macro(y_ref[d.pliegue == k], pred[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        c = cobertura[nombre]
        res.append(dict(brazo="sam_puntos_" + nombre, macro_f1_oof=round(abl.macro(y_ref, pred, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((pred == y_ref).mean()), 3),
                        cobertura=round(float(c.mean()), 3), macro_f1_cubiertos=round(abl.macro(y_ref[c], pred[c], CLASES), 3) if c.any() else np.nan, macro_f1_pixel_cubiertos=round(abl.macro(y_ref[c], pp[c], CLASES), 3) if c.any() else np.nan,
                        **{"f1_" + cl: round(v, 3) for cl, v in zip(CLASES, f1_score(y_ref, pred, labels=CLASES, average=None, zero_division=0))}))
        obs, pv = abl.permutacion_bloques(y_ref, pred, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y_ref, pred, pp)
        pr.append(dict(brazo="sam_puntos_" + nombre, contraste=nombre + " − pixel union", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        print("%-16s OOF macro-F1 %.3f (pliegues %.3f a %.3f) | cobertura %.2f, en cubiertos %.3f frente a píxel %.3f | − pixel %+.3f, p %.3f" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl), res[-1]["cobertura"], res[-1]["macro_f1_cubiertos"], res[-1]["macro_f1_pixel_cubiertos"], obs, pv), flush=True)
    pd.DataFrame(res).to_csv(AQUI / ("sam_puntos_2025_resumen%s.csv" % SUF), index=False); pd.DataFrame(pr).to_csv(AQUI / ("sam_puntos_2025_pruebas%s.csv" % SUF), index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y_ref, pliegue=d.pliegue, oof_pixel_union=pp, area_mejor_ha=am * 0.01, area_menor_ha=an * 0.01, puntaje=pt, **{"oof_" + n: p for n, p in preds.items()}, **{"cubierto_" + n: c for n, c in cobertura.items()})).to_csv(AQUI / ("sam_puntos_2025_oof%s.csv" % SUF), index=False)


if __name__ == "__main__":
    main()
