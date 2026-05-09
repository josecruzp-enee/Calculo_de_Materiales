# -*- coding: utf-8 -*-
#exportadores/reporte_costos_proyecto.py
from __future__ import annotations

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus.tables import TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


styles = getSampleStyleSheet()


# =====================================================
# FORMATOS
# =====================================================
def _fmt_lps(valor) -> str:
    try:
        return f"L {float(valor):,.2f}"
    except Exception:
        return "L 0.00"


def _fmt_lps_0(valor) -> str:
    try:
        return f"L {float(valor):,.0f}"
    except Exception:
        return "L 0"


def _fmt_pct(valor) -> str:
    try:
        return f"{float(valor):,.2f} %"
    except Exception:
        return "0.00 %"


def _to_float(valor, default=0.0) -> float:
    try:
        if valor is None:
            return default

        if isinstance(valor, str):
            valor = (
                valor.replace("L", "")
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

        return float(valor)

    except Exception:
        return default


# =====================================================
# COLORES
# =====================================================
def _color_utilidad(valor):
    valor = _to_float(valor)

    if valor < 0:
        return colors.HexColor("#8B1E1E")

    return colors.HexColor("#1B5E20")


def _color_estado(nivel):
    nivel = str(nivel or "").lower().strip()

    if nivel == "critico":
        return colors.HexColor("#8B1E1E")

    if nivel == "advertencia":
        return colors.HexColor("#B26A00")

    if nivel == "aceptable":
        return colors.HexColor("#0B3B63")

    if nivel == "bueno":
        return colors.HexColor("#1B5E20")

    return colors.HexColor("#0B3B63")


# =====================================================
# ESTILOS
# =====================================================
def _estilos():

    return {
        "titulo": ParagraphStyle(
            "titulo_costos",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0B3B63"),
            spaceAfter=12,
        ),

        "subtitulo": ParagraphStyle(
            "subtitulo_costos",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#0B3B63"),
            spaceBefore=4,
            spaceAfter=7,
        ),

        "kpi_label": ParagraphStyle(
            "kpi_label",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),

        "kpi_valor": ParagraphStyle(
            "kpi_valor",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),

        "evaluacion_titulo": ParagraphStyle(
            "evaluacion_titulo",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.white,
        ),

        "evaluacion_texto": ParagraphStyle(
            "evaluacion_texto",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#263238"),
        ),

        "nota": ParagraphStyle(
            "nota_costos",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#455A64"),
        ),
    }


# =====================================================
# KPI PRINCIPALES
# =====================================================
def _bloque_kpis(elementos, resultado):

    st = _estilos()

    venta = resultado.get("precio_venta", 0)
    costo = resultado.get("costo_total_real", 0)
    utilidad = resultado.get("utilidad", 0)
    margen = resultado.get("margen_pct", 0)

    color_resultado = _color_utilidad(utilidad)

    data = [[
        [
            Paragraph("VENTA", st["kpi_label"]),
            Paragraph(_fmt_lps_0(venta), st["kpi_valor"]),
        ],
        [
            Paragraph("COSTO REAL", st["kpi_label"]),
            Paragraph(_fmt_lps_0(costo), st["kpi_valor"]),
        ],
        [
            Paragraph("UTILIDAD", st["kpi_label"]),
            Paragraph(_fmt_lps_0(utilidad), st["kpi_valor"]),
        ],
        [
            Paragraph("MARGEN", st["kpi_label"]),
            Paragraph(f"{_to_float(margen):,.1f} %", st["kpi_valor"]),
        ],
    ]]

    tabla = Table(
        data,
        colWidths=[132, 132, 132, 132],
        rowHeights=[66],
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#0B3B63")),
        ("BACKGROUND", (2, 0), (3, 0), color_resultado),

        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#0B3B63")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 16))


# =====================================================
# TABLA DE DISTRIBUCIÓN
# =====================================================
def _tabla_distribucion(resultado):

    distribucion = resultado.get("distribucion_costos")

    data = [
        ["Rubro", "Monto", "%"],
    ]

    if isinstance(distribucion, list) and distribucion:
        for item in distribucion:
            data.append([
                str(item.get("rubro", "")),
                _fmt_lps(item.get("monto", 0)),
                _fmt_pct(item.get("porcentaje", 0)),
            ])

    else:
        costo_total = _to_float(resultado.get("costo_total_real", 0))

        rubros = [
            ("Materiales", resultado.get("costo_materiales", 0)),
            ("Cuadrilla", resultado.get("costo_cuadrilla", 0)),
            ("Agujeros", resultado.get("costo_agujeros", 0)),
            ("Grúa", resultado.get("costo_grua", 0)),
            ("Flete", resultado.get("costo_flete", 0)),
            ("Ingeniería", resultado.get("costo_ingenieria", 0)),
            ("Contingencia", resultado.get("contingencia", 0)),
        ]

        for rubro, monto in rubros:
            monto = _to_float(monto)

            if monto <= 0:
                continue

            porcentaje = (
                monto / costo_total * 100
            ) if costo_total else 0

            data.append([
                rubro,
                _fmt_lps(monto),
                _fmt_pct(porcentaje),
            ])

    tabla = Table(
        data,
        colWidths=[118, 92, 55],
        repeatRows=1,
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.3),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#263238")),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.30, colors.HexColor("#D9E2EC")),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F7F9FB"),
        ]),

        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return tabla


