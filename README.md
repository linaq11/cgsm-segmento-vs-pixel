# Segmento frente a píxel en la clasificación del manglar de la Ciénaga Grande de Santa Marta: qué aporta el contexto espacial a 10 m

Código, resultados tabulados y figuras de un estudio desarrollado en la Maestría en Geomática de la Universidad Nacional de Colombia (2026).

**Autora:** Lina María Quintero Fonseca

El estudio mide qué aporta la segmentación de imágenes a la clasificación de coberturas del manglar de la Ciénaga Grande de Santa Marta (CGSM) frente a la decisión por píxel, con los mismos puntos de referencia de 2025, el mismo Random Forest y la misma validación por bloques espaciales. Compara el Segment Anything Model (SAM) en dos configuraciones, SLIC en cinco escalas (de 139 a 0,25 ha) y Felzenszwalb a 0,25 y 1 ha, en tres entradas (30 variables espectrales de Sentinel-2, 64 dimensiones de AlphaEarth y su unión), con una familia de contrastes declarada de antemano y corregida por Holm. Añade la delimitación del manglar frente a INVEMAR 1:25.000 y Global Mangrove Watch 2020, exploratorios con DeepLabV3+, k vecinos y propagación de etiquetas sobre AlphaEarth, una extensión con trece pruebas (filtro de mayoría, bordes adaptativos, SAM con indicaciones y por texto, cambio por objeto, serie mensual, ECOSTRESS, Prithvi-EO 2.0, contexto multiescala, suavizado de probabilidades, objetos sobre el embedding y Sentinel-1) y una segunda ronda de muestra con 100 puntos dirigidos etiquetados a ciegas, sobre la que se repite la cadena completa con 820 puntos.

El informe completo está en `informe/Informe2.md` (y en PDF en la misma carpeta), el plan declarado antes de correr la familia de contrastes en `informe/PLAN_informe2.md`, y las tablas de resultados con su lectura en `resultados/resultados_informe2.md`.

## Contenido del repositorio

| Carpeta | Contenido |
|---|---|
| `scripts/` | 26 scripts de Python de la primera ronda (720 puntos), numerados en el orden del flujo. Cada uno documenta en su cabecera su propósito, los archivos de entrada, los productos que genera y la forma de ejecutarlo. |
| `scripts/segunda_ronda/` | Las copias de los scripts 01, 03, 05, 06, 12 y 21 ajustadas a la muestra de 820 puntos, más `24_s1_entrada.py` (Sentinel-1 como entrada) y `25_curva_humedal.py` (curva de aprendizaje de la clase humedal). |
| `scripts/muestra_2025/` | Tres scripts de la muestra de referencia que los anteriores importan o que generan los puntos dirigidos: el módulo de validación cruzada y pruebas (`40_ablacion_entradas.py`) y el sorteo de las rondas dirigidas 2 y 3 con su herramienta de etiquetado a ciegas para Earth Engine. |
| `resultados/` | Tablas CSV y archivos de texto generados por los scripts: resúmenes por brazo, contrastes con p de permutación y de McNemar, bordes e interior, F1 por clase, delimitación, transferencia temporal, cambio por objeto y calibración de Felzenszwalb. La subcarpeta `segunda_ronda/` contiene las mismas tablas para los 820 puntos. |
| `figuras/` | Las nueve figuras del informe en PNG. |
| `informe/` | Informe en Markdown y PDF, y plan declarado. |
| `DOCUMENTACION_scripts.md` | Cabeceras y comentarios de todos los scripts, reunidos por `generar_documentacion.py`. |

No se incluyen los archivos por punto de la muestra de referencia de 2025 (coordenadas, etiquetas, variables extraídas, predicciones fuera de pliegue por punto, agregados por segmento), ni los rásteres de entrada y salida (`datos/`: compuestos de Sentinel-2, mapas de segmentos de SAM, SLIC y Felzenszwalb, mapas por píxel y por pliegue, compuestos trimestrales para Prithvi, PCA de AlphaEarth), ni los pesos de SAM ViT-H, Prithvi-EO 2.0 y Grounding DINO. Todos se regeneran o se descargan con los scripts.

