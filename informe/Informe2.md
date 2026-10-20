Universidad Nacional de Colombia
Maestría en Geomática
Percepción Remota Avanzada, 2026-2
Informe 2
Lina María Quintero Fonseca
Segmento frente a píxel en la clasificación de coberturas asociadas al manglar de la Ciénaga Grande de Santa Marta: una comparación con validación espacial y escala de segmentación declarada

## Resumen

La segmentación de imágenes se propone con frecuencia como una forma de incorporar contexto espacial a la clasificación de coberturas, bajo el supuesto de que decidir por objeto reduce el ruido del píxel y mejora los bordes. Con el fin de medir ese aporte en el manglar de la Ciénaga Grande de Santa Marta (CGSM), se comparó la decisión por píxel con la decisión por segmento sobre los mismos 720 puntos de referencia de 2025, con seis clases y el mismo Random Forest. Las entradas fueron las tres del Informe 1 (30 variables espectrales de Sentinel-2, 64 dimensiones de AlphaEarth y su unión) y la validación, la misma por bloques espaciales de 12 km con búfer de 2,6 km. Los segmentos provinieron del Segment Anything Model en dos configuraciones fijadas de antemano y de SLIC en un barrido declarado de cinco escalas, de 139 a 0,25 ha. Para separar la unidad de decisión del contexto como rasgo, se añadieron dos brazos: el píxel con los estadísticos de su segmento y el voto por mayoría de las predicciones por píxel dentro del segmento. El contraste primario, SLIC de 1 ha frente a píxel con la entrada unión, dio una diferencia de macro-F1 de −0,012 (p = 0,48), por debajo de la diferencia mínima detectable de 0,016. En la familia de 35 contrastes con corrección de Holm, el segmento como unidad de decisión nunca superó al píxel y la pérdida creció con el tamaño del objeto, de −0,04 con SLIC de 4 ha a −0,27 con SAM grueso. El contexto como rasgo adicional fue neutro en todas las escalas. En los 208 puntos de borde el píxel bajó de 0,63 a 0,45 de macro-F1 y solo SLIC de 0,25 ha lo mejoró en ese grupo, de 0,45 a 0,51. La delimitación del manglar contra INVEMAR 1:25.000 y Global Mangrove Watch 2020 mostró que las dos referencias coinciden entre sí con un Jaccard de 0,51 y que el mapa por píxel alcanza 0,46 y 0,54 dentro de un corredor de 1 km, mientras que fuera del corredor el mapa añade 142 km² de manglar en zonas sin puntos de referencia. Tres exploratorios cerraron el informe: DeepLabV3+ con etiquetas débiles (0,45), un clasificador de k vecinos sobre AlphaEarth (0,58, igual al Random Forest de 94 variables) y la propagación semisupervisada de etiquetas sobre el mismo embedding (0,54). Una extensión posterior con un filtro de mayoría de 5 por 5, el segmentador de Felzenszwalb a 0,25 y 1 ha, SAM con los puntos como indicaciones, segmentación por texto, cambio por objeto, la serie mensual completa, la temperatura de superficie de ECOSTRESS y Prithvi-EO 2.0 como extractor congelado dejó el mismo veredicto para la clasificación, con mejoras de una o dos centésimas sin segmentador, y mostró que el objeto sí elimina el ruido de sal y pimienta del cambio 2021 a 2025 sin alterar el acuerdo con la referencia. Con esta muestra y a 10 m, el contexto espacial aporta en lo que al píxel le falta cuando el objeto es pequeño, de 0,25 ha: cinco centésimas en los bordes, doce en el humedal herbáceo (sin potencia para afirmarlo) y la limpieza del cambio temporal. No aporta en la exactitud global ni en la delimitación, y a partir de 4 ha quita más de lo que da. El segmento no reemplaza al píxel, lo complementa en esos tres puntos. Una segunda ronda de 100 puntos dirigidos, etiquetados a ciegas, mostró que el 43 % del manglar del mapa fuera del corredor es manglar que ninguna referencia cartografía, reprodujo el aporte del contexto de 0,25 ha sobre 820 puntos (0,613 frente a 0,587, p = 0,055) y situó la mejora del humedal herbáceo en el tamaño de la muestra: su F1 sube de 0,22 a 0,35 con 40 ejemplos más, a costa del manglar degradado, con el que comparte el espacio espectral a 10 m. Sentinel-1 como entrada no cambió ese cuadro.

## Introducción

El análisis de imágenes basado en objetos sustituyó al píxel como unidad de decisión en buena parte de la cartografía de coberturas de alta resolución. Blaschke (2010) resumió el argumento: los objetos agrupan píxeles homogéneos, permiten describir forma y contexto y producen mapas con menos ruido de sal y pimienta. Sin embargo, ese argumento se formuló para imágenes submétricas, en las que un píxel es mucho menor que cualquier objeto de interés. A 10 m, la resolución de Sentinel-2, un píxel del manglar de la CGSM ya contiene varias copas y la ventaja del objeto deja de ser evidente.

Los modelos fundacionales de segmentación cambiaron la forma de obtener los objetos. El Segment Anything Model (SAM) delimita regiones sin entrenamiento específico (Kirillov et al., 2023) y sus adaptaciones geoespaciales han mostrado resultados con cero o un ejemplo en imágenes de satélite (Osco et al., 2023; Wu y Osco, 2023). En paralelo, el Informe 1 de este curso mostró que la representación anual de AlphaEarth (Brown et al., 2025) iguala o supera a las variables espectrales multitemporales en la clasificación por píxel de estas mismas coberturas, con una ventaja que depende del tamaño de la muestra de entrenamiento. Queda entonces una pregunta de diseño que ninguno de los dos resultados responde: si, con la misma información y la misma validación, decidir por segmento aporta algo sobre decidir por píxel.

La pregunta tiene una dificultad metodológica conocida. Cuando se compara píxel con segmento cambiando a la vez el segmentador, los rasgos y la unidad de decisión, no se sabe a qué atribuir la diferencia. Por lo tanto, este informe fija todo lo demás y mueve una cosa a la vez: la escala del segmento entra como barrido declarado antes de correr, el contexto se evalúa por separado como rasgo y como unidad, y la comparación se somete a una prueba de permutación por bloques con corrección por comparaciones múltiples (Holm, 1979). Las reglas se escribieron antes de obtener el primer resultado, como en el Informe 1, y las desviaciones posteriores se declaran en el texto.

## Pregunta de investigación

¿Mejora la incorporación de contexto espacial mediante segmentación la clasificación y la delimitación de las coberturas asociadas al manglar de la CGSM frente a la decisión por píxel, con las mismas entradas, clases y particiones?

De esta pregunta se derivan tres cuestiones específicas. La primera es si el segmento como unidad de decisión supera al píxel, y a qué escala. La segunda es si el aporte, de existir, viene del contexto en sí o del segmentador, lo que se resuelve con dos segmentadores de naturaleza distinta y con brazos que separan el rasgo de la unidad. La tercera es si la mejora, de existir, se concentra en los puntos de borde, que es donde el argumento del objeto promete más.

## Área de estudio y datos

El dominio analítico es el mismo del Informe 1 y de la tesis: 2.042 km² del sistema lagunar y deltaico de la CGSM, en EPSG:9377 y malla de 10 m (Figura 1). Las variables se tomaron del cubo de datos de la CGSM, que organiza compuestos mensuales de Sentinel-2 L2A sobre esa malla. Para 2025 se construyeron las mismas 30 variables espectrales del Informe 1: medianas por banda de la estación seca (enero a marzo) y de la estación húmeda (septiembre a noviembre), con NDVI, NDWI y MNDWI por estación, y doce descriptores fenológicos de la serie mensual. La representación de AlphaEarth de 2025 aportó 64 dimensiones por punto (Brown et al., 2025). La unión de ambas suma 94 variables.

La imagen que entró a los segmentadores fue el compuesto de estación seca de 2025 del cubo, mediana de enero a marzo en las bandas B4, B3, B2 y B8, en la malla exacta del cubo de 7.150 por 6.022 píxeles. Se eligió la estación seca porque es la de menor nubosidad y la misma que usan los compuestos de clasificación del cubo.

La referencia es la muestra de entrenamiento de 2025 de la tesis: 720 puntos etiquetados por interpretación visual a ciegas de las predicciones de cualquier modelo, en seis clases: agua (212), manglar intacto (151), vegetación flotante (129), manglar degradado (111), humedal herbáceo (73) y otro (44). De ellos, 208 se marcaron como puntos de borde durante el etiquetado, es decir, a menos de 30 m de una transición de clases. Esta muestra reemplaza a las 600 etiquetas débiles de WorldCover 2021 del Informe 1 y permite por primera vez evaluar las dos condiciones del manglar. Como referencias cartográficas independientes para la delimitación se usaron la capa de manglar 1:25.000 del INVEMAR, con la que se construyó el dominio, y Global Mangrove Watch versión 3 de 2020 (Bunting et al., 2022).

![Figura 1. Dominio analítico sobre el compuesto seco de 2025. a) Los 720 puntos de referencia por clase. b) Los cinco pliegues de validación por bloques de 12 km y los 208 puntos de borde.](figuras/fig1_muestra.png)

## Metodología

### Diseño experimental

