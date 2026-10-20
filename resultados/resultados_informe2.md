# Informe 2: resultados consolidados (2026-10-19)

Píxel (referencia): macro-F1 OOF espectral 0,580, AlphaEarth 0,595, unión 0,591. Familia de 35 contrastes, Holm. Contraste primario: SLIC 1 ha, entrada unión.

## Tabla A. Segmento frente a píxel por segmentador (diferencia de macro-F1 OOF, p de permutación por bloques; * significativo tras Holm)

| Segmentador | espectral | AlphaEarth | unión (segmento) | píxel + contexto | voto por mayoría |
|---|---|---|---|---|---|
| SAM grueso (1024/32) | -0.269 (p 0.000)* | -0.242 (p 0.000)* | -0.219 (p 0.000)* | -0.014 (p 0.242) | -0.166 (p 0.000)* |
| SAM fino (512/64) | -0.172 (p 0.000)* | -0.122 (p 0.000)* | -0.130 (p 0.000)* | +0.004 (p 0.812) | -0.086 (p 0.000)* |
| SLIC 139 ha | -0.217 (p 0.000)* | -0.175 (p 0.000)* | -0.163 (p 0.001)* | -0.002 (p 0.926) | -0.197 (p 0.000)* |
| SLIC 16 ha | -0.130 (p 0.000)* | -0.076 (p 0.001)* | -0.101 (p 0.000)* | -0.016 (p 0.379) | -0.113 (p 0.000)* |
| SLIC 4 ha | -0.114 (p 0.001)* | -0.037 (p 0.048) | -0.047 (p 0.006) | +0.003 (p 0.866) | -0.080 (p 0.000)* |
| SLIC 1 ha | -0.079 (p 0.004) | -0.019 (p 0.325) | -0.012 (p 0.484) | +0.015 (p 0.218) | -0.050 (p 0.000)* |
| SLIC 0,25 ha | -0.036 (p 0.106) | -0.010 (p 0.495) | +0.020 (p 0.279) | +0.013 (p 0.320) | +0.001 (p 0.944) |

## Tabla B. Delimitación del manglar (intacto + degradado) en el corredor de 1 km alrededor de INVEMAR + GMW

Referencias: INVEMAR 1:25.000 31.905 ha, GMW 2020 41.498 ha, unión 48.595 ha, intersección 24.809 ha (Jaccard entre referencias 0,51). Corredor 127.951 ha.

| Mapa | Manglar en corredor (ha) | Fuera del corredor (ha) | Jaccard INVEMAR corredor / dominio | Jaccard GMW corredor / dominio | INVEMAR recuperado | Mediana borde mapa→INVEMAR (m) |
|---|---|---|---|---|---|---|
| píxel | 67521 | 14191 | 0.461 / 0.381 | 0.538 / 0.449 | 0.983 | 122 |
| SAM grueso (1024/32) | 73451 | 19164 | 0.398 / 0.317 | 0.456 / 0.367 | 0.940 | 60 |
| SAM fino (512/64) | 74536 | 17538 | 0.394 / 0.320 | 0.481 / 0.393 | 0.943 | 54 |
| SLIC 139 ha | 72085 | 13349 | 0.356 / 0.303 | 0.437 / 0.374 | 0.855 | 232 |
| SLIC 16 ha | 71090 | 13754 | 0.396 / 0.334 | 0.496 / 0.419 | 0.916 | 132 |
| SLIC 4 ha | 69860 | 13791 | 0.422 / 0.354 | 0.525 / 0.441 | 0.947 | 94 |
| SLIC 1 ha | 68895 | 14077 | 0.441 / 0.367 | 0.537 / 0.449 | 0.966 | 90 |
| SLIC 0,25 ha | 68236 | 14113 | 0.453 / 0.376 | 0.538 / 0.449 | 0.978 | 103 |

## Muestra frente a referencias

