from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors


def build_tabla_presupuesto(df, styles):

    story = []

    categorias = df["Categoria"].unique()

    item_categoria = 1

    for cat in categorias:

        df_cat = df[df["Categoria"] == cat]

        # =========================
        # TITULO CATEGORIA
        # =========================
        story.append(
            Paragraph(f"{item_categoria}.00 {cat}", styles["Heading3"])
        )

        data = [
            ["ITEM", "DESCRIPCIÓN", "UNIDAD", "CANTIDAD", "PRECIO UNIT.", "TOTAL"]
        ]

        item_sub = 1

        total_categoria = 0

        for _, row in df_cat.iterrows():

            item = f"{item_categoria}.{item_sub:02d}"

            total = row["Cantidad"] * row["Precio Unitario"]

            total_categoria += total

            data.append([
                item,
                row["Descripción"],
                row["Unidad"],
                row["Cantidad"],
                f"L {row['Precio Unitario']:,.2f}",
                f"L {total:,.2f}",
            ])

            item_sub += 1

        # =========================
        # FILA SUBTOTAL
        # =========================
        data.append([
            "",
            f"SUBTOTAL {cat}",
            "",
            "",
            "",
            f"L {total_categoria:,.2f}"
        ])

        # =========================
        # TABLA
        # =========================
        table = Table(data, repeatRows=1)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),

            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ]))

        story.append(table)
        story.append(Spacer(1, 12))

        item_categoria += 1

    # =========================
    # GRAN TOTAL
    # =========================
    total_general = df["Total"].sum()

    story.append(
        Paragraph(f"<b>GRAN TOTAL: L {total_general:,.2f}</b>", styles["Heading2"])
    )

    return story
