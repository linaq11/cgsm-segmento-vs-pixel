# -*- coding: utf-8 -*-
r"""Figuras del Informe 2 (segmento frente a píxel, CGSM 2025). Todas se leen de las salidas reales de 01 a 10.

SALIDA: figuras/fig1_muestra.png, fig2_segmentaciones.png, fig3_diferencias.png, fig4_bordes.png,
        fig5_delimitacion.png, fig6_exploratorios.png, fig7_clases.png
USO: python 11_figuras.py
"""
import importlib.util
import os

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
FIG = AQUI / "figuras"; FIG.mkdir(exist_ok=True)
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
AOI = AQUI.parent.parent / "AVANCE TESIS" / "AOI" / "AOI_tesis_CGSM_v1.geojson"
CLASES = ["agua", "humedal_herbaceo", "manglar_degradado", "manglar_intacto", "otro", "vegetacion_flotante"]
NOMBRE = {"agua": "agua", "humedal_herbaceo": "humedal herbáceo", "manglar_degradado": "manglar degradado", "manglar_intacto": "manglar intacto", "otro": "otro", "vegetacion_flotante": "vegetación flotante"}
COLOR = {"agua": "#3b6fc8", "humedal_herbaceo": "#c8c878", "manglar_degradado": "#e6963c", "manglar_intacto": "#146e28", "otro": "#b4b4b4", "vegetacion_flotante": "#8cc85a"}
SEGS = ["sam", "sam_fino", "slic", "slic_16ha", "slic_4ha", "slic_fino", "slic_025ha"]
NSEG = {"sam": "SAM grueso\n(1024/32)", "sam_fino": "SAM fino\n(512/64)", "slic": "SLIC 139 ha", "slic_16ha": "SLIC 16 ha", "slic_4ha": "SLIC 4 ha", "slic_fino": "SLIC 1 ha", "slic_025ha": "SLIC 0,25 ha"}
ENT = {"s2_multitemporal": "espectral (30)", "alphaearth": "AlphaEarth (64)", "s2_mas_alphaearth": "unión (94)", "pixel_mas_segmento": "píxel + contexto", "voto_mayoria_union": "voto por mayoría"}
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})


