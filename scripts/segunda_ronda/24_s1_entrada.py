# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): Sentinel-1 como entrada, por píxel y como media por objeto.

Humedal herbáceo inundado y manglar degradado comparten espacio espectral a 10 m (curva de aprendizaje: cada 20 puntos de
humedal suben su F1 y bajan el de degradado). La retrodispersión en banda C distingue vegetación herbácea sobre agua de
dosel leñoso abierto (doble rebote bajo dosel inundado), que la óptica no ve. Del cubo S1 (12 meses de 2025, VV y VH en dB,
10 m) se derivan 14 variables por punto: medianas de época seca (ene-mar) y húmeda (sep-nov) de VV, VH y VH−VV, y mínimo,
máximo, amplitud y desviación anual de VV y VH. Las mismas 14 se calculan con las medias mensuales dentro del objeto de
0,25 ha (SLIC y Felzenszwalb) de cada punto, con los polígonos de 03.

Brazos (misma CV congelada, muestra de 820; contraste frente al píxel unión y frente a píxel + contexto SLIC 0,25 ha):
  s1_solo, s2_mas_alphaearth_mas_s1, pixel_mas_slic025_mas_s1 (píxel + contexto óptico + S1 píxel + S1 objeto SLIC),
  pixel_mas_felz025_mas_s1. Se repite el resumen sobre el subconjunto de los 720 de la primera ronda.

