# -*- coding: utf-8 -*-
r"""TESSERA 2025 en los 720 puntos de la muestra (cuarta entrada del Informe 2, punto 5 de la auditoria).

Usa geotessera (sample_embeddings_at_points, 128 dimensiones, teselas de 0,1 grado a 10 m, descarga
automatica de las que falten). Si alguna tesela de 2025 no existe, los puntos que caen en ella quedan sin
valor y se reporta la cobertura: la entrada entra al informe solo si cubre los 720 puntos (si no, se
declara, como se hizo con 2021 en el Informe 1, donde cubria 305 de 600).

SALIDA: tessera_2025_puntos.csv (id, T000..T127) y tessera_2025_cobertura.txt
USO: python 07_tessera_2025.py
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
from geotessera import GeoTessera

AQUI = Path(__file__).resolve().parent
MUESTRA = AQUI.parent.parent / "AVANCE TESIS" / "MUESTRA_2025"
e = pd.read_csv(MUESTRA / "etiquetas_2025.csv")[["id", "lon", "lat", "clase_final"]]
gt = GeoTessera()
pts = list(zip(e.lon.values, e.lat.values))
presentes = gt.check_tiles_present(pts, year=2025)
print("teselas necesarias: %d, ya locales: %d" % (len(presentes), sum(presentes.values())), flush=True)
t0 = time.time()
try:
    emb, meta = gt.sample_embeddings_at_points(pts, year=2025, include_metadata=True, auto_download=True)
except Exception as ex:
    print("ERROR en la descarga o el muestreo:", repr(ex)); raise
emb = np.asarray(emb, dtype="float32")
print("embeddings: forma %s en %.0f s" % (emb.shape, time.time() - t0), flush=True)
ok = np.isfinite(emb).all(axis=1)
d = pd.DataFrame(emb, columns=["T%03d" % i for i in range(emb.shape[1])]); d.insert(0, "id", e.id.values)
d.to_csv(AQUI / "tessera_2025_puntos.csv", index=False)
res = ["TESSERA 2025: %d de 720 puntos con embedding (%d dimensiones)" % (ok.sum(), emb.shape[1]),
       "por clase: " + str(e[ok].clase_final.value_counts().to_dict()),
       "sin dato por clase: " + str(e[~ok].clase_final.value_counts().to_dict()),
       "teselas: " + str(presentes)]
open(AQUI / "tessera_2025_cobertura.txt", "w", encoding="utf-8").write("\n".join(res)); print("\n".join(res[:3]))
