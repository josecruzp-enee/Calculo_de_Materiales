from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors

from exportadores.precios_puntos import procesar_puntos


def generar_seccion_presupuesto(doc, styles):

    elems = [PageBreak()]

    elems.append(Paragraph("<b>9. PRESUPUESTO DETALLADO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    df = procesar_puntos()

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos de cotización.", styles["BodyText"]))
        return elems

    # 🔥 SI NO TIENES CATEGORÍA, CREA UNA
    if "Categoria" not in df.columns:
        df["Categoria"] = "GENERAL"

    categorias = df["Categoria"].unique()

    item_cat = 1

    for cat in categorias:

        elems.append(Paragraph(f"<b>{item_cat}.00 {cat}</b>", styles["Heading3"]))
        elems.append(Spacer(1, 6))

        df_cat = df[df["Categoria"] == cat]

        data = [["ITEM", "DESCRIPCIÓN", "UND", "CANT", "P.U.", "TOTAL"]]

        item_sub = 1
        total_cat = 0

        for _, r in df_cat.iterrows():

            item = f"{item_cat}.{item_sub:02d}"

            pu = r.get("Precio Unitario", 0)
            cant = r.get("Cantidad", 0)
            total = pu * cant

            total_cat += total

            data.append([
                item,
                r.get("Descripción", r.get("Estructura", "")),
                r.get("Unidad", "Und"),
                cant,
                f"L {pu:,.2f}",
                f"L {total:,.2f}",
            ])

            item_sub += 1

        # subtotal
        data.append([
            "",
            f"SUBTOTAL {cat}",
            "",
            "",
            "",
            f"L {total_cat:,.2f}"
        ])

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

            ("ALIGN", (2,1), (-1,-1), "CENTER"),
            ("ALIGN", (4,1), (-1,-1), "RIGHT"),

            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 12))

        item_cat += 1

    # GRAN TOTAL
    total_general = (df["Cantidad"] * df["Precio Unitario"]).sum()

    elems.append(
        Paragraph(f"<b>GRAN TOTAL: L {total_general:,.2f}</b>", styles["Heading2"])
    )

    return elems