SALIDAS: s1_2025_puntos.csv (12 x 2 bandas por punto, píxel y objeto), s1_2025_{resumen,pruebas,bordes,oof}.csv
USO: python 24_s1_entrada.py
"""
import importlib.util
import os

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
RAIZ_S1 = "projects/basic-buttress-338101/assets/cgsm_datacube_v1/s1/"
MESES = ["2025%02d" % m for m in range(1, 13)]
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
BUFER = 2600
for n, f in (("v01", "01_variables_2025.py"), ("m03", "03_clasificar_segmentos.py"), ("m21", "21_contexto_multiescala.py")):
    spec = importlib.util.spec_from_file_location(n, AQUI / f); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); globals()[n] = mod
abl = m21.abl; SEGC = m21.SEGC
MB = [m + "_" + b for m in MESES for b in ("VV", "VH")]


def pila_s1():
    import ee
    ims = []
    for m in MESES:
        im = ee.Image(RAIZ_S1 + m).select(["VV", "VH"]); ims.append(im.updateMask(im.gt(-40)).rename([m + "_VV", m + "_VH"]))
    return ee.Image.cat(ims)


def extraer(d):
    """VV y VH mensuales en el píxel de cada punto y como media en su objeto de 0,25 ha (SLIC y Felzenszwalb)."""
    import ee
    f = AQUI / "s1_2025_puntos.csv"
    if f.exists():
        return pd.read_csv(f)
    ee.Initialize(project="basic-buttress-338101"); ee.data.setDeadline(240000)
    pila = pila_s1()
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in d.itertuples()])
    r = pila.reduceRegions(fc, ee.Reducer.first(), 10).getInfo()["features"]
    t = pd.DataFrame([dict(id=x["properties"]["id"], **{"px_" + k: x["properties"].get(k) for k in MB}) for x in r])
    print("píxel: %d puntos" % len(t), flush=True)
    from pyproj import Transformer
    import shapely.ops as so
    tr = Transformer.from_crs(9377, 4326, always_xy=True)
    for segn, pref in (("slic_025ha", "os_"), ("felz_025ha", "of_")):
        ids, polis, crs = m03.poligonos_de_puntos(DATOS / ("segmentos_%s.tif" % segn), d)
        feats = [ee.Feature(ee.Geometry(so.transform(lambda x, y, z=None: tr.transform(x, y), g).__geo_interface__), {"sid": int(sid)}) for sid, g in polis.items()]
        filas = []
        for i in range(0, len(feats), 100):
            rr = pila.reduceRegions(ee.FeatureCollection(feats[i:i + 100]), ee.Reducer.mean(), 10, tileScale=4).getInfo()["features"]
            filas += [dict(sid=x["properties"]["sid"], **{pref + k: x["properties"].get(k) for k in MB}) for x in rr]
            print("   %s: %d de %d objetos" % (segn, min(i + 100, len(feats)), len(feats)), flush=True)
        vs = pd.DataFrame(filas); mp = pd.DataFrame({"id": d.id.values, "sid": ids}).merge(vs, on="sid", how="left").drop(columns="sid")
        t = t.merge(mp, on="id", how="left")
    t.to_csv(f, index=False); return t


def rasgos(t, pref):
    """18 variables S1 a partir de las 24 bandas mensuales con prefijo pref (px_, os_, of_)."""
    g = lambda m, b: t[pref + m + "_" + b].astype(float)
    out = {}
    for est, ms in (("seca", ["202501", "202502", "202503"]), ("humeda", ["202509", "202510", "202511"])):
        vv = pd.concat([g(m, "VV") for m in ms], axis=1).median(1); vh = pd.concat([g(m, "VH") for m in ms], axis=1).median(1)
        out[pref + "s1_" + est + "_VV"], out[pref + "s1_" + est + "_VH"], out[pref + "s1_" + est + "_VHmVV"] = vv, vh, vh - vv
    for b in ("VV", "VH"):
        a = pd.concat([g(m, b) for m in MESES], axis=1)
        out[pref + "s1_min_" + b], out[pref + "s1_max_" + b] = a.min(1), a.max(1)
        out[pref + "s1_amp_" + b], out[pref + "s1_sd_" + b] = a.max(1) - a.min(1), a.std(1)
    return pd.DataFrame(out)


def main():
    from sklearn.metrics import f1_score
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv").merge(pd.read_csv(AQUI / "pixel_2025_oof.csv")[["id", "oof_s2_mas_alphaearth"]], on="id")
    for c in SEGC:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median"))
    t = extraer(d[["id", "lon", "lat"]]).set_index("id").loc[d.id].reset_index()
    for pref in ("px_", "os_", "of_"):
        d = pd.concat([d.reset_index(drop=True), rasgos(t, pref).reset_index(drop=True)], axis=1)
    for pref, segn in (("c025_", "slic_025ha"), ("f025_", "felz_025ha")):
        d = pd.concat([d.reset_index(drop=True), m21.contexto(d, segn, pref).reset_index(drop=True)], axis=1)
    for c in d.columns:
        if d[c].dtype != object and d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median")).fillna(d[c].median())
    S1 = lambda pref: [c for c in d.columns if c.startswith(pref + "s1_")]
    ctx = lambda pref: [pref + c for c in SEGC]
    print("variables S1 por píxel: %d; faltantes antes de imputar: %d puntos sin S1 en el píxel" % (len(S1("px_")), int(t[["px_" + k for k in MB]].isna().all(1).sum())), flush=True)
    brazos = {"s1_solo": S1("px_"), "s2_mas_alphaearth_mas_s1": SEGC + S1("px_"),
              "pixel_mas_slic025": SEGC + ctx("c025_"), "pixel_mas_slic025_mas_s1": SEGC + ctx("c025_") + S1("px_") + S1("os_"),
              "pixel_mas_felz025_mas_s1": SEGC + ctx("f025_") + S1("px_") + S1("of_")}
    y = d.clase_final.to_numpy(); bloques = d.bloque12.to_numpy(); pp = d.oof_s2_mas_alphaearth.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    borde = d.borde_final.astype(str).str.lower().isin(["si", "sí", "true", "1"]).to_numpy(); r1 = (d.id <= 720).to_numpy()
    res, pr, bor, oofs = [], [], [], {}
    for nombre, cc in brazos.items():
        p = abl.oof(d, cc, BUFER); oofs[nombre] = p
        por_pl = [abl.macro(y[d.pliegue == k], p[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, n_vars=len(cc), macro_f1_oof=round(abl.macro(y, p, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((p == y).mean()), 3),
                        macro_f1_720=round(abl.macro(y[r1], p[r1], CLASES), 3), **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y, p, labels=CLASES, average=None, zero_division=0))}))
        for ref_n, ref in (("pixel union", pp), ("pixel_mas_slic025", oofs.get("pixel_mas_slic025"))):
            if ref is None or nombre == "pixel_mas_slic025": continue
            obs, pv = abl.permutacion_bloques(y, p, ref, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y, p, ref)
            pr.append(dict(brazo=nombre, contraste=nombre + " − " + ref_n, dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
        for g, m in (("borde", borde), ("interior", ~borde)):
            bor.append(dict(brazo=nombre, grupo=g, n=int(m.sum()), macro_f1_pixel=round(abl.macro(y[m], pp[m], CLASES), 3), macro_f1_brazo=round(abl.macro(y[m], p[m], CLASES), 3)))
        print("%-28s OOF macro-F1 %.3f (720: %.3f) | − pixel union %+.3f | borde %.3f interior %.3f | humedal %.2f degradado %.2f" % (nombre, res[-1]["macro_f1_oof"], res[-1]["macro_f1_720"], res[-1]["macro_f1_oof"] - 0.587, bor[-2]["macro_f1_brazo"], bor[-1]["macro_f1_brazo"], res[-1]["f1_humedal_herbaceo"], res[-1]["f1_manglar_degradado"]), flush=True)
    pd.DataFrame(res).to_csv(AQUI / "s1_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "s1_2025_pruebas.csv", index=False); pd.DataFrame(bor).to_csv(AQUI / "s1_2025_bordes.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y, pliegue=d.pliegue, oof_pixel_union=pp, **{"oof_" + n: p for n, p in oofs.items()})).to_csv(AQUI / "s1_2025_oof.csv", index=False)
    print(pd.DataFrame(pr).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
