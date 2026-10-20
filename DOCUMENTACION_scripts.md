# Documentación de los scripts

Cabecera y comentarios de cada script, extraídos del código con `generar_documentacion.py`, en el orden del flujo de trabajo del informe. Cada cabecera dice qué hace el script, qué lee, qué escribe y cómo se ejecuta.

## 1. Compuesto y variables por punto

### `00_compuesto_seco_2025.py`

Compuesto de estacion seca 2025 del cubo, como GeoTIFF local, para segmentarlo con SAM.

Mediana de los compuestos mensuales de enero a marzo de 2025 de la coleccion s2 del cubo
(projects/basic-buttress-338101/assets/cgsm_datacube_v1/s2), bandas B4, B3, B2 y B8
(reflectancia x10000, uint16), en la malla exacta del cubo (EPSG:9377, 10 m, 7150 x 6022).
La estacion seca se elige porque es la de menor nubosidad y la misma que usan los
compuestos de clasificacion del contrato del cubo (epoca P2/P3).

Salida: datos/s2_2025_seca.tif (4 bandas) y datos/s2_2025_seca_rgb.tif (RGB uint8 con
estiramiento fijo 0-3000 y gamma 1/1,5, el mismo de las laminas del visor), que es lo que
entra a SAM.

USO: python 00_compuesto_seco_2025.py

### `01_variables_2025.py`

Variables por punto para el Informe 2: las mismas entradas del Informe 1, pero de 2025 y sobre la
muestra de referencia propia de 720 puntos, mas la linea base por pixel con el esquema de validacion
congelado de la muestra (PROTOCOLO, k = 5 por bloques de 12 km, bufer 2,6 km).

ENTRADAS
  MUESTRA_2025/etiquetas_2025.csv   id, lon, lat, clase_final, borde_final
  MUESTRA_2025/pliegues_cv.csv      bloque12 y pliegue (congelados)
  cubo s2 2025 (GEE)                12 compuestos mensuales, B2 B3 B4 B8 B11 B12 x10000
  GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL 2025   A00-A63

VARIABLES (identicas a linea_base_2021.py / representaciones_2021.py)
  seca   : mediana ene-mar por banda, 6 bandas + NDVI, NDWI, MNDWI recalculados  (9)
  humeda : mediana sep-nov                                                       (9)
  fenologia : min, max, amp, sd de NDVI, NDWI y MNDWI en los 12 meses             (12)
  alphaearth : A00-A63                                                           (64)
BRAZOS por pixel: s2_multitemporal (30), alphaearth (64), union (94). Motor: el de
MUESTRA_2025/40_ablacion_entradas.py (RF 500 arboles, semilla 20261007, OOF con bufer,
permutacion pareada por bloques, 2000 repeticiones).

SALIDAS (informe2/)
  variables_2025_puntos.csv      720 x (id, clase_final, borde_final, bloque12, pliegue, 94 variables)
  pixel_2025_resumen.csv         macro-F1 OOF por brazo, con minimo y maximo por pliegue
  pixel_2025_clases.csv          F1 por clase y brazo
  pixel_2025_pruebas.csv         contrastes pareados por bloques
  pixel_2025_oof.csv             predicciones OOF por brazo (para el analisis de bordes y de segmentos)
USO: python 01_variables_2025.py [--sin-gee]

Comentarios en el código:

- línea 45: oof, macro, permutacion_bloques, mcnemar
- línea 108: imputacion minima, declarada: mediana de la clase

## 2. Segmentación y agregación

### `02_segmentar.py`

Segmentacion del compuesto seco de 2025 con SAM (samgeo) y con SLIC (control), en la malla del cubo.

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

Comentarios en el código:

- línea 87: dentro de la tesela, de mayor a menor area con sobreescritura: la mascara mas pequena queda encima
- línea 88: (como samgeo), de modo que un objeto anidado no desaparece dentro del grande que lo contiene
- línea 94: fusion solo con el mismo objeto visto desde otra tesela. Se compara en la zona que las dos teselas
- línea 95: observaron: (1) de la parte de la mascara nueva ya pintada por teselas previas, mas de la mitad
- línea 96: pertenece al objeto i; y (2) de la parte del objeto i dentro de esta ventana, mas de la mitad cae en
- línea 97: la mascara nueva. Un objeto grande partido por la costura cumple las dos; un objeto anidado
- línea 98: (pequeno dentro de grande, en cualquier sentido) falla una de ellas y no se absorbe.
- línea 113: entre teselas manda la primera: solo se escriben los pixeles aun sin objeto
- línea 150: sin mascara: el SLIC enmascarado de skimage (maskSLIC) es un orden de magnitud mas lento; el vacio se
- línea 151: segmenta como fondo uniforme y se anula despues con el dominio
- línea 153: SLICO (slic_zero): compacidad adaptativa por superpixel, independiente de la escala; con compactness fija
- línea 154: y superpixeles de 1 ha el termino espacial dominaba y salia una rejilla regular (18-oct)

### `13_felzenszwalb.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): segmentador con bordes adaptativos a 0,25 y 1 ha.

SLICO produjo celdas casi regulares a todas las escalas (Figura 2 del informe), así que los brazos SLIC midieron escala
de agregación y no delimitación. Felzenszwalb y Huttenlocher (2004) construyen regiones por grafo cuyo tamaño sigue el
contraste local, con bordes que se adaptan a la imagen. Se corre por teselas de 1024 px sobre Lab del compuesto RGB de
estación seca (misma entrada que SLIC), con min_size igual al área objetivo en píxeles (25 y 100) y la escala calibrada
en una tesela de calibración para que la mediana del área de los segmentos quede cerca del objetivo. Después se clasifica
con 03 (--seg felz_025ha | felz_1ha) y se compara con píxel y con SLIC a la misma escala.

