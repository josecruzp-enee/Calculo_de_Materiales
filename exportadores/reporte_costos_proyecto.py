# -*- coding: utf-8 -*-
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

import math


# =====================================================
# 🔥 GANTT POR ACTIVIDADES
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

    data = [["Actividad", "Inicio", "Fin", "Duración"]]

    dia_actual = 0

    for nombre, duracion in actividades:

        if duracion == 0:
            continue

        inicio = dia_actual
        fin = inicio + duracion

        data.append([nombre, inicio, fin, duracion])

        dia_actual = fin

    return Table(data)


# =====================================================
# 🔥 PDF COSTOS PROYECTO COMPLETO
# =====================================================
def generar_pdf_costos_proyecto(resultado, df_materiales_costos, ruta="costos_proyecto.pdf"):

    doc = SimpleDocTemplate(ruta)
    styles = getSampleStyleSheet()

    elementos = []

    # =====================================================
    # TÍTULO
    # =====================================================
    elementos.append(Paragraph("INFORME DE COSTOS DE PROYECTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 0. DATOS DEL PROYECTO
    # =====================================================
    elementos.append(Paragraph("0. Datos del Proyecto", styles["Heading2"]))

    data_datos = [
        ["Concepto", "Valor"],
        ["Total estructuras", resultado.get("total_estructuras", 0)],
        ["Postes", resultado.get("num_postes", 0)],
        ["Retenidas", resultado.get("num_retenidas", 0)],
        ["Longitud primaria (m)", resultado.get("longitud_primario", 0)],
        ["Longitud secundaria (m)", resultado.get("longitud_secundario", 0)],
    ]

    tabla = Table(data_datos)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 1. TIEMPO
    # =====================================================
    elementos.append(Paragraph("1. Tiempo del Proyecto", styles["Heading2"]))

    data_tiempo = [
        ["Concepto", "Valor"],
        ["Días totales", resultado.get("dias_totales", 0)],
    ]

    tabla = Table(data_tiempo)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 🔥 GANTT
    # =====================================================
    elementos.append(Paragraph("Cronograma de Obra (Gantt)", styles["Heading2"]))
    elementos.append(Spacer(1, 8))

    tabla_gantt = generar_gantt_actividades(resultado)
    tabla_gantt.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
    ]))

    elementos.append(tabla_gantt)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 🔥 2. MATERIALES CON PRECIO
    # =====================================================
    elementos.append(Paragraph("2. Materiales del Proyecto", styles["Heading2"]))
    elementos.append(Spacer(1, 8))

    data_mat = [["Descripción", "Und", "Cant", "P.U.", "Total"]]

    for _, row in df_materiales_costos.iterrows():
        data_mat.append([
            str(row.get("Materiales", "")),
            str(row.get("Unidad", "")),
            f"{row.get('Cantidad', 0):,.2f}",
            f"L {row.get('Costo Unitario', 0):,.2f}",
            f"L {row.get('Costo Total', 0):,.2f}",
        ])

    tabla_mat = Table(data_mat)
    tabla_mat.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ]))

    elementos.append(tabla_mat)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 3. COSTOS
    # =====================================================
    elementos.append(Paragraph("3. Costos del Proyecto", styles["Heading2"]))

    data_costos = [
        ["Concepto", "Lempiras"],
        ["Materiales", f"L {resultado.get('costo_materiales', 0):,.2f}"],
        ["Cuadrilla", f"L {resultado.get('costo_cuadrilla', 0):,.2f}"],
        ["Agujeros", f"L {resultado.get('costo_agujeros', 0):,.2f}"],
        ["Grúa", f"L {resultado.get('costo_grua', 0):,.2f}"],
        ["ENEE", f"L {resultado.get('costo_enee', 0):,.2f}"],
        ["Contingencia", f"L {resultado.get('contingencia', 0):,.2f}"],
    ]

    tabla = Table(data_costos)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 4. RESULTADO FINANCIERO
    # =====================================================
    elementos.append(Paragraph("4. Resultado Financiero", styles["Heading2"]))

    data_final = [
        ["Concepto", "Valor"],
        ["Costo total real", f"L {resultado.get('costo_total_real', 0):,.2f}"],
        ["Precio venta", f"L {resultado.get('precio_venta', 0):,.2f}"],
        ["Utilidad", f"L {resultado.get('utilidad', 0):,.2f}"],
        ["Margen (%)", f"{resultado.get('margen_pct', 0)} %"],
    ]

    tabla = Table(data_final)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # 5. EVALUACIÓN
    # =====================================================
    elementos.append(Paragraph("5. Evaluación", styles["Heading2"]))

    margen = resultado.get("margen_pct", 0)

    if margen < 10:
        mensaje = "Margen bajo. Proyecto con alto riesgo financiero."
    elif margen < 20:
        mensaje = "Margen aceptable. Se recomienda optimización de costos."
    else:
        mensaje = "Margen saludable. Proyecto rentable."

    elementos.append(Paragraph(mensaje, styles["Normal"]))

    # =====================================================
    # GENERAR PDF
    # =====================================================
    doc.build(elementos)

    return ruta
