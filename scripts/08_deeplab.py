# -*- coding: utf-8 -*-
r"""Exploratorio DeepLabV3+ con etiquetas débiles (decisión de Lina, 2026-10-19; plantilla de geoai, Wu 2026).

Pregunta: ¿una red de segmentación semántica entrenada con el mapa por píxel como etiqueta débil (sin ver los
puntos) alcanza o supera al píxel en los 720 puntos? Para que la comparación sea OOF se entrenan cinco redes, una por
pliegue k, con el mapa mapa_pixel_2025_k<k>.tif (RF entrenado sin los puntos del pliegue k) como etiqueta, y cada red se
evalúa solo en los puntos del pliegue k. Mismo esquema de contraste que 03/06: permutación pareada por bloques de 12 km
y McNemar frente al píxel con entrada unión (pixel_2025_oof.csv).

Imagen: compuesto seco 2025 (B4, B3, B2, B8, uint16 reflectancia x10000) reescalado a uint8 (0-3000 -> 0-255) porque
geoai divide por 255. Teselas 256 px sin solape, etiqueta 0 = sin dato (clase extra, no se evalúa).

SALIDAS: datos/deeplab/mapa_deeplab_k<k>.tif, deeplab_2025_resumen.csv, deeplab_2025_pruebas.csv, deeplab_2025_clases.csv
USO: python 08_deeplab.py [--epocas 15]
"""
import importlib.util
import os
import sys
import time

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
OUT = DATOS / "deeplab"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
EPOCAS = int(sys.argv[sys.argv.index("--epocas") + 1]) if "--epocas" in sys.argv else 15
ARQ, ENC = "deeplabv3plus", "resnet34"
LR = float(sys.argv[sys.argv.index("--lr") + 1]) if "--lr" in sys.argv else 1e-3
PESOS = "--pesos" in sys.argv          # pesos de clase inversos a la frecuencia en la etiqueta débil (sensibilidad IDL cap. 5)
SUF = ("" if LR == 1e-3 else "_lr%g" % LR) + ("_pesos" if PESOS else "")

spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)


