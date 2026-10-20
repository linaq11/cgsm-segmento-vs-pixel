# -*- coding: utf-8 -*-
r"""Mapas de 2025 por pixel y por segmento (voto por mayoria) y medida de delimitacion (auditoria, puntos 1 y 3).

A. Mapas por pixel en Earth Engine. Entrada union (30 espectrales + 64 AlphaEarth de 2025) calculada sobre el
   AOI con las mismas formulas de 01; Random Forest de 500 arboles (smileRandomForest, semilla 20261007) con
   las variables de los 720 puntos tomadas de variables_2025_puntos.csv. Se exportan seis mapas uint8
   (clases 1 a 6 en orden alfabetico): uno por pliegue k, entrenado sin el pliegue k ni los puntos a menos de
   2,6 km de el (identico al OOF de 01), y uno con los 720 puntos para la delimitacion.
B. Voto por mayoria. Para cada raster de segmentos, la clase de cada segmento es la moda de los pixeles del mapa
   dentro de el. Brazo "voto OOF": a cada punto se le asigna la moda de su segmento en el mapa del pliegue al
   que pertenece (ningun punto ve un modelo entrenado con el). Se evalua con el motor de 01 (macro-F1, F1 por
   clase, permutacion por bloques frente al pixel, bordes).
C. Delimitacion del manglar (intacto + degradado) frente a Global Mangrove Watch v3 2020: Jaccard y distancia
   media de los pixeles de borde de cada mapa al borde de GMW (y a la inversa), para el mapa por pixel y los de
   voto. GMW es la unica capa de manglar independiente disponible en el proyecto; la de INVEMAR 1:25.000 no se
   encontro como archivo.

SALIDAS (datos/ y informe2/): mapa_pixel_2025_k<k>.tif, mapa_pixel_2025.tif, mapa_voto_<seg>.tif,
voto_2025_resumen.csv, voto_2025_pruebas.csv, voto_2025_bordes.csv, delimitacion_2025.csv
USO: python 06_mapas.py [--mapas] [--voto] [--delimitacion]   (sin argumentos: todo)
"""
import importlib.util
import os
import sys
# PostGIS deja un proj.db viejo en PROJ_DATA; rasterio necesita el suyo, fijado antes de importarlo (spec, reproducibilidad)
os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
RAIZ = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2/"
BANDAS = ["B2", "B3", "B4", "B8", "B11", "B12"]
MESES = ["2025%02d" % m for m in range(1, 13)]
F_AE = ["A%02d" % i for i in range(64)]
SEMILLA = 20261007
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)
F_S2 = v01.F_S2; COLS = F_S2 + F_AE
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]


# ------------------------------------------------------------------ A. mapas por pixel
def pila_gee():
    import ee
    def ind(img, pref):
        b = {x: img.select(pref + x) for x in BANDAS}
        return ee.Image.cat(b["B8"].subtract(b["B4"]).divide(b["B8"].add(b["B4"])).rename(pref + "NDVI"),
                            b["B3"].subtract(b["B8"]).divide(b["B3"].add(b["B8"])).rename(pref + "NDWI"),
                            b["B3"].subtract(b["B11"]).divide(b["B3"].add(b["B11"])).rename(pref + "MNDWI"))
    mens = {m: ee.Image(RAIZ + m).select(BANDAS).toFloat() for m in MESES}
    partes = []
    for est, ms in (("seca", ["202501", "202502", "202503"]), ("humeda", ["202509", "202510", "202511"])):
        med = ee.ImageCollection([mens[m] for m in ms]).median().rename([est + "_" + b for b in BANDAS])
        partes += [med, ind(med, est + "_")]
    for c in ("NDVI", "NDWI", "MNDWI"):
        serie = ee.ImageCollection([ind(mens[m].rename([m + "_" + b for b in BANDAS]), m + "_").select(m + "_" + c).rename(c) for m in MESES])
        mn, mx, sd = serie.min(), serie.max(), serie.reduce(ee.Reducer.stdDev())
        partes += [mn.rename("fen_%s_min" % c), mx.rename("fen_%s_max" % c), mx.subtract(mn).rename("fen_%s_amp" % c), sd.rename("fen_%s_sd" % c)]
    ae = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("2025-01-01", "2026-01-01").mosaic().select(F_AE)
    return ee.Image.cat(partes + [ae]).select(COLS)


