# -*- coding: utf-8 -*-
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def generar_pdf_costos_proyecto(resultado, ruta="costos_proyecto.pdf"):

    doc = SimpleDocTemplate(ruta)
    styles = getSampleStyleSheet()

    elementos = []

    # =====================================================
    # TÍTULO
    # =====================================================
    elementos.append(Paragraph("INFORME DE COSTOS DE PROYECTO", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # =====================================================
    # TIEMPO
    # =====================================================
    elementos.append(Paragraph("1. Tiempo del Proyecto", styles["Heading2"]))

    data_tiempo = [
        ["Concepto", "Valor"],
        ["Días primario", resultado.get("dias_primario", 0)],
        ["Días secundario", resultado.get("dias_secundario", 0)],
        ["Días estructuras", resultado.get("dias_estructura", 0)],
        ["Días totales", resultado.get("dias_totales", 0)],
    ]

    tabla = Table(data_tiempo)
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # COSTOS
    # =====================================================
    elementos.append(Paragraph("2. Costos del Proyecto", styles["Heading2"]))

    data_costos = [
        ["Concepto", "Lempiras"],
        ["Materiales", f"L {resultado.get('costo_materiales',0):,.2f}"],
        ["Cuadrilla", f"L {resultado.get('costo_cuadrilla',0):,.2f}"],
        ["Agujeros", f"L {resultado.get('costo_agujeros',0):,.2f}"],
        ["Grúa", f"L {resultado.get('costo_grua',0):,.2f}"],
        ["ENEE", f"L {resultado.get('costo_enee',0):,.2f}"],
        ["Contingencia", f"L {resultado.get('contingencia',0):,.2f}"],
    ]

    tabla = Table(data_costos)
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    # =====================================================
    # RESULTADO FINAL
    # =====================================================
    elementos.append(Paragraph("3. Resultado Financiero", styles["Heading2"]))

    data_final = [
        ["Concepto", "Valor"],
        ["Costo total real", f"L {resultado.get('costo_total_real',0):,.2f}"],
        ["Precio venta", f"L {resultado.get('precio_venta',0):,.2f}"],
        ["Utilidad", f"L {resultado.get('utilidad',0):,.2f}"],
        ["Margen (%)", f"{resultado.get('margen_pct',0)} %"],
    ]

    tabla = Table(data_final)
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
    ]))

    elementos.append(tabla)

    # =====================================================
    # GENERAR PDF
    # =====================================================
    doc.build(elementos)

    return ruta
