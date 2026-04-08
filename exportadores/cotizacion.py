from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors


def generar_seccion_presupuesto(doc, styles, costos):

    elems = [PageBreak()]

    # =====================================================
    # 🔹 TÍTULO
    # =====================================================
    elems.append(Paragraph("<b>9. PRESUPUESTO DETALLADO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    elems.append(Paragraph(
        "A continuación se presenta el presupuesto correspondiente al suministro e instalación "
        "de las estructuras del proyecto. Los precios incluyen materiales, costos operativos "
        "y utilidad.",
        styles["BodyText"]
    ))
    elems.append(Spacer(1, 12))

    # =====================================================
    # 🔹 DATA DESDE DOMINIO (🔥 NUEVO)
    # =====================================================
    if costos is None:
        raise ValueError("costos es None")

    df = costos.get("df_presupuesto")  # 🔥 CAMBIO CLAVE

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos de cotización.", styles["BodyText"]))
        return elems

    # =====================================================
    # 🔹 NORMALIZACIÓN (mínima)
    # =====================================================
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    required = ["Categoria", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Total"]
    faltantes = [c for c in required if c not in df.columns]

    if faltantes:
        raise ValueError(f"Faltan columnas en df_presupuesto: {faltantes}")

    categorias = df["Categoria"].unique()

    item_cat = 1

    # =====================================================
    # 🔹 TABLA POR CATEGORÍA
    # =====================================================
    for cat in categorias:

        elems.append(Paragraph(f"<b>{item_cat}.00 {cat}</b>", styles["Heading3"]))
        elems.append(Spacer(1, 6))

        df_cat = df[df["Categoria"] == cat]

        data = [["ITEM", "DESCRIPCIÓN", "UND", "CANT", "P.U.", "TOTAL"]]

        item_sub = 1
        total_cat = 0

        for _, r in df_cat.iterrows():

            descripcion = str(r["Descripción"]).strip()
            unidad = str(r["Unidad"])
            cant = float(r["Cantidad"])
            pu = float(r["Precio Unitario"])
            total = float(r["Total"])

            total_cat += total

            data.append([
                f"{item_cat}.{item_sub:02d}",
                descripcion,
                unidad,
                f"{cant:,.2f}",
                f"L {pu:,.2f}",
                f"L {total:,.2f}",
            ])

            item_sub += 1

        # 🔹 SUBTOTAL
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
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (5, 1), (-1, -1), "RIGHT"),

            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 12))

        item_cat += 1

    # =====================================================
    # 🔹 TOTAL GENERAL
    # =====================================================
    total_general = float(df["Total"].sum())

    elems.append(Spacer(1, 10))
    elems.append(
        Paragraph(
            f"<b>TOTAL GENERAL DEL PROYECTO: L {total_general:,.2f}</b>",
            styles["Heading2"]
        )
    )

    elems.append(Spacer(1, 10))

    # =====================================================
    # 🔹 NOTA FORMAL
    # =====================================================
    elems.append(
        Paragraph(
            "<font size=8><i>"
            "Nota: Este presupuesto incluye suministro de materiales, costos operativos "
            "y utilidad. Los precios están sujetos a variaciones según condiciones del mercado, "
            "ubicación del proyecto y disponibilidad de materiales."
            "</i></font>",
            styles["Normal"]
        )
    )

    return elems
