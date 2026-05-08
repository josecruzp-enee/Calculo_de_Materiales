# -*- coding: utf-8 -*-

from io import BytesIO

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors

from reportlab.pdfgen import canvas

from reportlab.platypus import Table, TableStyle

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Doughnut
from reportlab.graphics import renderPDF

from reportlab.lib.utils import ImageReader

import math


# =========================================================
# HELPERS
# =========================================================

def money(v):
    return f"L {v:,.2f}"


def rect_round(c, x, y, w, h,
               radius=10,
               fill="#FFFFFF",
               stroke="#D9E2EC"):

    c.setStrokeColor(colors.HexColor(stroke))
    c.setFillColor(colors.HexColor(fill))

    c.roundRect(
        x,
        y,
        w,
        h,
        radius,
        fill=1,
        stroke=1
    )


def titulo_panel(c, x, y, texto):

    c.setFont("Helvetica-Bold", 12)

    c.setFillColor(colors.HexColor("#0B3B63"))

    c.drawString(x, y, texto)


# =========================================================
# KPI CARD
# =========================================================

def draw_kpi_card(
    c,
    x,
    y,
    w,
    h,
    titulo,
    valor
):

    rect_round(
        c,
        x,
        y,
        w,
        h,
        radius=8,
        fill="#FFFFFF"
    )

    c.setFillColor(colors.HexColor("#4A5568"))

    c.setFont("Helvetica", 8)

    c.drawString(
        x + 12,
        y + h - 18,
        titulo
    )

    c.setFillColor(colors.HexColor("#0B3B63"))

    c.setFont("Helvetica-Bold", 18)

    c.drawString(
        x + 12,
        y + 18,
        valor
    )


# =========================================================
# DONUT CHART
# =========================================================

def draw_donut_chart(c, x, y, data_dict):

    d = Drawing(220, 180)

    donut = Doughnut()

    donut.x = 20

    donut.y = 10

    donut.width = 140

    donut.height = 140

    donut.data = list(data_dict.values())

    donut.labels = list(data_dict.keys())

    donut.slices.strokeWidth = 0.5

    donut.slices[0].fillColor = colors.HexColor("#1565C0")
    donut.slices[1].fillColor = colors.HexColor("#F9A825")
    donut.slices[2].fillColor = colors.HexColor("#43A047")
    donut.slices[3].fillColor = colors.HexColor("#8E24AA")
    donut.slices[4].fillColor = colors.HexColor("#26C6DA")

    d.add(donut)

    renderPDF.draw(
        d,
        c,
        x,
        y
    )


# =========================================================
# GANTT REAL
# =========================================================

def draw_gantt(c, x, y, actividades):

    row_h = 24

    day_w = 12

    left_w = 180

    dur_w = 60

    max_dias = 40

    total_w = left_w + dur_w + max_dias * day_w

    total_h = (len(actividades) + 1) * row_h

    rect_round(
        c,
        x,
        y - total_h,
        total_w,
        total_h,
        radius=6,
        fill="#FFFFFF"
    )

    c.setFillColor(colors.HexColor("#0B3B63"))

    c.rect(
        x,
        y - row_h,
        total_w,
        row_h,
        fill=1,
        stroke=0
    )

    c.setFillColor(colors.white)

    c.setFont("Helvetica-Bold", 8)

    c.drawString(x + 10, y - 16, "ACTIVIDAD")

    c.drawString(x + left_w + 10, y - 16, "DÍAS")

    for d in range(max_dias):

        dx = x + left_w + dur_w + d * day_w

        c.drawCentredString(
            dx + 6,
            y - 16,
            str(d + 1)
        )

    current = 0

    for idx, (nombre, dias) in enumerate(actividades):

        yy = y - row_h * (idx + 2)

        c.setFillColor(colors.black)

        c.setFont("Helvetica", 8)

        c.drawString(x + 8, yy + 8, nombre)

        c.drawCentredString(
            x + left_w + 30,
            yy + 8,
            str(dias)
        )

        bar_x = x + left_w + dur_w + current * day_w

        bar_w = dias * day_w

        c.setFillColor(colors.HexColor("#1565C0"))

        c.rect(
            bar_x,
            yy + 4,
            bar_w,
            14,
            fill=1,
            stroke=0
        )

        current += dias

        c.setStrokeColor(colors.HexColor("#E2E8F0"))

        c.line(
            x,
            yy,
            x + total_w,
            yy
        )


# =========================================================
# MAIN PDF
# =========================================================

