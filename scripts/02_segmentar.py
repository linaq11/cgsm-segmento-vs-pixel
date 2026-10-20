# -*- coding: utf-8 -*-
r"""Segmentacion del compuesto seco de 2025 con SAM (samgeo) y con SLIC (control), en la malla del cubo.

SAM. Segment Anything en modo automatico sobre el RGB del compuesto (datos/s2_2025_seca_rgb.tif),
teselado en ventanas de 1024 px (batch=True de samgeo), modelo vit_h por defecto (--modelo vit_b si la
GPU no alcanza). Cada objeto recibe un id unico; los pixeles que SAM no cubre quedan en 0 y se tratan
como "sin segmento" (en la clasificacion por segmento conservan la decision por pixel, y se cuenta cuantos
puntos de referencia caen ahi). Parametros de la generacion automatica fijados aqui y no ajustados a las
etiquetas: points_per_side 32, pred_iou_thresh 0,86, stability_score_thresh 0,92, min_mask_region_area 100
(1 ha a 10 m).

SLIC. Superpixeles de skimage sobre el mismo RGB, con n_segments igual al numero de objetos SAM dentro del
dominio (o el que se pase con --slic N), compactness 10. Es el control: si SLIC da lo mismo que SAM, el
aporte es del contexto, no del segmentador.

SALIDAS (datos/): segmentos_sam.tif, segmentos_slic.tif (int32, malla del cubo), segmentos_resumen.csv
(numero de segmentos, area mediana y cuartiles en ha, fraccion del dominio cubierta).

USO: python 02_segmentar.py [--sam] [--slic [N]] [--modelo vit_h|vit_b]
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import rasterio

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
RGB = os.path.join(DATOS, "s2_2025_seca_rgb.tif")
CUATRO = os.path.join(DATOS, "s2_2025_seca.tif")


def dominio():
    with rasterio.open(CUATRO) as src:
        return src.read(1) > 0


def resumen(nombre, seg, dom):
    ids, n = np.unique(seg[dom & (seg > 0)], return_counts=True)
    ha = n * 0.01
    return dict(segmentador=nombre, n_segmentos=int(len(ids)), area_mediana_ha=round(float(np.median(ha)), 2), q25_ha=round(float(np.percentile(ha, 25)), 2),
                q75_ha=round(float(np.percentile(ha, 75)), 2), area_max_ha=round(float(ha.max()), 1), fraccion_dominio_cubierta=round(float((seg[dom] > 0).mean()), 3))


def sam(modelo, fino=False):
    """SAM automatico por teselas solapadas con fusion de objetos (opcion 1, decidida el 2026-10-18).

    Teselas de T px con paso T/2 (solape de la mitad). Cada mascara se lleva a coordenadas globales y se
    compara con los objetos ya pintados en su huella: si comparte mas de la mitad del area del menor con
    uno de ellos, es el mismo objeto y se funden (union-find). Los pixeles sin objeto reciben el id de la
    mascara; los ya asignados a otro objeto no fundido se conservan (el primero que llega manda). Al final
    los ids se reemplazan por la raiz de su conjunto y se renumeran. No hay umbral ajustado a etiquetas:
    el 0,5 de coincidencia es el criterio habitual de fusion por ventanas deslizantes."""
    import torch
    from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
    print("GPU:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no", flush=True)
    ck = {"vit_h": "sam_vit_h_4b8939.pth", "vit_l": "sam_vit_l_0b3195.pth", "vit_b": "sam_vit_b_01ec64.pth"}[modelo]
    ruta = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints", ck)
    modelo_sam = sam_model_registry[modelo](checkpoint=ruta).to("cuda" if torch.cuda.is_available() else "cpu")
    gen = SamAutomaticMaskGenerator(modelo_sam, points_per_side=64 if fino else 32, pred_iou_thresh=0.86, stability_score_thresh=0.92, min_mask_region_area=25 if fino else 100)
    with rasterio.open(RGB) as src:
        rgb = np.moveaxis(src.read(), 0, -1); prof = src.profile
    H, W, _ = rgb.shape; dom = dominio()
    T = 512 if fino else 1024; PASO = T // 2
    seg = np.zeros((H, W), dtype="int32"); area = {}; padre = {}
    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]; i = padre[i]
        return i
    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[rb] = ra; area[ra] += area[rb]
    sid = 0; t0 = time.time(); n_tiles = 0; fusiones = 0
    filas = list(range(0, max(H - T, 0) + 1, PASO)); cols = list(range(0, max(W - T, 0) + 1, PASO))
    if filas[-1] + T < H: filas.append(H - T)
    if cols[-1] + T < W: cols.append(W - T)
    for r0 in filas:
        for c0 in cols:
            r1, c1 = r0 + T, c0 + T
            if not dom[r0:r1, c0:c1].any():
                continue
            masks = gen.generate(np.ascontiguousarray(rgb[r0:r1, c0:c1])); n_tiles += 1
            ventana = seg[r0:r1, c0:c1]; local = np.zeros_like(ventana)
            # dentro de la tesela, de mayor a menor area con sobreescritura: la mascara mas pequena queda encima
            # (como samgeo), de modo que un objeto anidado no desaparece dentro del grande que lo contiene
            for m in sorted(masks, key=lambda x: -x["area"]):
                mk = m["segmentation"] & dom[r0:r1, c0:c1]
                if mk.sum() < (25 if fino else 100):
                    continue
                sid += 1; padre[sid] = sid; area[sid] = int(mk.sum())
                # fusion solo con el mismo objeto visto desde otra tesela. Se compara en la zona que las dos teselas
                # observaron: (1) de la parte de la mascara nueva ya pintada por teselas previas, mas de la mitad
                # pertenece al objeto i; y (2) de la parte del objeto i dentro de esta ventana, mas de la mitad cae en
                # la mascara nueva. Un objeto grande partido por la costura cumple las dos; un objeto anidado
                # (pequeno dentro de grande, en cualquier sentido) falla una de ellas y no se absorbe.
                exist = ventana[mk]; obs = int((exist > 0).sum())
                ids, cnt = np.unique(exist[exist > 0], return_counts=True)
                if obs:
                    por_raiz = {}
                    for i, n in zip(ids, cnt):
                        por_raiz[raiz(int(i))] = por_raiz.get(raiz(int(i)), 0) + int(n)
                    todo = ventana[ventana > 0]; uu, cc = np.unique(todo, return_counts=True)
                    en_ventana = {}
                    for i, n in zip(uu, cc):
                        en_ventana[raiz(int(i))] = en_ventana.get(raiz(int(i)), 0) + int(n)
                    for ri, n in por_raiz.items():
                        if n > 0.5 * obs and n > 0.5 * en_ventana[ri]:
                            unir(ri, sid); fusiones += 1
                local[mk] = sid
            # entre teselas manda la primera: solo se escriben los pixeles aun sin objeto
            ventana[(local > 0) & (ventana == 0)] = local[(local > 0) & (ventana == 0)]
            print("   tesela %d (%d,%d): %d mascaras, ids %d, fusiones %d, %.1f min" % (n_tiles, r0, c0, len(masks), sid, fusiones, (time.time() - t0) / 60), flush=True)
    lut = np.zeros(sid + 1, dtype="int32")
    for i in range(1, sid + 1):
        lut[i] = raiz(i)
    seg = lut[seg]
    u = np.unique(seg[seg > 0]); lut2 = np.zeros(seg.max() + 1, dtype="int32"); lut2[u] = np.arange(1, len(u) + 1); seg = lut2[seg]
    prof.update(count=1, dtype="int32", nodata=0, compress="deflate")
    out = os.path.join(DATOS, "segmentos_sam_fino.tif" if fino else "segmentos_sam.tif")
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(seg, 1)
    print("SAM %s %s: %d teselas solapadas, %d mascaras, %d fusiones, %d objetos finales, %.0f min" % (modelo, "fino" if fino else "grueso", n_tiles, sid, fusiones, len(u), (time.time() - t0) / 60), flush=True)
    return out


def slic(n, nombre="segmentos_slic.tif"):
    """SLIC por teselas de 1024 px (memoria acotada: la imagen entera en Lab necesitaba mas de 5 GB y en este equipo
    se iba a disco). En cada tesela el numero de superpixeles es proporcional a sus pixeles validos, de modo que el
    tamano medio objetivo (dominio / n) se conserva; los ids se desplazan para ser unicos. Un superpixel no cruza
    teselas: limitacion declarada, irrelevante para superpixeles de tamano fijo que no representan objetos."""
    from skimage.segmentation import slic as _slic
    from skimage.color import rgb2lab
    with rasterio.open(RGB) as src:
        prof = src.profile; H, W = src.height, src.width
    dom = dominio(); total = int(dom.sum()); t0 = time.time()
    seg = np.zeros((H, W), dtype="int32"); desplaz = 0; T = 1024
    with rasterio.open(RGB) as src:
        for r0 in range(0, H, T):
            for c0 in range(0, W, T):
                r1, c1 = min(r0 + T, H), min(c0 + T, W)
                dm = dom[r0:r1, c0:c1]
                if not dm.any():
                    continue
                k = max(int(round(n * dm.sum() / total)), 1)
                rgb = np.moveaxis(src.read(window=rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)), 0, -1)
                lab = rgb2lab(rgb).astype("float32")
                # sin mascara: el SLIC enmascarado de skimage (maskSLIC) es un orden de magnitud mas lento; el vacio se
                # segmenta como fondo uniforme y se anula despues con el dominio
                kk = max(int(round(k * dm.size / dm.sum())), 1)
                # SLICO (slic_zero): compacidad adaptativa por superpixel, independiente de la escala; con compactness fija
                # y superpixeles de 1 ha el termino espacial dominaba y salia una rejilla regular (18-oct)
                loc = _slic(lab, n_segments=kk, compactness=10, sigma=0, slic_zero=True, start_label=1, channel_axis=-1, convert2lab=False).astype("int32")
                loc[loc > 0] += desplaz; desplaz = int(loc.max()) if loc.max() > desplaz else desplaz
                seg[r0:r1, c0:c1] = np.where(dm, loc, 0)
    u = np.unique(seg[seg > 0]); lut = np.zeros(seg.max() + 1, dtype="int32"); lut[u] = np.arange(1, len(u) + 1); seg = lut[seg]
    print("SLIC: %d segmentos en %.0f s (objetivo %d, por teselas de %d px)" % (len(u), time.time() - t0, n, T), flush=True)
    prof.update(count=1, dtype="int32", nodata=0, compress="deflate")
    out = os.path.join(DATOS, nombre)
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(seg, 1)
    return out


def main():
    dom = dominio(); filas = []
    modelo = sys.argv[sys.argv.index("--modelo") + 1] if "--modelo" in sys.argv else "vit_h"
    if "--sam" in sys.argv or not os.path.exists(os.path.join(DATOS, "segmentos_sam.tif")):
        sam(modelo)
    if "--fino" in sys.argv:
        sam(modelo, fino=True)
    for nombre, f in (("SAM " + modelo + " grueso 1024/32", "segmentos_sam.tif"), ("SAM " + modelo + " fino 512/64", "segmentos_sam_fino.tif")):
        if os.path.exists(os.path.join(DATOS, f)):
            with rasterio.open(os.path.join(DATOS, f)) as src:
                filas.append(resumen(nombre, src.read(1).astype("int64"), dom))
    if "--slic" in sys.argv:
        i = sys.argv.index("--slic"); n = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit() else filas[0]["n_segmentos"]
        slic(n)
        with rasterio.open(os.path.join(DATOS, "segmentos_slic.tif")) as src:
            filas.append(resumen("SLIC n=%d" % n, src.read(1).astype("int64"), dom))
    else:
        for f in ("segmentos_slic.tif", "segmentos_slic_fino.tif"):
            if os.path.exists(os.path.join(DATOS, f)):
                with rasterio.open(os.path.join(DATOS, f)) as src:
                    filas.append(resumen(f, src.read(1).astype("int64"), dom))
    r = pd.DataFrame(filas); r.to_csv(os.path.join(DATOS, "segmentos_resumen.csv"), index=False); print(r.to_string(index=False))


if __name__ == "__main__":
    main()