# =====================================================
# TABLA RESULTADO
# =====================================================
def _tabla_resultado(resultado):

    data = [
        ["Resultado", "Valor"],
        ["Subtotal costos", _fmt_lps(resultado.get("subtotal_costos", 0))],
        ["Contingencia", _fmt_lps(resultado.get("contingencia", 0))],
        ["Costo total real", _fmt_lps(resultado.get("costo_total_real", 0))],
        ["Venta", _fmt_lps(resultado.get("precio_venta", 0))],
        ["Utilidad", _fmt_lps(resultado.get("utilidad", 0))],
        ["Margen", _fmt_pct(resultado.get("margen_pct", 0))],
    ]

    tabla = Table(
        data,
        colWidths=[142, 112],
        repeatRows=1,
    )

    color_resultado = _color_utilidad(
        resultado.get("utilidad", 0)
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.3),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#263238")),

        ("FONTNAME", (0, 5), (-1, 6), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 5), (-1, 6), color_resultado),

        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.30, colors.HexColor("#D9E2EC")),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F7F9FB"),
        ]),

        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return tabla


# =====================================================
# BLOQUE FINANCIERO
# =====================================================
def _bloque_financiero(elementos, resultado):

    st = _estilos()

    elementos.append(
        Paragraph(
            "Resumen financiero interno",
            st["subtitulo"],
        )
    )

    tabla_izq = _tabla_distribucion(resultado)
    tabla_der = _tabla_resultado(resultado)

    fila = Table(
        [[tabla_izq, tabla_der]],
        colWidths=[275, 260],
    )

    fila.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos.append(fila)
    elementos.append(Spacer(1, 15))


# =====================================================
# INDICADORES OPERATIVOS
# =====================================================
def _bloque_indicadores(elementos, resultado):

    st = _estilos()

    elementos.append(
        Paragraph(
            "Indicadores operativos",
            st["subtitulo"],
        )
    )

    data = [
        ["Indicador", "Valor"],
        ["Total estructuras", f"{int(resultado.get('total_estructuras', 0)):,}"],
        ["Postes", f"{int(resultado.get('num_postes', 0)):,}"],
        ["Retenidas", f"{int(resultado.get('num_retenidas', 0)):,}"],
        ["Longitud primario", f"{_to_float(resultado.get('longitud_primario', 0)):,.2f} m"],
        ["Longitud secundario", f"{_to_float(resultado.get('longitud_secundario', 0)):,.2f} m"],
        ["Días estimados", f"{_to_float(resultado.get('dias_totales', 0)):,.0f}"],
        ["Costo por estructura", _fmt_lps(resultado.get("costo_por_estructura", 0))],
        ["Costo por poste", _fmt_lps(resultado.get("costo_por_poste", 0))],
        ["Utilidad diaria", _fmt_lps(resultado.get("utilidad_diaria", 0))],
    ]

    tabla = Table(
        data,
        colWidths=[270, 160],
        repeatRows=1,
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.3),

        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        ("GRID", (0, 0), (-1, -1), 0.30, colors.HexColor("#D9E2EC")),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F7F9FB"),
        ]),

        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 15))


# =====================================================
# CRONOGRAMA
# =====================================================
def _obtener_cronograma(resultado):

    cronograma = resultado.get("cronograma_resumen")

    if isinstance(cronograma, list) and cronograma:
        return cronograma

    dias = int(_to_float(resultado.get("dias_totales", 1), 1))

    return [
        {
            "actividad": "Ejecución del proyecto",
            "duracion_dias": dias,
            "inicio": 1,
            "fin": dias,
        }
    ]


