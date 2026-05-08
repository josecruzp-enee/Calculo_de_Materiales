# -*- coding: utf-8 -*-
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus.tables import TableStyle

import math

from exportadores.pdf_base import estilo_tabla


# =====================================================
# 🔥 ESTILO KPI
# =====================================================
def _estilo_kpi(tabla):

    tabla.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1F4E79")),

        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),

        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),

        ("FONTSIZE", (0, 0), (-1, -1), 16),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),

        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),

        ("TOPPADDING", (0, 0), (-1, -1), 12),

        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1F4E79")),
    ]))


# =====================================================
# 🔥 GANTT VISUAL
# =====================================================
def _bloque_gantt(elementos, styles, resultado):

    elementos.append(
        Paragraph(
            "Cronograma Estimado",
            styles["Heading2"]
        )
    )

    elementos.append(Spacer(1, 8))

    num_postes = resultado.get("num_postes", 0)

    num_retenidas = resultado.get("num_retenidas", 0)

    total_estructuras = resultado.get("total_estructuras", 0)

    long_prim = resultado.get("longitud_primario", 0)

    actividades = [

        ("Levantamiento", 1),

        ("Agujeros",
         math.ceil((num_postes + num_retenidas) / 20)),

        ("Postes",
         math.ceil(num_postes / 8)),

        ("Retenidas",
         math.ceil(num_retenidas / 8)),

        ("Estructuras",
         math.ceil(total_estructuras / 8)),

        ("Tendido MT",
         math.ceil(long_prim / 500)),
    ]

    data = [[
        "Actividad",
        "Días",
        "Cronograma"
    ]]

    for nombre, dias in actividades:

        if dias <= 0:
            continue

        barra = "█" * min(dias, 20)

        data.append([
            nombre,
            str(dias),
            barra
        ])

    tabla = Table(
        data,
        colWidths=[180, 60, 260]
    )

    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)

    elementos.append(Spacer(1, 16))


# =====================================================
# 🔥 KPIs PRINCIPALES
# =====================================================
def _bloque_kpis(elementos, resultado):

    venta = resultado.get("precio_venta", 0)

    costo = resultado.get("costo_total_real", 0)

    utilidad = resultado.get("utilidad", 0)

    margen = resultado.get("margen_pct", 0)

    data = [[

        f"VENTA\nL {venta:,.0f}",

        f"COSTO\nL {costo:,.0f}",

        f"UTILIDAD\nL {utilidad:,.0f}",

        f"MARGEN\n{margen:.1f} %"
    ]]

    tabla = Table(
        data,
        colWidths=[130, 130, 130, 130],
        rowHeights=[60]
    )

    _estilo_kpi(tabla)

    elementos.append(tabla)

    elementos.append(Spacer(1, 20))


# =====================================================
# 🔥 DISTRIBUCIÓN DE COSTOS
# =====================================================
def _bloque_distribucion(elementos, styles, resultado):

    elementos.append(
        Paragraph(
            "Distribución de Costos",
            styles["Heading2"]
        )
    )

    elementos.append(Spacer(1, 8))

    tabla = Table([

        ["Concepto", "%"],

        [
            "Materiales",
            f"{resultado.get('porcentaje_materiales', 0)} %"
        ],

        [
            "Cuadrilla",
            f"{resultado.get('porcentaje_cuadrilla', 0)} %"
        ],

        [
            "Grúa",
            f"{resultado.get('porcentaje_grua', 0)} %"
        ],
    ],
        colWidths=[250, 120]
    )

    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)

    elementos.append(Spacer(1, 16))


# =====================================================
# 🔥 RESULTADO FINANCIERO
# =====================================================
def _bloque_resultado(elementos, styles, resultado):

    elementos.append(
        Paragraph(
            "Resultado Financiero",
            styles["Heading2"]
        )
    )

    elementos.append(Spacer(1, 8))

    tabla = Table([

        ["Concepto", "Valor"],

        [
            "Costo total real",
            f"L {resultado.get('costo_total_real', 0):,.2f}"
        ],

        [
            "Precio venta",
            f"L {resultado.get('precio_venta', 0):,.2f}"
        ],

        [
            "Utilidad",
            f"L {resultado.get('utilidad', 0):,.2f}"
        ],

        [
            "Margen",
            f"{resultado.get('margen_pct', 0)} %"
        ],
    ],
        colWidths=[250, 180]
    )

    tabla.setStyle(estilo_tabla())

    elementos.append(tabla)

    elementos.append(Spacer(1, 16))


# =====================================================
# 🔥 EVALUACIÓN EJECUTIVA
# =====================================================
def _bloque_evaluacion(elementos, styles, resultado):

    elementos.append(
        Paragraph(
            "Evaluación Ejecutiva",
            styles["Heading2"]
        )
    )

    elementos.append(Spacer(1, 8))

    margen = resultado.get("margen_pct", 0)

    if margen < 0:

        texto = """
        <b>Proyecto NO rentable.</b><br/><br/>

        El costo total estimado supera el valor de venta
        del proyecto. Se recomienda revisar costos de
        materiales, logística y márgenes de instalación.
        """

    elif margen < 10:

        texto = """
        <b>Proyecto con margen bajo.</b><br/><br/>

        Existe riesgo financiero moderado. Se recomienda
        optimizar costos operativos y logísticos.
        """

    elif margen < 20:

        texto = """
        <b>Proyecto con margen aceptable.</b><br/><br/>

        El proyecto presenta una rentabilidad moderada.
        """

    else:

        texto = """
        <b>Proyecto rentable.</b><br/><br/>

        El análisis financiero muestra un margen saludable.
        """

    elementos.append(
        Paragraph(
            texto,
            styles["BodyText"]
        )
    )


# =====================================================
# 🔥 PDF FINAL
# =====================================================
def generar_pdf_costos_proyecto(

    resultado,

    df_materiales_costos=None,

    ruta="costos_proyecto.pdf"
):

    doc = SimpleDocTemplate(
        ruta,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    elementos = []

    # =================================================
    # TÍTULO
    # =================================================
    elementos.append(
        Paragraph(
            "ANÁLISIS FINANCIERO DEL PROYECTO",
            styles["Title"]
        )
    )

    elementos.append(Spacer(1, 18))

    # =================================================
    # KPIs
    # =================================================
    _bloque_kpis(
        elementos,
        resultado
    )

    # =================================================
    # DISTRIBUCIÓN
    # =================================================
    _bloque_distribucion(
        elementos,
        styles,
        resultado
    )

    # =================================================
    # GANTT
    # =================================================
    _bloque_gantt(
        elementos,
        styles,
        resultado
    )

    # =================================================
    # RESULTADO
    # =================================================
    _bloque_resultado(
        elementos,
        styles,
        resultado
    )

    # =================================================
    # EVALUACIÓN
    # =================================================
    _bloque_evaluacion(
        elementos,
        styles,
        resultado
    )

    # =================================================
    # BUILD
    # =================================================
    doc.build(elementos)

    return ruta
