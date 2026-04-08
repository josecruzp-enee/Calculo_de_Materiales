# -*- coding: utf-8 -*-
"""
reportes/presupuesto_estructuras.py

Genera tabla PDF de estructuras usando costos ya calculados.
NO calcula costos.
"""

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors


def generar_tabla_presupuesto(doc, styles, df_estructuras, df_costos_estructuras):

    elems = []

    # -----------------------------------------------------
    # VALIDACIÓN
    # -----------------------------------------------------
    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No hay datos de estructuras.", styles["BodyText"]))
        return elems

    if df_costos_estructuras is None or df_costos_estructuras.empty:
        raise ValueError("df_costos_estructuras vacío")

    # -----------------------------------------------------
    # NORMALIZAR
    # -----------------------------------------------------
    df_estructuras.columns = [str(c).strip().upper() for c in df_estructuras.columns]

    col_est = None
    for c in df_estructuras.columns:
        if "ESTRUCT" in c:
            col_est = c
            break

    if col_est is None:
        raise KeyError("No se encontró columna de estructura")

    df_estructuras = df_estructuras.rename(columns={col_est: "codigodeestructura"})

    # -----------------------------------------------------
    # PREPARAR COSTOS
    # -----------------------------------------------------
    df_costos_estructuras["codigodeestructura"] = (
        df_costos_estructuras["codigodeestructura"].astype(str).str.strip()
    )

    if "Precio Unitario" not in df_costos_estructuras.columns:
        raise ValueError("df_costos_estructuras debe tener 'Precio Unitario'")

    # -----------------------------------------------------
    # MERGE
    # -----------------------------------------------------
    df = df_estructuras.merge(
        df_costos_estructuras,
        on="codigodeestructura",
        how="left"
    )

    # -----------------------------------------------------
    # TABLA
    # -----------------------------------------------------
    data = [["ITEM", "DESCRIPCIÓN", "CANT", "P.U.", "TOTAL"]]

    total_general = 0
    item = 1

    for _, row in df.iterrows():

        estructura = row["codigodeestructura"]
        cant = float(row.get("Cantidad", 1) or 0)

        pu = float(row.get("Precio Unitario", 0))
        total = pu * cant

        total_general += total

        descripcion = (
            f"Instalación y suministro de {int(cant)} "
            f"estructura(s) tipo {estructura}"
        )

        data.append([
            f"2.{item:02d}",
            descripcion,
            f"{int(cant)}",
            f"L {pu:,.2f}",
            f"L {total:,.2f}"
        ])

        item += 1

    data.append(["", "TOTAL GENERAL", "", "", f"L {total_general:,.2f}"])

    # -----------------------------------------------------
    # FORMATO
    # -----------------------------------------------------
    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.10,
            doc.width * 0.45,
            doc.width * 0.10,
            doc.width * 0.15,
            doc.width * 0.20,
        ]
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("ALIGN", (3,1), (-1,-1), "RIGHT"),
        ("ALIGN", (4,1), (-1,-1), "RIGHT"),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))

    elems.append(Paragraph("<b>2. COSTO DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))
    elems.append(tabla)

    return elems
