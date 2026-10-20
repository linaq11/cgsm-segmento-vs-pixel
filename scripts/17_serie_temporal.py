# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): modelo temporal sobre la serie mensual de 2025.

El Random Forest del píxel resume la serie mensual en 30 variables (medianas de dos estaciones y 12 descriptores
fenológicos). Aquí la serie entra entera: 12 meses x 9 canales (B2, B3, B4, B8, B11, B12, NDVI, NDWI, MNDWI) más un
canal de máscara de mes sin dato (relleno con la mediana del punto). Dos brazos con la misma CV congelada (k = 5 por
bloques de 12 km, búfer 2,6 km) y contraste de permutación por bloques frente al píxel espectral (0,580) y al píxel
unión (0,591):
  - serie_cruda_rf: Random Forest sobre los 120 valores de la serie (control: ¿importa el modelo o la información?).
  - serie_cnn1d: red convolucional 1D (2 capas, 32 y 64 filtros, núcleo 3, agrupación global, capa densa), entropía
    cruzada ponderada por la inversa de la frecuencia, Adam 1e-3, 150 épocas, estandarización por canal con las
    estadísticas del entrenamiento del pliegue, semilla 20261007.

SALIDAS: serie_mensual_2025_puntos.csv (caché de GEE), serie_2025_{resumen,pruebas,oof}.csv
USO: python 17_serie_temporal.py [--epocas 150]
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
BANDAS = ["B2", "B3", "B4", "B8", "B11", "B12"]
MESES = ["2025%02d" % m for m in range(1, 13)]
EPOCAS = int(sys.argv[sys.argv.index("--epocas") + 1]) if "--epocas" in sys.argv else 150
BUFER = 2600
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)


def serie():
    f = AQUI / "serie_mensual_2025_puntos.csv"
    if f.exists():
        return pd.read_csv(f)
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat", "clase_final", "borde_final"]]
    raw = v01.muestrear_gee(e)
    cols = ["id"] + [m + "_" + b for m in MESES for b in BANDAS]
    raw[cols].to_csv(f, index=False); return raw[cols]


def tensor(raw):
    """(n, 10, 12): 6 bandas, 3 índices y máscara; NaN de un mes rellenado con la mediana del punto."""
    n = len(raw); X = np.full((n, 10, 12), np.nan, np.float32)
    for j, m in enumerate(MESES):
        b = {k: raw[m + "_" + k].to_numpy(np.float32) for k in BANDAS}
        for i, k in enumerate(BANDAS): X[:, i, j] = b[k] / 10000.0
        X[:, 6, j] = (b["B8"] - b["B4"]) / (b["B8"] + b["B4"] + 1e-6)
        X[:, 7, j] = (b["B3"] - b["B8"]) / (b["B3"] + b["B8"] + 1e-6)
        X[:, 8, j] = (b["B3"] - b["B11"]) / (b["B3"] + b["B11"] + 1e-6)
    X[:, 9, :] = np.isnan(X[:, 0, :]).astype(np.float32)
    med = np.nanmedian(X[:, :9, :], axis=2, keepdims=True)
    for c in range(9):
        Xc = X[:, c, :]; mc = np.broadcast_to(med[:, c, :], Xc.shape); Xc[np.isnan(Xc)] = mc[np.isnan(Xc)]
    X = np.nan_to_num(X, nan=0.0)
    return X


