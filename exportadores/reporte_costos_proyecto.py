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


styles = getSampleStyleSheet()


# =====================================================
# ESTILO KPI
# =====================================================
def _estilo_kpi(tabla):

    tabla.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor("#0B3B63")),

        ("TEXTCOLOR", (0, 0), (-1, -1),
         colors.white),

        ("FONTNAME", (0, 0), (-1, -1),
         "Helvetica-Bold"),

        ("FONTSIZE", (0, 0), (-1, -1),
         16),

        ("ALIGN", (0, 0), (-1, -1),
         "CENTER"),

        ("VALIGN", (0, 0), (-1, -1),
         "MIDDLE"),

        ("BOTTOMPADDING", (0, 0), (-1, -1),
         14),

        ("TOPPADDING", (0, 0), (-1, -1),
         14),

        ("BOX", (0, 0), (-1, -1),
         1, colors.HexColor("#0B3B63")),
    ]))


# =====================================================
# KPI PRINCIPALES
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
        colWidths=[135, 135, 135, 135],
        rowHeights=[75]
    )

    _estilo_kpi(tabla)

    elementos.append(tabla)

    elementos.append(Spacer(1, 22))


# =====================================================
# TABLA DISTRIBUCIÓN
# =====================================================
def _tabla_distribucion(resultado):

    tabla = Table([

        ["Distribución", "%"],

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
        colWidths=[180, 90]
    )

    tabla.setStyle(estilo_tabla())

    return tabla


# =====================================================
# TABLA RESULTADO
# =====================================================
def _tabla_resultado(resultado):

    tabla = Table([

        ["Resultado", "Valor"],

        [
            "Costo total",
            f"L {resultado.get('costo_total_real', 0):,.2f}"
        ],

        [
            "Venta",
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
        colWidths=[180, 120]
    )

    tabla.setStyle(estilo_tabla())

    return tabla


# =====================================================
# GANTT VISUAL REAL
# =====================================================
def _bloque_gantt(elementos, resultado):

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

        (
            "Agujeros",
            math.ceil((num_postes + num_retenidas) / 20)
        ),

        (
            "Postes",
            math.ceil(num_postes / 8)
        ),

        (
            "Retenidas",
            math.ceil(num_retenidas / 8)
        ),

        (
            "Estructuras",
            math.ceil(total_estructuras / 8)
        ),

        (
            "Tendido MT",
            math.ceil(long_prim / 500)
        ),
    ]

    max_dias = 25

    encabezado = [
        "Actividad",
        "Días"
    ] + [str(i) for i in range(1, max_dias + 1)]

    data = [encabezado]

    inicio = 1

    for nombre, dias in actividades:

        fila = [
            nombre,
            str(dias)
        ]

        for d in range(1, max_dias + 1):

            if inicio <= d < inicio + dias:
                fila.append("")
            else:
                fila.append("")

        data.append(fila)

        inicio += dias

    col_widths = [150, 45] + [10] * max_dias

    tabla = Table(
        data,
        colWidths=col_widths,
        rowHeights=22
    )

    style = [

        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#0B3B63")),

        ("TEXTCOLOR", (0, 0), (-1, 0),
         colors.white),

        ("FONTNAME", (0, 0), (-1, 0),
         "Helvetica-Bold"),

        ("FONTSIZE", (0, 0), (-1, 0),
         7),

        ("ALIGN", (0, 0), (-1, -1),
         "CENTER"),

        ("GRID", (0, 0), (-1, -1),
         0.4, colors.HexColor("#D9E2EC")),

        ("VALIGN", (0, 0), (-1, -1),
         "MIDDLE"),
    ]

    inicio = 1

    for fila_idx, (_, dias) in enumerate(
        actividades,
        start=1
    ):

        col_inicio = 2 + inicio - 1

        col_fin = col_inicio + dias - 1

        style.append(

            (
                "BACKGROUND",
                (col_inicio, fila_idx),
                (col_fin, fila_idx),
                colors.HexColor("#1565C0")
            )
        )

        inicio += dias

    tabla.setStyle(TableStyle(style))

    elementos.append(tabla)

    elementos.append(Spacer(1, 22))


# =====================================================
# EVALUACIÓN EJECUTIVA
# =====================================================
def _bloque_evaluacion(elementos, resultado):

    margen = resultado.get("margen_pct", 0)

    if margen < 0:

        texto = """
        <b>Proyecto NO rentable.</b><br/><br/>
        El costo total estimado supera el valor de venta
        del proyecto.
        """

    elif margen < 10:

        texto = """
        <b>Proyecto con margen bajo.</b><br/><br/>
        Existe riesgo financiero moderado.
        """

    elif margen < 20:

        texto = """
        <b>Proyecto con margen aceptable.</b><br/><br/>
        El proyecto presenta rentabilidad moderada.
        """

    else:

        texto = """
        <b>Proyecto rentable.</b><br/><br/>
        El análisis financiero muestra un margen saludable.
        """

    tabla_eval = Table(
        [[
            Paragraph(
                texto,
                styles["BodyText"]
            )
        ]],
        colWidths=[540]
    )

    tabla_eval.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor("#F4F6F8")),

        ("BOX", (0, 0), (-1, -1),
         1, colors.HexColor("#D9E2EC")),

        ("LEFTPADDING", (0, 0), (-1, -1), 14),

        ("RIGHTPADDING", (0, 0), (-1, -1), 14),

        ("TOPPADDING", (0, 0), (-1, -1), 12),

        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    elementos.append(
        Paragraph(
            "Evaluación Ejecutiva",
            styles["Heading2"]
        )
    )

    elementos.append(Spacer(1, 8))

    elementos.append(tabla_eval)

    elementos.append(Spacer(1, 20))


# =====================================================
# BLOQUE COMPLETO
# =====================================================
def construir_bloque_costos(
    elementos,
    styles,
    resultado,
    df_materiales_costos=None
):

    if not resultado:
        return

    # KPI
    _bloque_kpis(
        elementos,
        resultado
    )

    # DISTRIBUCIÓN + RESULTADO
    tabla_izq = _tabla_distribucion(
        resultado
    )

    tabla_der = _tabla_resultado(
        resultado
    )

    fila_financiera = Table([[
        tabla_izq,
        tabla_der
    ]])

    fila_financiera.setStyle(TableStyle([

        ("VALIGN", (0, 0), (-1, -1),
         "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 0),

        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
    ]))

    elementos.append(fila_financiera)

    elementos.append(Spacer(1, 22))

    # GANTT
    _bloque_gantt(
        elementos,
        resultado
    )

    # EVALUACIÓN
    _bloque_evaluacion(
        elementos,
        resultado
    )


# =====================================================
# PDF FINAL
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

    elementos = []

    elementos.append(
        Paragraph(
            "ANÁLISIS FINANCIERO DEL PROYECTO",
            styles["Title"]
        )
    )

    elementos.append(Spacer(1, 20))

    construir_bloque_costos(
        elementos,
        styles,
        resultado,
        df_materiales_costos
    )

    doc.build(elementos)

    return ruta
