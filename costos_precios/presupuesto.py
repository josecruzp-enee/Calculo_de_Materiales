# -*- coding: utf-8 -*-
"""
exportadores/presupuesto.py

Sección de presupuesto basada en resultados del dominio de costos.
✔ Solo renderiza
❌ No calcula
❌ No transforma lógica de negocio
"""

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
import pandas as pd


# ==========================================================
# VALIDADOR CONTRATO
# ==========================================================
def _validar_df_presupuesto(df: pd.DataFrame) -> pd.DataFrame:

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("df_presupuesto inválido o vacío")

    columnas_req = {
        "Categoria",
        "Descripción",
        "Unidad",
        "Cantidad",
        "Precio Unitario",
        "Total",
    }

    if not columnas_req.issubset(df.columns):
        raise ValueError(f"df_presupuesto debe contener {columnas_req}")

    df = df.copy()

    df.columns = [str(c).strip() for c in df.columns]

    # tipos
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce").fillna(0)
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)

    # limpiar basura
    df = df[df["Cantidad"] > 0]

    if df.empty:
        raise ValueError("df_presupuesto sin datos válidos")

    return df


# ==========================================================
# SECCIÓN PRESUPUESTO (CONTRATO LIMPIO)
# ==========================================================
def generar_seccion_presupuesto_costos(doc, styles, df_presupuesto: pd.DataFrame):

    elems = [PageBreak()]

    elems.append(Paragraph("<b>9. PRESUPUESTO DETALLADO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    # =====================================================
    # VALIDACIÓN CONTRATO
    # =====================================================
    try:
        df = _validar_df_presupuesto(df_presupuesto)
    except Exception:
        elems.append(Paragraph("No hay datos de presupuesto.", styles["BodyText"]))
        return elems

    # =====================================================
    # ORDEN
    # =====================================================
    df = df.sort_values(by=["Categoria", "Descripción"]).reset_index(drop=True)

    categorias = df["Categoria"].dropna().unique()

    if len(categorias) == 0:
        elems.append(Paragraph("No hay categorías válidas.", styles["BodyText"]))
        return elems

    item_cat = 1
    total_general = 0.0

    # =====================================================
    # LOOP
    # =====================================================
    for cat in categorias:

        df_cat = df[df["Categoria"] == cat]

        if df_cat.empty:
            continue

        elems.append(Paragraph(f"<b>{item_cat}.00 {cat}</b>", styles["Heading3"]))
        elems.append(Spacer(1, 6))

        data = [["ITEM", "DESCRIPCIÓN", "UND", "CANT", "P.U.", "TOTAL"]]

        total_cat = 0.0

        for i, r in enumerate(df_cat.itertuples(index=False), start=1):

            item = f"{item_cat}.{i:02d}"

            total_cat += float(r.Total)

            data.append([
                item,
                str(r.Descripción),
                str(r.Unidad),
                f"{float(r.Cantidad):,.2f}",
                f"L {float(r._asdict()['Precio Unitario']):,.2f}",
                f"L {float(r.Total):,.2f}",
            ])

        # subtotal
        data.append([
            "",
            f"SUBTOTAL {cat}",
            "",
            "",
            "",
            f"L {total_cat:,.2f}"
        ])

        total_general += total_cat

        # tabla
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

            ("ALIGN", (2, 1), (3, -1), "CENTER"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),

            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 12))

        item_cat += 1

    # =====================================================
    # TOTAL GENERAL
    # =====================================================
    elems.append(
        Paragraph(
            f"<b>GRAN TOTAL: L {total_general:,.2f}</b>",
            styles["Heading2"]
        )
    )

    return elems
