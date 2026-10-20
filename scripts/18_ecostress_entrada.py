# -*- coding: utf-8 -*-
r"""Extensión del Informe 2 (decisión de Lina, 2026-10-19): temperatura de superficie nocturna de ECOSTRESS como entrada.

Para cada uno de los 720 puntos se toma, de NASA/ECOSTRESS/L2T_LSTE/V2 en Earth Engine (misma limpieza que el ejercicio
del curso: nube 0, QC bits 0-1 <= 1, 270 < LST < 340 K), la mediana mensual de 2025 de la temperatura de superficie
nocturna (hora local fuera de 06-18) y diurna, a 70 m. Variables: 12 medianas nocturnas, 12 diurnas, y por régimen la
mediana, el mínimo, el máximo, la amplitud y la desviación anual, más el número de meses con dato. Los meses sin dato se
rellenan con la mediana anual del punto y, si el punto no tiene ningún mes, con la mediana de su clase (declarado).
Brazos con la CV congelada: lst sola, espectral + lst, unión + lst; contraste de permutación frente al mismo brazo sin lst.

SALIDAS: ecostress_2025_puntos.csv (caché), ecostress_2025_{resumen,pruebas,oof}.csv
USO: python 18_ecostress_entrada.py
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
BUFER = 2600
spec = importlib.util.spec_from_file_location("variables", AQUI / "01_variables_2025.py")
v01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v01)
spec2 = importlib.util.spec_from_file_location("ablacion", MUESTRA / "40_ablacion_entradas.py")
abl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(abl)
F_S2, F_AE = v01.F_S2, v01.F_AE


def muestrear():
    f = AQUI / "ecostress_2025_puntos.csv"
    if f.exists():
        return pd.read_csv(f)
    import ee
    ee.Initialize(project="basic-buttress-338101")
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]]
    pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"id": int(r.id)}) for r in e.itertuples()])
    col = ee.ImageCollection("NASA/ECOSTRESS/L2T_LSTE/V2").filterBounds(pts.geometry().bounds()).filterDate("2025-01-01", "2026-01-01")
    def limpia(img):
        qc_ok = img.select("QC").bitwiseAnd(3).lte(1)
        ok = img.select("cloud").eq(0).And(qc_ok).And(img.select("LST").gt(270)).And(img.select("LST").lt(340))
        fecha = ee.Date(img.get("system:time_start")); hora = fecha.advance(-5, "hour").get("hour")
        return img.select("LST").subtract(273.15).rename("LST_C").updateMask(ok).set({"dia": hora.gte(6).And(hora.lt(18)), "mes": fecha.get("month")})
    limpio = col.map(limpia)
    bandas = []
    for reg, valor in (("n", 0), ("d", 1)):
        sub_r = limpio.filter(ee.Filter.eq("dia", valor))
        for mes in range(1, 13):
            sub = sub_r.filter(ee.Filter.eq("mes", mes)); n = sub.size()
            img = ee.Image(ee.Algorithms.If(n.gt(0), sub.median(), ee.Image.constant(-9999).toFloat().rename("LST_C"))).rename("lst%s_%02d" % (reg, mes))
            bandas.append(img)
    pila = ee.Image.cat(bandas)
    r = pila.reduceRegions(pts, ee.Reducer.first(), 70).getInfo()["features"]
    cols = ["lst%s_%02d" % (reg, mes) for reg in ("n", "d") for mes in range(1, 13)]
    d = pd.DataFrame([dict(id=x["properties"]["id"], **{c: x["properties"].get(c) for c in cols}) for x in r])
    d[cols] = d[cols].replace(-9999, np.nan)
    d.to_csv(f, index=False); return d


def rasgos(d):
    out = pd.DataFrame({"id": d.id})
    for reg in ("n", "d"):
        cols = ["lst%s_%02d" % (reg, m) for m in range(1, 13)]; M = d[cols].to_numpy(float)
        out["lst%s_meses" % reg] = np.isfinite(M).sum(1)
        with np.errstate(all="ignore"):
            med = np.nanmedian(M, 1); out["lst%s_med" % reg] = med; out["lst%s_min" % reg] = np.nanmin(M, 1); out["lst%s_max" % reg] = np.nanmax(M, 1)
            out["lst%s_amp" % reg] = out["lst%s_max" % reg] - out["lst%s_min" % reg]; out["lst%s_sd" % reg] = np.nanstd(M, 1)
        Mf = np.where(np.isfinite(M), M, med[:, None])
        for j, c in enumerate(cols): out[c] = Mf[:, j]
    out["lst_dn_dif"] = out["lstd_med"] - out["lstn_med"]
    return out


def main():
    from sklearn.metrics import f1_score
    raw = muestrear(); r = rasgos(raw)
    F_LST = [c for c in r.columns if c != "id"]
    d = pd.read_csv(AQUI / "variables_2025_puntos.csv").merge(pd.read_csv(AQUI / "pixel_2025_oof.csv")[["id", "oof_s2_multitemporal", "oof_s2_mas_alphaearth"]], on="id").merge(r, on="id")
    assert len(d) == 720
    sin_n = d.lstn_meses.eq(0).sum(); sin_d = d.lstd_meses.eq(0).sum()
    print("puntos sin ningún mes nocturno: %d; sin ningún mes diurno: %d; meses nocturnos por punto mediana %.0f, diurnos %.0f" % (sin_n, sin_d, d.lstn_meses.median(), d.lstd_meses.median()), flush=True)
    for c in F_S2 + F_AE + F_LST:
        if d[c].isna().any(): d[c] = d[c].fillna(d.groupby("clase_final")[c].transform("median")).fillna(d[c].median())
    y = d.clase_final.to_numpy(); bloques = d.bloque12.to_numpy(); rng = np.random.default_rng(abl.SEMILLA)
    brazos = {"lst_sola": (F_LST, None), "s2_multitemporal_mas_lst": (F_S2 + F_LST, "oof_s2_multitemporal"), "s2_mas_alphaearth_mas_lst": (F_S2 + F_AE + F_LST, "oof_s2_mas_alphaearth")}
    res, pr, oofs = [], [], {}
    for nombre, (cols, ref) in brazos.items():
        p = abl.oof(d, cols, BUFER); oofs[nombre] = p
        por_pl = [abl.macro(y[d.pliegue == k], p[d.pliegue == k], CLASES) for k in sorted(d.pliegue.unique())]
        res.append(dict(brazo=nombre, n_vars=len(cols), macro_f1_oof=round(abl.macro(y, p, CLASES), 3), min_pliegue=round(min(por_pl), 3), max_pliegue=round(max(por_pl), 3), exactitud=round(float((p == y).mean()), 3),
                        **{"f1_" + c: round(v, 3) for c, v in zip(CLASES, f1_score(y, p, labels=CLASES, average=None, zero_division=0))}))
        linea = "%-28s OOF macro-F1 %.3f (pliegues %.3f a %.3f)" % (nombre, res[-1]["macro_f1_oof"], min(por_pl), max(por_pl))
        if ref:
            pp = d[ref].to_numpy(); obs, pv = abl.permutacion_bloques(y, p, pp, bloques, CLASES, rng); mb, mc, pm = abl.mcnemar(y, p, pp)
            pr.append(dict(brazo=nombre, contraste="%s − %s" % (nombre, ref.replace("oof_", "")), dif_macro_f1=round(obs, 3), p_permutacion_bloques=round(pv, 4), mcnemar_b=mb, mcnemar_c=mc, p_mcnemar=round(pm, 4)))
            linea += " | − sin lst %+.3f (p %.3f, McNemar %.3f)" % (obs, pv, pm)
        print(linea, flush=True)
    pd.DataFrame(res).to_csv(AQUI / "ecostress_2025_resumen.csv", index=False); pd.DataFrame(pr).to_csv(AQUI / "ecostress_2025_pruebas.csv", index=False)
    pd.DataFrame(dict(id=d.id, clase_final=y, pliegue=d.pliegue, **{"oof_" + n: p for n, p in oofs.items()})).to_csv(AQUI / "ecostress_2025_oof.csv", index=False)
    print({c: round(float(d[c].median()), 1) for c in ("lstn_med", "lstd_med", "lst_dn_dif")}, flush=True)


if __name__ == "__main__":
    main()