De 262 puntos propios de manglar: 172 dentro de la unión INVEMAR + GMW, 71 en el corredor fuera de la unión, 19 a más de 1 km de cualquier referencia (lista en `puntos_manglar_revisar.csv`). De 116 puntos no manglar fuera del corredor, el mapa por píxel no llama manglar a ninguno: la sobreestimación del sur (14.191 ha) está en zonas sin puntos. Muestra: otro 44, humedal 73.

## Tabla C. Exploratorio DeepLabV3+ (resnet34, etiquetas débiles = mapa RF por píxel del mismo pliegue, 15 épocas, 371 teselas de 256 px por pliegue)

| Brazo | macro-F1 OOF | pliegues | exactitud | agua | humedal | degradado | intacto | otro | flotante | deeplab − píxel unión | p permutación | p McNemar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DeepLabV3+ etiquetas débiles | 0.454 | 0.297 a 0.520 | 0.574 | 0.729 | 0.125 | 0.526 | 0.734 | 0.388 | 0.219 | -0.137 | 0.0000 | 0.0000 |
| DeepLabV3+ etiquetas débiles corregidas con los parches SLIC 0,25 ha de los puntos de entrenamiento | 0.442 | 0.294 a 0.524 | 0.562 | 0.741 | 0.115 | 0.467 | 0.732 | 0.312 | 0.287 | -0.149 | 0.0000 | 0.0000 |

Lectura: la red reproduce las clases dominantes del mapa débil (con o sin los parches de los puntos: 131 ha pintadas por pliegue no mueven a la red) (intacto 0,73, agua 0,73) pero pierde las minoritarias (humedal 0,13, flotante 0,22); con etiquetas que ya tienen macro-F1 0,59 y sin ver los puntos, no puede superar al maestro. Resultado negativo, exploratorio, una sola configuración.

## Tabla D. Exploratorio semisupervisado sobre AlphaEarth 2025 (64 dimensiones, misma CV congelada)

| Brazo | macro-F1 OOF | pliegues | agua | humedal | degradado | intacto | otro | flotante | − píxel unión | p permutación | p McNemar |
|---|---|---|---|---|---|---|---|---|---|---|---|
| k vecinos (k 10), solo puntos etiquetados | 0.579 | 0.441 a 0.652 | 0.815 | 0.258 | 0.569 | 0.797 | 0.467 | 0.571 | -0.012 | 0.6080 | 0.8424 |
| LabelSpreading (knn 10, alpha 0,2) + 20.000 píxeles sin etiqueta | 0.540 | 0.455 a 0.597 | 0.797 | 0.232 | 0.480 | 0.692 | 0.377 | 0.662 | -0.051 | 0.0840 | 0.0241 |

Lectura: el embedding fundacional con un clasificador trivial (k vecinos) iguala al Random Forest con 94 variables (−0,012, p 0,61): la información está en el embedding, no en el clasificador. Añadir 20.000 píxeles sin etiqueta por propagación no ayuda (−0,051, p 0,08; McNemar p 0,02): las clases minoritarias (humedal, flotante) se diluyen hacia las dominantes.

## Extensión (2026-10-19, decisión de Lina): filtro de mayoría 5 x 5 sobre el mapa por píxel

| Brazo | macro-F1 OOF | pliegues | borde (n 208) | interior (n 512) | − píxel unión (OOF sklearn) | − mapa por pliegue sin filtro (pareado exacto) | Jaccard INVEMAR / GMW corredor | mediana de borde hacia INVEMAR |
|---|---|---|---|---|---|---|---|---|
| píxel unión | 0,591 | 0,439 a 0,601 | 0,453 | 0,626 | | | 0,461 / 0,538 | 122 m |
| filtro de mayoría 5 x 5 | 0,605 | 0,464 a 0,640 | 0,472 | 0,635 | +0,014 (p 0,24) | +0,014 (p 0,10) | 0,458 / 0,539 | 110 m |

Control: el mapa por pliegue (RF en Earth Engine) reproduce la predicción OOF de sklearn en el 95,6 % de los puntos. El filtro cambia el 4,3 a 4,9 % de los píxeles de cada mapa. Lectura: +0,014 está por debajo de la DMD (0,016); el filtro mejora bordes (+0,02) e interior (+0,01) sin costo y sin segmentador, y no cambia la delimitación.