SALIDAS: datos/segmentos_felz_025ha.tif, datos/segmentos_felz_1ha.tif, felz_calibracion.csv
USO: python 13_felzenszwalb.py

Comentarios en el código:

- línea 32: píxeles de 10 m
- línea 34: la escala apenas mueve la mediana en Lab; el tamaño minimo sí (calibracion del 19-oct)

### `23_felz_embedding.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): segmentar sobre el embedding de AlphaEarth, no sobre el RGB.

Las tres primeras componentes principales de AlphaEarth 2025 (ejes calculados con los 20.000 píxeles sin etiqueta de
alphaearth_pool_2025.csv) se exportan desde Earth Engine como imagen de tres bandas de 8 bits en la malla del cubo, y sobre
ella se corre Felzenszwalb con el tamaño mínimo que dio 0,25 ha sobre el RGB (min_size 8). Los bordes siguen así el
significado temático del embedding y no el color. Después 03 clasifica por segmento (--seg felz_ae_025ha).

SALIDAS: datos/alphaearth_2025_pca3_8bit.tif, datos/segmentos_felz_ae_025ha.tif, y las salidas de 03 para felz_ae_025ha
USO: python 23_felz_embedding.py

### `03_clasificar_segmentos.py`

Clasificacion por segmento frente a por pixel, con las mismas entradas, puntos, pliegues y motor.

COMO. Para cada uno de los 720 puntos se toma el segmento que lo contiene (SAM o SLIC, datos/segmentos_*.tif),
se vectoriza ese segmento y se agregan dentro de el las 94 variables del Informe 1 (media y desviacion) desde
Earth Engine: los 12 compuestos mensuales de 2025 del cubo (de los que salen las 30 espectrales, calculadas
sobre las medias por segmento igual que 01 las calcula por pixel) y AlphaEarth 2025 (64). El clasificador
es el mismo Random Forest, con los mismos pliegues y bufer; la unidad de decision cambia porque las
variables describen el segmento y no el pixel. Un punto cuyo segmento es 0 (SAM no lo cubrio) conserva sus
variables por pixel y se cuenta.

BRAZOS: pixel (01) frente a segmento, para s2_multitemporal, alphaearth y union; dos segmentadores.
PRUEBAS (PLAN): permutacion pareada por bloques de la diferencia segmento − pixel con la misma entrada;
McNemar como cifra; F1 por clase; bordes (borde_final) frente a interior.

SALIDAS (informe2/): segmentos_puntos_<seg>.csv, segmento_2025_resumen.csv, segmento_2025_clases.csv,
segmento_2025_pruebas.csv, segmento_2025_bordes.csv, segmento_2025_oof.csv
USO: python 03_clasificar_segmentos.py [--seg sam|slic] [--sin-gee]

Comentarios en el código:

- línea 43: construir, F_S2, BRAZOS, CONTRASTES
- línea 101: heterogeneidad interna del segmento en la estacion seca
- línea 119: tabla por punto con variables de segmento; sin segmento -> variables de pixel y sd 0
- línea 132: contexto como rasgo (auditoría, punto 1): el pixel conserva sus 94 variables y anade las de su segmento
- línea 136: brazos por segmento (variables del segmento) y brazo pixel + segmento

## 3. Familia de contrastes, mapas, voto y delimitación

### `05_pruebas_holm.py`

Reúne los contrastes segmento − píxel de todos los segmentadores, marca el contraste primario declarado en el
PLAN (SLIC de 1 ha frente a píxel, entrada unión) y aplica Holm sobre la familia completa de contrastes.

ENTRADAS: segmento_2025_pruebas_<seg>.csv y segmento_2025_resumen_<seg>.csv (de 03), pixel_2025_resumen.csv (de 01).
SALIDAS: resumen_segmento_vs_pixel.csv (tabla maestra) y resumen_segmento_vs_pixel.md.
USO: python 05_pruebas_holm.py

Comentarios en el código:

- línea 16: SLIC de 1 ha, entrada union
- línea 37: brazo de voto por mayoria (06), si existe: entra a la misma familia

### `06_mapas.py`

Mapas de 2025 por pixel y por segmento (voto por mayoria) y medida de delimitacion (auditoria, puntos 1 y 3).

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

Comentarios en el código:

- línea 25: PostGIS deja un proj.db viejo en PROJ_DATA; rasterio necesita el suyo, fijado antes de importarlo (spec, reproducibilidad)
- línea 48: ------------------------------------------------------------------ A. mapas por pixel
- línea 107: ------------------------------------------------------------------ B. voto por mayoria
- línea 143: sin segmento: decision por pixel del mismo mapa
- línea 145: mapa de voto con el modelo completo, para la delimitacion
- línea 163: ------------------------------------------------------------------ C. delimitacion frente a GMW 2020
- línea 164: corredor de evaluacion alrededor de la union de referencias
- línea 184: Corredor de evaluacion (regla anadida el 2026-10-19, ver PLAN): 1 km alrededor de la union INVEMAR + GMW, el mismo
- línea 185: margen con que la propuesta define el AOI. Fuera del corredor las referencias no tienen cobertura (INVEMAR no
- línea 186: cartografia la orilla oriental ni el sur), asi que el manglar del mapa alli se reporta aparte como sobreestimacion.

### `04_transferencia.py`

Transferencia temporal 2021 → 2025 por pixel: entrenar con las 600 etiquetas debiles de WorldCover 2021
(Informe 1) y evaluar sobre la muestra propia de 2025, con las mismas tres entradas.

