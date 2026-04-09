# -*- coding: utf-8 -*-
"""
reportes/presupuesto_estructuras.py

Renderiza tabla PDF de costos de estructuras.
✔ SOLO presentación
✔ Consume salida de costos
✔ Sin lógica de negocio
"""

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
import pandas as pd


# =========================================================
# HELPERS
# =========================================================
def _validar_df(df: pd.DataFrame, nombre: str):
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError(f"{nombre} inválido")

    if df.empty:
        raise ValueError(f"{nombre} vacío")


def _fmt_moneda(valor: float) -> str:
    return f"L {valor:,.2f}"


# =========================================================
# RENDER TABLA
# =========================================================
def generar_tabla_presupuesto(
    doc,
    styles,
    df_costos_por_punto: pd.DataFrame,
):

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    _validar_df(df_costos_por_punto, "df_costos_por_punto")

    required_cols = [
        "Punto",
        "Estructura",
        "Cantidad",
        "Precio Unitario",
        "Subtotal Precio",
    ]

    faltantes = [c for c in required_cols if c not in df_costos_por_punto.columns]
    if faltantes:
        raise ValueError(f"df_costos_por_punto sin columnas requeridas: {faltantes}")

    # =====================================================
    # NORMALIZACIÓN SEGURA (SIN MUTAR ORIGINAL)
    # =====================================================
    df = df_costos_por_punto.copy()

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce").fillna(0)
    df["Subtotal Precio"] = pd.to_numeric(df["Subtotal Precio"], errors="coerce").fillna(0)

    # ✔ orden consistente
    df = df.sort_values(by=["Punto", "Estructura"]).reset_index(drop=True)

    # =====================================================
    # TABLA
    # =====================================================
    data = [["ITEM", "DESCRIPCIÓN", "CANT", "P.U.", "TOTAL"]]

    total_general = float(df["Subtotal Precio"].sum())
    item = 1

    for _, row in df.iterrows():

        estructura = row["Estructura"]
        cant = int(row["Cantidad"])
        pu = float(row["Precio Unitario"])
        total = float(row["Subtotal Precio"])

        descripcion = (
            f"Instalación y suministro de {cant} "
            f"estructura(s) tipo {estructura}"
        )

        data.append([
            f"{item:02d}",
            descripcion,
            f"{cant}",
            _fmt_moneda(pu),
            _fmt_moneda(total),
        ])

        item += 1

    # TOTAL
    data.append(["", "TOTAL GENERAL", "", "", _fmt_moneda(total_general)])

    # =====================================================
    # FORMATO
    # =====================================================
    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.08,
            doc.width * 0.47,
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

        ("ALIGN", (2,1), (2,-2), "CENTER"),
        ("ALIGN", (3,1), (4,-2), "RIGHT"),

        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))

    elems = []
    elems.append(Paragraph("<b>2. COSTO DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))
    elems.append(tabla)

    return elems