## Extensión: SAM con los puntos de referencia como indicaciones (`14_sam_puntos.py`, ViT-H, ventana 1024 px)

Máscara 'mejor' (mayor puntaje) mediana 4.659 ha, 'menor' 99,8 ha; puntaje mediano 0,97. Con ventana de 512 px y búfer 2,6 km la cobertura de prueba era 4 % (alcance 2,56 km < búfer), por eso la ventana de 1.024 px y la sensibilidad con búfer 0.

| Variante | búfer | cobertura de prueba | macro-F1 en cubiertos (SAM / píxel) | macro-F1 OOF con respaldo píxel | − píxel | p |
|---|---|---|---|---|---|---|
| pintura_mejor | 2,6 km | 0.53 | 0.310 / 0.559 | 0.456 | -0.135 | 0.000 |
| pintura_menor | 2,6 km | 0.07 | 0.373 / 0.341 | 0.587 | -0.004 | 0.260 |
| objeto_propio | 2,6 km | 0.34 | 0.389 / 0.509 | 0.550 | -0.041 | 0.035 |
| pintura_mejor | 0 | 0.78 | 0.313 / 0.580 | 0.386 | -0.205 | 0.000 |
| pintura_menor | 0 | 0.20 | 0.314 / 0.464 | 0.568 | -0.023 | 0.002 |
| objeto_propio | 0 | 0.51 | 0.327 / 0.547 | 0.486 | -0.105 | 0.001 |

Lectura: el prompt por punto no produce parches a 10 m (la máscara de mayor puntaje es casi la ventana entera) y propagar etiquetas por esas máscaras empeora al píxel en los puntos cubiertos (0,31 frente a 0,56). Negativo con y sin búfer.

## Extensión: Felzenszwalb con bordes adaptativos (`13_felzenszwalb.py`, scale 100, sigma 0,5; min_size 8 px → 820.021 segmentos, mediana 0,21 ha; min_size 32 px → 159.027 segmentos, mediana 1,08 ha)

| Segmentador | espectral | AlphaEarth | unión (segmento) | píxel + contexto | borde / interior (unión) |
|---|---|---|---|---|---|
| Felzenszwalb 0,25 ha | -0.007 (p 0.655) | +0.014 (p 0.451) | +0.013 (p 0.389) | +0.006 (p 0.475) | 0.470 / 0.639 |
| Felzenszwalb 1 ha | -0.039 (p 0.053) | +0.003 (p 0.875) | +0.017 (p 0.271) | -0.004 (p 0.743) | 0.472 / 0.656 |

Comparar con SLIC a la misma escala (Tabla A): SLIC 0,25 ha unión +0,020, SLIC 1 ha unión −0,012. Lectura: con bordes adaptativos el segmento a 0,25 ha mejora al píxel en una centésima en todas las entradas salvo la espectral, por debajo de la DMD; a 1 ha la unión sube +0,017 (p 0,27) y el interior pasa de 0,626 a 0,656, mientras la espectral baja −0,039 (p 0,05). Con bordes adaptativos la escala de 1 ha deja de perder, pero ninguna diferencia supera la DMD ni sobrevive a una corrección por la familia. La conclusión del informe no cambia: el contexto aporta a lo sumo una o dos centésimas.

## Extensión: cambio 2021 → 2025 por píxel frente a por objeto (`15_cambio_objeto.py`; mismo RF entrenado con las 600 etiquetas WorldCover 2021, cuatro clases, aplicado a las pilas de 2021 y 2025; objetos = Felzenszwalb 1 ha)

| Unidad | área cambiada (ha) | fracción del dominio | componentes conexas | componentes ≤ 4 px | área de cambio en componentes ≤ 4 px |
|---|---|---|---|---|---|
| pixel | 30986 | 15.2 % | 115239 | 87281 | 4.5 % |
| objeto_felz_1ha | 26609 | 13.0 % | 7926 | 4115 | 0.2 % |

Acuerdo con un cambio de referencia débil en 591 puntos (WorldCover 2021 frente a la etiqueta propia de 2025 a cuatro clases; prevalencia de cambio 34 %):