El diseño cruza dos factores. El primero es la unidad de decisión: píxel, segmento SAM en dos configuraciones y segmento SLIC en cinco escalas. El segundo es la entrada, repetida del Informe 1: espectral multitemporal (30 variables), AlphaEarth (64) y unión (94). Para cada combinación se entrenó el mismo Random Forest de 500 árboles con la misma semilla (Breiman, 2001), de modo que solo cambió la unidad sobre la que se calculan las variables y se decide la clase.

Con el fin de separar la unidad de decisión del contexto como rasgo, se añadieron dos brazos por segmentador. En el primero, llamado píxel más contexto, el clasificador decide por píxel pero recibe, además de las 94 variables del punto, las medias de las mismas variables dentro de su segmento. En el segundo, llamado voto por mayoría, el clasificador por píxel del pliegue correspondiente predice todo el mapa y cada segmento recibe la clase mayoritaria de sus píxeles. El primero mide el contexto como información. El segundo mide el segmento como unidad con el mismo modelo que el píxel.

La escala de segmentación se fijó como barrido antes de correr: SLIC con objetivo de 0,25, 1, 4 y 16 ha, más la escala de 139 ha de la prueba de tubería. SAM se corrió en una configuración gruesa, con teselas de 1.024 píxeles y 32 puntos por lado, y una fina, con teselas de 512 píxeles y 64 puntos por lado. Se declara una desviación: la configuración fina de SAM y la escala de 1 ha de SLIC se añadieron después de ver la prueba de tubería con SAM grueso y SLIC de 139 ha, que produjeron unidades de paisaje y no rodales. Para que la escala no quedara como parámetro elegido a mano después de ver resultados, se convirtió en barrido completo y el contraste primario se fijó en SLIC de 1 ha antes de correr el barrido.

### Muestra y particiones espaciales

La validación reutiliza el esquema congelado de la muestra de 2025: cinco pliegues formados por 24 bloques de 12 km, con exclusión de los puntos de entrenamiento situados a menos de 2,6 km de cualquier punto de prueba (Figura 1b). Roberts et al. (2017) muestran que sin esa separación la autocorrelación espacial infla la exactitud estimada. Todas las predicciones que se reportan son fuera de pliegue, y la macro-F1 se calcula sobre los 720 puntos reunidos y pliegue a pliegue. Una segunda ronda con 100 puntos dirigidos, descrita más adelante, repite la cadena sobre 820 puntos con los mismos bloques.

### Segmentación

SAM se ejecutó con el modelo ViT-H sobre el compuesto RGB de estación seca, estirado a 8 bits con el mismo rango fijo de las láminas del visor del cubo. El modo por lotes de samgeo entrega una máscara binaria y no objetos individuales (Wu y Osco, 2023), por lo que el teselado se implementó directamente sobre el generador automático de máscaras: teselas con solape de la mitad de su lado, máscaras llevadas a coordenadas globales y fusión por unión-búsqueda de las máscaras de teselas vecinas cuando el solape supera la mitad de la zona observada en común en los dos sentidos. Dentro de cada tesela la máscara más pequeña se pinta encima, para que los objetos pequeños no desaparezcan bajo los grandes. La configuración gruesa procesó 116 teselas, 6.483 máscaras y 3.727 fusiones en 17 minutos, con 1.808 objetos finales. La fina procesó 407 teselas, 26.945 máscaras y 16.029 fusiones en 130 minutos, con 6.962 objetos. Queda una costura residual entre teselas, declarada como limitación.

SLIC se ejecutó con la variante SLICO de scikit-image sobre el espacio Lab del mismo compuesto RGB, por teselas de 1.024 píxeles y sin máscara, con el número de segmentos ajustado a cada escala objetivo (Achanta et al., 2012). Los recuentos finales fueron 1.712, 13.554, 51.425, 204.223 y 821.468 segmentos para 139, 16, 4, 1 y 0,25 ha, en menos de un minuto por escala. La Figura 2 muestra que, sobre este compuesto, SLICO produce celdas casi regulares a todas las escalas, con bordes que apenas se adaptan a la imagen. Por lo tanto, los brazos SLIC miden el efecto de agregar la información en celdas de un área dada, más que el de delimitar objetos. SAM, en cambio, produce objetos que siguen los bordes de los parches de manglar, los cuerpos de agua y los claros.

![Figura 2. Ventana de 3 km por 3 km sobre el compuesto seco de 2025 en el complejo occidental, centrada en un punto de manglar degradado de borde. Bordes de los objetos de SAM grueso, SAM fino y SLIC a cuatro escalas. SLICO produce celdas casi regulares; SAM sigue los parches y los cuerpos de agua.](figuras/fig2_segmentaciones.png)

### Agregación y brazos por segmento

Para los brazos con el segmento como unidad, cada una de las 94 variables se agregó por segmento como media de los píxeles que lo componen. La agregación se hizo en Earth Engine sobre los polígonos de los segmentos que contienen puntos de referencia, de modo que cada punto recibió las variables y la clase de su segmento. Para la entrada unión se evaluó además una variante con la desviación estándar dentro del segmento, que se reporta pero no entra al contraste primario. Un punto sin segmento asignado conserva su decisión por píxel.

### Métricas y pruebas

La métrica principal es la macro-F1 fuera de pliegue sobre las seis clases, con su mínimo y máximo entre pliegues, y la F1 por clase. El contraste primario declarado es SLIC de 1 ha frente a píxel con la entrada unión. Cada contraste segmento menos píxel se somete a una prueba de permutación pareada por bloques: los 24 bloques se reasignan al azar entre los dos brazos 2.000 veces y el valor p es la fracción de permutaciones con una diferencia al menos tan grande como la observada. La prueba de McNemar se reporta como cifra de comparación (Foody, 2004). Sobre la familia completa de 35 contrastes se aplica la corrección de Holm (1979). La diferencia mínima detectable de la prueba principal, calculada en el protocolo de la muestra, es de 0,016 de macro-F1 con potencia 0,80, de modo que un resultado nulo significa una diferencia menor de unas 0,02.

Los puntos de borde y los interiores se analizan por separado como lectura descriptiva, sin prueba. Las clases manglar degradado y humedal herbáceo tienen potencia baja declarada en el protocolo de la muestra y se reportan sin concluir sobre ellas por separado.

### Delimitación

La delimitación se midió sobre mapas completos. El mapa por píxel de 2025 se produjo con el Random Forest de la entrada unión entrenado con los 720 puntos, y un mapa por pliegue con el modelo entrenado sin los puntos de ese pliegue, que sirve para el voto por mayoría. Para cada segmentador el mapa de voto se comparó, igual que el de píxel, contra las dos referencias de manglar mediante el índice de Jaccard y la distancia mediana entre bordes en los dos sentidos.

Se declara un cambio de regla posterior a los resultados. La primera corrida mostró que la capa del INVEMAR no cubre la orilla oriental ni el sur del dominio: 163 de los 262 puntos de referencia etiquetados como manglar caen fuera de sus polígonos y solo 2 de los 458 puntos de otras clases caen dentro. En consecuencia, el Jaccard sobre todo el dominio medía la cobertura parcial de la referencia y no la calidad del mapa. La regla añadida evalúa la coincidencia dentro de un corredor de 1 km alrededor de la unión de INVEMAR y GMW, el mismo margen con que la propuesta de tesis define el dominio, y reporta aparte el manglar del mapa fuera del corredor como estimación de sobreestimación. Se reportan los dos valores, dominio y corredor.

### Análisis secundario y exploratorios

Como análisis secundario se midió la transferencia temporal del clasificador por píxel: el modelo entrenado con las 600 etiquetas débiles de WorldCover 2021 del Informe 1, en cuatro clases, se evaluó sobre los 591 puntos de 2025 que no son vegetación flotante, con intacto y degradado agrupados en manglar.

Tres exploratorios, declarados como tales y sin compromiso en el plan, cerraron el informe. El primero entrenó DeepLabV3+ con codificador ResNet-34 (Chen et al., 2018) sobre teselas de 256 píxeles del compuesto seco con el mapa por píxel como etiqueta débil, mediante la plantilla de geoai (Wu, 2026). Para que la evaluación fuera fuera de pliegue se entrenaron cinco redes, una por pliegue, cada una con el mapa del Random Forest que no vio los puntos de ese pliegue, durante 15 épocas. Una segunda versión pintó, sobre esa etiqueta débil, el segmento SLIC de 0,25 ha de cada punto de entrenamiento con su clase real. El tercero preguntó si el embedding de AlphaEarth separa las clases sin Random Forest: un clasificador de 10 vecinos con los puntos de entrenamiento, y una propagación de etiquetas (Zhou et al., 2004) hacia 20.000 píxeles del dominio sin etiqueta más los puntos de prueba, con la misma partición y el mismo búfer.

### Extensión posterior al cierre

