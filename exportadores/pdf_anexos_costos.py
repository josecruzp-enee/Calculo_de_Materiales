# -*- coding: utf-8 -*-
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
    return f"L {valor:,.0f}" if valor % 1 == 0 else f"L {valor:,.2f}"


# =========================================================
# REPORTE COSTOS DE ESTRUCTURAS (PRESUPUESTO)
# =========================================================
def generar_tabla_costos_estructura(
    doc,
    styles,
    df_costos_estructura: pd.DataFrame,
):

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    _validar_df(df_costos_estructura, "df_costos_estructura")

    df = df_costos_estructura.copy()

    # =====================================================
    # NORMALIZAR NOMBRE
    # =====================================================
    if "Estructura" not in df.columns:
        if "codigodeestructura" in df.columns:
            df["Estructura"] = df["codigodeestructura"]
        else:
            raise ValueError("No existe columna 'Estructura'")

    required = ["Estructura", "Cantidad", "Costo Unitario", "Costo Total"]
    faltantes = [c for c in required if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")

    # =====================================================
    # NORMALIZACIÓN
    # =====================================================
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Costo Unitario"] = pd.to_numeric(df["Costo Unitario"], errors="coerce").fillna(0)
    df["Costo Total"] = pd.to_numeric(df["Costo Total"], errors="coerce").fillna(0)

    df = df.sort_values("Estructura").reset_index(drop=True)

    # =====================================================
    # TABLA
    # =====================================================
    data = [["ITEM", "ESTRUCTURA", "CANT", "P.U.", "TOTAL"]]

    total_general = float(df["Costo Total"].sum())

    for i, (_, row) in enumerate(df.iterrows(), start=1):

        data.append([
            f"{i:02d}",
            str(row["Estructura"]),
            f"{int(row['Cantidad'])}",
            _fmt_moneda(row["Costo Unitario"]),
            _fmt_moneda(row["Costo Total"]),
        ])

    # TOTAL GENERAL
    data.append([
        "",
        "TOTAL GENERAL",
        "",
        "",
        _fmt_moneda(total_general)
    ])

    # =====================================================
    # FORMATO
    # =====================================================
    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.08,
            doc.width * 0.32,
            doc.width * 0.12,
            doc.width * 0.20,
            doc.width * 0.28,
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
    elems.append(Paragraph("<b>2. PRESUPUESTO DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))
    elems.append(tabla)

    return elems