| Unidad | exactitud | F1 cambio | F1 sin cambio | puntos predichos como cambio | acuerdo en el tipo de transición |
|---|---|---|---|---|---|
| pixel | 0.665 | 0.353 | 0.774 | 105 | 0.426 |
| objeto | 0.673 | 0.367 | 0.780 | 104 | 0.268 |

Transiciones principales (píxel / objeto, ha): agua → humedal 8.318 / 7.672; otro → humedal 6.392 / 5.734; humedal → manglar 6.008 / 4.317; humedal → otro 4.712 / 4.093; manglar → humedal 1.149 / 769.

Lectura: el objeto elimina el ruido de sal y pimienta del cambio (del 4,5 % al 0,2 % del área cambiada en manchas de 4 píxeles o menos, y de 115.239 a 7.926 componentes) y reduce el área cambiada del 15,2 al 13,0 %, sin cambiar el acuerdo con la referencia débil en los puntos (exactitud 0,67 en ambos). Es el uso del segmento que la literatura de objetos sí respalda: no clasificar mejor, sino limpiar el cambio. La referencia de cambio es débil (WorldCover 2021) y el F1 de cambio de 0,35 a 0,37 lo refleja; se reporta como lectura, no como exactitud. Dos observaciones de la Figura 8: la transición dominante agua → humedal (8.300 ha) coincide con la expansión de vegetación flotante de 2025, clase que el modelo de 2021 no tiene y que asigna a humedal; y los objetos de Felzenszwalb no cruzan las teselas de 1.024 px, lo que deja costuras rectas visibles en el cambio por objeto (misma limitación que SLIC).

## Extensión: segmentación por texto, cero ejemplos (`16_texto_langsam.py`: Grounding DINO 'tiny' de transformers para las cajas con la indicación "mangrove", SAM ViT-H para la máscara de cada caja; umbrales 0,24; 31 teselas de 1.024 px)

| Mapa | área marcada como manglar (ha) | F1 manglar vs resto (720 puntos) | precisión | exhaustividad | Jaccard corredor INVEMAR / GMW |
|---|---|---|---|---|---|
| texto "mangrove" | 188575 | 0.576 | 0.408 | 0.981 | 0.269 / 0.348 |
| píxel unión (OOF) | 81.712 | 0.796 | 0.775 | 0.817 | 0,461 / 0,538 |

Lectura: el texto marca el 92 % del dominio como manglar (57 cajas que cubren teselas casi enteras), de modo que la exhaustividad es 0,98 y la precisión 0,41. A 10 m y en falso color natural, Grounding DINO no distingue manglar de otra vegetación ni del agua turbia. Negativo. Nota: samgeo.text_sam (LangSAM) no carga con transformers 5.20 (BertModel sin get_extended_attention_mask); se reimplementó con los mismos componentes.

## Extensión: sensibilidad de DeepLabV3+ a las técnicas de entrenamiento (IDL cap. 5; `08_deeplab.py --epocas 30 --lr 1e-4 --pesos`)

| Configuración | macro-F1 OOF | pliegues | humedal | flotante | − píxel unión | p |
|---|---|---|---|---|---|---|
| por defecto: lr 1e-3, 15 épocas, sin pesos | 0,454 | 0,297 a 0,520 | 0,125 | 0,219 | −0,137 | < 0,001 |
| lr 1e-4, 30 épocas con parada temprana, pesos de clase inversos a la frecuencia | 0.518 | 0.362 a 0.562 | 0.136 | 0.571 | -0.073 | 0.0005 |

Lectura: la tasa baja, las 30 épocas con parada temprana y los pesos de clase suben la macro-F1 de 0,454 a 0,518 (+0,064) y recuperan la vegetación flotante (0,22 → 0,57) y otro (0,39 → 0,48), pero no el humedal (0,14), y la red sigue 0,073 por debajo del píxel (p < 0,001). El negativo de DeepLab con etiquetas débiles se atenúa con las técnicas del capítulo 5 de IDL y no desaparece.