Después de cerrar la familia de contrastes se añadieron cinco pruebas, declaradas como extensión y no como parte del plan, para responder a las limitaciones identificadas en la discusión. La primera aplica un filtro de mayoría de 5 por 5 píxeles al mapa por píxel de cada pliegue, que equivale a la celda de 0,25 ha sin segmentador. La segunda reemplaza SLICO por el segmentador de Felzenszwalb y Huttenlocher (2004), cuyos bordes siguen el contraste local, con el tamaño mínimo calibrado en una tesela para que la mediana de los segmentos quede en 0,21 y 1,08 ha. La tercera usa los puntos de referencia de entrenamiento como indicaciones de SAM, en el modo que Osco et al. (2023) describen como un ejemplo: cada máscara hereda la clase de su punto y los puntos de prueba toman la clase pintada en su píxel, o la de su propia máscara por mayoría de los puntos de entrenamiento que contiene. La cuarta compara el cambio 2021 a 2025 por píxel y por objeto con un mismo clasificador, entrenado con las 600 etiquetas débiles de 2021 y aplicado a las pilas de los dos años, con los objetos de Felzenszwalb de 1 ha. La quinta segmenta por texto, sin ejemplos, con Grounding DINO (Liu et al., 2023) para las cajas de la indicación "mangrove" y SAM para las máscaras, que es la combinación que samgeo empaqueta como LangSAM. Todas conservan la partición, el búfer y las pruebas del plan. A estas cinco se sumaron cuatro pruebas más, pedidas tras leer los resultados. La sexta repite DeepLabV3+ con las técnicas de entrenamiento del capítulo 5 de IDL: tasa de aprendizaje de 10⁻⁴, 30 épocas con parada temprana y pesos de clase inversos a la frecuencia. La séptima entrega al clasificador la serie mensual completa de 2025 en lugar de sus resúmenes: 12 meses por 9 canales (seis bandas y tres índices) más una máscara de mes sin dato, con un Random Forest sobre los 120 valores y una red convolucional unidimensional de dos capas. La octava añade la temperatura de superficie de ECOSTRESS (Fisher et al., 2020) como entrada: medianas mensuales nocturnas y diurnas de 2025 a 70 m en cada punto, con la misma limpieza del ejercicio del curso, en tres brazos (sola, con lo espectral y con la unión). La novena usa Prithvi-EO 2.0 (Szwarcman et al., 2024), el modelo fundacional de 300 millones de parámetros preentrenado sobre HLS, como extractor congelado: ventanas de 224 píxeles con las seis bandas que el modelo espera y cuatro compuestos trimestrales de 2025 del cubo, de las que se toman el token del parche central y la media de todos los tokens, con tres desviaciones declaradas (B8 en lugar del NIR estrecho de HLS, sin codificación de coordenadas ni fechas, y sin ajuste fino). La prueba de SAM con indicaciones tiene una condición adicional que se declara: con ventanas de 512 píxeles el alcance de una máscara (2,56 km) es menor que el búfer (2,6 km), de modo que ninguna máscara de entrenamiento podía alcanzar un punto de prueba, y se corrió con ventanas de 1.024 píxeles y, como sensibilidad prevista en el protocolo, con búfer cero.

Tras esas nueve, cuatro pruebas más cerraron la familia de la segmentación y la de las entradas. La décima entrega al píxel, además de sus 94 variables, las medias de sus objetos a dos o tres escalas a la vez, Felzenszwalb de 0,25 y 1 ha o SLIC de 0,25, 1 y 4 ha, para medir el contexto multiescala como rasgo. La undécima sustituye el voto por mayoría por el promedio de las seis probabilidades del Random Forest dentro del objeto de 0,25 ha, con decisión por el máximo. La duodécima traza los objetos de Felzenszwalb sobre las tres primeras componentes principales de AlphaEarth, que explican el 74 % de su varianza, en lugar del RGB, para separar el efecto de la fuente de los bordes del efecto de la escala. La decimotercera añade Sentinel-1 como entrada, con 14 variables de retrodispersión de los 12 meses de 2025 del cubo: medianas de las épocas seca y húmeda de VV, VH y su diferencia, y mínimo, máximo, amplitud y desviación anual de cada polarización, por píxel y como media dentro del objeto de 0,25 ha. Esta última se midió sobre la muestra de la segunda ronda que se describe a continuación.

### Segunda ronda de muestra

El hallazgo de delimitación y la confusión entre humedal herbáceo y manglar degradado motivaron una segunda ronda de muestra, declarada como tal y separada de la familia principal. Se sortearon 100 puntos dirigidos con semilla fija, fuera de la reserva de validación y a 200 m o más de cualquier otro punto, en dos estratos: 60 donde el mapa por píxel de 2025 asigna manglar a más de 1 km de la unión de INVEMAR y GMW, y 40 donde asigna humedal herbáceo. La intérprete etiquetó los 100 puntos a ciegas, sin conocer el estrato ni la clase del mapa, con el criterio de la muestra de 2025 y una precisión operativa añadida: los troncos o la estructura leñosa visibles en la imagen de alta resolución se etiquetan como degradado, y la vegetación lisa y continua como humedal. Con los 820 puntos se repitió la cadena completa, píxel, nueve segmentadores, voto, delimitación, filtro de mayoría y contexto multiescala, con los mismos bloques y el mismo búfer, de modo que los 100 puntos entran en la validación cruzada y no solo en el entrenamiento. Sobre esa muestra se midió además una curva de aprendizaje de la clase humedal, quitando al azar puntos de esa clase hasta dejar 40, 73, 90 y 113, con cinco sorteos por tamaño, y la variante con humedal y degradado fusionados en una sola clase.

## Resultados

### Línea base por píxel

La Tabla 1 muestra la línea base por píxel de 2025. Las tres entradas quedaron entre 0,580 y 0,595 de macro-F1, y ninguno de los tres contrastes entre ellas fue distinto de cero: AlphaEarth menos espectral +0,015 (p = 0,46), unión menos espectral +0,011 (p = 0,47) y unión menos AlphaEarth −0,004 (p = 0,72). Con referencia propia y unos 500 puntos de entrenamiento por pliegue, la ventaja de AlphaEarth del Informe 1, de +0,038 con 270 puntos, desapareció. Este resultado coincide con la lectura de eficiencia de etiquetas que cerró ese informe. Por clase, el píxel separó bien agua y manglar intacto (F1 de 0,80 y 0,79) y mal el humedal herbáceo (0,22 a 0,28).

Tabla 1. Línea base por píxel de 2025: macro-F1 fuera de pliegue por entrada (n = 720, seis clases, cinco pliegues de 12 km con búfer de 2,6 km).

| Entrada | Variables | Macro-F1 | Mínimo y máximo por pliegue | Exactitud |
|---|---|---|---|---|
| Espectral multitemporal | 30 | 0,580 | 0,459 a 0,598 | 0,649 |
| AlphaEarth 2025 | 64 | 0,595 | 0,528 a 0,617 | 0,667 |
| Unión | 94 | 0,591 | 0,439 a 0,601 | 0,662 |

### Segmento frente a píxel

El contraste primario, SLIC de 1 ha frente a píxel con la entrada unión, dio una diferencia de −0,012 (p = 0,48). La diferencia está por debajo de la mínima detectable, de modo que el resultado se lee como ausencia de diferencia mayor de unas 0,02. La Tabla 2 y la Figura 3 muestran la familia completa. En las tres entradas y en todas las escalas, el segmento como unidad de decisión fue igual o peor que el píxel, y la pérdida creció con el tamaño del objeto. SAM grueso perdió entre 0,22 y 0,27, SAM fino entre 0,12 y 0,17, SLIC de 139 ha entre 0,16 y 0,22 y SLIC de 16 ha entre 0,08 y 0,13, todos significativos tras Holm. SLIC de 4 ha perdió entre 0,04 y 0,11, con significación solo para la entrada espectral. SLIC de 1 ha y de 0,25 ha quedaron dentro del ruido, entre −0,08 y +0,02, sin ningún contraste significativo.

El contexto como rasgo fue neutro. El brazo píxel más contexto se movió entre −0,016 y +0,015 en los siete segmentadores, sin ninguna diferencia significativa. El voto por mayoría, que usa el mismo modelo por píxel y solo cambia la unidad, perdió entre 0,05 y 0,20 en todos los segmentadores salvo SLIC de 0,25 ha, donde fue idéntico al píxel (+0,001, p = 0,94). Puesto que el voto y el segmento como unidad pierden lo mismo a cada escala, la pérdida no viene de agregar las variables sino de decidir por un objeto que contiene más de una clase.

Tabla 2. Diferencia de macro-F1 fuera de pliegue entre cada brazo y el píxel con la misma entrada, con el valor p de la permutación por bloques. El asterisco marca los contrastes significativos tras la corrección de Holm sobre los 35.

| Segmentador | Espectral | AlphaEarth | Unión (segmento) | Píxel más contexto | Voto por mayoría |
|---|---|---|---|---|---|
| SAM grueso (1024/32) | −0,269 (p < 0,001)* | −0,242 (p < 0,001)* | −0,219 (p < 0,001)* | −0,014 (p = 0,24) | −0,166 (p < 0,001)* |
| SAM fino (512/64) | −0,172 (p < 0,001)* | −0,122 (p < 0,001)* | −0,130 (p < 0,001)* | +0,004 (p = 0,81) | −0,086 (p < 0,001)* |
| SLIC 139 ha | −0,217 (p < 0,001)* | −0,175 (p < 0,001)* | −0,163 (p = 0,001)* | −0,002 (p = 0,93) | −0,197 (p < 0,001)* |
| SLIC 16 ha | −0,130 (p < 0,001)* | −0,076 (p = 0,001)* | −0,101 (p < 0,001)* | −0,016 (p = 0,38) | −0,113 (p < 0,001)* |
| SLIC 4 ha | −0,114 (p = 0,001)* | −0,037 (p = 0,048) | −0,047 (p = 0,006) | +0,003 (p = 0,87) | −0,080 (p < 0,001)* |
| SLIC 1 ha (primario) | −0,079 (p = 0,004) | −0,019 (p = 0,33) | −0,012 (p = 0,48) | +0,015 (p = 0,22) | −0,050 (p < 0,001)* |
| SLIC 0,25 ha | −0,036 (p = 0,11) | −0,010 (p = 0,50) | +0,020 (p = 0,28) | +0,013 (p = 0,32) | +0,001 (p = 0,94) |

