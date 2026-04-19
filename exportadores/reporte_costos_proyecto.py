# -*- coding: utf-8 -*-
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet

import math

# 🔥 IMPORTAMOS TU SISTEMA BASE
from exportadores.pdf_base import estilo_tabla, salto_pagina_seguro


# =====================================================
# 🔥 GANTT (MEJORADO PERO SIMPLE)
# =====================================================
def generar_gantt_actividades(resultado):

    num_postes = resultado.get("num_postes", 0)
    num_retenidas = resultado.get("num_retenidas", 0)
    total_estructuras = resultado.get("total_estructuras", 0)
    long_prim = resultado.get("longitud_primario", 0)
    long_sec = resultado.get("longitud_secundario", 0)

    d_levantamiento = 1
    total_agujeros = num_postes + num_retenidas
    d_agujeros = math.ceil(total_agujeros / 20)
    d_postes = math.ceil(num_postes / 8)
    d_retenidas = math.ceil(num_retenidas / 8)
    d_estructuras = math.ceil(total_estructuras / 8)

    d_primario = math.ceil(long_prim / 500) if long_prim > 0 else 0
    d_secundario = math.ceil(long_sec / 300) if long_sec > 0 else 0

    actividades = [
        ("Levantamiento", d_levantamiento),
        ("Apertura de agujeros", d_agujeros),
        ("Hincado de postes", d_postes),
        ("Puesta de retenidas", d_retenidas),
        ("Armado de estructuras", d_estructuras),
        ("Tendido línea primaria", d_primario),
        ("Tendido línea secundaria", d_secundario),
    ]

    data = [["Actividad", "Duración", "Progreso"]]

    for nombre, duracion in actividades:
        if duracion == 0:
            continue
        barra = "█" * int(duracion)
        data.append([nombre, duracion, barra])

    tabla = Table(data)
    tabla.setStyle(estilo_tabla())

    return tabla


# =====================================================
# 🔥 BLOQUE COSTOS (YA UNIFICADO)
# =====================================================
def construir_bloque_costos(elementos, styles, resultado, df_materiales_costos):

    # =============================
    # DATOS
    # =============================
    elementos.append(Paragraph("Datos del Proyecto", styles["Heading2"]))
    elementos.append(Spacer(1, 6))

    tabla_info = Table([
        ["Concepto", "Valor"],
        ["Total estructuras", resultado.get("total_estructuras", 0)],
        ["Postes", resultado.get("num_postes", 0)],
        ["Retenidas", resultado.get("num_retenidas", 0)],
        ["Longitud primaria (m)", resultado.get("longitud_primario", 0)],
        ["Longitud secundaria (m)", resultado.get("longitud_secundario", 0)],
    ])
    tabla_info.setStyle(estilo_tabla())

    elementos.append(tabla_info)
    elementos.append(Spacer(1, 12))

    # =============================
    # GANTT
    # =============================
    elementos.append(Paragraph("Cronograma de Obra", styles["Heading2"]))
    elementos.append(Spacer(1, 6))

    elementos.append(generar_gantt_actividades(resultado))

    # 🔥 SALTO CONTROLADO
    salto_pagina_seguro(elementos)

    # =============================
    # MATERIALES
    # =============================
    elementos.append(Paragraph("Materiales del Proyecto", styles["Heading2"]))
    elementos.append(Spacer(1, 6))

    data_mat = [["Descripción", "Und", "Cant", "P.U.", "Total"]]

    if df_materiales_costos is not None and not df_materiales_costos.empty:
        for _, row in df_materiales_costos.iterrows():
            data_mat.append([
                str(row.get("Materiales", "")),
                str(row.get("Unidad", "")),
                f"{row.get('Cantidad', 0):,.2f}",
                f"L {row.get('Costo Unitario', 0):,.2f}",
                f"L {row.get('Costo Total', 0):,.2f}",
            ])

    tabla_mat = Table(data_mat)
    tabla_mat.setStyle(estilo_tabla())

    elementos.append(tabla_mat)

    # 🔥 SALTO CONTROLADO
    salto_pagina_seguro(elementos)

    # =============================
    # COSTOS
    # =============================
    elementos.append(Paragraph("Costos del Proyecto", styles["Heading2"]))
    elementos.append(Spacer(1, 6))

    tabla_costos = Table([
        ["Concepto", "Lempiras"],
        ["Materiales", f"L {resultado.get('costo_materiales', 0):,.2f}"],
        ["Cuadrilla", f"L {resultado.get('costo_cuadrilla', 0):,.2f}"],
        ["Agujeros", f"L {resultado.get('costo_agujeros', 0):,.2f}"],
        ["Grúa", f"L {resultado.get('costo_grua', 0):,.2f}"],
        ["ENEE", f"L {resultado.get('costo_enee', 0):,.2f}"],
        ["Contingencia", f"L {resultado.get('contingencia', 0):,.2f}"],
    ])
    tabla_costos.setStyle(estilo_tabla())

    elementos.append(tabla_costos)
    elementos.append(Spacer(1, 12))

    # =============================
    # RESULTADO FINAL
    # =============================
    tabla_final = Table([
        ["Concepto", "Valor"],
        ["Costo total real", f"L {resultado.get('costo_total_real', 0):,.2f}"],
        ["Precio venta", f"L {resultado.get('precio_venta', 0):,.2f}"],
        ["Utilidad", f"L {resultado.get('utilidad', 0):,.2f}"],
        ["Margen (%)", f"{resultado.get('margen_pct', 0)} %"],
    ])
    tabla_final.setStyle(estilo_tabla())

    elementos.append(tabla_final)
    elementos.append(Spacer(1, 12))

    # =============================
    # EVALUACIÓN
    # =============================
    elementos.append(Paragraph("Evaluación", styles["Heading2"]))

    margen = resultado.get("margen_pct", 0)

    if margen < 10:
        msg = "Margen bajo. Proyecto con alto riesgo financiero."
    elif margen < 20:
        msg = "Margen aceptable. Se recomienda optimización de costos."
    else:
        msg = "Margen saludable. Proyecto rentable."

    elementos.append(Paragraph(msg, styles["Normal"]))


# =====================================================
# 🔥 PDF FINAL
# =====================================================
def generar_pdf_costos_proyecto(resultado, df_materiales_costos, ruta="costos_proyecto.pdf"):

    doc = SimpleDocTemplate(ruta)
    styles = getSampleStyleSheet()

    elementos = []

    elementos.append(Paragraph("INFORME DE COSTOS DE PROYECTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

    construir_bloque_costos(
        elementos,
        styles,
        resultado,
        df_materiales_costos
    )

    doc.build(elementos)

    return ruta