def mapas():
    import ee, geemap, rasterio
    from pyproj import CRS, Transformer
    from scipy.spatial import cKDTree
    ee.Initialize(project="basic-buttress-338101")
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv")
    for c in COLS:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    d["clase_num"] = d.clase_final.map({c: i + 1 for i, c in enumerate(CLASES)})
    x, y = Transformer.from_crs(4326, 32618, always_xy=True).transform(d.lon.values, d.lat.values); XY = np.c_[x, y]
    pila = pila_gee()
    ref = ee.Image(RAIZ + "202512").getInfo()["bands"][0]; tr, dims = ref["crs_transform"], ref["dimensions"]
    WKT = CRS.from_epsg(9377).to_wkt(version="WKT1_GDAL")
    x0, y0 = tr[2], tr[5]; x1, y1 = x0 + dims[0] * tr[0], y0 + dims[1] * tr[4]
    region = ee.Geometry.Rectangle([x0 + 1, y1 + 1, x1 - 1, y0 - 1], WKT, False)
    AOI = ee.FeatureCollection("projects/basic-buttress-338101/assets/AOI_tesis_CGSM_v1").geometry()
    def entrenar(sub):
        fc = ee.FeatureCollection([ee.Feature(None, {**{c: float(r[c]) for c in COLS}, "clase_num": int(r.clase_num)}) for _, r in sub.iterrows()])
        rf = ee.Classifier.smileRandomForest(numberOfTrees=500, seed=SEMILLA).train(fc, "clase_num", COLS)
        return pila.classify(rf).toUint8().updateMask(ee.Image.constant(1).clip(AOI).mask())
    tareas = [("mapa_pixel_2025.tif", d)]
    for k in sorted(d.pliegue.unique()):
        te = (d.pliegue == k).to_numpy(); tr_ = ~te
        tr_ &= cKDTree(XY[te]).query(XY)[0] >= 2600
        tareas.append(("mapa_pixel_2025_k%d.tif" % k, d[tr_]))
    for nombre, sub in tareas:
        out = DATOS / nombre
        if out.exists():
            with rasterio.open(out, "r+") as r:
                r.crs = rasterio.crs.CRS.from_epsg(9377)
            print(nombre, "ya existe, CRS reestampado", flush=True); continue
        print("%s: %d puntos de entrenamiento" % (nombre, len(sub)), flush=True)
        geemap.download_ee_image(entrenar(sub), str(out), region=region, crs=WKT, crs_transform=tr, scale=10, dtype="uint8")
        with rasterio.open(out, "r+") as r:
            r.crs = rasterio.crs.CRS.from_epsg(9377)
        print("   escrito", flush=True)


# ------------------------------------------------------------------ B. voto por mayoria
def moda_por_segmento(seg, mapa):
    """Clase mas frecuente (1..6) de cada id de segmento; 0 donde no hay segmento o mapa."""
    m = (seg > 0) & (mapa > 0)
    s, c = seg[m].astype(np.int64), mapa[m].astype(np.int64)
    n = int(seg.max()) + 1
    cuentas = np.zeros((n, 7), dtype=np.int32)
    np.add.at(cuentas, (s, c), 1)
    moda = cuentas.argmax(axis=1).astype("uint8"); moda[cuentas.sum(axis=1) == 0] = 0
    return moda