## Extensión: modelo temporal sobre la serie mensual completa de 2025 (`17_serie_temporal.py`; 12 meses x 9 canales + máscara, misma CV congelada)

| Brazo | macro-F1 OOF | pliegues | − píxel espectral (0,580) | p | − píxel unión (0,591) | p |
|---|---|---|---|---|---|---|
| Random Forest sobre los 120 valores de la serie | 0.570 | 0.500 a 0.577 | -0.010 | 0.544 | -0.021 | 0.323 |
| CNN 1D (32 y 64 filtros, entropía ponderada, 150 épocas) | 0.552 | 0.438 a 0.606 | -0.028 | 0.318 | -0.039 | 0.069 |

Lectura: la serie mensual entera no supera a los 30 resúmenes estacionales y fenológicos que ya usa el píxel (−0,010 con el mismo RF, −0,028 con la CNN). La información temporal útil ya está capturada por las medianas de estación y los descriptores de amplitud; el modelo temporal no añade nada con 720 puntos.

## Extensión: temperatura de superficie de ECOSTRESS como entrada (`18_ecostress_entrada.py`; medianas mensuales 2025 nocturnas y diurnas a 70 m, 24 + 13 variables; todos los puntos con al menos un mes nocturno, mediana 8 meses nocturnos y 4 diurnos)

| Brazo | variables | macro-F1 OOF | pliegues | − mismo brazo sin LST | p | McNemar |
|---|---|---|---|---|---|---|
| LST sola | 37 | 0.245 | 0.164 a 0.331 | | | |
| espectral + LST | 67 | 0.550 | 0.474 a 0.561 | -0.030 | 0.038 | 0.457 |
| unión + LST | 131 | 0.588 | 0.440 a 0.598 | -0.003 | 0.837 | 0.860 |

Lectura: a 70 m y con 8 meses nocturnos por punto, la temperatura de superficie separa poco por sí sola (0,25, por encima del azar de 0,17) y, añadida a las entradas ópticas, resta o no cambia. El dato térmico de ECOSTRESS no entra como variable de clasificación de coberturas; su lugar, si lo tiene, es como indicador de estado o de inundación en la serie temporal, no en el clasificador.

## Extensión: representaciones de Prithvi-EO 2.0 (300M, codificador congelado, ventana 224 px, cuatro compuestos trimestrales de 2025; `19_prithvi.py`)

| Brazo | variables | macro-F1 OOF | pliegues | − AlphaEarth (0,595) | p | − píxel unión (0,591) | p |
|---|---|---|---|---|---|---|---|
| token del parche central, media de 4 instantes | 1024 | 0.407 | 0.342 a 0.446 | -0.188 | 0.000 | -0.184 | 0.000 |
| media de todos los tokens de la ventana | 1024 | 0.440 | 0.324 a 0.448 | -0.155 | 0.001 | -0.151 | 0.000 |
| espectral (30) + parche central (1.024) | 1054 | 0.467 | 0.386 a 0.527 | -0.129 | 0.000 | -0.124 | 0.001 |

Lectura: usado como extractor congelado sobre Sentinel-2 del cubo, Prithvi-EO 2.0 queda 0,15 a 0,19 por debajo de AlphaEarth y por debajo de las variables espectrales solas (0,580); añadido a lo espectral baja a 0,467 porque el Random Forest reparte sus divisiones entre 1.054 variables y las 30 espectrales pierden peso. Desviaciones declaradas: B8 en lugar de B05 (NIR estrecho de HLS), sin codificación de coordenadas ni fechas, cuatro instantes trimestrales en vez de las fechas HLS del preentrenamiento, y sin ajuste fino. Con esas condiciones, el modelo fundacional preentrenado en HLS no transfiere al cubo de Sentinel-2 de la CGSM; un ajuste fino con etiquetas densas queda como línea de la tesis, no del informe.

## Extensión: contexto multiescala como rasgo (`21_contexto_multiescala.py`; el píxel conserva sus 94 variables y recibe las medias de sus objetos a varias escalas)

