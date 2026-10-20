# Informe 2 de Percepción Remota Avanzada: plan de ejecución

Fecha de fijación: 2026-10-18. Las reglas de abajo se escriben antes de correr nada, como en el Informe 1.

## Pregunta

¿Mejora la incorporación de contexto espacial mediante segmentación la clasificación y la delimitación de las coberturas asociadas al manglar de la CGSM frente a la decisión por píxel, con las mismas entradas, clases y particiones?

## Qué cambia respecto al Informe 1

| | Informe 1 | Informe 2 |
|---|---|---|
| Referencia | 600 etiquetas débiles de WorldCover 2021 | muestra propia 2025, 720 puntos, seis clases, 208 de borde |
| Año | 2021 | 2025 (transferencia 2021 → 2025 como análisis secundario) |
| Unidad de decisión | píxel | píxel frente a segmento |
| Validación | bloques de 6 y 16 km, reserva | esquema congelado de la muestra: k = 5 por bloques de 12 km, búfer 2,6 km (PROTOCOLO) |
| Entradas | 30 espectrales + 64 AlphaEarth | las mismas, de 2025 |

## Auditoría del 2026-10-18 (aplicada en su totalidad por decisión de Lina)

Desviación declarada: SAM fino (512 px, 64 puntos) y SLIC de 1 ha se añadieron después de ver la prueba de tubería con SAM grueso y SLIC de 139 ha (unidades de paisaje, no rodales). Para que la escala no quede como parámetro elegido a mano, se convierte en barrido prefijado: SLIC de 0,25, 1, 4 y 16 ha. Las cinco correcciones:

1. Separar unidad de decisión de rasgos agregados: brazos adicionales "píxel + estadísticos de su segmento" (contexto como rasgo) y "voto por mayoría de las predicciones por píxel dentro del segmento" (segmento como unidad, mismo modelo).
2. Un contraste primario declarado: SLIC de 1 ha frente a píxel con la entrada unión, macro-F1 total, permutación por bloques. Holm sobre la familia de contrastes segmento − píxel. Bordes e interior como lectura descriptiva.
3. Delimitación medida sobre mapas: mapa por píxel de 2025 (RF en Earth Engine con los 720 puntos) y mapa por segmento del segmentador ganador (voto por mayoría), comparados contra la línea de manglar de INVEMAR 1:25.000 por desplazamiento de borde y Jaccard.
4. Escala como barrido declarado (SLIC 0,25, 1, 4 y 16 ha) y SAM en dos configuraciones fijadas (grueso 1024/32, fino 512/64, teselas solapadas con fusión).
5. TESSERA 2025 como cuarta entrada si cubre los 720 puntos (si no, se declara). Diferencia mínima detectable de la prueba principal: 0,016 de macro-F1 con potencia 0,80 y nivel 0,05 (`MUESTRA_2025/dmd_2025.csv`, calculada sobre el brazo de referencia de la ablación): un resultado nulo significa "diferencia menor de unas 0,02".

## Factores y brazos

1. **Unidad de decisión** (factor principal): píxel; segmento SAM (samgeo sobre el compuesto seco de 2025, modo automático, con teselado); segmento SLIC (skimage, superpíxeles de tamaño comparable) como control de la calidad de segmentación.
2. **Entrada** (factor del Informe 1, repetido): s2_multitemporal (30), alphaearth (64), unión (94).

Para los brazos por segmento, cada variable se agrega por segmento (media y desviación dentro del segmento) y el clasificador decide por segmento; cada punto de referencia recibe la clase de su segmento. Mismo Random Forest (500 árboles, semilla 20261007), mismos puntos, mismos pliegues, mismo búfer.

## Métricas y pruebas (fijadas de antemano)

- Macro-F1 fuera de pliegue, pliegue a pliegue (mínimo y máximo), F1 por clase.
- Prueba principal: permutación pareada por bloques (24 bloques, 2.000 repeticiones) de la diferencia de macro-F1 entre segmento y píxel con la misma entrada. McNemar solo como cifra de comparación.
- Bordes: los 208 puntos con `borde_final = si` frente a los 512 interiores, F1 y exactitud por grupo y por unidad de decisión. Además, distancia de cada punto a la transición de clases más cercana del mapa por píxel (30 m como umbral).
- Delimitación: para el manglar, coincidencia del mapa por segmento con el mapa por píxel y con Global Mangrove Watch 2020 (Jaccard), solo como lectura, no como verdad.
- manglar_degradado y humedal_herbaceo: potencia baja declarada (PROTOCOLO); se reportan, no se concluye sobre ellos por separado.

