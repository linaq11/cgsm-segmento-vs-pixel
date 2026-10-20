# Segmento frente a píxel: familia de contrastes con Holm

Contraste primario declarado: slic_fino con la entrada s2_mas_alphaearth. Familia: 45 contrastes. DMD de la prueba: 0,016 de macro-F1 (potencia 0,80).

| Segmentador | Entrada | Contraste | macro-F1 píxel | macro-F1 brazo | Diferencia | p permutación | p Holm | Primario |
|---|---|---|---|---|---|---|---|---|
| slic_fino | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.586 | -0.002 | 0.9160 | 1.0000 | sí |
| felz_025ha | alphaearth | segmento − pixel | 0.582 | 0.595 | +0.013 | 0.3105 | 1.0000 |  |
| felz_025ha | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.591 | +0.003 | 0.7605 | 1.0000 |  |
| felz_025ha | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.597 | +0.010 | 0.4710 | 1.0000 |  |
| felz_025ha | s2_multitemporal | segmento − pixel | 0.555 | 0.560 | +0.005 | 0.7535 | 1.0000 |  |
| felz_025ha | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.597 | +0.010 | 0.2590 | 1.0000 |  |
| felz_1ha | alphaearth | segmento − pixel | 0.582 | 0.606 | +0.024 | 0.1885 | 1.0000 |  |
| felz_1ha | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.586 | -0.002 | 0.9135 | 1.0000 |  |
| felz_1ha | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.599 | +0.012 | 0.4510 | 1.0000 |  |
| felz_1ha | s2_multitemporal | segmento − pixel | 0.555 | 0.536 | -0.020 | 0.1865 | 1.0000 |  |
| felz_1ha | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.579 | -0.009 | 0.5165 | 1.0000 |  |
| sam | alphaearth | segmento − pixel | 0.582 | 0.386 | -0.195 | 0.0000 | 0.0000 |  |
| sam | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.588 | +0.001 | 0.9685 | 1.0000 |  |
| sam | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.378 | -0.210 | 0.0000 | 0.0000 |  |
| sam | s2_multitemporal | segmento − pixel | 0.555 | 0.356 | -0.199 | 0.0000 | 0.0000 |  |
| sam | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.417 | -0.171 | 0.0000 | 0.0000 |  |
| sam_fino | alphaearth | segmento − pixel | 0.582 | 0.453 | -0.129 | 0.0000 | 0.0000 |  |
| sam_fino | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.596 | +0.009 | 0.6230 | 1.0000 |  |
| sam_fino | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.444 | -0.143 | 0.0005 | 0.0170 |  |
| sam_fino | s2_multitemporal | segmento − pixel | 0.555 | 0.423 | -0.133 | 0.0000 | 0.0000 |  |
| sam_fino | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.497 | -0.090 | 0.0000 | 0.0000 |  |
| slic | alphaearth | segmento − pixel | 0.582 | 0.433 | -0.149 | 0.0000 | 0.0000 |  |
| slic | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.587 | -0.001 | 0.9375 | 1.0000 |  |
| slic | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.436 | -0.152 | 0.0015 | 0.0495 |  |
| slic | s2_multitemporal | segmento − pixel | 0.555 | 0.418 | -0.137 | 0.0045 | 0.1305 |  |
| slic | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.422 | -0.166 | 0.0000 | 0.0000 |  |
| slic_025ha | alphaearth | segmento − pixel | 0.582 | 0.583 | +0.001 | 0.9215 | 1.0000 |  |
| slic_025ha | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.613 | +0.026 | 0.0550 | 1.0000 |  |
| slic_025ha | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.592 | +0.004 | 0.7595 | 1.0000 |  |
| slic_025ha | s2_multitemporal | segmento − pixel | 0.555 | 0.540 | -0.015 | 0.3490 | 1.0000 |  |
| slic_025ha | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.587 | -0.001 | 0.9520 | 1.0000 |  |
| slic_16ha | alphaearth | segmento − pixel | 0.582 | 0.525 | -0.057 | 0.0205 | 0.5535 |  |
| slic_16ha | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.589 | +0.002 | 0.8765 | 1.0000 |  |
| slic_16ha | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.508 | -0.079 | 0.0030 | 0.0900 |  |
| slic_16ha | s2_multitemporal | segmento − pixel | 0.555 | 0.460 | -0.096 | 0.0015 | 0.0495 |  |
| slic_16ha | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.496 | -0.091 | 0.0000 | 0.0000 |  |
| slic_4ha | alphaearth | segmento − pixel | 0.582 | 0.553 | -0.028 | 0.1380 | 1.0000 |  |
| slic_4ha | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.595 | +0.008 | 0.6120 | 1.0000 |  |
| slic_4ha | s2_mas_alphaearth | segmento − pixel | 0.587 | 0.549 | -0.038 | 0.0605 | 1.0000 |  |
| slic_4ha | s2_multitemporal | segmento − pixel | 0.555 | 0.458 | -0.098 | 0.0025 | 0.0775 |  |
| slic_4ha | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.514 | -0.073 | 0.0000 | 0.0000 |  |
| slic_fino | alphaearth | segmento − pixel | 0.582 | 0.586 | +0.005 | 0.6180 | 1.0000 |  |
| slic_fino | pixel_mas_segmento | pixel+segmento − pixel | 0.587 | 0.593 | +0.006 | 0.6505 | 1.0000 |  |
| slic_fino | s2_multitemporal | segmento − pixel | 0.555 | 0.519 | -0.036 | 0.1635 | 1.0000 |  |
| slic_fino | voto_mayoria_union | voto por mayoria − pixel | 0.587 | 0.554 | -0.033 | 0.0125 | 0.3500 |  |