![Figura 3. Diferencia de macro-F1 fuera de pliegue entre cada brazo y el píxel con la misma entrada, por segmentador. Los símbolos llenos son significativos tras Holm. La banda gris marca la diferencia mínima detectable de ±0,016.](figuras/fig3_diferencias.png)

Por clase, la pérdida de los segmentadores grandes se concentró en manglar intacto y en otro (Figura 7). Con SAM fino y la entrada unión, manglar intacto bajó de 0,79 a 0,52 y otro de 0,55 a 0,32, mientras que agua y vegetación flotante apenas cambiaron. SLIC de 0,25 ha con la entrada unión subió el humedal herbáceo de 0,22 a 0,34 y otro de 0,55 a 0,62, y bajó agua de 0,80 a 0,76 y vegetación flotante de 0,62 a 0,58. El humedal es la clase que peor separa el píxel y la que más gana con la celda de 0,25 ha, pero con 73 puntos y potencia baja declarada el movimiento se reporta como indicio y no como resultado.

### Bordes e interior

La Figura 4 y la Tabla 3 separan los 208 puntos de borde de los 512 interiores. Con la entrada unión, el píxel pasó de 0,626 en el interior a 0,453 en el borde, una caída de 0,17 que mide lo que cuesta la transición a 10 m. Ningún segmentador grande redujo esa caída: SAM grueso, SAM fino y SLIC de 139 y 16 ha estuvieron por debajo del píxel en los dos grupos. SLIC de 1 ha igualó al píxel en el interior (0,634 frente a 0,626) y quedó por debajo en el borde (0,413). Solo SLIC de 0,25 ha mejoró el borde, de 0,453 a 0,506, sin perder en el interior (0,638). El voto por mayoría a esa escala dio 0,481 en el borde. En consecuencia, el único aporte del contexto que aparece en esta muestra es el de una celda de 0,25 ha, equivalente a 25 píxeles, sobre los puntos de transición, y su magnitud, de unas cinco centésimas sobre 208 puntos, no alcanza a mover la macro-F1 total.

Tabla 3. Macro-F1 fuera de pliegue en puntos de borde (n = 208) e interiores (n = 512) con la entrada unión, para el píxel, el segmento como unidad y el voto por mayoría.

| Segmentador | Píxel, borde | Segmento, borde | Voto, borde | Píxel, interior | Segmento, interior | Voto, interior |
|---|---|---|---|---|---|---|
| SAM grueso | 0,453 | 0,259 | 0,286 | 0,626 | 0,402 | 0,475 |
| SAM fino | 0,453 | 0,375 | 0,395 | 0,626 | 0,482 | 0,543 |
| SLIC 139 ha | 0,453 | 0,349 | 0,287 | 0,626 | 0,451 | 0,429 |
| SLIC 16 ha | 0,453 | 0,358 | 0,343 | 0,626 | 0,516 | 0,514 |
| SLIC 4 ha | 0,453 | 0,419 | 0,358 | 0,626 | 0,579 | 0,555 |
| SLIC 1 ha | 0,453 | 0,413 | 0,405 | 0,626 | 0,634 | 0,582 |
| SLIC 0,25 ha | 0,453 | 0,506 | 0,481 | 0,626 | 0,638 | 0,622 |

![Figura 4. Macro-F1 fuera de pliegue en puntos de borde e interiores, con la entrada unión, para píxel, segmento como unidad y voto por mayoría.](figuras/fig4_bordes.png)

### Delimitación del manglar

El mapa por píxel de 2025 contiene 817 km² de manglar, intacto más degradado, frente a 319 km² de la capa del INVEMAR y 415 km² de GMW 2020 dentro del dominio. Las dos referencias coinciden entre sí en 248 km², un Jaccard de 0,51, de modo que ningún mapa puede esperar un acuerdo mucho mayor con cualquiera de ellas. Dentro del corredor de 1 km, el mapa por píxel alcanzó un Jaccard de 0,461 contra INVEMAR y de 0,538 contra GMW, con el 98 % de la referencia del INVEMAR recuperada y una mediana de desplazamiento de borde de 122 m hacia la referencia y de 32 m desde ella (Tabla 4, Figura 5). Fuera del corredor, el mapa añade 142 km² de manglar, concentrados en el bosque inundable del sur, entre los ríos Fundación y Aracataca, y en el extremo occidental.

Esa sobreestimación no es visible en la macro-F1 por puntos. De los 116 puntos de referencia de otras clases situados fuera del corredor, el mapa no llama manglar a ninguno. La muestra tiene 44 puntos de otro y 73 de humedal, y ninguno cae en las manchas del sur, por lo que la métrica por puntos no puede detectar un error en zonas no muestreadas. Por otra parte, 19 puntos etiquetados como manglar quedaron a más de 1 km de cualquier referencia. Una revisión visual posterior sobre el compuesto de 2025 y la imagen de alta resolución confirmó 17 de ellos y reclasificó 2 como otro. Las etiquetas originales se conservaron para todos los cálculos de este informe, porque la revisión se hizo después de ver los mapas, y las dos correcciones se registraron en una columna aparte de la muestra. Su efecto máximo, 2 de 720 puntos, está por debajo de la diferencia mínima detectable.

Ningún segmentador mejoró la delimitación del píxel. SAM fino tuvo la mediana de desplazamiento más baja hacia la referencia, 54 m, pero el Jaccard más bajo en el corredor, 0,394, porque sus objetos grandes incorporan agua y otras coberturas al manglar. SLIC de 0,25 ha y de 1 ha reprodujeron el píxel, con Jaccard de 0,453 y 0,441.

Tabla 4. Delimitación del manglar (intacto más degradado) dentro del corredor de 1 km alrededor de INVEMAR 1:25.000 y GMW 2020. Área del mapa fuera del corredor y Jaccard en todo el dominio como columnas de control.

| Mapa | Manglar en el corredor (km²) | Fuera del corredor (km²) | Jaccard INVEMAR, corredor | Jaccard GMW, corredor | Jaccard INVEMAR, dominio | INVEMAR recuperado | Mediana de borde hacia INVEMAR (m) |
|---|---|---|---|---|---|---|---|
| Píxel | 675 | 142 | 0,461 | 0,538 | 0,381 | 0,983 | 122 |
| SAM grueso | 735 | 192 | 0,398 | 0,456 | 0,317 | 0,940 | 60 |
| SAM fino | 745 | 175 | 0,394 | 0,481 | 0,320 | 0,943 | 54 |
| SLIC 139 ha | 721 | 133 | 0,356 | 0,437 | 0,303 | 0,855 | 232 |
| SLIC 16 ha | 711 | 138 | 0,396 | 0,496 | 0,334 | 0,916 | 132 |
| SLIC 4 ha | 699 | 138 | 0,422 | 0,525 | 0,354 | 0,947 | 94 |
| SLIC 1 ha | 689 | 141 | 0,441 | 0,537 | 0,367 | 0,966 | 90 |
| SLIC 0,25 ha | 682 | 141 | 0,453 | 0,538 | 0,376 | 0,978 | 103 |

![Figura 5. Manglar del mapa por píxel de 2025 frente a las dos referencias. Verde: dentro de INVEMAR o GMW. Naranja: fuera de las referencias pero dentro del corredor de 1 km. Rojo: fuera del corredor. Morado: referencia sin manglar en el mapa. La línea negra es el límite del corredor.](figuras/fig5_delimitacion.png)

### Transferencia temporal 2021 a 2025

El clasificador por píxel entrenado con las etiquetas débiles de 2021 y evaluado en los 591 puntos de 2025 perdió entre 0,03 y 0,05 de macro-F1 respecto de la validación cruzada de 2025 agrupada a cuatro clases (Tabla 5). La entrada espectral se degradó un 8,1 % y AlphaEarth y la unión un 4,6 %, dentro del rango de 9 a 14 % que Ball et al. (2026) reportan para transferencias de este tipo o por debajo de él. La pérdida se concentró en el manglar, cuya F1 bajó de 0,77 a 0,81 en la validación de 2025 a 0,60 a 0,62 en la transferencia, porque WorldCover 2021 etiqueta solo el dosel cerrado y la referencia de 2025 incluye el manglar degradado. Los 129 puntos de vegetación flotante, clase que no existe en 2021, se repartieron entre agua y humedal.

Tabla 5. Transferencia temporal por píxel: modelo entrenado con 600 etiquetas débiles de 2021 (cuatro clases) y evaluado en 591 puntos de 2025, frente a la validación cruzada de 2025 agrupada a cuatro clases.

