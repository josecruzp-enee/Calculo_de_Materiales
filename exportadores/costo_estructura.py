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
    # VALIDACIÓN SUAVE (NO ROMPER PDF)
    # =====================================================
    if (
        df_costos_estructura is None
        or not isinstance(df_costos_estructura, pd.DataFrame)
        or df_costos_estructura.empty
    ):
        return [
            Paragraph("No hay datos de costos de estructuras", styles["Normal"])
        ]

    df = df_costos_estructura.copy()

    # =====================================================
    # NORMALIZAR COLUMNAS
    # =====================================================
    df.columns = [c.strip() for c in df.columns]

    rename_map = {
        "COSTO UNITARIO": "Total Unitario",
        "COSTO_UNITARIO": "Total Unitario",
        "COSTO": "Total Unitario",
        "TOTAL UNITARIO": "Total Unitario",
        "TOTAL_UNITARIO": "Total Unitario",

        "MATERIAL UNITARIO": "Material Unitario",
        "MATERIAL_UNITARIO": "Material Unitario",
        "MATERIAL": "Material Unitario",

        "INSTALACION UNITARIO": "Instalación Unitario",
        "INSTALACIÓN UNITARIO": "Instalación Unitario",
        "INSTALACION_UNITARIO": "Instalación Unitario",
        "INSTALACIÓN_UNITARIO": "Instalación Unitario",
        "INSTALACION": "Instalación Unitario",
        "INSTALACIÓN": "Instalación Unitario",

        "TOTAL": "Costo Total",
        "COSTO TOTAL": "Costo Total",
        "COSTO_TOTAL": "Costo Total",

        "CANTIDAD": "Cantidad",
        "CANT": "Cantidad",

        "ESTRUCTURA": "Estructura",
        "CODIGODEESTRUCTURA": "Estructura",
        "CODIGO DE ESTRUCTURA": "Estructura",
        "CÓDIGO DE ESTRUCTURA": "Estructura",
    }

    df.rename(columns=lambda c: rename_map.get(c.upper(), c), inplace=True)

    # =====================================================
    # VALIDAR COLUMNA ESTRUCTURA
    # =====================================================
    if "Estructura" not in df.columns:
        return [
            Paragraph("No existe columna 'Estructura'", styles["Normal"])
        ]

    # =====================================================
    # ASEGURAR COLUMNAS NUMÉRICAS
    # =====================================================
    if "Cantidad" not in df.columns:
        return [
            Paragraph("No existe columna 'Cantidad'", styles["Normal"])
        ]

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)

    # Si no viene Material Unitario, asumir 0
    if "Material Unitario" not in df.columns:
        df["Material Unitario"] = 0

    # Si no viene Instalación Unitario, asumir 0
    if "Instalación Unitario" not in df.columns:
        df["Instalación Unitario"] = 0

    df["Material Unitario"] = pd.to_numeric(
        df["Material Unitario"], errors="coerce"
    ).fillna(0)

    df["Instalación Unitario"] = pd.to_numeric(
        df["Instalación Unitario"], errors="coerce"
    ).fillna(0)

    # =====================================================
    # CALCULAR TOTAL UNITARIO Y TOTAL POR FILA
    # =====================================================
    df["Total Unitario"] = df["Material Unitario"] + df["Instalación Unitario"]

    df["Material Total"] = df["Material Unitario"] * df["Cantidad"]
    df["Instalación Total"] = df["Instalación Unitario"] * df["Cantidad"]
    df["Costo Total"] = df["Total Unitario"] * df["Cantidad"]

    df = df.sort_values("Estructura").reset_index(drop=True)

    # =====================================================
    # TOTALES POR COLUMNA
    # =====================================================
    total_material = float(df["Material Total"].sum())
    total_instalacion = float(df["Instalación Total"].sum())
    total_cantidad = float(df["Cantidad"].sum())
    total_general = float(df["Costo Total"].sum())

    # =====================================================
    # TABLA
    # =====================================================
    data = [[
        "DESCRIPCIÓN",
        "MATERIAL",
        "INSTALACIÓN",
        "TOTAL UNIT",
        "CANT",
        "TOTAL",
    ]]

    for _, row in df.iterrows():

        estructura = str(row["Estructura"]).strip()

        descripcion = f"Suministro e instalación de estructura {estructura}"

        cantidad = float(row["Cantidad"])
        cantidad_txt = str(int(cantidad)) if cantidad.is_integer() else f"{cantidad:.2f}"

        data.append([
            descripcion,
            _fmt_moneda(float(row["Material Unitario"])),
            _fmt_moneda(float(row["Instalación Unitario"])),
            _fmt_moneda(float(row["Total Unitario"])),
            cantidad_txt,
            _fmt_moneda(float(row["Costo Total"])),
        ])

    # =====================================================
    # FILA TOTAL GENERAL
    # =====================================================
    cantidad_total_txt = (
        str(int(total_cantidad))
        if float(total_cantidad).is_integer()
        else f"{total_cantidad:.2f}"
    )

    data.append([
        "TOTAL",
        _fmt_moneda(total_material),
        _fmt_moneda(total_instalacion),
        "",
        cantidad_total_txt,
        _fmt_moneda(total_general),
    ])

    # =====================================================
    # FORMATO
    # =====================================================
    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.40,
            doc.width * 0.13,
            doc.width * 0.14,
            doc.width * 0.13,
            doc.width * 0.08,
            doc.width * 0.12,
        ],
        repeatRows=1,
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),

        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("ALIGN", (1, 1), (3, -1), "RIGHT"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("ALIGN", (5, 1), (5, -1), "RIGHT"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    # =====================================================
    # SALIDA
    # =====================================================
    elems = []
    elems.append(Paragraph("<b>PRESUPUESTO DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))
    elems.append(tabla)

    return elems