CLASES. El Informe 1 tiene cuatro (manglar, agua, humedal_herbaceo, otro); la muestra 2025 tiene seis. Para
evaluar se agrupa la referencia 2025 a las cuatro de 2021: manglar_intacto y manglar_degradado → manglar;
agua, humedal_herbaceo y otro iguales. vegetacion_flotante no tiene clase en 2021 (en WorldCover es agua o
humedal) y se EXCLUYE de la evaluacion; se reporta aparte que clase le asigna el modelo de 2021.

COMPARACION. Para cada entrada: (a) modelo 2021 → 2025 (transferencia, sin reentrenar); (b) modelo 2025 con
validacion cruzada congelada, con las predicciones OOF de 01 agrupadas a cuatro clases (lo que se obtiene
entrenando en el mismo anio); la diferencia (a) − (b) es la degradacion por transferencia, que Ball et al.
(2026) situan entre 9 y 14 %.

SALIDAS: transferencia_2021_2025_resumen.csv, transferencia_2021_2025_clases.csv, transferencia_2021_2025_flotante.csv
USO: python 04_transferencia.py

Comentarios en el código:

- línea 43: prefijo de 2021 → el de 2025
- línea 50: las reflectancias de 2021 estan en 0-1 y las de 2025 en x10000 (asset del cubo): se igualan; los indices y la fenologia ya son adimensionales
- línea 59: predecir flotante en un punto no flotante cuenta como error

## 4. Exploratorios

### `08_deeplab.py`

Exploratorio DeepLabV3+ con etiquetas débiles (decisión de Lina, 2026-10-19; plantilla de geoai, Wu 2026).

Pregunta: ¿una red de segmentación semántica entrenada con el mapa por píxel como etiqueta débil (sin ver los
puntos) alcanza o supera al píxel en los 720 puntos? Para que la comparación sea OOF se entrenan cinco redes, una por
pliegue k, con el mapa mapa_pixel_2025_k<k>.tif (RF entrenado sin los puntos del pliegue k) como etiqueta, y cada red se
evalúa solo en los puntos del pliegue k. Mismo esquema de contraste que 03/06: permutación pareada por bloques de 12 km
y McNemar frente al píxel con entrada unión (pixel_2025_oof.csv).

Imagen: compuesto seco 2025 (B4, B3, B2, B8, uint16 reflectancia x10000) reescalado a uint8 (0-3000 -> 0-255) porque
geoai divide por 255. Teselas 256 px sin solape, etiqueta 0 = sin dato (clase extra, no se evalúa).

SALIDAS: datos/deeplab/mapa_deeplab_k<k>.tif, deeplab_2025_resumen.csv, deeplab_2025_pruebas.csv, deeplab_2025_clases.csv
USO: python 08_deeplab.py [--epocas 15]

Comentarios en el código:

- línea 35: pesos de clase inversos a la frecuencia en la etiqueta débil (sensibilidad IDL cap. 5)

### `09_deeplab_corregido.py`

Exploratorio DeepLabV3+ con etiquetas débiles CORREGIDAS por los puntos propios (decisión de Lina, 2026-10-19).

Igual que 08_deeplab.py, pero la etiqueta de cada pliegue k es el mapa RF del pliegue (mapa_pixel_2025_k<k>.tif) con el
segmento SLIC de 0,25 ha de cada punto de ENTRENAMIENTO (pliegue != k y a más de 2,6 km de los puntos de prueba, mismo
búfer que la CV congelada) pintado con la clase real del punto. Los puntos de prueba nunca se pintan. Pregunta: ¿720
parches limpios bastan para que la red corrija al maestro?

SALIDAS: datos/deeplab/etiqueta_corr_k<k>.tif, mapa_deeplab_kc<k>.tif, deeplab_corr_2025_{resumen,pruebas,oof}.csv
USO: python 09_deeplab_corregido.py [--epocas 15]

Comentarios en el código:

- línea 57: sin segmento: ventana 3x3

### `10_propagacion_alphaearth.py`

Exploratorio: propagación de etiquetas sobre el embedding AlphaEarth 2025 (semisupervisado), decisión de Lina 2026-10-19.

Pregunta: ¿el embedding fundacional, sin Random Forest, separa las clases cuando las 720 etiquetas se propagan a un
conjunto de píxeles sin etiqueta? Dos brazos, mismo esquema OOF que la CV congelada (k = 5 bloques de 12 km, búfer de
2,6 km, contraste de permutación por bloques y McNemar frente al píxel con entrada unión):
  - knn_alphaearth: k vecinos (k = 10) solo con los puntos etiquetados de entrenamiento (control sin propagación).
  - propagacion_alphaearth: LabelSpreading (kernel knn, 10 vecinos, alpha 0,2) con los puntos de entrenamiento como
    etiquetados y un conjunto de 20.000 píxeles del AOI muestreados en Earth Engine más los puntos de prueba como no
    etiquetados.
El conjunto sin etiqueta se descarga una vez (alphaearth_pool_2025.csv, 4 lotes de 5.000 con semillas fijas).

SALIDAS: alphaearth_pool_2025.csv, propagacion_2025_{resumen,pruebas,oof}.csv
USO: python 10_propagacion_alphaearth.py

### `07_tessera_2025.py`

TESSERA 2025 en los 720 puntos de la muestra (cuarta entrada del Informe 2, punto 5 de la auditoria).

Usa geotessera (sample_embeddings_at_points, 128 dimensiones, teselas de 0,1 grado a 10 m, descarga
automatica de las que falten). Si alguna tesela de 2025 no existe, los puntos que caen en ella quedan sin
valor y se reporta la cobertura: la entrada entra al informe solo si cubre los 720 puntos (si no, se
declara, como se hizo con 2021 en el Informe 1, donde cubria 305 de 600).

