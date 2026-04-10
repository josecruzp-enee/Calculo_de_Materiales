# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


# =========================================================
# TABLA PRECIOS DE ESTRUCTURA (SOLO PRESENTACIÓN)
# =========================================================
def generar_tabla_precios_estructura(
    df_precios: pd.DataFrame,
):
    """
    Renderiza la tabla de precios unitarios por estructura.

    ⚠️ Este módulo NO calcula precios.
    Espera un DataFrame ya procesado desde costos_precios.
    """

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or not isinstance(df_precios, pd.DataFrame):
        raise ValueError("df_precios inválido")

    if df_precios.empty:
        raise ValueError("df_precios vacío")

    required = [
        "Estructura",
        "Costo Materiales",
        "Costo Operativo",
        "Costo Base",
        "Utilidad",
        "Precio Unitario",
    ]

    faltantes = [c for c in required if c not in df_precios.columns]
    if faltantes:
        raise ValueError(f"df_precios no cumple contrato: {faltantes}")

    # =====================================================
    # CONSTRUCCIÓN DE TABLA
    # =====================================================
    data = [[
        "Estructura",
        "Materiales",
        "Operativo",
        "Base",
        "Utilidad",
        "Precio Unitario",
    ]]

    for _, r in df_precios.iterrows():
        data.append([
            str(r["Estructura"]),
            f"L {float(r['Costo Materiales']):,.2f}",
            f"L {float(r['Costo Operativo']):,.2f}",
            f"L {float(r['Costo Base']):,.2f}",
            f"L {float(r['Utilidad']):,.2f}",
            f"L {float(r['Precio Unitario']):,.2f}",
        ])

    # =====================================================
    # DISEÑO
    # =====================================================
    tabla = Table(
        data,
        colWidths=[90, 80, 80, 80, 80, 100]
    )

    tabla.setStyle(TableStyle([
        # encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        # contenido
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),

        # bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        # padding
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),

        # filas alternas
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))

    return [tabla]


# =========================================================
# WRAPPER DE SECCIÓN COMPLETA
# =========================================================
from reportlab.platypus import Paragraph, Spacer, PageBreak


def seccion_precios_estructura(
    df_precios,
    styles,
    titulo: str = "PRECIOS UNITARIOS DE ESTRUCTURA",
):
    """
    Sección completa lista para insertar en PDF.

    ✔ incluye título
    ✔ incluye tabla
    ✔ incluye salto de página
    """

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or df_precios.empty:
        return elems  # no rompe el flujo

    # =====================================================
    # TÍTULO
    # =====================================================
    elems.append(Paragraph(titulo, styles["Heading1"]))
    elems.append(Spacer(1, 10))

    # =====================================================
    # TABLA
    # =====================================================
    elems.extend(
        generar_tabla_precios_estructura(df_precios)
    )

    # =====================================================
    # PAGE BREAK
    # =====================================================
    elems.append(PageBreak())

    return elems