| Brazo | variables | macro-F1 OOF | pliegues | − píxel unión | p | borde | interior | humedal |
|---|---|---|---|---|---|---|---|---|
| píxel + SLIC 0,25 + 1 + 4 ha | 376 | 0.604 | 0.477 a 0.655 | +0.013 | 0.396 | 0.470 | 0.636 | 0.26 |
| píxel + Felzenszwalb 0,25 + 1 ha + SLIC 4 ha | 376 | 0.610 | 0.466 a 0.648 | +0.019 | 0.229 | 0.475 | 0.645 | 0.25 |
| píxel + SLIC 0,25 + 1 ha | 282 | 0.603 | 0.456 a 0.624 | +0.012 | 0.401 | 0.452 | 0.648 | 0.26 |
| píxel + Felzenszwalb 0,25 + 1 ha | 282 | 0.617 | 0.439 a 0.649 | +0.026 | 0.083 | 0.475 | 0.658 | 0.29 |

Referencia píxel unión: 0,591, borde 0,453, interior 0,626, humedal 0,22. Lectura: la jerarquía de dos escalas con bordes adaptativos (Felzenszwalb 0,25 y 1 ha) es el mejor brazo de todo el informe, +0,026 (p 0,08), con el interior en 0,658 y el humedal en 0,29. Sigue por debajo del umbral de significación y apenas por encima de la DMD (0,016): el contexto multiescala aporta dos o tres centésimas, no más.

## Extensión: segmentar sobre el embedding de AlphaEarth (`23_felz_embedding.py`: PCA de 3 componentes de AlphaEarth 2025 exportada a 8 bits, Felzenszwalb min_size 8, mediana de objeto cercana a 0,25 ha)

| Entrada | segmento macro-F1 | − píxel misma entrada | p | borde / interior (unión) |
|---|---|---|---|---|
| espectral | 0.561 | -0.018 | 0.260 |  |
| AlphaEarth | 0.576 | -0.020 | 0.118 |  |
| unión | 0.586 | -0.005 | 0.654 | 0.465 / 0.619 |
| píxel + contexto | 0.582 | -0.009 | 0.383 |  |

Lectura: los objetos trazados sobre el embedding no mejoran a los trazados sobre el RGB (Felzenszwalb RGB 0,25 ha: unión 0,604, +0,013); con la unión el segmento queda en 0,586 (−0,005). Dónde se traza el borde, a 0,25 ha, no cambia el resultado: la escala manda, no la fuente de los bordes.

## Extensión: suavizado de probabilidades dentro del objeto (`22_suavizado_prob.py`; RF de Earth Engine por pliegue con salida de probabilidades, media de las seis probabilidades dentro del objeto del punto, decisión por el máximo)

| Objeto | macro-F1 OOF | pliegues | − píxel unión | p | borde | interior | humedal |
|---|---|---|---|---|---|---|---|
| felz_025ha | 0.568 | 0.447 a 0.580 | -0.023 | 0.099 | 0.447 | 0.597 | 0.15 |
| slic_025ha | 0.562 | 0.446 a 0.582 | -0.029 | 0.090 | 0.460 | 0.591 | 0.18 |

Lectura: promediar probabilidades en el objeto de 0,25 ha no mejora al voto duro (SLIC 0,25 ha voto +0,001) ni al píxel; con Felzenszwalb resta 0,023. Nota: la referencia píxel aquí es la OOF de sklearn y las probabilidades vienen del RF de Earth Engine, que coincide con sklearn en el 95,6 % de los puntos.

## Segunda ronda de muestra: 100 puntos dirigidos (2026-10-19)

| Estrato (ciego para la intérprete) | n | manglar intacto | manglar degradado | humedal | otro | flotante | agua |
|---|---|---|---|---|---|---|---|
| mapa dice manglar a más de 1 km de INVEMAR y GMW | 60 | 17 | 9 | 20 | 10 | 4 | 0 |
| mapa dice humedal herbáceo | 40 | 4 | 7 | 20 | 4 | 2 | 3 |