| Entrada | Macro-F1 2021 a 2025 | Macro-F1 validación 2025 | Degradación | F1 manglar, transferido | F1 manglar, validación 2025 |
|---|---|---|---|---|---|
| Espectral multitemporal | 0,560 | 0,610 | −8,1 % | 0,596 | 0,772 |
| AlphaEarth | 0,598 | 0,627 | −4,6 % | 0,618 | 0,814 |
| Unión | 0,587 | 0,615 | −4,6 % | 0,598 | 0,809 |

### Exploratorios

La Tabla 6 y la Figura 6 reúnen los exploratorios junto con los brazos principales. DeepLabV3+ con etiquetas débiles alcanzó 0,454 de macro-F1 fuera de pliegue, 0,137 por debajo del píxel (p < 0,001). La red reprodujo las clases dominantes del mapa del que aprendió, con F1 de 0,73 en agua y en manglar intacto, y perdió las minoritarias, con 0,13 en humedal y 0,22 en vegetación flotante. Pintar el segmento de 0,25 ha de cada punto de entrenamiento con su clase real, unas 131 ha por pliegue, no cambió el resultado: 0,442. Con 371 teselas por pliegue y 15 épocas, cada red tardó unos cinco minutos en una GPU de portátil.

El clasificador de 10 vecinos sobre AlphaEarth dio 0,579, a −0,012 del Random Forest con 94 variables (p = 0,61). La propagación de etiquetas hacia 20.000 píxeles sin etiqueta bajó a 0,540 (−0,051, p = 0,08, McNemar p = 0,02), porque humedal y vegetación flotante se diluyeron hacia las clases dominantes.

Tabla 6. Exploratorios con la misma validación congelada. Diferencia frente al píxel con la entrada unión y valor p de la permutación por bloques.

| Brazo | Macro-F1 | Mínimo y máximo por pliegue | Diferencia frente al píxel | p |
|---|---|---|---|---|
| DeepLabV3+ con etiquetas débiles | 0,454 | 0,297 a 0,520 | −0,137 | < 0,001 |
| DeepLabV3+ con etiquetas débiles y parches de los puntos | 0,442 | 0,294 a 0,524 | −0,149 | < 0,001 |
| k vecinos sobre AlphaEarth, solo puntos | 0,579 | 0,441 a 0,652 | −0,012 | 0,61 |
| Propagación sobre AlphaEarth con 20.000 píxeles | 0,540 | 0,455 a 0,597 | −0,051 | 0,08 |

![Figura 6. Macro-F1 fuera de pliegue de los brazos principales y exploratorios, con el rango entre pliegues. La línea punteada es el píxel con la entrada unión.](figuras/fig6_exploratorios.png)

![Figura 7. F1 por clase fuera de pliegue del píxel, de los segmentos de SLIC de 0,25 y 1 ha, de SAM fino y de DeepLabV3+ con etiquetas débiles, todos con la entrada unión o su equivalente.](figuras/fig7_clases.png)

### Extensión: filtro, bordes adaptativos, indicaciones, cambio por objeto y texto

La Tabla 7 reúne las cinco pruebas. El filtro de mayoría de 5 por 5 subió la macro-F1 de 0,591 a 0,605 (+0,014, p = 0,24). El contraste pareado exacto contra el mapa por pliegue sin filtrar dio también +0,014 (p = 0,10), con mejoras de 0,02 en el borde y 0,01 en el interior, sin cambiar la delimitación. Felzenszwalb a 0,25 ha dio +0,013 con la entrada unión y +0,014 con AlphaEarth, y a 1 ha +0,017 con la unión, con el interior en 0,656. Ninguna de estas diferencias supera la mínima detectable. Con bordes adaptativos la escala de 1 ha deja de perder, de modo que la pérdida de SLIC a esa escala se debía a las celdas regulares y no al tamaño, pero el techo del aporte sigue en una o dos centésimas.

SAM con los puntos como indicaciones fue negativo en sus tres variantes. La máscara de mayor puntaje para un punto cubre casi la ventana entera, con una mediana de 4.659 ha, y la más pequeña 100 ha. Pintar las máscaras de entrenamiento cubrió el 53 % de los puntos de prueba y en ellos la macro-F1 fue de 0,31 frente a 0,56 del píxel. Tomar la clase mayoritaria dentro de la máscara del propio punto de prueba dio −0,041 (p = 0,035). Con búfer cero los tres resultados empeoraron. La segmentación por texto marcó el 92 % del dominio como manglar, con exhaustividad 0,98 y precisión 0,41, frente a una F1 de manglar de 0,80 del píxel fuera de pliegue. Con esto quedan probados los cuatro modos de uso de SAM a 10 m, automático grueso y fino, con indicaciones y por texto, y ninguno iguala al píxel.

El cambio por objeto es la única prueba en la que el segmento aporta algo distinto del píxel (Figura 8). Con el mismo clasificador en las dos fechas, el cambio por píxel ocupa el 15,2 % del dominio en 115.239 componentes conexas, con el 4,5 % del área cambiada en manchas de cuatro píxeles o menos. Por objeto ocupa el 13,0 % en 7.926 componentes, con el 0,2 % en manchas pequeñas. En los 591 puntos con un cambio de referencia débil, WorldCover 2021 frente a la etiqueta propia de 2025, la exactitud fue 0,665 por píxel y 0,673 por objeto, con F1 de cambio de 0,35 y 0,37. El objeto limpia el cambio sin mejorar ni empeorar el acuerdo. La transición dominante, de agua a humedal herbáceo en unas 8.300 ha, coincide con la vegetación flotante de 2025, clase que el modelo de 2021 no conoce.

Las cuatro pruebas posteriores no cambiaron el cuadro. Con las técnicas de entrenamiento del capítulo 5 de IDL, DeepLabV3+ subió de 0,454 a 0,518 y recuperó la vegetación flotante (0,22 a 0,57) y la clase otro, pero no el humedal, y quedó 0,073 por debajo del píxel (p < 0,001). La serie mensual completa no superó a sus resúmenes: 0,570 con el Random Forest sobre los 120 valores (−0,010 frente a la entrada espectral, p = 0,54) y 0,552 con la red unidimensional (−0,028, p = 0,32). La temperatura de superficie de ECOSTRESS, con una mediana de ocho meses nocturnos por punto, separó poco por sí sola (0,245), restó 0,030 a la entrada espectral (p = 0,038) y no cambió la unión (−0,003, p = 0,84). Prithvi-EO 2.0 como extractor congelado quedó entre 0,15 y 0,19 por debajo de AlphaEarth (0,407 con el parche central y 0,440 con el contexto, p ≤ 0,001) y, añadido a lo espectral, bajó el resultado a 0,467 porque el Random Forest reparte sus divisiones entre 1.054 variables. Con las desviaciones declaradas, el modelo preentrenado en HLS no transfiere al cubo de Sentinel-2 sin ajuste fino.

Las cuatro últimas pruebas acotan la segmentación por el lado del rasgo y de la entrada. El contexto multiescala es el mejor brazo de la primera ronda: el píxel con las medias de sus objetos de Felzenszwalb de 0,25 y 1 ha dio 0,617 (+0,026, p = 0,083), con el interior en 0,658 y el humedal en 0,29, apenas por encima de la mínima detectable y por debajo del umbral de significación. Promediar las probabilidades dentro del objeto de 0,25 ha, en lugar de votar, restó 0,023 con Felzenszwalb y 0,029 con SLIC, de modo que la información de las probabilidades no recupera lo que la decisión por objeto pierde. Trazar los objetos sobre el embedding de AlphaEarth en vez del RGB dio 0,586 con la unión (−0,005, p = 0,65), lo mismo que los objetos del RGB a la misma escala: la escala manda, no la fuente de los bordes. Sentinel-1, medido sobre los 820 puntos, no aportó. Sola dio 0,429 con un F1 de humedal de 0,08, sumada a la unión +0,005 (p = 0,27) y sumada al píxel con contexto de SLIC de 0,25 ha +0,004 (p = 0,42), con el humedal en 0,37 y el degradado en 0,54. La retrodispersión mensual en banda C a 10 m no separa el herbáceo inundado del leñoso abierto en este sistema. Con esa prueba queda medida la familia de entradas, espectral, AlphaEarth, Prithvi, ECOSTRESS y Sentinel-1, y la única que suma sobre la unión es el contexto del objeto pequeño.

Tabla 7. Extensión posterior al cierre: macro-F1 fuera de pliegue y contraste frente al píxel con la entrada unión (permutación por bloques), o la métrica que corresponde a cada prueba.