def generar_pdf_dashboard_ejecutivo(
    resultado,
    ruta="dashboard_ejecutivo.pdf"
):

    buffer = BytesIO()

    c = canvas.Canvas(
        buffer,
        pagesize=landscape(letter)
    )

    W, H = landscape(letter)

    # =====================================================
    # BACKGROUND
    # =====================================================

    c.setFillColor(colors.HexColor("#F7FAFC"))

    c.rect(0, 0, W, H, fill=1, stroke=0)

    # =====================================================
    # HEADER
    # =====================================================

    c.setFillColor(colors.HexColor("#0B3B63"))

    c.setFont("Helvetica-Bold", 24)

    c.drawString(
        40,
        H - 45,
        "REPORTE EJECUTIVO DEL PROYECTO"
    )

    c.setStrokeColor(colors.HexColor("#CBD5E0"))

    c.line(
        40,
        H - 60,
        W - 40,
        H - 60
    )

    # =====================================================
    # KPI CARDS
    # =====================================================

    venta = resultado.get("precio_venta", 0)

    costo = resultado.get("costo_total_real", 0)

    utilidad = resultado.get("utilidad", 0)

    margen = resultado.get("margen_pct", 0)

    cards_y = H - 150

    draw_kpi_card(
        c,
        40,
        cards_y,
        170,
        80,
        "PRECIO VENTA",
        money(venta)
    )

    draw_kpi_card(
        c,
        225,
        cards_y,
        170,
        80,
        "COSTO REAL",
        money(costo)
    )

    draw_kpi_card(
        c,
        410,
        cards_y,
        170,
        80,
        "UTILIDAD",
        money(utilidad)
    )

    draw_kpi_card(
        c,
        595,
        cards_y,
        170,
        80,
        "MARGEN",
        f"{margen:.2f}%"
    )

    # =====================================================
    # DONUT
    # =====================================================

    titulo_panel(
        c,
        40,
        H - 210,
        "DISTRIBUCIÓN DE COSTOS"
    )

    draw_donut_chart(
        c,
        40,
        H - 450,
        {
            "Materiales": resultado.get("porcentaje_materiales", 0),
            "Cuadrilla": resultado.get("porcentaje_cuadrilla", 0),
            "Grúa": resultado.get("porcentaje_grua", 0),
            "Permisos": 4,
            "Contingencia": 5,
        }
    )

    # =====================================================
    # RESUMEN FINANCIERO
    # =====================================================

    titulo_panel(
        c,
        360,
        H - 210,
        "RESUMEN FINANCIERO"
    )

    data = [

        ["Concepto", "Valor"],

        ["Costo total", money(costo)],

        ["Precio venta", money(venta)],

        ["Utilidad", money(utilidad)],

        ["Margen", f"{margen:.2f}%"],
    ]

    tabla = Table(
        data,
        colWidths=[220, 150]
    )

    tabla.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#0B3B63")),

        ("TEXTCOLOR", (0, 0), (-1, 0),
         colors.white),

        ("FONTNAME", (0, 0), (-1, 0),
         "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1),
         0.5, colors.HexColor("#D9E2EC")),

        ("FONTNAME", (0, 1), (-1, -1),
         "Helvetica"),

        ("FONTSIZE", (0, 0), (-1, -1), 9),

        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),

        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    tabla.wrapOn(c, W, H)

    tabla.drawOn(
        c,
        360,
        H - 420
    )

    # =====================================================
    # GANTT
    # =====================================================

    titulo_panel(
        c,
        40,
        260,
        "CRONOGRAMA DE OBRA"
    )

    actividades = [

        ("Levantamiento", 1),

        ("Agujeros", 4),

        ("Postes", 6),

        ("Retenidas", 4),

        ("Estructuras", 15),

        ("Tendido MT", 2),
    ]

    draw_gantt(
        c,
        40,
        240,
        actividades
    )

    # =====================================================
    # EVALUACIÓN
    # =====================================================

    rect_round(
        c,
        650,
        70,
        160,
        120,
        radius=8,
        fill="#FFFFFF"
    )

    c.setFillColor(colors.HexColor("#0B3B63"))

    c.setFont("Helvetica-Bold", 12)

    c.drawString(
        665,
        165,
        "EVALUACIÓN"
    )

    c.setFont("Helvetica", 9)

    texto = []

    if margen < 0:

        texto = [
            "Proyecto NO rentable",
            "Revisar costos",
            "Optimizar estructuras",
        ]

    elif margen < 10:

        texto = [
            "Margen bajo",
            "Existe riesgo",
            "Optimizar operación",
        ]

    else:

        texto = [
            "Proyecto rentable",
            "Margen saludable",
            "Financieramente viable",
        ]

    yy = 140

    for t in texto:

        c.drawString(
            665,
            yy,
            f"• {t}"
        )

        yy -= 18

    # =====================================================
    # BUILD
    # =====================================================

    c.save()

    pdf = buffer.getvalue()

    buffer.close()

    with open(ruta, "wb") as f:
        f.write(pdf)

    return ruta