def rgb_8bit(sub=4):
    with rasterio.open(DATOS / "s2_2025_seca_8bit.tif") as src:
        a = src.read([3, 2, 1], out_shape=(3, src.height // sub, src.width // sub)); tr = src.transform * src.transform.scale(sub, sub)
    a = np.moveaxis(a, 0, -1).astype(np.float32); a = np.clip(a * 1.6, 0, 255) / 255.0
    ext = (tr.c, tr.c + tr.a * a.shape[1], tr.f + tr.e * a.shape[0], tr.f)
    return a, ext


def fig1():
    import geopandas as gpd
    from pyproj import Transformer
    d = pd.read_csv(AQUI / "pixel_2025_oof.csv").merge(pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat"]], on="id")
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(d.lon.values, d.lat.values)
    a, ext = rgb_8bit(); aoi = gpd.read_file(AOI).to_crs(9377)
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), dpi=150)
    for ax in axs:
        ax.imshow(a, extent=ext); aoi.boundary.plot(ax=ax, color="white", linewidth=0.6); ax.set_axis_off()
    for c in CLASES:
        m = d.clase_final == c; axs[0].scatter(x[m], y[m], s=7, c=COLOR[c], edgecolors="black", linewidths=0.2, label="%s (%d)" % (NOMBRE[c], m.sum()))
    axs[0].legend(loc="lower left", fontsize=7, framealpha=0.9, markerscale=1.6); axs[0].set_title("a) 720 puntos de referencia de 2025 por clase")
    cm = plt.get_cmap("tab10")
    for k in sorted(d.pliegue.unique()):
        m = d.pliegue == k; axs[1].scatter(x[m], y[m], s=7, color=cm(k - 1), edgecolors="black", linewidths=0.2, label="pliegue %d (%d)" % (k, m.sum()))
    b = d.borde_final.astype(str).str.lower().isin(["si", "sí", "true", "1"]) if "borde_final" in d.columns else np.zeros(len(d), bool)
    axs[1].scatter(x[b], y[b], s=26, facecolors="none", edgecolors="yellow", linewidths=0.5, label="punto de borde (%d)" % b.sum())
    axs[1].legend(loc="lower left", fontsize=7, framealpha=0.9, markerscale=1.6); axs[1].set_title("b) Cinco pliegues por bloques de 12 km y puntos de borde")
    fig.tight_layout(); fig.savefig(FIG / "fig1_muestra.png", bbox_inches="tight"); plt.close(fig); print("fig1")


def fig2():
    from pyproj import Transformer
    e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")
    bb = e[(e.clase_final == "manglar_degradado") & (e.borde_final.astype(str).str.lower().isin(["si", "sí", "true", "1"]))]
    sel = bb[(bb.lon > -74.62) & (bb.lon < -74.48) & (bb.lat > 10.72) & (bb.lat < 10.90)]; p = sel.iloc[len(sel) // 2] if len(sel) else bb.iloc[0]
    x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(p.lon, p.lat)
    with rasterio.open(DATOS / "s2_2025_seca_8bit.tif") as src:
        r0, c0 = src.index(x, y); L = 150   # 3 km x 3 km
        win = Window(c0 - L, r0 - L, 2 * L, 2 * L); rgb = np.moveaxis(src.read([3, 2, 1], window=win), 0, -1).astype(np.float32); rgb = np.clip(rgb * 1.6, 0, 255) / 255
    paneles = [("sam", "SAM grueso (1024/32)"), ("sam_fino", "SAM fino (512/64)"), ("slic_16ha", "SLIC 16 ha"), ("slic_4ha", "SLIC 4 ha"), ("slic_fino", "SLIC 1 ha"), ("slic_025ha", "SLIC 0,25 ha")]
    fig, axs = plt.subplots(2, 3, figsize=(11, 7.4), dpi=150)
    for ax, (s, t) in zip(axs.ravel(), paneles):
        with rasterio.open(DATOS / ("segmentos_%s.tif" % s)) as src:
            seg = src.read(1, window=win)
        ax.imshow(rgb); bord = (np.diff(seg, axis=0, prepend=seg[:1]) != 0) | (np.diff(seg, axis=1, prepend=seg[:, :1]) != 0)
        ov = np.zeros(bord.shape + (4,)); ov[bord] = (1, 1, 0, 0.9); ax.imshow(ov)
        ax.plot(L, L, "o", mfc="none", mec="red", mew=1.2, ms=10); ax.set_title("%s: %d objetos en la ventana" % (t, len(np.unique(seg)))); ax.set_axis_off()
    fig.suptitle("Ventana de 3 km x 3 km sobre el compuesto seco 2025 (id %d, manglar degradado de borde)" % p.id, fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "fig2_segmentaciones.png", bbox_inches="tight"); plt.close(fig); print("fig2", int(p.id))


def fig3():
    r = pd.read_csv(AQUI / "resumen_segmento_vs_pixel.csv")
    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=150)
    marc = {"s2_multitemporal": ("o", "#7a4a1e"), "alphaearth": ("s", "#1f5fa8"), "s2_mas_alphaearth": ("D", "#2a7d2a"), "pixel_mas_segmento": ("^", "#8a8a8a"), "voto_mayoria_union": ("v", "#b03060")}
    ys = {s: i for i, s in enumerate(SEGS)}
    for ent, (m, col) in marc.items():
        q = r[r.entrada == ent]
        for _, f in q.iterrows():
            y = ys[f.segmentador] + {"s2_multitemporal": -0.3, "alphaearth": -0.15, "s2_mas_alphaearth": 0, "pixel_mas_segmento": 0.15, "voto_mayoria_union": 0.3}[ent]
            ax.plot(f.dif, y, m, color=col, ms=6, mfc=col if f.significativo_holm else "white", mew=1.2)
        ax.plot([], [], m, color=col, label=ENT[ent])
    ax.axvline(0, color="black", linewidth=0.8); ax.axvspan(-0.016, 0.016, color="grey", alpha=0.15, label="DMD ±0,016")
    ax.set_yticks(list(ys.values())); ax.set_yticklabels([NSEG[s].replace("\n", " ") for s in SEGS]); ax.invert_yaxis()
    ax.set_xlabel("diferencia de macro-F1 fuera de pliegue (brazo − píxel con la misma entrada)")
    ax.set_title("Lleno: significativo tras Holm; vacío: no significativo. Primario: SLIC 1 ha, unión")
    ax.legend(loc="lower left", fontsize=7.5); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "fig3_diferencias.png", bbox_inches="tight"); plt.close(fig); print("fig3")