| Prueba | Resultado | Frente al píxel | p |
|---|---|---|---|
| Filtro de mayoría 5 por 5 | 0,605 (borde 0,472, interior 0,635) | +0,014 | 0,24 |
| Felzenszwalb 0,25 ha, unión | 0,604 (borde 0,470, interior 0,639) | +0,013 | 0,39 |
| Felzenszwalb 1 ha, unión | 0,608 (borde 0,472, interior 0,656) | +0,017 | 0,27 |
| SAM con indicaciones, pintura de máscaras (ventana 1.024 px) | 0,456 (cobertura 53 %, en cubiertos 0,31 frente a 0,56) | −0,135 | < 0,001 |
| SAM con indicaciones, objeto propio | 0,550 (cobertura 34 %) | −0,041 | 0,035 |
| Texto "mangrove", cero ejemplos | F1 manglar 0,576 (precisión 0,41, exhaustividad 0,98) | píxel 0,796 | |
| Cambio por objeto 2021 a 2025 | 13,0 % del dominio, 7.926 componentes, 0,2 % en manchas de 4 píxeles o menos | píxel 15,2 %, 115.239, 4,5 % | |
| DeepLabV3+ con tasa 10⁻⁴, parada temprana y pesos de clase | 0,518 (flotante 0,57, humedal 0,14) | −0,073 | < 0,001 |
| Serie mensual completa, Random Forest sobre 120 valores | 0,570 | −0,010 frente a espectral | 0,54 |
| Serie mensual completa, red convolucional 1D | 0,552 | −0,028 frente a espectral | 0,32 |
| ECOSTRESS sola | 0,245 | | |
| Espectral + ECOSTRESS | 0,550 | −0,030 frente a espectral | 0,038 |
| Unión + ECOSTRESS | 0,588 | −0,003 | 0,84 |
| Prithvi-EO 2.0 congelado, parche central | 0,407 | −0,188 frente a AlphaEarth | < 0,001 |
| Prithvi-EO 2.0 congelado, contexto de la ventana | 0,440 | −0,155 frente a AlphaEarth | 0,001 |
| Espectral + Prithvi | 0,467 | −0,124 | 0,001 |
| Contexto multiescala, píxel + Felzenszwalb 0,25 y 1 ha | 0,617 (borde 0,475, interior 0,658, humedal 0,29) | +0,026 | 0,083 |
| Contexto multiescala, píxel + SLIC 0,25, 1 y 4 ha | 0,604 | +0,013 | 0,40 |
| Suavizado de probabilidades, Felzenszwalb 0,25 ha | 0,568 | −0,023 | 0,10 |
| Suavizado de probabilidades, SLIC 0,25 ha | 0,562 | −0,029 | 0,09 |
| Felzenszwalb 0,25 ha sobre el embedding de AlphaEarth, unión | 0,586 | −0,005 | 0,65 |
| Sentinel-1 sola (820 puntos) | 0,429 (humedal 0,08) | −0,159 frente a 0,587 | < 0,001 |
| Unión + Sentinel-1 (820 puntos) | 0,593 | +0,005 | 0,27 |
| Píxel + contexto SLIC 0,25 ha + Sentinel-1 por píxel y por objeto (820 puntos) | 0,607 (humedal 0,37) | +0,004 frente al mismo brazo sin Sentinel-1 | 0,42 |

![Figura 8. Cambio 2021 a 2025 en una ventana de 10 km por 10 km del complejo occidental, con el mismo clasificador en las dos fechas. a) 2021 y b) 2025 en cuatro clases. c) Cambio por píxel y d) por objeto de Felzenszwalb de 1 ha. Las aristas rectas en d) son las teselas de 1.024 píxeles que los objetos no cruzan.](figuras/fig8_cambio_objeto.png)

### Segunda ronda: puntos dirigidos y 820 puntos

La revisión a ciegas de los 100 puntos dirigidos cambió la lectura de la delimitación (Tabla 8). De los 60 puntos donde el mapa pone manglar a más de 1 km de toda referencia, 26 son manglar, 17 intacto y 9 degradado, 20 son humedal herbáceo, 10 otro y 4 vegetación flotante. Por lo tanto, el 43 % del manglar del mapa fuera del corredor es manglar que ninguna referencia cartografía, y el 57 % restante es sobreestimación. De los 40 puntos donde el mapa pone humedal, 20 lo son y 7 son degradado, la misma confusión medida en los 720. El clasificador por píxel, evaluado fuera de pliegue sobre los 820, acierta 38 de los 100 puntos nuevos: de los 40 humedales reales predice 18 como humedal y 17 como degradado.

Tabla 8. Etiquetas a ciegas de los 100 puntos dirigidos por estrato. El estrato y la clase del mapa no se mostraron durante el etiquetado.

| Estrato | n | intacto | degradado | humedal | otro | flotante | agua |
|---|---|---|---|---|---|---|---|
| Mapa: manglar a más de 1 km de INVEMAR y GMW | 60 | 17 | 9 | 20 | 10 | 4 | 0 |
| Mapa: humedal herbáceo | 40 | 4 | 7 | 20 | 4 | 2 | 3 |

Con los 820 puntos la familia se repite y el cuadro se sostiene (Tabla 9). La exactitud global del píxel baja de 0,662 a 0,633 porque los puntos nuevos se sortearon donde el mapa falla, pero la macro-F1 de la unión casi no se mueve, de 0,591 a 0,587. El aporte del contexto de objeto pequeño reaparece con otra muestra y cambia de brazo: el píxel con el contexto de SLIC de 0,25 ha es ahora el mejor, 0,613 (+0,026, p = 0,055), con el humedal en 0,41 y la clase otro en 0,56, y el píxel con los objetos de Felzenszwalb de 0,25 y 1 ha queda en 0,608 (+0,020), con la mayor ganancia en los bordes, de 0,460 a 0,528. Que el primer lugar alterne entre SLIC y Felzenszwalb de una ronda a otra indica que la diferencia entre ambos es ruido y que lo que importa es la escala. El orden por tamaño se repite: de 0,25 a 1 ha neutro o positivo, de 4 ha en adelante negativo, con SLIC de 16 ha en −0,079 (p = 0,003) y SAM grueso en 0,378. El voto por mayoría vuelve a no aportar, +0,010 con Felzenszwalb de 0,25 ha y −0,001 con SLIC. La delimitación con el mapa entrenado con 820 puntos cambia poco: Jaccard de 0,470 contra INVEMAR y 0,545 contra GMW, y 940 ha menos de manglar fuera del corredor, que la revisión mostró que en un 43 % es manglar. Ningún contraste positivo supera la corrección de Holm en ninguna de las dos rondas.

Tabla 9. Primera ronda (720 puntos) frente a segunda ronda (820 puntos): macro-F1 fuera de pliegue y exactitud de los brazos principales, con la misma validación por bloques. Entre paréntesis, diferencia frente al píxel unión de la misma ronda y p de permutación.

| Brazo | 720: macro-F1 | 720: exactitud | 820: macro-F1 | 820: exactitud |
|---|---|---|---|---|
| Píxel espectral | 0,580 | 0,649 | 0,555 | 0,609 |
| Píxel AlphaEarth | 0,595 | 0,667 | 0,582 | 0,628 |
| Píxel unión | 0,591 | 0,662 | 0,587 | 0,633 |
| SLIC 0,25 ha, segmento con la unión | 0,611 (+0,020, 0,28) | 0,660 | 0,592 (+0,004, 0,76) | 0,626 |
| SLIC 0,25 ha, píxel con contexto | 0,604 (+0,013) | 0,668 | 0,613 (+0,026, 0,055) | 0,651 |
| Felzenszwalb 0,25 ha, segmento con la unión | 0,604 (+0,013, 0,39) | 0,671 | 0,597 (+0,010, 0,47) | 0,643 |
| Felzenszwalb 1 ha, segmento con la unión | 0,608 (+0,017, 0,27) | 0,671 | 0,599 (+0,012, 0,45) | 0,646 |
| Píxel con contexto de Felzenszwalb 0,25 y 1 ha | 0,617 (+0,026, 0,083) | 0,676 | 0,608 (+0,020, 0,30) | |
| Filtro de mayoría 5 por 5 | 0,605 (+0,014, 0,24) | 0,667 | 0,603 (+0,016, 0,14) | |
| SLIC 4 ha, segmento con la unión | 0,544 (−0,047) | 0,613 | 0,549 (−0,038, 0,06) | 0,594 |
| SLIC 16 ha, segmento con la unión | 0,490 (−0,101) | 0,557 | 0,508 (−0,079, 0,003) | 0,543 |
| SAM grueso, segmento con la unión | 0,372 (−0,219) | 0,438 | 0,378 | 0,434 |

La curva de aprendizaje separa lo que es muestra de lo que es señal (Figura 9). Con 40 puntos de humedal el píxel no reconoce la clase, F1 de 0,03, con 73 llega a 0,20, con 90 a 0,27 y con 113 a 0,36, sin meseta. Cada 20 ejemplos suben el F1 de humedal unas siete centésimas y la macro-F1 menos de una. Pero el F1 de degradado baja al mismo ritmo, de 0,61 a 0,52, de modo que los ejemplos nuevos mueven la frontera entre las dos clases y no las separan. Es la misma evidencia que la confusión de los 720: a 10 m las dos clases comparten el espacio espectral y la distinción es estructural, visible solo en la imagen de alta resolución. Fusionadas en una sola clase, la macro-F1 de cinco clases es 0,659 y la exactitud 0,702.

![Figura 9. Segunda ronda. a) Curva de aprendizaje de la clase humedal herbáceo sobre los 820 puntos: F1 de humedal, de degradado y macro-F1 del píxel unión al quitar al azar puntos de humedal (media y desviación de cinco sorteos). b) Macro-F1 de los brazos principales en las dos rondas.](figuras/fig9_segunda_ronda.png)

## Discusión