SALIDA: tessera_2025_puntos.csv (id, T000..T127) y tessera_2025_cobertura.txt
USO: python 07_tessera_2025.py

## 5. Extensión posterior al cierre

### `12_filtro_mayoria.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): filtro de mayoría de 5 x 5 píxeles sobre el mapa por píxel.

Pregunta: el aporte de SLIC 0,25 ha en los bordes (+0,05) ¿se obtiene con un filtro de mayoría de 5 x 5 (0,25 ha) sin
segmentador? Se filtra cada mapa por pliegue (mapa_pixel_2025_k<k>.tif, modelo sin los puntos del pliegue) y se evalúa en
los puntos del pliegue: OOF, bordes e interior, permutación por bloques y McNemar frente al píxel unión. El mapa completo
filtrado se compara contra INVEMAR y GMW en el corredor de 1 km (misma regla que 06).

SALIDAS: datos/mapa_pixel_2025_filtro5.tif, datos/mapa_pixel_2025_k<k>_filtro5.tif, filtro5_2025_{resumen,pruebas,bordes,oof}.csv,
         filtro5_2025_delimitacion.csv
USO: python 12_filtro_mayoria.py [--ventana 5]

Comentarios en el código:

- línea 93: delimitacion del mapa completo filtrado, misma regla del corredor de 06

### `14_sam_puntos.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): SAM con los puntos de referencia como indicaciones (one-shot,
Osco et al. 2023), evaluado fuera de pliegue con el esquema congelado.

Para cada uno de los 720 puntos se corre SamPredictor (ViT-H) sobre una ventana de 512 px del compuesto RGB de estación
seca centrada en el punto, con el punto como indicación positiva, y se guardan dos máscaras: la de mayor puntaje de SAM
("mejor") y la más pequeña de las tres ("menor"). Después, por pliegue k (entrenamiento = pliegue != k y a más de 2,6 km
de la prueba):
  - pintura_mejor / pintura_menor: las máscaras de los puntos de ENTRENAMIENTO se pintan con su clase, de mayor a menor
    área (la pequeña queda encima); el punto de prueba toma la clase pintada en su píxel. Sin pintura: decisión por
    píxel (OOF unión), y se reporta la cobertura.
  - objeto_propio: la máscara "mejor" del punto de PRUEBA (solo usa su posición, no su etiqueta) toma la clase
    mayoritaria de los puntos de entrenamiento que caen dentro; sin ninguno, decisión por píxel.
Contraste frente al píxel unión: permutación por bloques y McNemar, como en 03.

SALIDAS: datos/sam_puntos_mascaras.npz, sam_puntos_2025_{resumen,pruebas,oof,cobertura}.csv
Hallazgo del 19-oct: con ventana de 512 px (alcance 2,56 km) y búfer de 2,6 km ninguna máscara de entrenamiento puede
llegar a un punto de prueba (cobertura 4 %), así que la prueba se corre con ventana de 1024 px y, como sensibilidad
declarada en el protocolo, con búfer 0.

USO: python 14_sam_puntos.py [--ventana 1024] [--bufer 2600|0]

Comentarios en el código:

- línea 101: grandes primero, pequeñas encima
- línea 106: objeto propio: máscara del punto de prueba, clase mayoritaria de los puntos de entrenamiento dentro

### `15_cambio_objeto.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): cambio 2021 → 2025 por píxel frente a por objeto.

Un mismo clasificador (RF de 500 árboles en Earth Engine, entrenado con las 600 etiquetas débiles de WorldCover 2021 y
las 94 variables de 2021, cuatro clases: agua, humedal herbáceo, manglar, otro) se aplica a la pila de 2021 y a la de
2025 del cubo, de modo que la diferencia entre fechas no mezcla modelos. El cambio por píxel es el desacuerdo píxel a
píxel; el cambio por objeto usa los segmentos de Felzenszwalb de 1 ha de 2025 y la clase mayoritaria de cada objeto en
cada fecha. Se comparan: área cambiada, fragmentación del cambio (componentes conexas de 4 píxeles o menos, el ruido de
"sal y pimienta") y, en los 591 puntos de 2025 que no son vegetación flotante, el acuerdo con un cambio de referencia
débil: etiqueta WorldCover 2021 en el punto frente a la etiqueta propia de 2025 agrupada a cuatro clases.

SALIDAS: datos/mapa_2021_modelo2021.tif, datos/mapa_2025_modelo2021.tif, cambio_2025_{resumen,transiciones,puntos}.csv
USO: python 15_cambio_objeto.py

Comentarios en el código:

- línea 36: resto de WorldCover → otro
- línea 70: reflectancias de 2021 en 0-1 → unidades del cubo (x10000), como la pila
- línea 98: WorldCover 2021 en los 720 puntos (referencia débil de 2021)
- línea 143: puntos: referencia debil de cambio

### `16_texto_langsam.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): segmentación por texto, cero ejemplos, con LangSAM
(Grounding DINO 'tiny' de transformers para las cajas y SAM ViT-H para las máscaras; equivalente a LangSAM de samgeo, Wu y Osco 2023). Indicación "mangrove" sobre teselas de 1024 px del compuesto
RGB de estación seca 2025. No usa etiquetas, así que se evalúa en los 720 puntos sin pliegues: F1 de manglar (intacto +
degradado) frente a no manglar, y delimitación contra INVEMAR y GMW en el corredor de 1 km como los demás mapas.

SALIDAS: datos/mapa_texto_mangrove.tif (1 = manglar según el texto), texto_2025_resumen.csv
USO: python 16_texto_langsam.py [--prompt mangrove] [--umbral 0.24]