## Qué contaría como respuesta

- Si el macro-F1 por segmento supera al de píxel con p < 0,05 en la permutación y la mejora se concentra en los puntos de borde, el contexto espacial aporta.
- Si no hay diferencia, o la hay solo con SLIC y no con SAM, el aporte depende del segmentador y no del contexto en sí.
- Si el segmento empeora en humedal o degradado, el segmento borra la heterogeneidad fina que esas clases necesitan.

## Orden de ejecución

1. `00_compuesto_seco_2025.py`: compuesto seco 2025 del cubo como GeoTIFF (entrada de SAM y SLIC).
2. `01_variables_2025.py`: 94 variables en los 720 puntos y línea base por píxel con el motor congelado.
3. `02_segmentar.py`: SAM (samgeo, GPU) y SLIC sobre el compuesto; rásteres de segmentos en la malla del cubo.
4. `03_clasificar_segmentos.py`: agregación por segmento, OOF por segmento, pruebas, bordes.
5. `04_transferencia.py`: entrenar 2021 (600 puntos de WorldCover) y evaluar 2025 (720 puntos), por píxel y por segmento.
6. Figuras, tablas e informe con la misma estructura de artículo del Informe 1.

## Lo exploratorio

DeepLabV3+ solo si 1 a 5 cierran y queda tiempo; no es compromiso del informe.

## Recursos de Qiusheng Wu (revisados el 2026-10-19)

1. `geoai` (opengeoai.org): `train_landcover_classification.ipynb` es la plantilla del exploratorio DeepLabV3+ (chips imagen + etiqueta raster, `segmentation-models-pytorch`, `deeplabv3plus`); `samgeo.ipynb`, `grounded_sam.ipynb`; `wetland_sam3.ipynb` como línea futura (SAM3 por texto, acceso en Hugging Face); `tessera.ipynb` usa `geotessera` contra el mismo servidor (no resuelve la indisponibilidad de 2025).
2. samgeo (Wu y Osco 2023): en uso; su modo `batch` entrega máscara binaria, por eso el teselado solapado con fusión es propio (métodos y limitación).
3. Libro GeoAI with Python (book.opengeoai.org): capítulos de embeddings y segmentación.
4. geemap: descarga por teselas del cubo y figuras.

Citas (APA): Wu, Q. (2020). geemap: A Python package for interactive mapping with Google Earth Engine. *Journal of Open Source Software, 5*(51), 2305. https://doi.org/10.21105/joss.02305 · Wu, Q. y Osco, L. P. (2023). samgeo: A Python package for segmenting geospatial data with the Segment Anything Model (SAM). *Journal of Open Source Software, 8*(89), 5663. https://doi.org/10.21105/joss.05663 · Wu, Q. (2026). GeoAI: A Python package for integrating artificial intelligence with geospatial data analysis and visualization. *Journal of Open Source Software, 11*(118), 9605. https://doi.org/10.21105/joss.09605 · Wu, Q. (2026). *GeoAI with Python: A practical guide to open-source geospatial AI*. Publicación independiente. ISBN 979-8993859729 (PDF), 979-8253507414 (impreso). https://book.opengeoai.org

Decisión de Lina (2026-10-19): el exploratorio DeepLabV3+ SÍ entra, con la plantilla de `geoai` (`train_landcover_classification`), etiquetas débiles del mapa por píxel de 2025, evaluado con los 720 puntos.

## Cambio de regla del 2026-10-19 (delimitación, decisión de Lina: "corredor")

Al correr la delimitación, el mapa por píxel de 2025 tiene 81.712 ha de manglar frente a 31.905 ha de INVEMAR 1:25.000 y 41.498 ha de GMW 2020, con Jaccard 0,38 y 0,45 en todo el dominio. Dos causas: la capa INVEMAR no cubre la orilla oriental ni el sur del AOI (163 de los 262 puntos propios etiquetados como manglar caen fuera de sus polígonos, y solo 2 de 458 puntos no manglar caen dentro), y el mapa sobreestima manglar intacto en el bosque inundable del sur (la muestra tiene 44 puntos de "otro" y 73 de humedal). Regla añadida: la delimitación se evalúa dentro de un corredor de 1 km alrededor de la unión INVEMAR + GMW (el mismo margen con que la propuesta define el AOI); el manglar del mapa fuera del corredor se reporta aparte como sobreestimación, no entra al Jaccard. Se reportan ambos valores (dominio y corredor) y la carencia de puntos "otro" queda como limitación de la muestra. Implementado en `06_mapas.py` (`CORREDOR_M = 1000`).