El resultado principal se lee mejor como balance que como nulo. La pregunta no era si el segmento reemplaza al píxel sino si el contexto espacial aporta lo que al píxel le falta, y la respuesta tiene tres partes. Aporta en los bordes, en la clase minoritaria peor separada y en la limpieza del cambio temporal, siempre con objetos de 0,25 ha. No aporta en la exactitud global, donde a 1 ha la diferencia es menor de dos centésimas, ni en la delimitación. Y a cualquier escala mayor de 4 ha quita más de lo que da. La forma de la pérdida explica el mecanismo. El voto por mayoría, que no agrega variables y solo cambia la unidad, pierde lo mismo que el segmento como unidad a cada escala, y el contexto como rasgo adicional no cambia nada. Por lo tanto, el costo está en asignar una sola clase a un objeto que contiene varias, y la información del vecindario en sí no lo explica. En un manglar donde el dosel intacto, el degradado, el agua y la vegetación flotante se mezclan a decenas de metros, un objeto de 4 ha ya contiene esa mezcla, y uno de 95 ha, la mediana de SAM, contiene el paisaje entero.

Este resultado no contradice la literatura del análisis por objetos, sino que delimita su dominio. El argumento de Blaschke (2010) supone objetos mucho mayores que el píxel y mucho menores que la unidad temática. A 10 m, la primera condición se cumple apenas y la segunda falla para las coberturas de este sistema. Osco et al. (2023) advierten que SAM, entrenado con imágenes naturales, segmenta en imágenes de satélite por contraste y textura y no por significado temático, y eso es lo que la Figura 2 muestra: los objetos de SAM siguen los cuerpos de agua y los parches grandes, no la frontera entre manglar intacto y degradado.

La lectura de los bordes matiza el nulo. En los 208 puntos de transición, la celda de 0,25 ha mejora al píxel en cinco centésimas sin perder en el interior. Esa escala corresponde a una ventana de 5 por 5 píxeles, es decir, al tipo de suavizado local que un filtro de mayoría aplicaría al mapa. El aporte existe, es pequeño y no necesita un segmentador para obtenerse.

El hallazgo de delimitación tiene consecuencias más allá de este informe. Las dos referencias cartográficas disponibles coinciden entre sí en la mitad de su área, de modo que la pregunta "cuánto manglar hay" no tiene una respuesta de referencia a esta escala. El mapa por píxel recupera el 98 % de lo que el INVEMAR cartografió y añade 142 km² en zonas donde no hay puntos de muestra, y la macro-F1 por puntos no puede ver ese error. Para la tesis, esto fija dos tareas: reforzar la clase otro y los sectores del sur en el diseño de la muestra de validación, y estimar las áreas con una muestra probabilística y no con el conteo de píxeles del mapa, como recomiendan Olofsson et al. (2014).

Los exploratorios responden preguntas distintas y dan la misma lección. DeepLabV3+ no puede superar a un maestro de 0,59 cuando aprende de su mapa, y 720 parches limpios no cambian lo que una red aprende de 2.000 km² de etiqueta débil. El clasificador de vecinos sobre AlphaEarth iguala al Random Forest con 94 variables, lo que sitúa la información en el embedding y no en el clasificador, en línea con el Informe 1. La propagación a píxeles sin etiqueta pierde las clases minoritarias, que es el riesgo conocido del aprendizaje semisupervisado con clases desbalanceadas.

La extensión cierra dos de las preguntas que la familia principal dejaba abiertas. Con bordes adaptativos el segmento de 1 ha deja de perder, de modo que la pérdida de SLIC a esa escala era un artefacto de las celdas regulares, pero el aporte con bordes reales sigue en una o dos centésimas, igual que el del filtro de mayoría, que no necesita segmentador. SAM con indicaciones y por texto confirma lo que el modo automático mostraba: a 10 m el modelo devuelve el paisaje, no el parche, cualquiera que sea la forma de preguntarle. El cambio por objeto es la excepción con sentido: agregar por objeto elimina el ruido de sal y pimienta del cambio sin alterar el acuerdo con la referencia, que es exactamente el uso que Blaschke (2010) atribuye a los objetos en series temporales. Las cuatro pruebas posteriores delimitan lo que queda por intentar: la serie mensual entera no aporta sobre sus resúmenes, la temperatura de superficie no es una variable de cobertura, y un modelo fundacional preentrenado en HLS no transfiere congelado al cubo de Sentinel-2, de modo que la única representación fundacional que iguala a lo espectral sigue siendo AlphaEarth. El ajuste fino de Prithvi con etiquetas densas y el uso de ECOSTRESS como indicador de estado o de inundación quedan como líneas de la tesis. Las cuatro últimas pruebas cierran el inventario por el lado de la segmentación: el contexto multiescala es lo más que el objeto aporta como rasgo, dos o tres centésimas, el suavizado de probabilidades y los bordes trazados sobre el embedding no cambian nada, y Sentinel-1, la entrada con más base física para separar el humedal inundado del dosel abierto, tampoco lo hace a 10 m con compuestos mensuales.

La segunda ronda convierte dos de las limitaciones en medidas. Con otra muestra, más difícil por diseño, el contexto de objeto pequeño reaparece con el mismo tamaño, dos o tres centésimas de macro-F1 y siete en los bordes, y el primer lugar alterna entre SLIC y Felzenszwalb, de modo que el hallazgo es de escala y no de segmentador. El humedal herbáceo, la clase peor separada, mejora de 0,22 a 0,35 solo por pasar de 73 a 113 ejemplos, y la curva de aprendizaje muestra que ese ascenso continúa pero se paga con el degradado: los ejemplos mueven la frontera entre dos clases que a 10 m no se separan. Para la tesis esto deja una decisión en lugar de una duda. O se mapea una clase fusionada de humedal y manglar degradado, con 0,66 de macro-F1 en cinco clases, o se mantienen separadas y se acepta que su frontera depende de la proporción de ejemplos y no de la imagen. La revisión a ciegas de los puntos fuera del corredor resuelve además la pregunta que la Tabla 4 dejaba abierta: el mapa no solo sobreestima, también encuentra manglar que las referencias no cartografían, en una proporción de cuatro a seis, y una muestra probabilística de validación tendrá que cubrir ese sector para que el área estimada no herede el sesgo de ninguna de las dos referencias.

Los exploratorios y la extensión se leen mejor en la taxonomía que Safonova et al. (2023) proponen para el problema de los datos escasos en percepción remota: DeepLabV3+ con el mapa como etiqueta es aprendizaje débilmente supervisado, la propagación sobre AlphaEarth es semisupervisado, SAM con indicaciones es aprendizaje con un ejemplo y la segmentación por texto es sin ejemplos. Con 720 puntos, ninguna de las cuatro supera a un clasificador convencional sobre una representación preentrenada, que es la técnica de transferencia de esa misma lista. Safonova et al. (2023) advierten además que las exactitudes publicadas con datos escasos suelen ser sospechosamente altas por particiones que no controlan la dependencia espacial, y Rao et al. (2026) reúnen comparaciones entre métodos tradicionales y de aprendizaje profundo en las que la ventaja de los segundos depende del volumen de etiquetas. La validación por bloques con búfer de este informe es la razón de que las cifras queden por debajo de lo habitual, y el resultado de la transferencia 2021 a 2025 reproduce a escala de paisaje lo que Mohanty et al. (2016) midieron en imágenes de hojas: un modelo que rinde bien dentro de su distribución pierde cuando cambian la fecha y la definición de la referencia. De esa taxonomía, la técnica que queda por aplicar y que más le serviría a la tesis es el aprendizaje activo, es decir, elegir los próximos puntos a etiquetar donde el modelo está más inseguro, que en este dominio son el sur y la clase otro.

Quedan cuatro limitaciones. La primera es que SLICO produjo celdas casi regulares sobre este compuesto, por lo que el control de segmentación midió la escala de agregación y no la calidad de delimitación. La extensión con Felzenszwalb corrige esa limitación para la clasificación, pero sus objetos tampoco cruzan las teselas de 1.024 píxeles. La segunda es que SAM se corrió solo sobre la composición RGB de la estación seca, sin la banda infrarroja ni la estación húmeda. La tercera es la costura residual entre teselas de SAM. La cuarta es que la muestra, diseñada para entrenamiento, cubre mal el sur y la clase otro, lo que limita tanto la macro-F1 como la lectura de la delimitación. La segunda ronda reduce esa limitación con 100 puntos dirigidos, pero no la elimina, porque los puntos se sortearon donde el mapa dice manglar o humedal y no de forma probabilística, y porque los 100 no llevan marca de borde. TESSERA 2025, prevista como cuarta entrada, no estuvo disponible en el servidor durante el periodo del informe y se declara como tal.

## Conclusiones

Con los mismos 720 puntos, el mismo clasificador y la misma validación por bloques, el contexto espacial que aporta la segmentación se concentra en lo que al píxel le falta, y solo cuando el objeto es pequeño. A 0,25 ha, el segmento sube los puntos de borde de 0,45 a 0,51, el humedal herbáceo de 0,22 a 0,34 como indicio sin potencia, y elimina el ruido de sal y pimienta del cambio 2021 a 2025, de 115.239 a 7.926 manchas sin alterar el acuerdo con la referencia. Ese aporte en los bordes se obtiene también con un filtro de mayoría de 5 por 5, sin segmentador. La segunda ronda, con 100 puntos dirigidos y 820 en total, reproduce el aporte con el mismo tamaño, 0,613 frente a 0,587 con el contexto de SLIC de 0,25 ha, y lo sitúa en la escala y no en el segmentador.