Comentarios en el código:

- línea 37: samgeo.text_sam (groundingdino-py) no carga con transformers 5.x (BertModel sin get_extended_attention_mask, 19-oct);
- línea 38: se usa Grounding DINO de transformers para las cajas por texto y SamPredictor para las máscaras de cada caja.

### `17_serie_temporal.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): modelo temporal sobre la serie mensual de 2025.

El Random Forest del píxel resume la serie mensual en 30 variables (medianas de dos estaciones y 12 descriptores
fenológicos). Aquí la serie entra entera: 12 meses x 9 canales (B2, B3, B4, B8, B11, B12, NDVI, NDWI, MNDWI) más un
canal de máscara de mes sin dato (relleno con la mediana del punto). Dos brazos con la misma CV congelada (k = 5 por
bloques de 12 km, búfer 2,6 km) y contraste de permutación por bloques frente al píxel espectral (0,580) y al píxel
unión (0,591):
  - serie_cruda_rf: Random Forest sobre los 120 valores de la serie (control: ¿importa el modelo o la información?).
  - serie_cnn1d: red convolucional 1D (2 capas, 32 y 64 filtros, núcleo 3, agrupación global, capa densa), entropía
    cruzada ponderada por la inversa de la frecuencia, Adam 1e-3, 150 épocas, estandarización por canal con las
    estadísticas del entrenamiento del pliegue, semilla 20261007.

SALIDAS: serie_mensual_2025_puntos.csv (caché de GEE), serie_2025_{resumen,pruebas,oof}.csv
USO: python 17_serie_temporal.py [--epocas 150]

Comentarios en el código:

- línea 98: brazo 1: RF sobre la serie cruda (120 valores)

### `18_ecostress_entrada.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): temperatura de superficie nocturna de ECOSTRESS como entrada.

Para cada uno de los 720 puntos se toma, de NASA/ECOSTRESS/L2T_LSTE/V2 en Earth Engine (misma limpieza que el ejercicio
del curso: nube 0, QC bits 0-1 <= 1, 270 < LST < 340 K), la mediana mensual de 2025 de la temperatura de superficie
nocturna (hora local fuera de 06-18) y diurna, a 70 m. Variables: 12 medianas nocturnas, 12 diurnas, y por régimen la
mediana, el mínimo, el máximo, la amplitud y la desviación anual, más el número de meses con dato. Los meses sin dato se
rellenan con la mediana anual del punto y, si el punto no tiene ningún mes, con la mediana de su clase (declarado).
Brazos con la CV congelada: lst sola, espectral + lst, unión + lst; contraste de permutación frente al mismo brazo sin lst.

SALIDAS: ecostress_2025_puntos.csv (caché), ecostress_2025_{resumen,pruebas,oof}.csv
USO: python 18_ecostress_entrada.py

### `19a_compuestos_trimestrales.py`

Cuatro compuestos trimestrales de 2025 del cubo (B2, B3, B4, B8, B11, B12, uint16 x10000), en la malla exacta del cubo,
como entrada multitemporal de Prithvi-EO 2.0 (num_frames 4). Misma receta de exportación que 06_mapas.py (rectángulo
exacto contraído 1 m, WKT1_GDAL de 9377, máscara del AOI con imagen constante).

SALIDA: datos/s2_2025_q1.tif ... s2_2025_q4.tif
USO: python 19a_compuestos_trimestrales.py

### `19_prithvi.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): representaciones de Prithvi-EO 2.0 (300M) como entrada.

Prithvi-EO 2.0 (IBM y NASA, ViT-L preentrenado como autocodificador enmascarado sobre HLS) se usa como extractor de
rasgos congelado, en el mismo papel que AlphaEarth en el Informe 1: para cada uno de los 720 puntos se toma una ventana
de 224 x 224 píxeles del cubo con las seis bandas que el modelo espera (B2, B3, B4, B8, B11, B12, en el orden B02 B03 B04
B05 B06 B07 de HLS) y cuatro instantes temporales (compuestos trimestrales de 2025), normalizadas con la media y la
desviación del modelo, y se extraen dos representaciones del codificador sin enmascarar:
  - prithvi_centro: media sobre los cuatro instantes del token del parche central (16 x 16 m) donde cae el punto (1.024).
  - prithvi_contexto: media de todos los tokens de parche de la ventana (1.024), el contexto de 2,2 km.
Brazos con la CV congelada (RF 500 árboles, k = 5 bloques de 12 km, búfer 2,6 km): prithvi_centro, prithvi_contexto,
s2_mas_prithvi_centro, y contraste de permutación frente a alphaearth (0,595) y píxel unión (0,591). Desviación declarada:
la banda B8 (NIR ancho de Sentinel-2) ocupa el lugar de B05 (NIR estrecho de HLS), y el modelo no recibe coordenadas.

SALIDAS: prithvi_2025_puntos.npz (embeddings), prithvi_2025_{resumen,pruebas,oof}.csv
USO: python 19_prithvi.py

Comentarios en el código:

- línea 75: índice del parche central dentro de un instante
- línea 82: (6, W, W) x10000
- línea 87: (1 + T*196, 1024)
- línea 89: desplazamiento del punto dentro de la ventana cuando la ventana se recortó al borde

### `21_contexto_multiescala.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): contexto multiescala como rasgo.

Hasta ahora cada escala de contexto entró sola (píxel + medias de su segmento a una escala). Aquí el píxel recibe a la vez
las medias de sus celdas de 0,25, 1 y 4 ha (SLIC) o de sus objetos de Felzenszwalb de 0,25 y 1 ha más la celda SLIC de 4
ha, reutilizando las tablas por segmento ya agregadas en Earth Engine por 03 (segmentos_puntos_<seg>.csv). Misma CV
congelada, contraste de permutación frente al píxel unión (0,591), bordes e interior.

