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
    # 🔹 DATA DESDE MOTOR
    # =====================================================
    if costos is None:
        raise ValueError("costos es None")

    df = costos.get("df_costos_por_punto")

    if df is None or df.empty:
        elems.append(Paragraph("No hay datos de cotización.", styles["BodyText"]))
        return elems

    # =====================================================
    # 🔹 NORMALIZACIÓN
    # =====================================================
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Validaciones críticas
    required = ["codigodeestructura", "Cantidad", "Precio Unitario"]
    faltantes = [c for c in required if c not in df.columns]

    if faltantes:
        raise ValueError(f"Faltan columnas en df_costos_por_punto: {faltantes}")

    if "Subtotal Precio" not in df.columns:
        df["Subtotal Precio"] = df["Cantidad"] * df["Precio Unitario"]

    if "Categoria" not in df.columns:
        df["Categoria"] = "SUMINISTRO E INSTALACIÓN DE ESTRUCTURAS"

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

            estructura = str(r["codigodeestructura"]).strip()

            cant = float(r["Cantidad"] or 0)
            pu = float(r["Precio Unitario"] or 0)

            # 🔥 VALIDACIÓN FUERTE
            if pu <= 0:
                raise ValueError(f"Estructura sin precio válido: {estructura}")

            if "Subtotal Precio" in r:
                total = float(r["Subtotal Precio"])
            else:
                total = pu * cant

            total_cat += total

            descripcion = (
                f"Suministro e instalación de {int(cant)} "
                f"estructura tipo {estructura}"
            )

            data.append([
                f"{item_cat}.{item_sub:02d}",
                descripcion,
                "Und",
                f"{int(cant)}",
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
            ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

            ("GRID", (0,0), (-1,-1), 0.5, colors.black),

            ("ALIGN", (2,1), (-1,-1), "CENTER"),
            ("ALIGN", (4,1), (-1,-1), "RIGHT"),
            ("ALIGN", (5,1), (-1,-1), "RIGHT"),

            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 12))

        item_cat += 1

    # =====================================================
    # 🔹 TOTAL GENERAL
    # =====================================================
    total_general = float(df["Subtotal Precio"].sum())

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
