# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): representaciones de Prithvi-EO 2.0 (300M) como entrada.

Prithvi-EO 2.0 (IBM y NASA, ViT-L preentrenado como autocodificador enmascarado sobre HLS) se usa como extractor de
rasgos congelado, en el mismo papel que AlphaEarth en el Informe 1: para cada uno de los 720 puntos se toma una ventana
de 224 x 224 píxeles del cubo con las seis bandas que el modelo espera (B2, B3, B4, B8, B11, B12, en el orden B02 B03 B04
B05 B06 B07 de HLS) y cuatro instantes temporales (compuestos trimestrales de 2025), normalizadas con la media y la
desviación del modelo, y se extraen dos representaciones del codificador sin enmascarar:
  - prithvi_centro: media sobre los cuatro instantes del token del parche central (16 x 16 m) donde cae el punto (1.024).
  - prithvi_contexto: media de todos los tokens de parche de la ventana (1.024), el contexto de 2,2 km.
Brazos con la CV congelada (RF 500 árboles, k = 5 bloques de 12 km, búfer 2,6 km): prithvi_centro, prithvi_contexto,
s2_mas_prithvi_centro, y contraste de permutación frente a alphaearth (0,595) y píxel unión (0,591). Desviación declarada:
la banda B8 (NIR ancho de Sentinel-2) ocupa el lugar de B05 (NIR estrecho de HLS), y el modelo no recibe coordenadas.

SALIDAS: prithvi_2025_puntos.npz (embeddings), prithvi_2025_{resumen,pruebas,oof}.csv
USO: python 19_prithvi.py
"""
import importlib.util
import inspect
import json
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
PR = DATOS / "prithvi"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
W, PATCH, T = 224, 16, 4
BUFER = 2600
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)
F_S2, F_AE = v01.F_S2, v01.F_AE


def modelo():
    import torch
    sys.path.insert(0, str(PR))
    from prithvi_mae import PrithviMAE
    cfg = json.load(open(PR / "config.json"))["pretrained_cfg"]
    acepta = inspect.signature(PrithviMAE.__init__).parameters
    args = {k: v for k, v in cfg.items() if k in acepta}
    args.update(num_frames=T, in_chans=6, coords_encoding=[])
    m = PrithviMAE(**args)
    sd = torch.load(PR / "Prithvi_EO_V2_300M.pt", map_location="cpu", weights_only=True)
    for k in list(sd):
        if "pos_embed" in k: del sd[k]
    faltan = m.load_state_dict(sd, strict=False)
    print("Prithvi cargado; claves no usadas %d, claves faltantes %d" % (len(faltan.unexpected_keys), len(faltan.missing_keys)), flush=True)
    return m.eval(), np.array(cfg["mean"], np.float32), np.array(cfg["std"], np.float32)


def embeddings(d):
    f = AQUI / "prithvi_2025_puntos.npz"
    if f.exists():
        z = np.load(f); return z["centro"], z["contexto"]
    import torch
    from pyproj import Transformer
    from rasterio.transform import rowcol
    m, mu, sd = modelo(); dev = "cuda" if torch.cuda.is_available() else "cpu"; m = m.to(dev)
    srcs = [rasterio.open(DATOS / ("s2_2025_q%d.tif" % q)) for q in (1, 2, 3, 4)]
    H, Wd = srcs[0].height, srcs[0].width; trf = srcs[0].transform
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values); fil, col = rowcol(trf, x, y)
    n = len(d); centro = np.zeros((n, 1024), np.float32); contexto = np.zeros((n, 1024), np.float32); t0 = time.time()
    cen = 1 + (W // PATCH // 2) * (W // PATCH) + W // PATCH // 2          # índice del parche central dentro de un instante
    tpf = (W // PATCH) ** 2
    with torch.no_grad():
        for i in range(n):
            r0 = int(min(max(fil[i] - W // 2, 0), H - W)); c0 = int(min(max(col[i] - W // 2, 0), Wd - W))
            cubo = np.zeros((6, T, W, W), np.float32)
            for t, s in enumerate(srcs):
                a = s.read(window=rasterio.windows.Window(c0, r0, W, W)).astype(np.float32)      # (6, W, W) x10000
                a[a == 0] = np.nan
                cubo[:, t] = (a - mu[:, None, None]) / sd[:, None, None]
            cubo = np.nan_to_num(cubo, nan=0.0)
            xt = torch.tensor(cubo[None]).to(dev)
            tok = m.encoder.forward_features(xt)[-1][0]                      # (1 + T*196, 1024)
            pc = [tok[cen + t * tpf] for t in range(T)]
            # desplazamiento del punto dentro de la ventana cuando la ventana se recortó al borde
            pr_, pc_ = (fil[i] - r0) // PATCH, (col[i] - c0) // PATCH
            idx = 1 + pr_ * (W // PATCH) + pc_
            pc = [tok[idx + t * tpf] for t in range(T)]
            centro[i] = torch.stack(pc).mean(0).cpu().numpy(); contexto[i] = tok[1:].mean(0).cpu().numpy()
            if (i + 1) % 100 == 0:
                print("  %d/%d puntos, %.0f s" % (i + 1, n, time.time() - t0), flush=True)
    for s in srcs: s.close()
    np.savez_compressed(f, centro=centro, contexto=contexto); return centro, contexto


def main():
    from sklearn.metrics import f1_score
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv").merge(pd.read_csv(AQUI / "pixel_2025_oof.csv")[["id", "oof_alphaearth", "oof_s2_mas_alphaearth"]], on="id")
    assert len(d) == 720
    cen, ctx = embeddings(d)
    FC = ["P%04d" % i for i in range(1024)]; FX = ["X%04d" % i for i in range(1024)]
    d = pd.concat([d.reset_index(drop=True), pd.DataFrame(cen, columns=FC), pd.DataFrame(ctx, columns=FX)], axis=1)
    for c in F_S2:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    y = d.clase_final.to_numpy(); bloques = d.bloque12.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    brazos = {"prithvi_centro": FC, "prithvi_contexto": FX, "s2_mas_prithvi_centro": F_S2 + FC}
    res, pr, oofs = [], [], {}
    for nombre, cols in brazos.items():
        p = abl.oof(d, cols, BUFER); oofs[nombre] = p
        por_pl = [abl.macro(y[d.pliegue == k], p[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, n_vars=len(cols), macro_f1_oof=round(abl.macro(y, p, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((p == y).mean()), 3),
                        **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y, p, labels=CLASES, average=None, zero_division=0))}))
        linea = "%-24s OOF macro-F1 %.3f (pliegues %.3f a %.3f)" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl))
        for ref in ("oof_alphaearth", "oof_s2_mas_alphaearth"):
            pp = d[ref].to_numpy(); obs, pv = abl.permutacion_bloques(y, p, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y, p, pp)
            pr.append(dict(brazo=nombre, contraste="%s − %s" % (nombre, ref.replace("oof_", "")), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
            linea += " | − %s %+.3f (p %.3f)" % (ref.replace("oof_", ""), obs, pv)
        print(linea, flush=True)
    pd.DataFrame(res).to_csv(AQUI / "prithvi_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "prithvi_2025_pruebas.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y, pliegue=d.pliegue, **{"oof_" + n: p for n, p in oofs.items()})).to_csv(AQUI / "prithvi_2025_oof.csv", index=False)


if __name__ == "__main__":
    main()