SALIDAS: multiescala_2025_{resumen,pruebas,bordes,oof}.csv
USO: python 21_contexto_multiescala.py

Comentarios en el código:

- línea 51: sin segmento o sin agregacion: la variable del pixel

### `22_suavizado_prob.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): suavizado de probabilidades dentro del objeto en vez de voto duro.

El voto por mayoría (06) pierde la información de las probabilidades. Aquí, para cada pliegue k, el Random Forest de Earth
Engine (mismos puntos de entrenamiento y variables que 06, salida MULTIPROBABILITY) produce las seis probabilidades por
píxel, y para cada punto de prueba se promedian dentro de su objeto (polígono del segmento, como en 03) y se decide por el
máximo. Segmentadores: Felzenszwalb 0,25 ha y SLIC 0,25 ha. Contraste frente al píxel unión (OOF sklearn) y bordes.

SALIDAS: suavizado_prob_<seg>_puntos.csv (probabilidades medias por punto y pliegue), suavizado_2025_{resumen,pruebas,bordes,oof}.csv
USO: python 22_suavizado_prob.py

## 6. Segunda ronda de muestra (820 puntos)

### `muestra_2025/50_puntos_dirigidos_2026-10.py`

Puntos dirigidos de 2025 (decisión de Lina, 2026-10-19) para cubrir el hueco medido en el Informe 2: la muestra tiene 44
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

Comentarios en el código:

- línea 71: herramienta de etiquetado en el Code Editor (ciega: solo id y posicion)

### `muestra_2025/51_puntos_humedal_2026-10.py`

Tercera ronda dirigida (decisión de Lina, 2026-10-19): 60 puntos más en la frontera humedal / manglar degradado.

La curva de aprendizaje sobre los 820 mostró que el F1 de humedal sube unos 7 puntos por cada 20 ejemplos y aún no llega a
meseta, pero que lo que se mueve es la frontera con degradado. Por eso el estrato no es "donde el mapa dice humedal" (ya
usado en la ronda 2) sino donde el mapa de 820 dice manglar degradado a 300 m o menos de un píxel que dice humedal: la
zona de confusión. Sorteo con semilla fija, fuera de la reserva de validación, a 200 m o más entre sí y de los 820 puntos.
El estrato y la clase del mapa NO se muestran en la herramienta de etiquetado (ciego). Criterio v1.1: troncos o estructura
leñosa en Google de alta resolución = degradado; vegetación lisa y continua = humedal.

SALIDAS: puntos_humedal_2026-10.csv (id desde 821, lon, lat, estrato, clase_mapa, etapa), etiquetar_humedal_gee.js
USO: python 51_puntos_humedal_2026-10.py

Comentarios en el código:

- línea 31: mapa entrenado con 820

### `segunda_ronda/01_variables_2025.py`

Variables por punto para el Informe 2: las mismas entradas del Informe 1, pero de 2025 y sobre la
muestra de referencia propia de 720 puntos, mas la linea base por pixel con el esquema de validacion
congelado de la muestra (PROTOCOLO, k = 5 por bloques de 12 km, bufer 2,6 km).

ENTRADAS
  MUESTRA_2025/etiquetas_2025.csv   id, lon, lat, clase_final, borde_final
  MUESTRA_2025/pliegues_cv.csv      bloque12 y pliegue (congelados)
  cubo s2 2025 (GEE)                12 compuestos mensuales, B2 B3 B4 B8 B11 B12 x10000
  GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL 2025   A00-A63

VARIABLES (identicas a linea_base_2021.py / representaciones_2021.py)
  seca   : mediana ene-mar por banda, 6 bandas + NDVI, NDWI, MNDWI recalculados  (9)
  humeda : mediana sep-nov                                                       (9)
  fenologia : min, max, amp, sd de NDVI, NDWI y MNDWI en los 12 meses             (12)
  alphaearth : A00-A63                                                           (64)
BRAZOS por pixel: s2_multitemporal (30), alphaearth (64), union (94). Motor: el de
MUESTRA_2025/40_ablacion_entradas.py (RF 500 arboles, semilla 20261007, OOF con bufer,
permutacion pareada por bloques, 2000 repeticiones).

SALIDAS (informe2/)
  variables_2025_puntos.csv      720 x (id, clase_final, borde_final, bloque12, pliegue, 94 variables)
  pixel_2025_resumen.csv         macro-F1 OOF por brazo, con minimo y maximo por pliegue
  pixel_2025_clases.csv          F1 por clase y brazo
  pixel_2025_pruebas.csv         contrastes pareados por bloques
  pixel_2025_oof.csv             predicciones OOF por brazo (para el analisis de bordes y de segmentos)
USO: python 01_variables_2025.py [--sin-gee]

Comentarios en el código:

- línea 45: oof, macro, permutacion_bloques, mcnemar
- línea 108: imputacion minima, declarada: mediana de la clase

### `segunda_ronda/03_clasificar_segmentos.py`

Clasificacion por segmento frente a por pixel, con las mismas entradas, puntos, pliegues y motor.

COMO. Para cada uno de los 720 puntos se toma el segmento que lo contiene (SAM o SLIC, datos/segmentos_*.tif),
se vectoriza ese segmento y se agregan dentro de el las 94 variables del Informe 1 (media y desviacion) desde
Earth Engine: los 12 compuestos mensuales de 2025 del cubo (de los que salen las 30 espectrales, calculadas
sobre las medias por segmento igual que 01 las calcula por pixel) y AlphaEarth 2025 (64). El clasificador
es el mismo Random Forest, con los mismos pliegues y bufer; la unidad de decision cambia porque las
variables describen el segmento y no el pixel. Un punto cuyo segmento es 0 (SAM no lo cubrio) conserva sus
variables por pixel y se cuenta.

