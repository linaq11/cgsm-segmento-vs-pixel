# -*- coding: utf-8 -*-
r"""Tercera ronda dirigida (decisión de Lina, 2026-10-19): 60 puntos más en la frontera humedal / manglar degradado.

La curva de aprendizaje sobre los 820 mostró que el F1 de humedal sube unos 7 puntos por cada 20 ejemplos y aún no llega a
meseta, pero que lo que se mueve es la frontera con degradado. Por eso el estrato no es "donde el mapa dice humedal" (ya
usado en la ronda 2) sino donde el mapa de 820 dice manglar degradado a 300 m o menos de un píxel que dice humedal: la
zona de confusión. Sorteo con semilla fija, fuera de la reserva de validación, a 200 m o más entre sí y de los 820 puntos.
El estrato y la clase del mapa NO se muestran en la herramienta de etiquetado (ciego). Criterio v1.1: troncos o estructura
leñosa en Google de alta resolución = degradado; vegetación lisa y continua = humedal.

SALIDAS: puntos_humedal_2026-10.csv (id desde 821, lon, lat, estrato, clase_mapa, etapa), etiquetar_humedal_gee.js
USO: python 51_puntos_humedal_2026-10.py
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
MAPA = AQUI.parent.parent / "PERCEPCION REMOTA AVANZADA" / "informe2_ampliada" / "datos" / "mapa_pixel_2025.tif"   # mapa entrenado con 820
SEMILLA = 20261020
N = 60
DMIN = 200.0
DFRONTERA = 300.0
DEGRADADO, HUMEDAL = 3, 2


def main():
    with rasterio.open(MAPA) as src:
        m = src.read(1); trf = src.transform
    dom = m > 0
    cerca_humedal = distance_transform_edt(m != HUMEDAL) * 10 <= DFRONTERA
    reserva = gpd.read_file(AQUI / "reserva_validacion.geojson").to_crs(9377)
    en_reserva = features.rasterize(((x, 1) for x in reserva.geometry), out_shape=m.shape, transform=trf, fill=0, dtype="uint8").astype(bool)
    cand = (m == DEGRADADO) & cerca_humedal & ~en_reserva & dom
    e = pd.read_csv(AQUI / "etiquetas_2025_ampliada.csv"); x, y = Transformer.from_crs(4326, 9377, always_xy=True).transform(e.lon.values, e.lat.values)
    arbol = cKDTree(np.c_[x, y]); rng = np.random.default_rng(SEMILLA)
    f, c = np.where(cand); print("frontera degradado/humedal: %d píxeles candidatos (%.0f ha)" % (len(f), len(f) * 0.01), flush=True)
    elegidos = []
    for k in rng.permutation(len(f)):
        px, py = trf * (c[k] + 0.5, f[k] + 0.5)
        if arbol.query([px, py])[0] < DMIN: continue
        if elegidos and cKDTree(np.array(elegidos)).query([px, py])[0] < DMIN: continue
        elegidos.append([px, py])
        if len(elegidos) == N: break
    lon, lat = Transformer.from_crs(9377, 4326, always_xy=True).transform(np.array(elegidos)[:, 0], np.array(elegidos)[:, 1])
    nid = int(e.id.max()) + 1; filas = []
    for (px, py), lo, la in zip(elegidos, lon, lat):
        r_, c_ = rasterio.transform.rowcol(trf, px, py)
        filas.append(dict(id=nid, lon=round(float(lo), 6), lat=round(float(la), 6), estrato="frontera_degradado_humedal", clase_mapa=int(m[r_, c_]), etapa="dirigida_humedal_2026-10")); nid += 1
    d = pd.DataFrame(filas); d.to_csv(AQUI / "puntos_humedal_2026-10.csv", index=False, lineterminator="\n")
    print("escritos %d puntos, ids %d a %d" % (len(d), d.id.min(), d.id.max()), flush=True)
    P = json.dumps([dict(id=int(r.id), lon=r.lon, lat=r.lat) for r in d.itertuples()])
    js = """// Etiquetado a ciegas de los 60 puntos de la frontera humedal / degradado (ronda 3, 2026-10). Pegar en code.earthengine.google.com y Run.
