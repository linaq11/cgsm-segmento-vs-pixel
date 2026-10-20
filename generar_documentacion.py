# -*- coding: utf-8 -*-
"""Reúne en un solo Markdown todo lo redactado en los scripts: la cabecera (docstring) y los
comentarios de cada uno, en el orden del flujo de trabajo del Informe 2. Escribe DOCUMENTACION_scripts.md.

USO: python generar_documentacion.py
"""
import ast
import io
import os
import tokenize

AQUI = os.path.dirname(os.path.abspath(__file__))
ORDEN = [
    ("1. Compuesto y variables por punto", ["00_compuesto_seco_2025.py", "01_variables_2025.py"]),
    ("2. Segmentación y agregación", ["02_segmentar.py", "13_felzenszwalb.py", "23_felz_embedding.py", "03_clasificar_segmentos.py"]),
    ("3. Familia de contrastes, mapas, voto y delimitación", ["05_pruebas_holm.py", "06_mapas.py", "04_transferencia.py"]),
    ("4. Exploratorios", ["08_deeplab.py", "09_deeplab_corregido.py", "10_propagacion_alphaearth.py", "07_tessera_2025.py"]),
    ("5. Extensión posterior al cierre", ["12_filtro_mayoria.py", "14_sam_puntos.py", "15_cambio_objeto.py", "16_texto_langsam.py", "17_serie_temporal.py",
                                         "18_ecostress_entrada.py", "19a_compuestos_trimestrales.py", "19_prithvi.py", "21_contexto_multiescala.py", "22_suavizado_prob.py"]),
    ("6. Segunda ronda de muestra (820 puntos)", ["muestra_2025/50_puntos_dirigidos_2026-10.py", "muestra_2025/51_puntos_humedal_2026-10.py", "segunda_ronda/01_variables_2025.py",
                                                   "segunda_ronda/03_clasificar_segmentos.py", "segunda_ronda/05_pruebas_holm.py", "segunda_ronda/06_mapas.py", "segunda_ronda/12_filtro_mayoria.py",
                                                   "segunda_ronda/21_contexto_multiescala.py", "segunda_ronda/24_s1_entrada.py", "segunda_ronda/25_curva_humedal.py"]),
    ("7. Figuras e informe", ["11_figuras.py", "26_fig9_segunda_ronda.py", "informe_a_word.py"]),
    ("Dependencia compartida de la muestra de 2025", ["muestra_2025/40_ablacion_entradas.py"]),
]


def cabecera_y_comentarios(ruta):
    src = open(ruta, encoding="utf-8").read()
    doc = ast.get_docstring(ast.parse(src)) or "(sin cabecera)"
    coms = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT and not tok.string.startswith("# -*-"):
            coms.append((tok.start[0], tok.string.lstrip("# ").rstrip()))
    return doc, coms


def listar_py(base):
    out = []
    for raiz, _, archivos in os.walk(base):
        for a in archivos:
            if a.endswith(".py"):
                out.append(os.path.relpath(os.path.join(raiz, a), base).replace(os.sep, "/"))
    return sorted(out)


salida = ["# Documentación de los scripts", "", "Cabecera y comentarios de cada script, extraídos del código con `generar_documentacion.py`, en el orden del flujo de trabajo del informe. Cada cabecera dice qué hace el script, qué lee, qué escribe y cómo se ejecuta.", ""]
vistos = set()
for etapa, lista in ORDEN:
    salida += ["## " + etapa, ""]
    for f in lista:
        ruta = os.path.join(AQUI, "scripts", f)
        if not os.path.exists(ruta):
            continue
        vistos.add(f)
        doc, coms = cabecera_y_comentarios(ruta)
        salida += ["### `%s`" % f, "", doc.strip(), ""]
        if coms:
            salida += ["Comentarios en el código:", ""] + ["- línea %d: %s" % (n, c) for n, c in coms] + [""]
faltan = [f for f in listar_py(os.path.join(AQUI, "scripts")) if f not in vistos]
if faltan:
    salida += ["## Otros", ""]
    for f in faltan:
        doc, coms = cabecera_y_comentarios(os.path.join(AQUI, "scripts", f))
        salida += ["### `%s`" % f, "", doc.strip(), ""] + (["Comentarios en el código:", ""] + ["- línea %d: %s" % (n, c) for n, c in coms] + [""] if coms else [])
open(os.path.join(AQUI, "DOCUMENTACION_scripts.md"), "w", encoding="utf-8", newline="\n").write("\n".join(salida))
print("DOCUMENTACION_scripts.md:", len(vistos) + len(faltan), "scripts,", sum(len(x.split()) for x in salida), "palabras")
