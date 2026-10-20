# -*- coding: utf-8 -*-
r"""Puntos dirigidos de 2025 (decisión de Lina, 2026-10-19) para cubrir el hueco medido en el Informe 2: la muestra tiene 44
puntos de "otro" y ninguno en las manchas del sur donde el mapa por píxel pone manglar a más de 1 km de INVEMAR y GMW, y 73
de humedal herbáceo, la clase peor separada.

Dos estratos, sorteados con semilla fija, fuera de la reserva de validación, a 200 m o más entre sí y de los 720 puntos:
  - otro_fuera_corredor (60): píxeles donde el mapa 2025 dice manglar (intacto o degradado) a más de 1 km de la unión
    INVEMAR + GMW; es donde el mapa sobreestima y la muestra no mira.
  - humedal_mapa (40): píxeles donde el mapa 2025 dice humedal herbáceo, en cualquier parte del dominio.
El estrato y la clase del mapa NO se muestran en la herramienta de etiquetado (ciego). La etiqueta real la pone Lina con el
criterio v1. Los puntos entran con etapa "dirigida_2026-10" y no se mezclan con los 720 de los informes salvo como segunda
ronda declarada.

SALIDAS: puntos_dirigidos_2026-10.csv (id desde 721, lon, lat, estrato, clase_mapa, etapa), etiquetar_dirigidos_gee.js
USO: python 50_puntos_dirigidos_2026-10.py
"""
import importlib.util
import json
import os

os.environ["PROJ_DATA"] = os.path.join(importlib.util.find_spec("rasterio").submodule_search_locations[0], "proj_data"); os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"]
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from pyproj import Transformer

AQUI = Path(__file__).resolve().parent
INF2 = AQUI.parent.parent / "PERCEPCION REMOTA AVANZADA" / "informe2"
SEMILLA = 20261019
N = {"otro_fuera_corredor": 60, "humedal_mapa": 40}
DMIN = 200.0