BRAZOS: pixel (01) frente a segmento, para s2_multitemporal, alphaearth y union; dos segmentadores.
PRUEBAS (PLAN): permutacion pareada por bloques de la diferencia segmento − pixel con la misma entrada;
McNemar como cifra; F1 por clase; bordes (borde_final) frente a interior.

SALIDAS (informe2/): segmentos_puntos_<seg>.csv, segmento_2025_resumen.csv, segmento_2025_clases.csv,
segmento_2025_pruebas.csv, segmento_2025_bordes.csv, segmento_2025_oof.csv
USO: python 03_clasificar_segmentos.py [--seg sam|slic] [--sin-gee]

Comentarios en el código:

- línea 43: construir, F_S2, BRAZOS, CONTRASTES
- línea 101: heterogeneidad interna del segmento en la estacion seca
- línea 119: tabla por punto con variables de segmento; sin segmento -> variables de pixel y sd 0
- línea 132: contexto como rasgo (auditoría, punto 1): el pixel conserva sus 94 variables y anade las de su segmento
- línea 136: brazos por segmento (variables del segmento) y brazo pixel + segmento

### `segunda_ronda/05_pruebas_holm.py`

Reúne los contrastes segmento − píxel de todos los segmentadores, marca el contraste primario declarado en el
PLAN (SLIC de 1 ha frente a píxel, entrada unión) y aplica Holm sobre la familia completa de contrastes.

ENTRADAS: segmento_2025_pruebas_<seg>.csv y segmento_2025_resumen_<seg>.csv (de 03), pixel_2025_resumen.csv (de 01).
SALIDAS: resumen_segmento_vs_pixel.csv (tabla maestra) y resumen_segmento_vs_pixel.md.
USO: python 05_pruebas_holm.py

Comentarios en el código:

- línea 16: SLIC de 1 ha, entrada union
- línea 37: brazo de voto por mayoria (06), si existe: entra a la misma familia

### `segunda_ronda/06_mapas.py`

Mapas de 2025 por pixel y por segmento (voto por mayoria) y medida de delimitacion (auditoria, puntos 1 y 3).

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

Comentarios en el código:

- línea 25: PostGIS deja un proj.db viejo en PROJ_DATA; rasterio necesita el suyo, fijado antes de importarlo (spec, reproducibilidad)
- línea 48: ------------------------------------------------------------------ A. mapas por pixel
- línea 107: ------------------------------------------------------------------ B. voto por mayoria
- línea 143: sin segmento: decision por pixel del mismo mapa
- línea 145: mapa de voto con el modelo completo, para la delimitacion
- línea 163: ------------------------------------------------------------------ C. delimitacion frente a GMW 2020
- línea 164: corredor de evaluacion alrededor de la union de referencias
- línea 184: Corredor de evaluacion (regla anadida el 2026-10-19, ver PLAN): 1 km alrededor de la union INVEMAR + GMW, el mismo
- línea 185: margen con que la propuesta define el AOI. Fuera del corredor las referencias no tienen cobertura (INVEMAR no
- línea 186: cartografia la orilla oriental ni el sur), asi que el manglar del mapa alli se reporta aparte como sobreestimacion.

### `segunda_ronda/12_filtro_mayoria.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): filtro de mayoría de 5 x 5 píxeles sobre el mapa por píxel.

Pregunta: el aporte de SLIC 0,25 ha en los bordes (+0,05) ¿se obtiene con un filtro de mayoría de 5 x 5 (0,25 ha) sin
segmentador? Se filtra cada mapa por pliegue (mapa_pixel_2025_k<k>.tif, modelo sin los puntos del pliegue) y se evalúa en
los puntos del pliegue: OOF, bordes e interior, permutación por bloques y McNemar frente al píxel unión. El mapa completo
filtrado se compara contra INVEMAR y GMW en el corredor de 1 km (misma regla que 06).

SALIDAS: datos/mapa_pixel_2025_filtro5.tif, datos/mapa_pixel_2025_k<k>_filtro5.tif, filtro5_2025_{resumen,pruebas,bordes,oof}.csv,
         filtro5_2025_delimitacion.csv
USO: python 12_filtro_mayoria.py [--ventana 5]

Comentarios en el código:

- línea 93: delimitacion del mapa completo filtrado, misma regla del corredor de 06

### `segunda_ronda/21_contexto_multiescala.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): contexto multiescala como rasgo.

Hasta ahora cada escala de contexto entró sola (píxel + medias de su segmento a una escala). Aquí el píxel recibe a la vez
las medias de sus celdas de 0,25, 1 y 4 ha (SLIC) o de sus objetos de Felzenszwalb de 0,25 y 1 ha más la celda SLIC de 4
ha, reutilizando las tablas por segmento ya agregadas en Earth Engine por 03 (segmentos_puntos_<seg>.csv). Misma CV
congelada, contraste de permutación frente al píxel unión (0,591), bordes e interior.

SALIDAS: multiescala_2025_{resumen,pruebas,bordes,oof}.csv
USO: python 21_contexto_multiescala.py

Comentarios en el código:

- línea 51: sin segmento o sin agregacion: la variable del pixel

### `segunda_ronda/24_s1_entrada.py`

Extensión del Informe 2 (decisión de Lina, 2026-10-19): Sentinel-1 como entrada, por píxel y como media por objeto.

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