def _bloque_cronograma(elementos, resultado):

    st = _estilos()

    elementos.append(
        Paragraph(
            "Cronograma estimado",
            st["subtitulo"],
        )
    )

    cronograma = _obtener_cronograma(resultado)

    max_dia = 1

    for item in cronograma:
        fin = item.get("fin")

        if fin:
            max_dia = max(max_dia, int(fin))

    max_visible = min(max_dia, 45)

    encabezado = [
        "Actividad",
        "Dur.",
        "Inicio",
        "Fin",
    ] + [str(i) for i in range(1, max_visible + 1)]

    data = [encabezado]

    for item in cronograma:
        actividad = item.get("actividad", "")
        duracion = item.get("duracion_dias", 0)
        inicio = item.get("inicio")
        fin = item.get("fin")

        fila = [
            actividad,
            str(duracion or 0),
            f"Día {inicio}" if inicio else "—",
            f"Día {fin}" if fin else "—",
        ]

        for _ in range(1, max_visible + 1):
            fila.append("")

        data.append(fila)

    ancho_dia = 6.2 if max_visible > 35 else 7.8

    tabla = Table(
        data,
        colWidths=[110, 28, 38, 38] + [ancho_dia] * max_visible,
        rowHeights=16,
        repeatRows=1,
    )

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 5.2),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 5.2),

        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2EC")),

        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]

    for fila_idx, item in enumerate(cronograma, start=1):
        inicio = item.get("inicio")
        fin = item.get("fin")

        if not inicio or not fin:
            continue

        inicio = int(inicio)
        fin = int(fin)

        if inicio > max_visible:
            continue

        fin_visible = min(fin, max_visible)

        col_inicio = 4 + inicio - 1
        col_fin = 4 + fin_visible - 1

        style.append((
            "BACKGROUND",
            (col_inicio, fila_idx),
            (col_fin, fila_idx),
            colors.HexColor("#1565C0"),
        ))

    tabla.setStyle(TableStyle(style))

    elementos.append(tabla)

    if max_dia > max_visible:
        elementos.append(Spacer(1, 4))
        elementos.append(
            Paragraph(
                f"Nota: el cronograma tiene {max_dia} días. "
                f"Se muestran los primeros {max_visible} días.",
                st["nota"],
            )
        )

    elementos.append(Spacer(1, 15))


# =====================================================
# EVALUACIÓN EJECUTIVA
# =====================================================
def _bloque_evaluacion(elementos, resultado):

    st = _estilos()

    estado = resultado.get("estado_proyecto")
    mensaje = resultado.get("mensaje_evaluacion")
    nivel = resultado.get("nivel_evaluacion")

    if not estado:
        utilidad = _to_float(resultado.get("utilidad", 0))
        margen = _to_float(resultado.get("margen_pct", 0))

        if utilidad < 0:
            estado = "NO RENTABLE"
            mensaje = "El costo total estimado supera el valor de venta del proyecto."
            nivel = "critico"

        elif margen < 10:
            estado = "RENTABILIDAD BAJA"
            mensaje = "El proyecto tiene utilidad positiva, pero el margen es bajo."
            nivel = "advertencia"

        elif margen < 20:
            estado = "RENTABLE"
            mensaje = "El proyecto presenta utilidad positiva con margen aceptable."
            nivel = "aceptable"

        else:
            estado = "RENTABLE ALTO"
            mensaje = "El proyecto presenta una rentabilidad favorable."
            nivel = "bueno"

    color = _color_estado(nivel)

    utilidad = resultado.get("utilidad", 0)
    margen = resultado.get("margen_pct", 0)

    texto = (
        f"{mensaje}<br/><br/>"
        f"<b>Utilidad estimada:</b> {_fmt_lps(utilidad)}<br/>"
        f"<b>Margen estimado:</b> {_fmt_pct(margen)}"
    )

    tabla = Table(
        [
            [
                Paragraph(
                    f"Evaluación ejecutiva: {estado}",
                    st["evaluacion_titulo"],
                )
            ],
            [
                Paragraph(
                    texto,
                    st["evaluacion_texto"],
                )
            ],
        ],
        colWidths=[535],
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F6F8")),

        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#D9E2EC")),

        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))


# =====================================================
# BLOQUE COMPLETO
# =====================================================
def construir_bloque_costos(
    elementos,
    styles_param,
    resultado,
    df_materiales_costos=None,
):

    if not resultado:
        return

    _bloque_kpis(elementos, resultado)

    _bloque_financiero(elementos, resultado)

    _bloque_indicadores(elementos, resultado)

    _bloque_cronograma(elementos, resultado)

    _bloque_evaluacion(elementos, resultado)


# =====================================================
# PDF FINAL INDIVIDUAL
# =====================================================
def generar_pdf_costos_proyecto(
    resultado,
    df_materiales_costos=None,
    ruta="costos_proyecto.pdf",
):

    doc = SimpleDocTemplate(
        ruta,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elementos = []

    st = _estilos()

    elementos.append(
        Paragraph(
            "ANÁLISIS FINANCIERO INTERNO DEL PROYECTO",
            st["titulo"],
        )
    )

    construir_bloque_costos(
        elementos=elementos,
        styles_param=styles,
        resultado=resultado,
        df_materiales_costos=df_materiales_costos,
    )

    doc.build(elementos)

    return ruta