def cnn_oof(X, y, d, XY):
    import torch, torch.nn as nn
    from scipy.spatial import cKDTree
    torch.manual_seed(abl.SEMILLA); np.random.seed(abl.SEMILLA)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    cidx = {c: i for i, c in enumerate(CLASES)}; yi = np.array([cidx[c] for c in y])
    pred = np.empty(len(y), dtype=object)
    for k in sorted(d.pliegue.unique()):
        te, tr = (d.pliegue == k).to_numpy(), (d.pliegue != k).to_numpy(copy=True); tr &= cKDTree(XY[te]).query(XY)[0] >= BUFER
        mu = X[tr].mean(axis=(0, 2), keepdims=True); sd = X[tr].std(axis=(0, 2), keepdims=True) + 1e-6
        Xt = torch.tensor((X - mu) / sd, dtype=torch.float32).to(dev); yt = torch.tensor(yi).to(dev)
        w = np.bincount(yi[tr], minlength=6).astype(float); w = (w.sum() / (6 * np.maximum(w, 1))); w = torch.tensor(w, dtype=torch.float32).to(dev)
        red = nn.Sequential(nn.Conv1d(10, 32, 3, padding=1), nn.ReLU(), nn.Conv1d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Dropout(0.2), nn.Linear(64, 6)).to(dev)
        opt = torch.optim.Adam(red.parameters(), lr=1e-3, weight_decay=1e-4); perdida = nn.CrossEntropyLoss(weight=w)
        idx = np.where(tr)[0]
        for ep in range(EPOCAS):
            red.train(); np.random.shuffle(idx)
            for i0 in range(0, len(idx), 32):
                b = idx[i0:i0 + 32]; opt.zero_grad(); l = perdida(red(Xt[b]), yt[b]); l.backward(); opt.step()
        red.eval()
        with torch.no_grad():
            p = red(Xt[te]).argmax(1).cpu().numpy()
        pred[te] = np.array(CLASES)[p]
        print("  pliegue %d: cnn macro-F1 %.3f (%d entrenamiento)" % (k, abl.macro(y[te], pred[te], CLASES), tr.sum()), flush=True)
    return pred


def main():
    from pyproj import Transformer
    from sklearn.metrics import f1_score
    raw = serie(); d = pd.read_csv(AQUI / "pixel_2025_oof.csv").merge(pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]], on="id").merge(raw, on="id")
    assert len(d) == 720
    X = tensor(d); y = d.clase_final.to_numpy(); print("serie: %d puntos, meses sin dato %.1f %%" % (len(d), 100 * X[:, 9, :].mean()), flush=True)
    xu, yu = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values); XY = np.c_[xu, yu]
    # brazo 1: RF sobre la serie cruda (120 valores)
    cols = ["s%02d_%d" % (c, j) for c in range(10) for j in range(12)]
    dd = pd.concat([d[["id", "lon", "lat", "clase_final", "pliegue", "bloque12"]].reset_index(drop=True), pd.DataFrame(X.reshape(len(d), -1), columns=cols)], axis=1)
    preds = {"serie_cruda_rf": abl.oof(dd, cols, BUFER)}
    print("serie_cruda_rf OOF macro-F1 %.3f" % abl.macro(y, preds["serie_cruda_rf"], CLASES), flush=True)
    preds["serie_cnn1d"] = cnn_oof(X, y, d, XY)
    bloques = d.bloque12.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    pe, pu = d.oof_s2_multitemporal.to_numpy(), d.oof_s2_mas_alphaearth.to_numpy()
    res, pr = [], []
    for nombre, p in preds.items():
        por_pl = [abl.macro(y[d.pliegue == k], p[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, macro_f1_oof=round(abl.macro(y, p, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((p == y).mean()), 3),
                        **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y, p, labels=CLASES, average=None, zero_division=0))}))
        for ref, pp in (("pixel espectral", pe), ("pixel union", pu)):
            obs, pv = abl.permutacion_bloques(y, p, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y, p, pp)
            pr.append(dict(brazo=nombre, contraste="%s − %s" % (nombre, ref), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        print("%-16s OOF macro-F1 %.3f (pliegues %.3f a %.3f) | − espectral %+.3f (p %.3f) | − union %+.3f (p %.3f)" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl), pr[-2]["dif_macro_f1"], pr[-2]["p_permutacion_bloques"], pr[-1]["dif_macro_f1"], pr[-1]["p_permutacion_bloques"]), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "serie_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "serie_2025_pruebas.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y, pliegue=d.pliegue, oof_pixel_union=pu, **{"oof_" + n: p for n, p in preds.items()})).to_csv(AQUI / "serie_2025_oof.csv", index=False)


if __name__ == "__main__":
    main()
