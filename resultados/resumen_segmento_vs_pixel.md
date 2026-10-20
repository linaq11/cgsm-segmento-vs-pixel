# Segmento frente a píxel: familia de contrastes con Holm

Contraste primario declarado: slic_fino con la entrada s2_mas_alphaearth. Familia: 35 contrastes. DMD de la prueba: 0,016 de macro-F1 (potencia 0,80).

| Segmentador | Entrada | Contraste | macro-F1 píxel | macro-F1 brazo | Diferencia | p permutación | p Holm | Primario |
|---|---|---|---|---|---|---|---|---|
| slic_fino | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.579 | -0.012 | 0.4845 | 1.0000 | sí |
| sam | alphaearth | segmento − pixel | 0.595 | 0.353 | -0.242 | 0.0000 | 0.0000 |  |
| sam | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.577 | -0.014 | 0.2425 | 1.0000 |  |
| sam | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.372 | -0.219 | 0.0000 | 0.0000 |  |
| sam | s2_multitemporal | segmento − pixel | 0.580 | 0.311 | -0.269 | 0.0000 | 0.0000 |  |
| sam | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.425 | -0.166 | 0.0000 | 0.0000 |  |
| sam_fino | alphaearth | segmento − pixel | 0.595 | 0.474 | -0.122 | 0.0000 | 0.0000 |  |
| sam_fino | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.595 | +0.004 | 0.8120 | 1.0000 |  |
| sam_fino | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.461 | -0.130 | 0.0000 | 0.0000 |  |
| sam_fino | s2_multitemporal | segmento − pixel | 0.580 | 0.408 | -0.172 | 0.0000 | 0.0000 |  |
| sam_fino | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.505 | -0.086 | 0.0000 | 0.0000 |  |
| slic | alphaearth | segmento − pixel | 0.595 | 0.420 | -0.175 | 0.0000 | 0.0000 |  |
| slic | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.589 | -0.002 | 0.9265 | 1.0000 |  |
| slic | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.428 | -0.163 | 0.0005 | 0.0095 |  |
| slic | s2_multitemporal | segmento − pixel | 0.580 | 0.363 | -0.217 | 0.0000 | 0.0000 |  |
| slic | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.394 | -0.197 | 0.0000 | 0.0000 |  |
| slic_025ha | alphaearth | segmento − pixel | 0.595 | 0.586 | -0.010 | 0.4950 | 1.0000 |  |
| slic_025ha | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.604 | +0.013 | 0.3200 | 1.0000 |  |
| slic_025ha | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.611 | +0.020 | 0.2785 | 1.0000 |  |
| slic_025ha | s2_multitemporal | segmento − pixel | 0.580 | 0.544 | -0.036 | 0.1065 | 1.0000 |  |
| slic_025ha | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.592 | +0.001 | 0.9435 | 1.0000 |  |
| slic_16ha | alphaearth | segmento − pixel | 0.595 | 0.519 | -0.076 | 0.0005 | 0.0095 |  |
| slic_16ha | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.575 | -0.016 | 0.3790 | 1.0000 |  |
| slic_16ha | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.490 | -0.101 | 0.0000 | 0.0000 |  |
| slic_16ha | s2_multitemporal | segmento − pixel | 0.580 | 0.450 | -0.130 | 0.0000 | 0.0000 |  |
| slic_16ha | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.478 | -0.113 | 0.0000 | 0.0000 |  |
| slic_4ha | alphaearth | segmento − pixel | 0.595 | 0.558 | -0.037 | 0.0480 | 0.6720 |  |
| slic_4ha | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.594 | +0.003 | 0.8655 | 1.0000 |  |
| slic_4ha | s2_mas_alphaearth | segmento − pixel | 0.591 | 0.544 | -0.047 | 0.0060 | 0.0900 |  |
| slic_4ha | s2_multitemporal | segmento − pixel | 0.580 | 0.466 | -0.114 | 0.0005 | 0.0095 |  |
| slic_4ha | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.511 | -0.080 | 0.0000 | 0.0000 |  |
| slic_fino | alphaearth | segmento − pixel | 0.595 | 0.576 | -0.019 | 0.3245 | 1.0000 |  |
| slic_fino | pixel_mas_segmento | pixel+segmento − pixel | 0.591 | 0.606 | +0.015 | 0.2180 | 1.0000 |  |
| slic_fino | s2_multitemporal | segmento − pixel | 0.580 | 0.501 | -0.079 | 0.0035 | 0.0560 |  |
| slic_fino | voto_mayoria_union | voto por mayoria − pixel | 0.591 | 0.541 | -0.050 | 0.0000 | 0.0000 |  |
