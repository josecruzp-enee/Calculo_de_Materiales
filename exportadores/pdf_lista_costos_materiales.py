# -*- coding: utf-8 -*-
from __future__ import annotations

from io import BytesIO
import pandas as pd

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet


# =========================================================
# 🔧 VALIDACIÓN
# =========================================================
def _validar_df(df: pd.DataFrame):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("DataFrame inválido o vacío")

    columnas = {"Materiales", "Unidad", "Cantidad", "Costo Unitario", "Costo Total"}
    if not columnas.issubset(df.columns):
        raise ValueError(f"Columnas inválidas: {list(df.columns)}")


# =========================================================
# 🎨 ESTILOS
# =========================================================
def _get_styles():
    return getSampleStyleSheet()


# =========================================================
# 🧾 HEADER
# =========================================================
def _build_header(elementos, styles, nombre_proyecto):
    elementos.append(Paragraph("<b>LISTA DE MATERIALES</b>", styles["Title"]))
    elementos.append(Paragraph(f"Proyecto: {nombre_proyecto}", styles["Normal"]))
    elementos.append(Spacer(1, 12))


# =========================================================
# 📊 DATA TABLA
# =========================================================
def _build_data(df: pd.DataFrame):

    data = [["Material", "Unidad", "Cantidad", "P.U.", "Total"]]
    total_general = 0.0

    for _, row in df.iterrows():
        try:
            material = str(row["Materiales"])
            unidad = str(row["Unidad"])
            cantidad = float(row["Cantidad"])
            pu = float(row["Costo Unitario"])
            total = float(row["Costo Total"])
        except Exception:
            continue

        total_general += total

        data.append([
            material,
            unidad,
            f"{cantidad:,.2f}",
            f"L {pu:,.2f}",
            f"L {total:,.2f}",
        ])

    return data, total_general


# =========================================================
# 📐 TABLA
# =========================================================
def _build_table(data, total_general):

    # total final
    data.append(["", "", "", "<b>TOTAL</b>", f"<b>L {total_general:,.2f}</b>"])

    tabla = Table(data, colWidths=[230, 60, 80, 80, 90], repeatRows=1)

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    return tabla


# =========================================================
# 🏗 BUILD PDF
# =========================================================
def _build_pdf(elementos):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    if not pdf or len(pdf) < 100:
        raise ValueError("PDF generado vacío")

    return pdf


# =========================================================
# 🚀 MOTOR PRINCIPAL
# =========================================================
def generar_pdf_lista_materiales(
    df: pd.DataFrame,
    nombre_proyecto: str = "Proyecto"
) -> bytes:

    # 1. validar
    _validar_df(df)

    # 2. estilos
    styles = _get_styles()

    # 3. contenedor
    elementos = []

    # 4. header
    _build_header(elementos, styles, nombre_proyecto)

    # 5. datos
    data, total = _build_data(df)

    # 6. tabla
    tabla = _build_table(data, total)
    elementos.append(tabla)

    # 7. build
    return _build_pdf(elementos)
