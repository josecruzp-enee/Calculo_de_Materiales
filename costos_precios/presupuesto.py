# -*- coding: utf-8 -*-
"""
costo_precio/presupuesto.py

Sección de presupuesto basada en resultados del dominio de costos.
NO accede a fuentes externas.
"""

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors


# ==========================================================
# SECCIÓN PRESUPUESTO
# ==========================================================
def generar_seccion_presupuesto_costos(doc, styles, resultados_costos):
    """
    INPUT:
        resultados_costos: dict de orquestador_costos

    Espera:
        resultados_costos["df_costos_por_punto"]
        resultados_costos["df_costos_materiales"] (opcional)
    """

    elems = [PageBreak()]

    elems.append(Paragraph("<b>9. PRESUPUESTO DETALLADO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    # ------------------------------------------------------
    # DATA PRINCIPAL
    # ------------------------------------------------------
    df = resultados_costos.get("df_costos_por_punto")

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos de costos por punto.", styles["BodyText"]))
        return elems

    df = df.copy()

    # ------------------------------------------------------
    # NORMALIZACIÓN
    # ------------------------------------------------------
    if "Categoria" not in df.columns:
        df["Categoria"] = "ESTRUCTURAS"

    if "Descripción" not in df.columns:
        df["Descripción"] = df.get("Estructura", "ITEM")

    if "Unidad" not in df.columns:
        df["Unidad"] = "Und"

    if "Precio Unitario" not in df.columns:
        df["Precio Unitario"] = 0.0

    if "Cantidad" not in df.columns:
        df["Cantidad"] = 0.0

    # ------------------------------------------------------
    # AGRUPACIÓN POR CATEGORÍA
    # ------------------------------------------------------
    categorias = df["Categoria"].unique()

    item_cat = 1
    total_general = 0

    for cat in categorias:

        elems.append(Paragraph(f"<b>{item_cat}.00 {cat}</b>", styles["Heading3"]))
        elems.append(Spacer(1, 6))

        df_cat = df[df["Categoria"] == cat]

        data = [["ITEM", "DESCRIPCIÓN", "UND", "CANT", "P.U.", "TOTAL"]]

        item_sub = 1
        total_cat = 0

        for _, r in df_cat.iterrows():

            item = f"{item_cat}.{item_sub:02d}"

            pu = float(r.get("Precio Unitario", 0) or 0)
            cant = float(r.get("Cantidad", 0) or 0)
            total = pu * cant

            total_cat += total

            data.append([
                item,
                str(r.get("Descripción")),
                str(r.get("Unidad")),
                f"{cant:,.2f}",
                f"L {pu:,.2f}",
                f"L {total:,.2f}",
            ])

            item_sub += 1

        # subtotal categoría
        data.append([
            "",
            f"SUBTOTAL {cat}",
            "",
            "",
            "",
            f"L {total_cat:,.2f}"
        ])

        total_general += total_cat

        # --------------------------------------------------
        # TABLA
        # --------------------------------------------------
        tabla = Table(
            data,
            colWidths=[
                doc.width * 0.10,
                doc.width * 0.45,
                doc.width * 0.10,
                doc.width * 0.10,
                doc.width * 0.12,
                doc.width * 0.13,
            ]
        )

        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

            ("GRID", (0,0), (-1,-1), 0.5, colors.black),

            ("ALIGN", (2,1), (3,-1), "CENTER"),
            ("ALIGN", (4,1), (-1,-1), "RIGHT"),

            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 12))

        item_cat += 1

    # ------------------------------------------------------
    # TOTAL GENERAL
    # ------------------------------------------------------
    elems.append(
        Paragraph(f"<b>GRAN TOTAL: L {total_general:,.2f}</b>", styles["Heading2"])
    )

    return elems
