# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): segmentación por texto, cero ejemplos, con LangSAM
(Grounding DINO 'tiny' de transformers para las cajas y SAM ViT-H para las máscaras; equivalente a LangSAM de samgeo, Wu y Osco 2023). Indicación "mangrove" sobre teselas de 1024 px del compuesto
RGB de estación seca 2025. No usa etiquetas, así que se evalúa en los 720 puntos sin pliegues: F1 de manglar (intacto +
degradado) frente a no manglar, y delimitación contra INVEMAR y GMW en el corredor de 1 km como los demás mapas.

SALIDAS: datos/mapa_texto_mangrove.tif (1 = manglar según el texto), texto_2025_resumen.csv
USO: python 16_texto_langsam.py [--prompt mangrove] [--umbral 0.24]
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
from PIL import Image

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
RGB = DATOS / "s2_2025_seca_rgb.tif"
PROMPT = sys.argv[sys.argv.index("--prompt") + 1] if "--prompt" in sys.argv else "mangrove"
UMBRAL = float(sys.argv[sys.argv.index("--umbral") + 1]) if "--umbral" in sys.argv else 0.24
T = 1024


def segmentar():
    out = DATOS / ("mapa_texto_%s.tif" % PROMPT.replace(" ", "_"))
    if out.exists():
        with rasterio.open(out) as s:
            return s.read(1)
    # samgeo.text_sam (groundingdino-py) no carga con transformers 5.x (BertModel sin get_extended_attention_mask, 19-oct);
    # se usa Grounding DINO de transformers para las cajas por texto y SamPredictor para las máscaras de cada caja.
    import torch
    from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
    from segment_anything import sam_model_registry, SamPredictor
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-tiny"); gd = AutoModelForZeroShotObjectDetection.from_pretrained("IDEA-Research/grounding-dino-tiny").to(dev)
    ruta = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints", "sam_vit_h_4b8939.pth")
    pred = SamPredictor(sam_model_registry["vit_h"](checkpoint=ruta).to(dev))
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as s:
        dom = s.read(1) > 0
    with rasterio.open(RGB) as src:
        prof = src.profile; H, W = src.height, src.width
        mapa = np.zeros((H, W), np.uint8); t0 = time.time(); n = 0; detecciones = 0
        texto = PROMPT.strip().rstrip(".") + "."
        for r0 in range(0, H, T):
            for c0 in range(0, W, T):
                r1, c1 = min(r0 + T, H), min(c0 + T, W)
                if not dom[r0:r1, c0:c1].any():
                    continue
                rgb = np.ascontiguousarray(np.moveaxis(src.read(window=rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)), 0, -1))
                im = Image.fromarray(rgb)
                ent = proc(images=im, text=texto, return_tensors="pt").to(dev)
                with torch.no_grad():
                    sal = gd(**ent)
                det = proc.post_process_grounded_object_detection(sal, ent.input_ids, threshold=UMBRAL, text_threshold=UMBRAL, target_sizes=[im.size[::-1]])[0]
                cajas = det["boxes"].cpu().numpy() if len(det["boxes"]) else np.zeros((0, 4))
                if len(cajas):
                    pred.set_image(rgb)
                    for caja in cajas:
                        m, _, _ = pred.predict(box=caja, multimask_output=False); mapa[r0:r1, c0:c1][m[0]] = 1
                    detecciones += len(cajas)
                n += 1
                if n % 10 == 0:
                    print("   %d teselas, %d detecciones, %.1f min" % (n, detecciones, (time.time() - t0) / 60), flush=True)
    mapa[~dom] = 0
    prof.update(count=1, dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(mapa, 1)
    print("LangSAM '%s': %d teselas, %d detecciones, %.0f ha marcadas, %.0f min" % (PROMPT, n, detecciones, mapa.sum() * 0.01, (time.time() - t0) / 60), flush=True)
    return mapa


def main():
    from pyproj import Transformer
    from rasterio.transform import rowcol
    from sklearn.metrics import f1_score, precision_score, recall_score
    import geopandas as gpd
    from rasterio import features
    from scipy.ndimage import distance_transform_edt, binary_erosion
    mapa = segmentar()
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as s:
        px = s.read(1); trf = s.transform
    dom = px > 0
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat", "clase_final"]]
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(e.lon.values, e.lat.values); fil, col = rowcol(trf, x, y)
    fil = np.clip(fil, 0, px.shape[0] - 1); col = np.clip(col, 0, px.shape[1] - 1)
    ref = e.clase_final.str.startswith("manglar").to_numpy(); pt = mapa[fil, col] == 1; pp = np.isin(px[fil, col], [3, 4])
    res = dict(prompt=PROMPT, umbral=UMBRAL, n=len(e), prevalencia_manglar=round(float(ref.mean()), 3),
               f1_texto=round(f1_score(ref, pt), 3), precision_texto=round(precision_score(ref, pt), 3), recall_texto=round(recall_score(ref, pt), 3),
               f1_pixel_manglar=round(f1_score(ref, pp), 3), precision_pixel=round(precision_score(ref, pp), 3), recall_pixel=round(recall_score(ref, pp), 3), area_texto_ha=round(float((mapa == 1).sum() * 0.01)))
    aoi = gpd.read_file(AQUI.parent.parent / "AVANCE TESIS" / "AOI" / "AOI_tesis_CGSM_v1.geojson").to_crs(4326)
    refs = {"INVEMAR_25k": gpd.read_file("C:/LINA/UNAL 2626-1/PROG_SIG/Docker_1/proyecto-cgsm/data/validation/invemar_manglar_25k.geojson").to_crs(9377),
            "GMW_2020": gpd.read_file("zip://" + str(AQUI.parent.parent / "AVANCE TESIS" / "PROYECTO" / "gmw_v3_2020_vec.zip"), bbox=tuple(aoi.total_bounds)).to_crs(9377)}
    rasters = {rn: features.rasterize(((g, 1) for g in rg.geometry), out_shape=px.shape, transform=trf, fill=0, dtype="uint8").astype(bool) & dom for rn, rg in refs.items()}
    ru = np.logical_or.reduce(list(rasters.values())); corr = (distance_transform_edt(~ru) * 10 <= 1000) & dom
    man = (mapa == 1) & corr
    for rn, rr in rasters.items():
        res["jaccard_corredor_" + rn] = round(float((man & rr).sum() / (man | rr).sum()), 3); res["recuperado_" + rn] = round(float((man & rr).sum() / rr.sum()), 3)
    res["area_fuera_corredor_ha"] = round(float(((mapa == 1) & ~corr).sum() * 0.01))
    pd.DataFrame([res]).to_csv(AQUI / ("texto_2025_resumen_%s.csv" % PROMPT.replace(" ", "_")), index=False); print(res, flush=True)


if __name__ == "__main__":
    main()
