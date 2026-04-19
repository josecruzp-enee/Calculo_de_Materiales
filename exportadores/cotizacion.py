# =========================================================
# HELPERS VISUALES
# =========================================================
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib import colors


def _agregar_notas(elems, styles):

    elems.append(Paragraph("<b>Notas:</b>", styles["Normal"]))

    elems.append(Paragraph(
        "- Los precios incluyen el suministro e instalación de los materiales y equipos descritos.",
        styles["Normal"]
    ))

    elems.append(Paragraph(
        "- La gestión de permisos ante ENEE se encuentra incluida dentro del alcance del proyecto.",
        styles["Normal"]
    ))

    elems.append(Paragraph(
        "- La presente oferta tiene una validez de 30 días calendario a partir de la fecha de emisión.",
        styles["Normal"]
    ))


def _estilo_cotizacion(tabla):
    """
    Ajustes específicos SOLO para cotización
    (encima de estilo_tabla)
    """

    from reportlab.platypus import TableStyle

    tabla.setStyle(TableStyle([

        # 🔹 SUBTOTAL (fila -3)
        ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#D9E1F2")),
        ("FONTNAME", (0, -3), (-1, -3), "Helvetica-Bold"),

        # 🔹 TOTAL FINAL (fila -1)
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),

    ]))


# =========================================================
# COTIZACIÓN FINAL (MODULAR)
# =========================================================
from reportlab.platypus import Table
from exportadores.pdf_base import estilo_tabla


def generar_seccion_cotizacion_final(doc, styles, df_precios):

    elems = []

    if df_precios is None or df_precios.empty:
        elems.append(Paragraph("SIN DATOS PARA COTIZACIÓN", styles["Normal"]))
        return elems

    # =====================================================
    # BASE
    # =====================================================
    if "Subtotal" in df_precios.columns:
        total_base = float(df_precios["Subtotal"].sum())
    else:
        total_base = float(df_precios["Precio Total"].sum())

    # =====================================================
    # CÁLCULOS
    # =====================================================
    ingenieria = total_base * 0.15
    subtotal = total_base + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    # =====================================================
    # DATA
    # =====================================================
    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación", f"L {total_base:,.2f}"],
        ["Gastos de Ingeniería (15%)", f"L {ingenieria:,.2f}"],
        ["SUBTOTAL", f"L {subtotal:,.2f}"],
        ["ISV (15%)", f"L {isv:,.2f}"],
        ["TOTAL PROYECTO", f"L {total_final:,.2f}"],
    ]

    tabla = Table(
        data,
        colWidths=[doc.width * 0.7, doc.width * 0.3],
        repeatRows=1
    )

    # 🔥 ESTILO BASE (GLOBAL)
    tabla.setStyle(estilo_tabla())

    # 🔥 AJUSTE SOLO PARA COTIZACIÓN
    _estilo_cotizacion(tabla)

    elems.append(tabla)

    # 🔥 NOTAS
    _agregar_notas(elems, styles)

    return elems
