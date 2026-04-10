# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

from costos_precios.precio_estructura import calcular_precio_estructura


# =========================================================
# GENERADOR DATAFRAME PRECIOS
# =========================================================
def generar_df_precios_estructura(
    df_costos_estructura: pd.DataFrame,
    porcentaje_utilidad: float = 0.15,
) -> pd.DataFrame:

    if df_costos_estructura is None or df_costos_estructura.empty:
        raise ValueError("df_costos_estructura vacío")

    df = df_costos_estructura.copy()

    # 🔥 DETECCIÓN FLEXIBLE
    def col(name):
        for c in df.columns:
            if name.lower() in c.lower():
                return c
        return None

    col_est = col("estructura")
    col_mat = col("material")
    col_op = col("operativo")

    if not all([col_est, col_mat, col_op]):
        raise ValueError("Columnas necesarias no encontradas")

    resultados = []

    for _, r in df.iterrows():

        res = calcular_precio_estructura(
            estructura=str(r[col_est]),
            costo_materiales=float(r[col_mat]),
            costo_operativo=float(r[col_op]),
            porcentaje_utilidad=porcentaje_utilidad,
        )

        resultados.append({
            "Estructura": res.estructura,
            "Costo Materiales": res.costo_materiales,
            "Costo Operativo": res.costo_operativo,
            "Costo Base": res.costo_base,
            "Utilidad": res.utilidad,
            "Precio Unitario": res.precio_unitario,
        })

    return pd.DataFrame(resultados)


# =========================================================
# RENDER PDF
# =========================================================
def generar_tabla_precios_estructura(
    df_costos_estructura: pd.DataFrame,
    porcentaje_utilidad: float = 0.15,
):

    df = generar_df_precios_estructura(
        df_costos_estructura,
        porcentaje_utilidad
    )

    data = [[
        "Estructura",
        "Materiales",
        "Operativo",
        "Base",
        "Utilidad",
        "Precio Unitario"
    ]]

    for _, r in df.iterrows():
        data.append([
            r["Estructura"],
            f"L {r['Costo Materiales']:,.2f}",
            f"L {r['Costo Operativo']:,.2f}",
            f"L {r['Costo Base']:,.2f}",
            f"L {r['Utilidad']:,.2f}",
            f"L {r['Precio Unitario']:,.2f}",
        ])

    tabla = Table(data, colWidths=[90, 80, 80, 80, 80, 100])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [tabla]
