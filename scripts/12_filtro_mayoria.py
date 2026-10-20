# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): filtro de mayoría de 5 x 5 píxeles sobre el mapa por píxel.

Pregunta: el aporte de SLIC 0,25 ha en los bordes (+0,05) ¿se obtiene con un filtro de mayoría de 5 x 5 (0,25 ha) sin
segmentador? Se filtra cada mapa por pliegue (mapa_pixel_2025_k<k>.tif, modelo sin los puntos del pliegue) y se evalúa en
los puntos del pliegue: OOF, bordes e interior, permutación por bloques y McNemar frente al píxel unión. El mapa completo
filtrado se compara contra INVEMAR y GMW en el corredor de 1 km (misma regla que 06).

SALIDAS: datos/mapa_pixel_2025_filtro5.tif, datos/mapa_pixel_2025_k<k>_filtro5.tif, filtro5_2025_{resumen,pruebas,bordes,oof}.csv,
         filtro5_2025_delimitacion.csv
USO: python 12_filtro_mayoria.py [--ventana 5]
"""
import importlib.util
import os
import sys

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import uniform_filter

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
V = int(sys.argv[sys.argv.index("--ventana") + 1]) if "--ventana" in sys.argv else 5
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)


def mayoria(m, v=V):
    """Clase mayoritaria en la ventana v x v, sin contar el sin dato (0); el sin dato se conserva."""
    mejor = np.zeros(m.shape, np.float32); out = np.zeros(m.shape, np.uint8)
    for c in range(1, len(CLASES) + 1):
        f = uniform_filter((m == c).astype(np.float32), size=v, mode="constant")
        gana = f > mejor; out[gana] = c; mejor[gana] = f[gana]
    out[m == 0] = 0
    return out


def filtrar(entrada, salida):
    if salida.exists():
        with rasterio.open(salida) as src:
            return src.read(1)
    with rasterio.open(entrada) as src:
        m = src.read(1); prof = src.profile
    f = mayoria(m); prof.update(compress="deflate")
    with rasterio.open(salida, "w", **prof) as dst:
        dst.write(f, 1)
    print("filtrado %s: %.1f %% de píxeles cambian" % (entrada.name, 100 * float((f != m)[m > 0].mean())), flush=True)
    return f


def main():
    from pyproj import Transformer
    from rasterio.transform import rowcol
    from sklearn.metrics import f1_score
    d = pd.read_csv(AQUI / "pixel_2025_oof.csv").merge(pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]], on="id")
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        trf = src.transform
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
    fil, col = rowcol(trf, x, y); fil = np.clip(fil, 0, 6021); col = np.clip(col, 0, 7149)
    pred = np.empty(len(d), dtype=object); pred_sin = np.empty(len(d), dtype=object)
    for k in sorted(d.pliegue.unique()):
        f = filtrar(DATOS / ("mapa_pixel_2025_k%d.tif" % k), DATOS / ("mapa_pixel_2025_k%d_filtro%d.tif" % (k, V)))
        with rasterio.open(DATOS / ("mapa_pixel_2025_k%d.tif" % k)) as src:
            mk = src.read(1)
        te = (d.pliegue == k).to_numpy()
        pred[te] = np.array([CLASES[v - 1] if v > 0 else "sin dato" for v in f[fil[te], col[te]]], dtype=object)
        pred_sin[te] = np.array([CLASES[v - 1] if v > 0 else "sin dato" for v in mk[fil[te], col[te]]], dtype=object)
    y_ref, bloques, pp = d.clase_final.to_numpy(), d.bloque12.to_numpy(), d.oof_s2_mas_alphaearth.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    print("control: el mapa por pliegue sin filtro reproduce el OOF del píxel en %.1f %% de los puntos" % (100 * float((pred_sin == pp).mean())), flush=True)
    por_pl = [abl.macro(y_ref[d.pliegue == k], pred[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
    res = dict(brazo="pixel_union_filtro%d" % V, macro_f1_oof=round(abl.macro(y_ref, pred, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((pred == y_ref).mean()), 3),
               **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y_ref, pred, labels=CLASES, average=None, zero_division=0))})
    obs, pv = abl.permutacion_bloques(y_ref, pred, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y_ref, pred, pp)
    obs2, pv2 = abl.permutacion_bloques(y_ref, pred, pred_sin, bloques, CLASES, rng); mb2, mc2, pm2 = abl.mcnemar(y_ref, pred, pred_sin)
    pr = [dict(brazo=res["brazo"], contraste="filtro de mayoria %dx%d − pixel union (OOF sklearn)" % (V, V), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)),
          dict(brazo=res["brazo"], contraste="filtro de mayoria %dx%d − mapa por pliegue sin filtro (pareado exacto)" % (V, V), dif_macro_f1=round(obs2, 3), p_permutacion_bloques=round(pv2, 4), mcnemar_b=mb2, mcnemar_c=mc2, p_mcnemar=round(pm2, 4))]
    print("mapa por pliegue sin filtro: macro-F1 %.3f | filtro − sin filtro %+.3f, p %.3f" % (abl.macro(y_ref, pred_sin, CLASES), obs2, pv2), flush=True)
    bor = []
    borde = d.borde_final.astype(str).str.lower().isin(["si", "sí", "true", "1"]).to_numpy()
    for g, m in (("borde", borde), ("interior", ~borde)):
        bor.append(dict(grupo=g, n=int(m.sum()), macro_f1_pixel=round(abl.macro(y_ref[m], pp[m], CLASES), 3), macro_f1_filtro=round(abl.macro(y_ref[m], pred[m], CLASES), 3)))
    pd.DataFrame([res]).to_csv(AQUI / ("filtro%d_2025_resumen.csv" % V), index=False); pd.DataFrame(pr).to_csv(AQUI / ("filtro%d_2025_pruebas.csv" % V), index=False)
    pd.DataFrame(bor).to_csv(AQUI / ("filtro%d_2025_bordes.csv" % V), index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y_ref, pliegue=d.pliegue, oof_filtro=pred, oof_pixel_union=pp)).to_csv(AQUI / ("filtro%d_2025_oof.csv" % V), index=False)
    print("filtro %dx%d OOF macro-F1 %.3f (pliegues %.3f a %.3f) | − pixel %+.3f, p %.3f | McNemar p %.3f" % (V, V, res["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv, pm), flush=True)
    print("bordes:", bor, flush=True)
    # delimitacion del mapa completo filtrado, misma regla del corredor de 06
    import geopandas as gpd
    from rasterio import features
    from scipy.ndimage import distance_transform_edt, binary_erosion
    fm = filtrar(DATOS / "mapa_pixel_2025.tif", DATOS / ("mapa_pixel_2025_filtro%d.tif" % V))
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        m0 = src.read(1)
    dom = m0 > 0
    aoi = gpd.read_file(AQUI.parent.parent / "AVANCE TESIS" / "AOI" / "AOI_tesis_CGSM_v1.geojson").to_crs(4326)
    refs = {"INVEMAR_25k": gpd.read_file("C:/LINA/UNAL 2626-1/PROG_SIG/Docker_1/proyecto-cgsm/data/validation/invemar_manglar_25k.geojson").to_crs(9377),
            "GMW_2020": gpd.read_file("zip://" + str(AQUI.parent.parent / "AVANCE TESIS" / "PROYECTO" / "gmw_v3_2020_vec.zip"), bbox=tuple(aoi.total_bounds)).to_crs(9377)}
    rasters = {rn: features.rasterize(((g, 1) for g in rg.geometry), out_shape=m0.shape, transform=trf, fill=0, dtype="uint8").astype(bool) & dom for rn, rg in refs.items()}
    ru = np.logical_or.reduce(list(rasters.values())); corr = (distance_transform_edt(~ru) * 10 <= 1000) & dom
    def borde_m(mm): return mm & ~binary_erosion(mm)
    filas = []
    for nombre, mp in (("pixel", m0), ("filtro%d" % V, fm)):
        man_dom = np.isin(mp, [3, 4]) & dom; man = man_dom & corr; bm = borde_m(man)
        for rn, ref_r in rasters.items():
            bg = borde_m(ref_r); dg = distance_transform_edt(~bg) * 10
            filas.append(dict(referencia=rn, mapa=nombre, area_manglar_mapa_corredor_ha=round(man.sum() * 0.01), area_manglar_mapa_fuera_corredor_ha=round((man_dom & ~corr).sum() * 0.01),
                              jaccard_corredor=round((man & ref_r).sum() / (man | ref_r).sum(), 3), referencia_recuperada=round((man & ref_r).sum() / ref_r.sum(), 3), mediana_mapa_a_ref_m=round(float(np.median(dg[bm])), 1)))
            print(filas[-1], flush=True)
    pd.DataFrame(filas).to_csv(AQUI / ("filtro%d_2025_delimitacion.csv" % V), index=False)


if __name__ == "__main__":
    main()