def fig4():
    filas = []
    for s in SEGS:
        b = pd.read_csv(AQUI / ("segmento_2025_bordes_%s.csv" % s)); b = b[b.entrada == "s2_mas_alphaearth"]
        v = pd.read_csv(AQUI / "voto_2025_bordes.csv"); v = v[v.segmentador == s]
        for g in ["borde", "interior"]:
            filas.append(dict(seg=s, grupo=g, pixel=float(b[b.grupo == g].macro_f1_pixel.iloc[0]), segmento=float(b[b.grupo == g].macro_f1_segmento.iloc[0]), voto=float(v[v.grupo == g].macro_f1_voto.iloc[0])))
    t = pd.DataFrame(filas)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), dpi=150, sharey=True)
    for ax, g, n in zip(axs, ["borde", "interior"], [208, 512]):
        q = t[t.grupo == g]; x = np.arange(len(SEGS))
        ax.bar(x - 0.27, q.pixel, 0.27, color="#8a8a8a", label="píxel (misma entrada unión)")
        ax.bar(x, q.segmento, 0.27, color="#2a7d2a", label="segmento como unidad")
        ax.bar(x + 0.27, q.voto, 0.27, color="#b03060", label="voto por mayoría")
        ax.set_xticks(x); ax.set_xticklabels([NSEG[s] for s in SEGS], fontsize=7.5); ax.set_title("%s (n = %d)" % ("puntos de borde" if g == "borde" else "puntos interiores", n)); ax.set_ylim(0, 0.75); ax.grid(axis="y", alpha=0.3)
    axs[0].set_ylabel("macro-F1 fuera de pliegue"); axs[0].legend(fontsize=7.5, loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "fig4_bordes.png", bbox_inches="tight"); plt.close(fig); print("fig4")


def fig5():
    import geopandas as gpd
    from rasterio import features
    from scipy.ndimage import distance_transform_edt
    with rasterio.open(DATOS / "mapa_pixel_2025.tif") as src:
        m = src.read(1); tr = src.transform
    aoi = gpd.read_file(AOI).to_crs(4326)
    inv = gpd.read_file("C:/LINA/UNAL 2626-1/PROG_SIG/Docker_1/proyecto-cgsm/data/validation/invemar_manglar_25k.geojson").to_crs(9377)
    gmw = gpd.read_file("zip://C:/LINA/UNAL 2626-1/AVANCE TESIS/PROYECTO/gmw_v3_2020_vec.zip", bbox=tuple(aoi.total_bounds)).to_crs(9377)
    dom = m > 0
    rz = lambda g: features.rasterize(((x, 1) for x in g.geometry), out_shape=m.shape, transform=tr, fill=0, dtype="uint8").astype(bool) & dom
    ri, rg = rz(inv), rz(gmw); ru = ri | rg; corr = (distance_transform_edt(~ru) * 10 <= 1000) & dom
    mang = np.isin(m, [3, 4]) & dom
    cat = np.zeros(m.shape, np.uint8)                       # 1 acuerdo, 2 mapa fuera de ref en corredor, 3 mapa fuera del corredor, 4 ref sin mapa
    cat[mang & ru] = 1; cat[mang & ~ru & corr] = 2; cat[mang & ~corr] = 3; cat[ru & ~mang] = 4
    col = np.zeros(m.shape + (3,), np.uint8); col[dom] = (235, 235, 235); col[(m == 1) & dom] = (200, 215, 235)
    col[cat == 1] = (20, 110, 40); col[cat == 2] = (240, 170, 50); col[cat == 3] = (200, 40, 40); col[cat == 4] = (120, 60, 200)
    sub = 3; ext = (tr.c, tr.c + tr.a * m.shape[1], tr.f + tr.e * m.shape[0], tr.f)
    fig, ax = plt.subplots(figsize=(8.5, 7), dpi=150); ax.imshow(col[::sub, ::sub], extent=ext)
    bc = corr & ~(np.roll(corr, 1, 0) & np.roll(corr, -1, 0) & np.roll(corr, 1, 1) & np.roll(corr, -1, 1))
    ov = np.zeros(m.shape + (4,), np.float32); ov[bc] = (0, 0, 0, 1); ax.imshow(ov[::sub, ::sub], extent=ext)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#146e28", label="manglar del mapa dentro de INVEMAR o GMW (%.0f km²)" % ((cat == 1).sum() / 1e4)),
                       Patch(color="#f0aa32", label="manglar del mapa fuera de las referencias, en el corredor de 1 km (%.0f km²)" % ((cat == 2).sum() / 1e4)),
                       Patch(color="#c82828", label="manglar del mapa fuera del corredor (%.0f km²)" % ((cat == 3).sum() / 1e4)),
                       Patch(color="#783cc8", label="referencia sin manglar en el mapa (%.0f km²)" % ((cat == 4).sum() / 1e4)),
                       Patch(facecolor="white", edgecolor="black", label="límite del corredor de 1 km")], loc="lower left", fontsize=7.5, framealpha=0.95)
    ax.set_axis_off(); ax.set_title("Mapa por píxel 2025 (manglar intacto + degradado) frente a INVEMAR 1:25.000 y GMW 2020")
    fig.tight_layout(); fig.savefig(FIG / "fig5_delimitacion.png", bbox_inches="tight"); plt.close(fig); print("fig5")