// Criterio v1.1: troncos o estructura leñosa visible en alta resolución = manglar degradado; vegetación lisa y continua = humedal herbáceo.
var P = %s;
var puntos = ee.FeatureCollection(P.map(function(q){ return ee.Feature(ee.Geometry.Point([q.lon, q.lat]), {id: q.id}); }));
var aoi = puntos.geometry().bounds().buffer(5000);
function s2(ini, fin, nub){ return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi).filterDate(ini, fin).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', nub))
  .map(function(im){ var scl = im.select('SCL'); return im.updateMask(scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10))); }).median(); }
var seca = s2('2025-01-01', '2025-04-30', 20), hum = s2('2025-09-01', '2025-11-30', 40);
Map.addLayer(seca, {bands: ['B4','B3','B2'], min: 200, max: 2500}, 'S2 seca 2025 RGB');
Map.addLayer(seca, {bands: ['B8','B4','B3'], min: 200, max: 4500}, 'S2 seca 2025 falso color', false);
Map.addLayer(hum, {bands: ['B8','B4','B3'], min: 200, max: 4500}, 'S2 húmeda 2025 falso color', false);
Map.addLayer(puntos.style({color: 'red', pointSize: 7, fillColor: 'ff000060'}), {}, 'puntos ronda 3');
Map.setOptions('SATELLITE');
var i = 0; var dec = {};
var capaActual = ui.Map.Layer(ee.FeatureCollection([]), {}, 'punto actual'); Map.layers().add(capaActual);
var panel = ui.Panel({style: {width: '320px'}}); var titulo = ui.Label('', {fontWeight: 'bold', fontSize: '14px'}); var detalle = ui.Label('');
var salida = ui.Textbox({style: {width: '300px'}}); var resumen = ui.Label('0 de ' + P.length + ' etiquetados');
function ir(n){ i = Math.max(0, Math.min(P.length - 1, n)); var q = P[i]; Map.centerObject(ee.Geometry.Point([q.lon, q.lat]), 17);
  capaActual.setEeObject(ee.FeatureCollection([ee.Feature(ee.Geometry.Point([q.lon, q.lat]).buffer(60))]).style({color: 'ffff00', fillColor: '00000000', width: 3}));
  titulo.setValue('Punto ' + (i + 1) + ' de ' + P.length + ' | id ' + q.id); detalle.setValue(dec[q.id] ? 'etiqueta: ' + dec[q.id] : 'sin etiqueta'); }
function decidir(v){ return function(){ dec[P[i].id] = v; actualizar(); if (i < P.length - 1) ir(i + 1); else ir(i); }; }
function actualizar(){ var filas = ['id,clase']; var n = 0; P.forEach(function(q){ if (dec[q.id]) { filas.push(q.id + ',' + dec[q.id]); n++; } });
  salida.setValue(filas.join(String.fromCharCode(10))); resumen.setValue(n + ' de ' + P.length + ' etiquetados'); }
panel.add(ui.Label('Ronda 3: frontera humedal / degradado, etiquetado a ciegas', {fontWeight: 'bold'})); panel.add(titulo); panel.add(detalle);
panel.add(ui.Panel([ui.Button('humedal herbáceo', decidir('humedal_herbaceo')), ui.Button('manglar degradado', decidir('manglar_degradado'))], ui.Panel.Layout.flow('horizontal')));
panel.add(ui.Panel([ui.Button('manglar intacto', decidir('manglar_intacto')), ui.Button('agua', decidir('agua'))], ui.Panel.Layout.flow('horizontal')));
panel.add(ui.Panel([ui.Button('otro', decidir('otro')), ui.Button('veg. flotante', decidir('vegetacion_flotante')), ui.Button('no sé', decidir('no_se'))], ui.Panel.Layout.flow('horizontal')));
panel.add(ui.Panel([ui.Button('anterior', function(){ ir(i - 1); }), ui.Button('siguiente', function(){ ir(i + 1); })], ui.Panel.Layout.flow('horizontal')));
panel.add(resumen); panel.add(ui.Label('Al terminar, copia este texto y pégalo en el chat:')); panel.add(salida);
ui.root.add(panel); ir(0);
""" % P
    open(AQUI / "etiquetar_humedal_gee.js", "w", encoding="utf-8").write(js); print("herramienta GEE escrita: etiquetar_humedal_gee.js", flush=True)


if __name__ == "__main__":
    main()