### `segunda_ronda/25_curva_humedal.py`

Curva de aprendizaje de la clase humedal herbáceo sobre la muestra de 820 (Informe 2, segunda ronda).

Se quitan al azar puntos de humedal hasta dejar 40, 73 (ronda 1), 90 y 113 (todos), cinco sorteos por tamaño, y se repite
el píxel unión con la misma CV congelada. Se reporta el F1 de humedal, el de degradado y la macro-F1. Además la variante
con humedal y degradado fusionados (cinco clases).

SALIDAS: curva_humedal_820.csv, fusion_humedal_degradado_820.csv
USO: python 25_curva_humedal.py

## 7. Figuras e informe

### `11_figuras.py`

Figuras del Informe 2 (segmento frente a píxel, CGSM 2025). Todas se leen de las salidas reales de 01 a 10.

SALIDA: figuras/fig1_muestra.png, fig2_segmentaciones.png, fig3_diferencias.png, fig4_bordes.png,
        fig5_delimitacion.png, fig6_exploratorios.png, fig7_clases.png
USO: python 11_figuras.py

Comentarios en el código:

- línea 72: 3 km x 3 km
- línea 137: 1 acuerdo, 2 mapa fuera de ref en corredor, 3 mapa fuera del corredor, 4 ref sin mapa

### `26_fig9_segunda_ronda.py`

Figura 9 del Informe 2: segunda ronda. a) curva de aprendizaje de humedal sobre los 820 (informe2_ampliada/curva_humedal_820.csv),
b) macro-F1 de los brazos principales en las dos rondas, leída de los resúmenes reales de informe2/ e informe2_ampliada/.
SALIDA: figuras/fig9_segunda_ronda.png
USO: python 26_fig9_segunda_ronda.py

### `informe_a_word.py`

Convierte Informe2.md en Informe2.docx: carta, margenes 2,5 cm, Calibri 11,
cuerpo justificado, encabezados en negrita sin numerar, tablas markdown con fila
de encabezado sombreada y figuras insertadas desde ![pie](ruta).

El bloque de cabecera (lineas antes del primer "## ") va una por linea, sin
negrita, salvo la ultima, que es el titulo.

USO
    python informe_a_word.py

## Dependencia compartida de la muestra de 2025

### `muestra_2025/40_ablacion_entradas.py`

Ablacion de entradas con la muestra 2025 bajo el esquema de CV aprobado (PROTOCOLO,
"Validacion cruzada, puntos dirigidos y reporte", 20-sep-2026).

PREGUNTA. Que aporta cada fuente al clasificador de seis clases: optico de Sentinel-2
(cubo 2025), banda C de Sentinel-1 (orbita 142) y banda L de NISAR (traza 083). La
ablacion principal de la tesis es la de NISAR: O+C+L frente a O+C.

ENTRADAS
  etiquetas_2025.csv            clase_final, lon, lat (720 puntos)
  pliegues_cv.csv               pliegue 1-5 y bloque de 12 km por id (congelado, hash en PROTOCOLO)
  ../../RADAR/clave_muestra2025_puntos.csv   VV, VH (mediana de 61 pasadas S1) y HH, HV
                                (mediana de 12 escenas NISAR), extraidos por clave_vs_muestra2025.py
  cubo s2 2025 en GEE           medianas anuales de B2, B3, B4, B8, B11, B12, NDVI, NDWI, CMRI
                                y minimo, maximo y amplitud de NDVI (12 imagenes mensuales)

ESQUEMA. k = 5 pliegues por bloques de 12 km; al evaluar un pliegue se retiran del
entrenamiento los puntos a menos de BUFER m de cualquier punto de prueba (2,6 km por
defecto; --bufer 0|2600|5200 para la sensibilidad declarada). Random Forest de 500 arboles
con hiperparametros fijos (sin ajuste interno: la pregunta es sobre las entradas, no sobre
el modelo). Predicciones fuera de pliegue (OOF) para cada brazo.

REPORTE (segun el protocolo)
  - macro-F1 OOF por brazo, y pliegue a pliegue (minimo, maximo)
  - F1 por clase con intervalo por remuestreo de bloques (24 bloques, 2000 repeticiones),
    con la proporcion de repeticiones sin la clase
  - prueba principal entre brazos: permutacion pareada en el nivel de bloque sobre la
    diferencia de macro-F1 OOF (2000 permutaciones); McNemar solo como cifra de comparacion
  - manglar_degradado: su F1 se declara de potencia muy baja (protocolo); se reporta igual

SENSIBILIDAD (protocolo): --bufer 0|2600|5200 y --k 10. Con --k 10 los 24 bloques se reparten
en diez pliegues con la misma regla determinista de 32_esquema_cv.py (de mayor a menor numero
de puntos, cada bloque al pliegue mas vacio).

SERIE TEMPORAL (--serie): brazo Os = las 6 bandas medianas mas NDVI y NDWI de cada uno de los
12 meses de 2025 (24 variables; un mes sin dato en un punto se rellena con la mediana anual
de ese punto, y se reporta cuantos). Brazos Os, Os+C, Os+L, Os+C+L; contrastes Os vs O,
Os+C+L vs Os+C, Os+C vs Os.

USO: python 40_ablacion_entradas.py [--bufer 2600] [--k 5] [--serie] [--sin-gee]
Salidas: ablacion_2025_rasgos.csv (cache de rasgos), ablacion_2025_oof.csv,
         ablacion_2025_resumen.csv, ablacion_2025_clases.csv, ablacion_2025_pruebas.csv
         (con sufijo _bufer0, _bufer5200, _k10 o _serie segun la corrida)