El contexto no aporta en la exactitud global ni en la delimitación. A 1 ha la diferencia de macro-F1 es menor de dos centésimas y ningún segmentador sube el Jaccard del píxel contra INVEMAR y GMW, que entre sí coinciden en 0,51. A partir de 4 ha el segmento quita más de lo que da, hasta 0,27 con SAM grueso, porque un objeto de ese tamaño contiene varias clases y la decisión única las borra. El contexto como rasgo adicional es neutro en todas las escalas, de modo que el costo está en la unidad de decisión y no en la información del vecindario.

Los exploratorios y la extensión acotan lo demás: SAM no produce parches a 10 m en ninguno de sus cuatro modos, DeepLabV3+ con etiquetas débiles no supera al mapa del que aprende, la serie mensual entera no aporta sobre sus resúmenes, la temperatura de superficie no es variable de cobertura, Prithvi-EO 2.0 congelado no transfiere y Sentinel-1 no separa el humedal del manglar degradado, mientras que AlphaEarth con un clasificador trivial iguala al Random Forest de 94 variables. Lo que sí quedó medido es dónde está el error que la métrica por puntos no ve: en referencias parciales que discrepan entre sí y en 142 km² de manglar del mapa en un sur sin puntos de muestra, de los que la revisión a ciegas mostró que el 43 % es manglar y el 57 % sobreestimación. La clase humedal herbáceo sube de 0,22 a 0,35 con 40 ejemplos más, y la curva de aprendizaje indica que seguirá subiendo a costa del degradado, porque a 10 m las dos clases comparten el espacio espectral.

## Trabajo futuro

Para la tesis, el resultado desplaza el esfuerzo del segmentador hacia la referencia: muestra de validación probabilística con la clase otro y el sur reforzados, estimación de áreas por muestra y no por mapa, y un filtro de mayoría de 5 por 5 píxeles como tratamiento de bordes en lugar de una segmentación. Para el curso, las dos pruebas que quedaban, SAM con indicaciones y un segmentador de bordes adaptativos, se corrieron en la extensión. Queda por probar un segmentador sin costuras de tesela y una referencia de cambio independiente de WorldCover para medir la exactitud del cambio por objeto. La segunda ronda deja en marcha una tercera, de 60 puntos sorteados en la frontera entre humedal y degradado, y una decisión para la tesis: fusionar las dos clases en el mapa o mantenerlas con su frontera declarada como dependiente de la muestra.

## Bibliografía

Achanta, R., Shaji, A., Smith, K., Lucchi, A., Fua, P. y Süsstrunk, S. (2012). SLIC superpixels compared to state-of-the-art superpixel methods. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 34*(11), 2274-2282. https://doi.org/10.1109/TPAMI.2012.120

Ball, J. G. C., Wicklein, J. A., Feng, Z., Knezevic, J., Jaffer, S., Madhavapeddy, A., Atzberger, C., Dalponte, M. y Coomes, D. A. (2026). Geospatial foundation models enable data-efficient tree species mapping in temperate mountain forests. *Science of Remote Sensing, 14*, Artículo 100466. https://doi.org/10.1016/j.srs.2026.100466

Blaschke, T. (2010). Object based image analysis for remote sensing. *ISPRS Journal of Photogrammetry and Remote Sensing, 65*(1), 2-16. https://doi.org/10.1016/j.isprsjprs.2009.06.004

Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5-32. https://doi.org/10.1023/A:1010933404324

Brown, C. F., Kazmierski, M. R., Pasquarella, V. J., Rucklidge, W. J., Samsikova, M., Zhang, C., Shelhamer, E., Lahera, E., Wiles, O., Ilyushchenko, S., Gorelick, N., Zhang, L. L., Alj, S., Schechter, E., Askay, S., Guinan, O., Moore, R., Boukouvalas, A. y Kohli, P. (2025). *AlphaEarth Foundations: An embedding field model for accurate and efficient global mapping from sparse label data* [Preimpresión]. arXiv. https://doi.org/10.48550/arXiv.2507.22291

Bunting, P., Rosenqvist, A., Hilarides, L., Lucas, R. M., Thomas, N., Tadono, T., Worthington, T. A., Spalding, M., Murray, N. J. y Rebelo, L.-M. (2022). Global mangrove extent change 1996-2020: Global Mangrove Watch version 3.0. *Remote Sensing, 14*(15), Artículo 3657. https://doi.org/10.3390/rs14153657

Chen, L.-C., Zhu, Y., Papandreou, G., Schroff, F. y Adam, H. (2018). Encoder-decoder with atrous separable convolution for semantic image segmentation. En V. Ferrari, M. Hebert, C. Sminchisescu y Y. Weiss (Eds.), *Computer Vision – ECCV 2018* (Lecture Notes in Computer Science, Vol. 11211, pp. 833-851). Springer. https://doi.org/10.1007/978-3-030-01234-2_49

Felzenszwalb, P. F. y Huttenlocher, D. P. (2004). Efficient graph-based image segmentation. *International Journal of Computer Vision, 59*(2), 167-181. https://doi.org/10.1023/B:VISI.0000022288.19776.77

Fisher, J. B., Lee, B., Purdy, A. J., Halverson, G. H., Dohlen, M. B., Cawse-Nicholson, K., Wang, A., Anderson, R. G., Aragon, B., Arain, M. A., Baldocchi, D. D., Baker, J. M., Barral, H., Bernacchi, C. J., Bernhofer, C., Biraud, S. C., Bohrer, G., Brunsell, N., Cappelaere, B., ... Hook, S. (2020). ECOSTRESS: NASA's next generation mission to measure evapotranspiration from the International Space Station. *Water Resources Research, 56*(4), e2019WR026058. https://doi.org/10.1029/2019WR026058

Foody, G. M. (2004). Thematic map comparison: Evaluating the statistical significance of differences in classification accuracy. *Photogrammetric Engineering & Remote Sensing, 70*(5), 627-633. https://doi.org/10.14358/PERS.70.5.627

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*(2), 65-70.

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A. C., Lo, W.-Y., Dollár, P. y Girshick, R. (2023). Segment anything. *arXiv*. https://arxiv.org/abs/2304.02643

Liu, S., Zeng, Z., Ren, T., Li, F., Zhang, H., Yang, J., Jiang, Q., Li, C., Yang, J., Su, H., Zhu, J. y Zhang, L. (2023). Grounding DINO: Marrying DINO with grounded pre-training for open-set object detection. *arXiv*. https://arxiv.org/abs/2303.05605

Mohanty, S. P., Hughes, D. P. y Salathé, M. (2016). Using deep learning for image-based plant disease detection. *Frontiers in Plant Science, 7*, Artículo 1419. https://doi.org/10.3389/fpls.2016.01419

Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E. y Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment, 148*, 42-57. https://doi.org/10.1016/j.rse.2014.02.015

Osco, L. P., Wu, Q., de Lemos, E. L., Gonçalves, W. N., Ramos, A. P. M., Li, J. y Marcato Junior, J. (2023). The Segment Anything Model (SAM) for remote sensing applications: From zero to one shot. *International Journal of Applied Earth Observation and Geoinformation, 124*, Artículo 103540. https://doi.org/10.1016/j.jag.2023.103540

Rao, S. V. B. S., Rao, T. S., Sowjanya, M. y Aruna, C. V. (2026). Deep learning and traditional methods for remote sensing image analysis. *Discover Imaging, 3*, Artículo 5. https://doi.org/10.1007/s44352-026-00027-4

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F. y Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913-929. https://doi.org/10.1111/ecog.02881

Safonova, A., Ghazaryan, G., Stiller, S., Main-Knorn, M., Nendel, C. y Ryo, M. (2023). Ten deep learning techniques to address small data problems with remote sensing. *International Journal of Applied Earth Observation and Geoinformation, 125*, Artículo 103569. https://doi.org/10.1016/j.jag.2023.103569

Szwarcman, D., Roy, S., Fraccaro, P., Gíslason, Þ. E., Blumenstiel, B., Ghosal, R., de Oliveira, P. H., Almeida, J. L. d. S., Sedona, R., Kang, Y., Chakraborty, S., Wang, S., Gomes, C., Kumar, A., Truong, M., Godwin, D., Lee, H., Hsu, C. Y., Lal, R., ... Moreno, J. B. (2024). Prithvi-EO-2.0: A versatile multi-temporal foundation model for Earth observation applications. *arXiv*. https://arxiv.org/abs/2412.02732

Wu, Q. (2026). GeoAI: A Python package for integrating artificial intelligence with geospatial data analysis and visualization. *Journal of Open Source Software, 11*(118), Artículo 9605. https://doi.org/10.21105/joss.09605

Wu, Q. y Osco, L. P. (2023). samgeo: A Python package for segmenting geospatial data with the Segment Anything Model (SAM). *Journal of Open Source Software, 8*(89), Artículo 5663. https://doi.org/10.21105/joss.05663

Zhou, D., Bousquet, O., Lal, T. N., Weston, J. y Schölkopf, B. (2004). Learning with local and global consistency. En S. Thrun, L. K. Saul y B. Schölkopf (Eds.), *Advances in Neural Information Processing Systems 16* (pp. 321-328). MIT Press.