## Flujo de trabajo

| Etapa | Scripts principales | Salidas principales |
|---|---|---|
| 1. Compuesto y variables por punto | `00_compuesto_seco_2025`, `01_variables_2025` | `datos/compuesto_seco_2025_rgb.tif`; 94 variables por punto; línea base por píxel (`pixel_2025_*.csv`) |
| 2. Segmentación y agregación | `02_segmentar` (SAM grueso y fino, SLIC en cinco escalas), `13_felzenszwalb`, `23_felz_embedding`, `03_clasificar_segmentos` | `datos/segmentos_*.tif`; medias y desviaciones por segmento en Earth Engine; brazos por segmento (`segmento_2025_*_<seg>.csv`) |
| 3. Familia de contrastes, mapas, voto y delimitación | `05_pruebas_holm`, `06_mapas`, `04_transferencia` | Tabla de 35 contrastes con Holm; mapas por pliegue; voto por mayoría (`voto_2025_*.csv`); delimitación contra INVEMAR y GMW (`delimitacion_2025.csv`); transferencia 2021 a 2025 |
| 4. Exploratorios | `08_deeplab`, `09_deeplab_corregido`, `10_propagacion_alphaearth`, `07_tessera_2025` | DeepLabV3+ con etiquetas débiles; k vecinos y propagación sobre AlphaEarth; cobertura de TESSERA (no disponible) |
| 5. Extensión posterior al cierre | `12_filtro_mayoria`, `14_sam_puntos`, `15_cambio_objeto`, `16_texto_langsam`, `17_serie_temporal`, `18_ecostress_entrada`, `19a_compuestos_trimestrales`, `19_prithvi`, `21_contexto_multiescala`, `22_suavizado_prob` | Tabla 7 del informe (`filtro5_*`, `sam_puntos_*`, `cambio_2025_*`, `texto_2025_*`, `serie_2025_*`, `ecostress_2025_*`, `prithvi_2025_*`, `multiescala_2025_*`, `suavizado_2025_*`) |
| 6. Segunda ronda de muestra | `muestra_2025/50_puntos_dirigidos_2026-10`, `muestra_2025/51_puntos_humedal_2026-10`, `segunda_ronda/*` | 100 puntos dirigidos y herramienta de etiquetado; tablas de los 820 puntos; Sentinel-1 (`s1_2025_*`); curva de aprendizaje (`curva_humedal_820.csv`, `fusion_humedal_degradado_820.csv`) |
| 7. Figuras e informe | `11_figuras`, `26_fig9_segunda_ronda`, `informe_a_word` | `figuras/fig1` a `fig9`; `Informe2.docx` |

## Datos externos

### Cubo de datos de la tesis en Earth Engine

Las variables espectrales se leen de un cubo mensual de Sentinel-2 (seis bandas, 10 m, 2025) y de Sentinel-1 (VV y VH en dB, 10 m, 2015 a 2025) publicado como activos privados del proyecto de Earth Engine de la tesis (`projects/basic-buttress-338101/assets/cgsm_datacube_v1/`). Los scripts que los usan requieren acceso a ese proyecto o la sustitución de las rutas por un cubo equivalente construido desde `COPERNICUS/S2_SR_HARMONIZED` y `COPERNICUS/S1_GRD`.

### Google Earth Engine (catálogo público)

- AlphaEarth: `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL`, 2025.
- ESA WorldCover 2021 (`ESA/WorldCover/v200`) para las etiquetas débiles de la transferencia temporal.
- ECOSTRESS LST (`NASA/ECOSTRESS/L2T_LSTE/V2`) para la extensión de temperatura de superficie.

### Referencias cartográficas del manglar

- INVEMAR, cartografía del manglar de la CGSM a escala 1:25.000.
- Global Mangrove Watch v3, 2020 (CC BY 4.0).

### Modelos preentrenados