Lectura: el 43 % del "manglar" del mapa fuera del corredor es manglar real que ninguna referencia cartografía; el 57 % restante es humedal, otro o flotante. La sobreestimación del sur existe, pero es la mitad de lo que el corredor sugería. La clase humedal del mapa acierta la mitad de las veces y confunde sobre todo con manglar degradado (7 de 40), coherente con la confusión medida en los 720.

## Segunda ronda declarada: cadena completa sobre 820 puntos (720 + 100 dirigidos; carpeta informe2_ampliada, 2026-10-19)

Misma CV congelada (5 pliegues por bloques de 12 km, búfer 2,6 km; pliegues 143/174/162/166/174), mismo RF y mismas 94 variables. Los 100 puntos nuevos no tienen marca de borde (los 208 de borde son los mismos de la primera ronda). Clases: agua 215, intacto 172, flotante 135, degradado 127, humedal 113, otro 58.

| Brazo | macro-F1 720 | exactitud 720 | macro-F1 820 | exactitud 820 |
|---|---|---|---|---|
| píxel espectral | 0,580 | 0,649 | 0,555 | 0,609 |
| píxel AlphaEarth | 0,595 | 0,667 | 0,582 | 0,628 |
| píxel unión (base) | 0,591 | 0,662 | 0,587 | 0,633 |
| SLIC 0,25 ha, segmento unión | 0,611 | 0,660 | 0,592 | 0,626 |
| SLIC 0,25 ha, píxel + contexto | 0,604 | 0,668 | 0,613 (+0,026, p 0,055) | 0,651 |
| Felz 0,25 ha, segmento unión | 0,604 | 0,671 | 0,597 (+0,010, p 0,47) | 0,643 |
| Felz 1 ha, segmento unión | 0,608 | 0,671 | 0,599 (+0,012, p 0,45) | 0,646 |
| píxel + Felz 0,25 + 1 ha (multiescala) | 0,617 | 0,676 | 0,608 (+0,020, p 0,30) | no calculada |
| filtro de mayoría 5 x 5 | 0,605 | 0,667 | 0,603 (+0,016, p 0,14) | no calculada |
| SLIC 4 ha, segmento unión | 0,544 | 0,613 | 0,549 (−0,038, p 0,06) | 0,594 |
| SLIC 16 ha, segmento unión | 0,490 | 0,557 | 0,508 (−0,079, p 0,003) | 0,543 |
| SAM grueso, segmento unión | 0,372 | 0,438 | 0,378 | 0,434 |

F1 por clase con 820 (píxel unión / píxel + SLIC 0,25 / multiescala Felz): agua 0,79 / 0,78 / 0,80; humedal 0,35 / 0,41 / 0,36; degradado 0,52 / 0,57 / 0,56; intacto 0,76 / 0,77 / 0,77; otro 0,51 / 0,56 / 0,53; flotante 0,58 / 0,59 / 0,62.

Bordes con 820 (píxel unión 0,460 borde, 0,618 interior): píxel + Felz 0,25 + 1 ha 0,528 borde y 0,622 interior; píxel + SLIC 0,25 + 1 + 4 ha 0,492 y 0,632.

Voto por mayoría con 820: Felz 0,25 ha 0,597 (+0,010, p 0,26), SLIC 0,25 ha 0,587 (−0,001), Felz 1 ha 0,579, SLIC 4 ha 0,514, SLIC 16 ha 0,496, SAM grueso 0,417. Ningún contraste de la familia de 45 supera Holm, salvo las pérdidas de SLIC 4 y 16 ha con voto (p Holm < 0,001).

Delimitación con el mapa entrenado con 820 (corredor de 1 km): píxel Jaccard 0,470 INVEMAR y 0,545 GMW (720: 0,461 y 0,538); manglar fuera del corredor 13.251 ha (720: 14.191 ha); referencia recuperada 0,981 INVEMAR y 0,914 GMW. Felz 0,25 ha y SLIC 0,25 ha quedan a menos de 0,01 del píxel; SAM y SLIC de 16 ha pierden 0,06 a 0,11.