def imagen_8bit():
    import rasterio
    f = DATOS / "s2_2025_seca_8bit.tif"
    if f.exists():
        return f
    with rasterio.open(DATOS / "s2_2025_seca.tif") as src:
        a = src.read(); prof = src.profile
    sin_dato = a[0] == 0
    a = np.clip(a.astype(np.float32) / 3000.0 * 255.0, 1, 255).astype(np.uint8)
    a[:, sin_dato] = 0
    prof.update(dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(f, "w", **prof) as dst:
        dst.write(a)
    print("imagen 8 bits escrita", flush=True)
    return f


def subcarpeta(base, clave):
    for p in Path(base).iterdir():
        if p.is_dir() and clave in p.name.lower():
            return p
    raise FileNotFoundError("sin carpeta %s en %s: %s" % (clave, base, [p.name for p in Path(base).iterdir()]))


def pesos_clase(etiqueta):
    import rasterio
    with rasterio.open(etiqueta) as src:
        m = src.read(1)
    n = np.bincount(m.ravel(), minlength=len(CLASES) + 1).astype(float); n[0] = n[1:].sum()
    w = 1.0 / np.sqrt(np.maximum(n, 1)); w = w / w[1:].mean(); w[0] = 0.05
    return [float(x) for x in w]


def entrenar_y_predecir(k, img, etiqueta):
    import geoai
    tiles = OUT / ("teselas_k%s" % k); modelo = OUT / ("modelo_k%s" % k); mapa = OUT / ("mapa_deeplab_k%s.tif" % k)
    if mapa.exists():
        return mapa
    t0 = time.time()
    if not tiles.exists():
        geoai.export_geotiff_tiles(str(img), str(tiles), in_class_data=str(etiqueta), tile_size=256, stride=256, skip_empty_tiles=True, quiet=True)
    imgs, labs = subcarpeta(tiles, "image"), subcarpeta(tiles, "label") if any("label" in p.name.lower() for p in tiles.iterdir()) else subcarpeta(tiles, "mask")
    print("k%s: %d teselas en %.0f s" % (k, len(list(imgs.glob("*.tif"))), time.time() - t0), flush=True)
    if not (modelo / "best_model.pth").exists():
        geoai.train_segmentation_model(images_dir=str(imgs), labels_dir=str(labs), output_dir=str(modelo), architecture=ARQ, encoder_name=ENC,
                                       num_channels=4, num_classes=len(CLASES) + 1, batch_size=8, num_epochs=EPOCAS, learning_rate=LR, seed=abl.SEMILLA,
                                       val_split=0.1, verbose=False, plot_curves=False, early_stopping_patience=5, class_weights=pesos_clase(etiqueta) if PESOS else None)
    print("k%s: entrenado en %.0f s" % (k, time.time() - t0), flush=True)
    geoai.semantic_segmentation(str(img), str(mapa), str(modelo / "best_model.pth"), architecture=ARQ, encoder_name=ENC, num_channels=4,
                                num_classes=len(CLASES) + 1, window_size=512, overlap=128, batch_size=8, quiet=True)
    print("k%s: mapa en %.0f s" % (k, time.time() - t0), flush=True)
    return mapa


def main():
    import rasterio
    from pyproj import Transformer
    from rasterio.transform import rowcol
    from sklearn.metrics import f1_score
    OUT.mkdir(exist_ok=True)
    img = imagen_8bit()
    d = pd.read_csv(AQUI / "pixel_2025_oof.csv")
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        trf = src.transform
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]]; d = d.merge(e, on="id")
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
    fil, col = rowcol(trf, x, y); fil = np.clip(fil, 0, 6021); col = np.clip(col, 0, 7149)
    pred = np.empty(len(d), dtype=object)
    for k in sorted(d.pliegue.unique()):
        mapa = entrenar_y_predecir("%d%s" % (k, SUF), img, DATOS / ("mapa_pixel_2025_k%d.tif" % k))
        with rasterio.open(mapa) as src:
            mk = src.read(1)
        te = (d.pliegue == k).to_numpy()
        c = mk[fil[te], col[te]]
        pred[te] = np.array([CLASES[v - 1] if 0 < v <= len(CLASES) else "sin dato" for v in c], dtype=object)
        print("pliegue %d: macro-F1 %.3f en %d puntos (sin dato %d)" % (k, abl.macro(d.clase_final[te].to_numpy(), pred[te], CLASES), te.sum(), (pred[te] == "sin dato").sum()), flush=True)
    y_ref, bloques, pp = d.clase_final.to_numpy(), d.bloque12.to_numpy(), d.oof_s2_mas_alphaearth.to_numpy()
    rng = np.random.default_rng(abl.SEMILLA)
    por_pl = [abl.macro(y_ref[d.pliegue == k], pred[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
    res = dict(brazo="deeplabv3plus_etiquetas_debiles" + SUF, epocas=EPOCAS, lr=LR, pesos=PESOS, macro_f1_oof=round(abl.macro(y_ref, pred, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3),
               exactitud=round(float((pred == y_ref).mean()), 3), **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y_ref, pred, labels=CLASES, average=None, zero_division=0))})
    obs, pv = abl.permutacion_bloques(y_ref, pred, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y_ref, pred, pp)
    pr = dict(brazo="deeplabv3plus_etiquetas_debiles", entrada="s2_2025_seca (4 bandas)", contraste="deeplab − pixel union", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4))
    pd.DataFrame([res]).to_csv(AQUI / ("deeplab_2025_resumen%s.csv" % SUF), index=False); pd.DataFrame([pr]).to_csv(AQUI / ("deeplab_2025_pruebas%s.csv" % SUF), index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y_ref, pliegue=d.pliegue, oof_deeplab=pred, oof_pixel_union=pp)).to_csv(AQUI / ("deeplab_2025_oof%s.csv" % SUF), index=False)
    print("DeepLabV3+ OOF macro-F1 %.3f (pliegues %.3f a %.3f) | deeplab − pixel %+.3f, p %.3f | McNemar p %.3f" % (res["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv, pm), flush=True)
    print({c: res["f1_" + c] for c in CLASES})


if __name__ == "__main__":
    main()