def voto(segmentadores):
    import rasterio
    from rasterio.transform import rowcol
    from pyproj import Transformer
    from sklearn.metrics import f1_score
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv"); pix = pd.read_csv(AQUI / "pixel_2025_oof.csv")
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        trf = src.transform
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
    fil, col = rowcol(trf, x, y); fil = np.clip(fil, 0, 6021); col = np.clip(col, 0, 7149)
    mapas_k = {k: rasterio.open(DATOS / ("mapa_pixel_2025_k%d.tif" % k)).read(1) for k in sorted(d.pliegue.unique())}
    y_ref, bloques = d.clase_final.to_numpy(), d.bloque12.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    res, pr, bor = [], [], []
    for segn in segmentadores:
        f = DATOS / ("segmentos_%s.tif" % segn)
        if not f.exists():
            print(segn, "sin raster, se salta"); continue
        with rasterio.open(f) as src:
            seg = src.read(1)
        pred = np.empty(len(d), dtype=object)
        for k, mk in mapas_k.items():
            moda = moda_por_segmento(seg, mk)
            te = (d.pliegue == k).to_numpy()
            sid = seg[fil[te], col[te]]
            clase = np.where(sid > 0, moda[sid], mk[fil[te], col[te]])          # sin segmento: decision por pixel del mismo mapa
            pred[te] = np.array([CLASES[c - 1] if c > 0 else "sin dato" for c in clase], dtype=object)
        # mapa de voto con el modelo completo, para la delimitacion
        with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
            completo = src.read(1); prof = src.profile
        moda = moda_por_segmento(seg, completo); vmap = np.where(seg > 0, moda[seg], completo).astype("uint8")
        with rasterio.open(DATOS / ("mapa_voto_%s.tif" % segn), "w", **prof) as dst:
            dst.write(vmap, 1)
        por_pl = [abl.macro(y_ref[d.pliegue == k], pred[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(segmentador=segn, brazo="voto_mayoria_union", macro_f1_oof=round(abl.macro(y_ref, pred, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((pred == y_ref).mean()), 3),
                        **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y_ref, pred, labels=CLASES, average=None, zero_division=0))}))
        pp = pix["oof_s2_mas_alphaearth"].to_numpy()
        obs, pv = abl.permutacion_bloques(y_ref, pred, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y_ref, pred, pp)
        pr.append(dict(segmentador=segn, entrada="s2_mas_alphaearth", contraste="voto por mayoria − pixel", dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        for grupo, m in (("borde", (d.borde_final == "si").to_numpy()), ("interior", (d.borde_final == "no").to_numpy())):
            bor.append(dict(segmentador=segn, grupo=grupo, n=int(m.sum()), macro_f1_pixel=round(abl.macro(y_ref[m], pp[m], CLASES), 3), macro_f1_voto=round(abl.macro(y_ref[m], pred[m], CLASES), 3)))
        print("%-14s voto OOF macro-F1 %.3f (pliegues %.3f a %.3f) | voto − pixel %+.3f, p %.3f" % (segn, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl), obs, pv), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "voto_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "voto_2025_pruebas.csv", index=False); pd.DataFrame(bor).to_csv(AQUI / "voto_2025_bordes.csv", index=False)


# ------------------------------------------------------------------ C. delimitacion frente a GMW 2020
CORREDOR_M = 1000   # corredor de evaluacion alrededor de la union de referencias


def delimitacion(segmentadores):
    """Manglar del mapa (intacto + degradado) frente a dos referencias independientes: INVEMAR 1:25.000 (la capa con la
    que se construyo el AOI: 1.000 poligonos, 319 km2 dentro del AOI) y Global Mangrove Watch v3 2020. Jaccard y
    distancias medias y medianas entre bordes, en los dos sentidos."""
    import geopandas as gpd, rasterio
    from rasterio import features
    from scipy.ndimage import distance_transform_edt, binary_erosion
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        pixel = src.read(1); trf = src.transform; shp = pixel.shape; dom = pixel > 0
    aoi = gpd.read_file(AQUI.parent.parent / "AVANCE TESIS" / "AOI" / "AOI_tesis_CGSM_v1.geojson").to_crs(4326)
    refs = {}
    inv = Path("C:/LINA/UNAL 2626-1/PROG_SIG/Docker_1/proyecto-cgsm/data/validation/invemar_manglar_25k.geojson")
    if inv.exists():
        refs["INVEMAR_25k"] = gpd.read_file(inv).to_crs(9377)
    gmw_zip = AQUI.parent.parent / "AVANCE TESIS" / "PROYECTO" / "gmw_v3_2020_vec.zip"
    refs["GMW_2020"] = gpd.read_file("zip://" + str(gmw_zip), bbox=tuple(aoi.total_bounds)).to_crs(9377)
    def borde(m): return m & ~binary_erosion(m)
    # Corredor de evaluacion (regla anadida el 2026-10-19, ver PLAN): 1 km alrededor de la union INVEMAR + GMW, el mismo
    # margen con que la propuesta define el AOI. Fuera del corredor las referencias no tienen cobertura (INVEMAR no
    # cartografia la orilla oriental ni el sur), asi que el manglar del mapa alli se reporta aparte como sobreestimacion.
    rasters = {rn: features.rasterize(((g, 1) for g in rg.geometry), out_shape=shp, transform=trf, fill=0, dtype="uint8").astype(bool) & dom for rn, rg in refs.items()}
    union_ref = np.logical_or.reduce(list(rasters.values()))
    corredor = (distance_transform_edt(~union_ref) * 10 <= CORREDOR_M) & dom
    filas = []
    for rn, ref_r in rasters.items():
        bg = borde(ref_r); dg = distance_transform_edt(~bg) * 10
        for nombre, f in [("pixel", DATOS / "mapa_pixel_2025.tif")] + [(s, DATOS / ("mapa_voto_%s.tif" % s)) for s in segmentadores]:
            if not f.exists(): continue
            with rasterio.open(f) as src:
                mp = src.read(1)
            man_dom = np.isin(mp, [3, 4]) & dom
            man = man_dom & corredor
            inter, union = (man & ref_r).sum(), (man | ref_r).sum()
            inter_d, union_d = (man_dom & ref_r).sum(), (man_dom | ref_r).sum()
            bm = borde(man); dm = distance_transform_edt(~bm) * 10
            filas.append(dict(referencia=rn, mapa=nombre, corredor_m=CORREDOR_M, area_corredor_ha=round(corredor.sum() * 0.01, 0),
                              area_manglar_mapa_corredor_ha=round(man.sum() * 0.01, 0), area_manglar_mapa_fuera_corredor_ha=round((man_dom & ~corredor).sum() * 0.01, 0),
                              area_referencia_ha=round(ref_r.sum() * 0.01, 0), jaccard_corredor=round(inter / union, 3), jaccard_dominio=round(inter_d / union_d, 3),
                              referencia_recuperada=round((man & ref_r).sum() / ref_r.sum(), 3),
                              dist_media_mapa_a_ref_m=round(float(dg[bm].mean()), 1), dist_media_ref_a_mapa_m=round(float(dm[bg].mean()), 1),
                              mediana_mapa_a_ref_m=round(float(np.median(dg[bm])), 1), mediana_ref_a_mapa_m=round(float(np.median(dm[bg])), 1)))
            print(filas[-1], flush=True)
    pd.DataFrame(filas).to_csv(AQUI / "delimitacion_2025.csv", index=False)


if __name__ == "__main__":
    segs = ["sam", "sam_fino", "slic", "slic_fino", "slic_16ha", "slic_4ha", "slic_025ha", "felz_025ha", "felz_1ha"]
    todo = len(sys.argv) == 1
    if todo or "--mapas" in sys.argv: mapas()
    if todo or "--voto" in sys.argv: voto(segs)
    if todo or "--delimitacion" in sys.argv: delimitacion(segs)