Los 100 puntos dirigidos vistos por el píxel OOF: 38 de 100 bien clasificados. Humedal real (40) se predice como degradado 17 veces y como humedal 18; manglar intacto real (21) se predice intacto 10 veces; otro real (14) se reparte entre intacto 6, humedal 4 y otro 2.

Lectura. (1) La exactitud global baja de 0,66 a 0,63 porque los 100 puntos nuevos se sortearon donde el mapa se equivoca, no porque el modelo empeore: el macro-F1 del píxel unión se mantiene (0,591 → 0,587). (2) Con 113 puntos de humedal en vez de 73, el F1 de humedal del píxel sube de 0,22 a 0,35: parte del problema de humedal era la muestra. (3) El aporte del contexto chico se sostiene en la segunda ronda y cambia de brazo: píxel + SLIC 0,25 ha es ahora el mejor (0,613, +0,026, p 0,055; humedal 0,41, otro 0,56) y píxel + Felz 0,25 + 1 ha queda en 0,608 (+0,020), con la mayor ganancia en borde (0,460 → 0,528). (4) El orden por tamaño de objeto se repite: 0,25 a 1 ha neutro o positivo, 4 ha en adelante negativo. (5) La delimitación casi no cambia: el mapa con 820 reduce 940 ha el manglar fuera del corredor, que la revisión a ciegas mostró que en un 43 % es manglar real. Ningún contraste positivo alcanza significancia con Holm en ninguna de las dos rondas; la ganancia de 2 a 3 puntos de macro-F1 está por encima de la DMD de 0,016 pero por debajo de lo que esta muestra puede declarar con 45 contrastes.

## Extensión: Sentinel-1 como entrada, por píxel y por objeto (informe2_ampliada/24_s1_entrada.py; 12 meses de 2025 de VV y VH en dB a 10 m; 14 variables por punto: medianas seca y húmeda de VV, VH y VH−VV, y mínimo, máximo, amplitud y desviación anual de VV y VH; las mismas 14 con la media mensual dentro del objeto de 0,25 ha; muestra de 820, misma CV)

| Brazo | n vars | macro-F1 820 | macro-F1 (720 de la ronda 1) | − píxel unión (p) | − píxel + SLIC 0,25 (p) | borde | interior | F1 humedal | F1 degradado |
|---|---|---|---|---|---|---|---|---|---|
| S1 solo | 14 | 0,429 | 0,432 | −0,159 (0,0005) | | 0,325 | 0,456 | 0,08 | 0,41 |
| píxel unión + S1 | 108 | 0,593 | 0,619 | +0,005 (0,27) | | 0,456 | 0,628 | 0,35 | 0,54 |
| píxel + contexto SLIC 0,25 (referencia, medias ópticas del objeto) | 188 | 0,602 | 0,622 | +0,015 | | 0,486 | 0,630 | 0,36 | 0,55 |
| píxel + contexto SLIC 0,25 + S1 píxel + S1 objeto | 216 | 0,607 | 0,632 | +0,019 (0,11) | +0,004 (0,42) | 0,498 | 0,635 | 0,37 | 0,54 |
| píxel + contexto Felz 0,25 + S1 píxel + S1 objeto | 216 | 0,590 | 0,608 | +0,002 (0,89) | −0,013 (0,27) | 0,468 | 0,617 | 0,32 | 0,54 |

Lectura. La banda C sola separa agua y manglar intacto pero no humedal (F1 0,08): la retrodispersión mensual a 10 m no distingue herbáceo inundado de leñoso abierto en esta ciénaga. Sumada a la óptica y a AlphaEarth no mueve nada: +0,005 por píxel y +0,004 sobre el mejor brazo con contexto, con humedal 0,36 → 0,37 y degradado 0,55 → 0,54. La hipótesis del doble rebote bajo dosel inundado no se sostiene con compuestos mensuales de 10 m; quedaría por probar con coherencia interferométrica o con banda L, fuera del alcance del informe. Con esto se cierra la familia de entradas: espectral, AlphaEarth, Prithvi, ECOSTRESS y S1 están medidas, y la única que aporta sobre espectral + AlphaEarth es el contexto de objeto chico.