def main():
    with rasterio.open(INF2 / "datos" / "mapa_pixel_2025.tif") as src:
        m = src.read(1); trf = src.transform
    dom = m > 0
    aoi = gpd.read_file(AQUI.parent / "AOI" / "AOI_tesis_CGSM_v1.geojson").to_crs(4326)
    inv = gpd.read_file("C:/LINA/UNAL 2626-1/PROG_SIG/Docker_1/proyecto-cgsm/data/validation/invemar_manglar_25k.geojson").to_crs(9377)
    gmw = gpd.read_file("zip://" + str(AQUI.parent / "PROYECTO" / "gmw_v3_2020_vec.zip"), bbox=tuple(aoi.total_bounds)).to_crs(9377)
    rz = lambda g: features.rasterize(((x, 1) for x in g.geometry), out_shape=m.shape, transform=trf, fill=0, dtype="uint8").astype(bool) & dom
    ru = rz(inv) | rz(gmw); corredor = (distance_transform_edt(~ru) * 10 <= 1000) & dom
    reserva = gpd.read_file(AQUI / "reserva_validacion.geojson").to_crs(9377); en_reserva = rz(reserva)
    cand = {"otro_fuera_corredor": np.isin(m, [3, 4]) & ~corredor & ~en_reserva, "humedal_mapa": (m == 2) & ~en_reserva}
    e = pd.read_csv(AQUI / "etiquetas_2025.csv"); x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(e.lon.values, e.lat.values)
    ocupados = [np.c_[x, y]]
    rng = np.random.default_rng(SEMILLA); filas = []; nid = int(e.id.max()) + 1
    for estrato, n in N.items():
        f, c = np.where(cand[estrato]); print("%s: %d píxeles candidatos (%.0f ha)" % (estrato, len(f), len(f) * 0.01), flush=True)
        orden = rng.permutation(len(f)); elegidos = []
        arbol = cKDTree(np.vstack(ocupados))
        for k in orden:
            px, py = trf * (c[k] + 0.5, f[k] + 0.5)
            if arbol.query([px, py])[0] < DMIN: continue
            if elegidos and cKDTree(np.array(elegidos)).query([px, py])[0] < DMIN: continue
            elegidos.append([px, py])
            if len(elegidos) == n: break
        lon, lat = Transformer.from_crs(9377, 4326, always_xy=True).transform(np.array(elegidos)[:, 0], np.array(elegidos)[:, 1])
        for (px, py), lo, la in zip(elegidos, lon, lat):
            r_, c_ = rasterio.transform.rowcol(trf, px, py)
            filas.append(dict(id=nid, lon=round(float(lo), 6), lat=round(float(la), 6), estrato=estrato, clase_mapa=int(m[r_, c_]), etapa="dirigida_2026-10")); nid += 1
        ocupados.append(np.array(elegidos))
    d = pd.DataFrame(filas); d.to_csv(AQUI / "puntos_dirigidos_2026-10.csv", index=False, lineterminator="\n")
    print("escritos %d puntos: %s" % (len(d), d.estrato.value_counts().to_dict()), flush=True)
    # herramienta de etiquetado en el Code Editor (ciega: solo id y posicion)
    P = json.dumps([dict(id=int(r.id), lon=r.lon, lat=r.lat) for r in d.itertuples()])
    js = """// Etiquetado a ciegas de los puntos dirigidos 2026-10 (100 puntos). Pegar en code.earthengine.google.com y Run.
// Botones: una clase por punto; al final copiar el cuadro (id,clase) y pegarlo en el chat. Criterio v1 de la muestra 2025.
var P = %s;
var puntos = ee.FeatureCollection(P.map(function(q){ return ee.Feature(ee.Geometry.Point([q.lon, q.lat]), {id: q.id}); }));
var aoi = puntos.geometry().bounds().buffer(5000);
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi).filterDate('2025-01-01', '2025-04-30')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(function(im){ var scl = im.select('SCL'); var m = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)); return im.updateMask(m); }).median();
var s2h = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi).filterDate('2025-09-01', '2025-11-30')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
  .map(function(im){ var scl = im.select('SCL'); var m = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)); return im.updateMask(m); }).median();
Map.addLayer(s2, {bands: ['B4','B3','B2'], min: 200, max: 2500}, 'S2 seca 2025 RGB');
Map.addLayer(s2, {bands: ['B8','B4','B3'], min: 200, max: 4500}, 'S2 seca 2025 falso color', false);
Map.addLayer(s2h, {bands: ['B8','B4','B3'], min: 200, max: 4500}, 'S2 húmeda 2025 falso color', false);
Map.addLayer(s2.normalizedDifference(['B8','B4']), {min: 0, max: 0.9, palette: ['white','yellow','green','darkgreen']}, 'NDVI seca', false);
Map.addLayer(puntos.style({color: 'red', pointSize: 7, fillColor: 'ff000060'}), {}, 'puntos dirigidos');
Map.setOptions('SATELLITE');
var i = 0; var dec = {};
var capaActual = ui.Map.Layer(ee.FeatureCollection([]), {}, 'punto actual'); Map.layers().add(capaActual);
var panel = ui.Panel({style: {width: '320px'}}); var titulo = ui.Label('', {fontWeight: 'bold', fontSize: '14px'}); var detalle = ui.Label('');
var salida = ui.Textbox({style: {width: '300px'}}); var resumen = ui.Label('0 de ' + P.length + ' etiquetados');
function ir(n){ i = Math.max(0, Math.min(P.length - 1, n)); var q = P[i]; Map.centerObject(ee.Geometry.Point([q.lon, q.lat]), 16);
  capaActual.setEeObject(ee.FeatureCollection([ee.Feature(ee.Geometry.Point([q.lon, q.lat]).buffer(60))]).style({color: 'ffff00', fillColor: '00000000', width: 3}));
  titulo.setValue('Punto ' + (i + 1) + ' de ' + P.length + ' | id ' + q.id); detalle.setValue(dec[q.id] ? 'etiqueta: ' + dec[q.id] : 'sin etiqueta'); }
function decidir(v){ return function(){ dec[P[i].id] = v; actualizar(); if (i < P.length - 1) ir(i + 1); else ir(i); }; }
function actualizar(){ var filas = ['id,clase']; var n = 0; P.forEach(function(q){ if (dec[q.id]) { filas.push(q.id + ',' + dec[q.id]); n++; } });
  salida.setValue(filas.join(String.fromCharCode(10))); resumen.setValue(n + ' de ' + P.length + ' etiquetados'); }
panel.add(ui.Label('Puntos dirigidos 2026-10, etiquetado a ciegas', {fontWeight: 'bold'})); panel.add(titulo); panel.add(detalle);
panel.add(ui.Panel([ui.Button('agua', decidir('agua')), ui.Button('humedal herbáceo', decidir('humedal_herbaceo'))], ui.Panel.Layout.flow('horizontal')));
panel.add(ui.Panel([ui.Button('manglar intacto', decidir('manglar_intacto')), ui.Button('manglar degradado', decidir('manglar_degradado'))], ui.Panel.Layout.flow('horizontal')));
panel.add(ui.Panel([ui.Button('otro', decidir('otro')), ui.Button('veg. flotante', decidir('vegetacion_flotante')), ui.Button('no sé', decidir('no_se'))], ui.Panel.Layout.flow('horizontal')));
panel.add(ui.Panel([ui.Button('anterior', function(){ ir(i - 1); }), ui.Button('siguiente', function(){ ir(i + 1); })], ui.Panel.Layout.flow('horizontal')));
panel.add(resumen); panel.add(ui.Label('Al terminar, copia este texto y pégalo en el chat:')); panel.add(salida);
ui.root.add(panel); ir(0);
""" % P
    open(AQUI / "etiquetar_dirigidos_gee.js", "w", encoding="utf-8").write(js); print("herramienta GEE escrita", flush=True)


if __name__ == "__main__":
    main()