- Segment Anything Model ViT-H (Meta).
- Prithvi-EO 2.0, 300M (IBM y NASA): `prithvi_mae.py`, `config.json` y `Prithvi_EO_V2_300M.pt` del repositorio de Hugging Face `ibm-nasa-geospatial/Prithvi-EO-2.0-300M`, colocados en `datos/prithvi/`.
- Grounding DINO tiny (IDEA Research), por `transformers`.
- DeepLabV3+ con ResNet-34 de `segmentation-models-pytorch`, siguiendo la plantilla de `geoai`.

### Muestra de referencia de 2025

Los 720 puntos de referencia de 2025, sus 100 puntos dirigidos de la segunda ronda, su esquema de validación cruzada por bloques y su reserva de validación son un producto propio de la tesis en elaboración y no se distribuyen con el informe. Los scripts los leen de `AVANCE TESIS/MUESTRA_2025/` (`etiquetas_2025.csv`, `pliegues_cv.csv`, `etiquetas_2025_ampliada.csv`, `pliegues_cv_ampliada.csv`, `reserva_validacion.geojson`), con las columnas `id, lon, lat, clase_final, borde_final` y `id, bloque12, pliegue`.

## Ejecución

Se recomienda Python 3.12 o superior. Las dependencias se instalan con:

```bash
pip install -r requirements.txt
```

Los scripts se ejecutan desde la carpeta `scripts/` en el orden de las etapas. Las etapas 3 a 7 trabajan sobre los CSV y los rásteres de las etapas 1 y 2, de modo que los resultados tabulados del repositorio permiten reconstruir las tablas y figuras del informe sin volver a segmentar. SAM ViT-H sobre el dominio completo tarda cerca de 17 minutos en la configuración gruesa y 130 en la fina con una GPU de 8 GB; DeepLabV3+, Prithvi y Grounding DINO también requieren GPU.

### Consideraciones locales

En Windows, una instalación paralela de PostGIS puede dejar en `PROJ_DATA` una base de datos de PROJ incompatible con la de `rasterio`. Los scripts fijan de forma explícita la ruta de PROJ del entorno de Python antes de importar `rasterio`.

Los scripts localizan la muestra de referencia y el área de estudio con rutas relativas a la carpeta del curso, que deben cambiarse al ejecutar el flujo en otro equipo:

```text
../../AVANCE TESIS/MUESTRA_2025/
../../AVANCE TESIS/AOI/AOI_tesis_CGSM_v1.geojson
```

La extracción de variables por segmento se hace en Earth Engine y requiere `ee.Initialize(project=<proyecto>)` con un proyecto propio.

## Reproducibilidad

El repositorio contiene los scripts, el plan declarado antes de las pruebas, los resultados tabulados y las figuras necesarios para reconstruir los análisis del informe. Las semillas, los pliegues, el búfer y la familia de contrastes están fijados en los scripts. Los archivos de gran tamaño y los datos de repositorios externos no se duplican, sino que se recuperan de sus fuentes. La muestra de referencia de 2025 es la única entrada que no se publica.

## Cómo citar

Quintero Fonseca, L. M. (2026). *Segmento frente a píxel en la clasificación del manglar de la Ciénaga Grande de Santa Marta: qué aporta el contexto espacial a 10 m* [Informe 2, curso Percepción Remota Avanzada]. Universidad Nacional de Colombia. https://github.com/linaq11/cgsm-segmento-vs-pixel

## Licencia

El código se distribuye bajo licencia MIT (véase `LICENSE`). Los datos y productos de terceros conservan las condiciones de uso de sus fuentes:

- Copernicus Sentinel-1 y Sentinel-2: ESA.
- AlphaEarth Satellite Embedding: Google, CC BY 4.0.
- ESA WorldCover: CC BY 4.0.
- Global Mangrove Watch: CC BY 4.0.
- ECOSTRESS: NASA.
- INVEMAR: según las condiciones de su portal de datos.
- Segment Anything Model: Apache 2.0. Prithvi-EO 2.0: Apache 2.0. Grounding DINO: Apache 2.0.