def fig6():
    px = pd.read_csv(AQUI / "pixel_2025_resumen.csv")
    filas = [dict(n="píxel, espectral (30)", v=px.loc[px.brazo == "s2_multitemporal"].iloc[0]), dict(n="píxel, AlphaEarth (64)", v=px.loc[px.brazo == "alphaearth"].iloc[0]), dict(n="píxel, unión (94)", v=px.loc[px.brazo == "s2_mas_alphaearth"].iloc[0])]
    for s, t in [("slic_025ha", "segmento SLIC 0,25 ha, unión"), ("slic_fino", "segmento SLIC 1 ha, unión (primario)"), ("sam_fino", "segmento SAM fino, unión")]:
        r = pd.read_csv(AQUI / ("segmento_2025_resumen_%s.csv" % s)); filas.append(dict(n=t, v=r.loc[r.brazo == "s2_mas_alphaearth"].iloc[0]))
    pr = pd.read_csv(AQUI / "propagacion_2025_resumen.csv")
    filas.append(dict(n="k vecinos sobre AlphaEarth (solo puntos)", v=pr.loc[pr.brazo == "knn_alphaearth"].iloc[0])); filas.append(dict(n="propagación AlphaEarth + 20.000 píxeles", v=pr.loc[pr.brazo == "propagacion_alphaearth"].iloc[0]))
    filas.append(dict(n="DeepLabV3+ etiquetas débiles", v=pd.read_csv(AQUI / "deeplab_2025_resumen.csv").iloc[0])); filas.append(dict(n="DeepLabV3+ débiles + parches de puntos", v=pd.read_csv(AQUI / "deeplab_corr_2025_resumen.csv").iloc[0]))
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=150); y = np.arange(len(filas))
    for i, f in enumerate(filas):
        v = f["v"]; c = "#8a8a8a" if f["n"].startswith("píxel") else ("#2a7d2a" if f["n"].startswith("segmento") else "#1f5fa8")
        ax.plot([v.min_pliegue, v.max_pliegue], [i, i], color=c, linewidth=2, alpha=0.5); ax.plot(v.macro_f1_oof, i, "o", color=c, ms=7)
        ax.text(v.max_pliegue + 0.01, i, "%.3f" % v.macro_f1_oof, va="center", fontsize=8)
    ax.axvline(px.loc[px.brazo == "s2_mas_alphaearth", "macro_f1_oof"].iloc[0], color="black", linestyle="--", linewidth=0.8)
    ax.set_yticks(y); ax.set_yticklabels([f["n"] for f in filas], fontsize=8); ax.invert_yaxis(); ax.set_xlim(0.2, 0.75); ax.grid(axis="x", alpha=0.3)
    ax.set_xlabel("macro-F1 fuera de pliegue (punto) y rango entre pliegues (línea)"); ax.set_title("Brazos principales y exploratorios con la misma validación congelada")
    fig.tight_layout(); fig.savefig(FIG / "fig6_exploratorios.png", bbox_inches="tight"); plt.close(fig); print("fig6")


def fig7():
    px = pd.read_csv(AQUI / "pixel_2025_clases.csv"); px = px[px.brazo == "s2_mas_alphaearth"].set_index("clase").f1
    s25 = pd.read_csv(AQUI / "segmento_2025_clases_slic_025ha.csv"); s25 = s25[s25.brazo == "s2_mas_alphaearth"].set_index("clase").f1_segmento
    s1 = pd.read_csv(AQUI / "segmento_2025_clases_slic_fino.csv"); s1 = s1[s1.brazo == "s2_mas_alphaearth"].set_index("clase").f1_segmento
    sf = pd.read_csv(AQUI / "segmento_2025_clases_sam_fino.csv"); sf = sf[sf.brazo == "s2_mas_alphaearth"].set_index("clase").f1_segmento
    dl = pd.read_csv(AQUI / "deeplab_2025_resumen.csv").iloc[0]
    x = np.arange(len(CLASES)); w = 0.17
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    for i, (nom, ser, c) in enumerate([("píxel, unión", px, "#8a8a8a"), ("SLIC 0,25 ha, unión", s25, "#5aa05a"), ("SLIC 1 ha, unión", s1, "#2a7d2a"), ("SAM fino, unión", sf, "#b03060"), ("DeepLabV3+ débiles", pd.Series({c: dl["f1_" + c] for c in CLASES}), "#1f5fa8")]):
        ax.bar(x + (i - 2) * w, [ser[c] for c in CLASES], w, color=c, label=nom)
    ax.set_xticks(x); ax.set_xticklabels([NOMBRE[c] for c in CLASES], fontsize=8); ax.set_ylabel("F1 fuera de pliegue"); ax.set_ylim(0, 0.9); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=7.5, ncol=3)
    ax.set_title("F1 por clase: píxel frente a segmento y a la red exploratoria")
    fig.tight_layout(); fig.savefig(FIG / "fig7_clases.png", bbox_inches="tight"); plt.close(fig); print("fig7")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7):
        try:
            f()
        except Exception as ex:
            print(f.__name__, "ERROR", repr(ex)[:300])
