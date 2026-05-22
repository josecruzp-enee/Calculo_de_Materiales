# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle

# 🔥 IMPORT DEL ESTILO GLOBAL
from exportadores.pdf_base import estilo_tabla


# =========================================================
# TABLA PRECIOS DE ESTRUCTURA
# =========================================================
def generar_tabla_precios_estructura(
    df_precios: pd.DataFrame,
    df_estructuras: pd.DataFrame | None = None,
):

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_precios is None or not isinstance(df_precios, pd.DataFrame):
        raise ValueError("df_precios inválido")

    if df_precios.empty:
        raise ValueError("df_precios vacío")

    # =====================================================
    # ESTILO TEXTO
    # =====================================================
    style_small = ParagraphStyle(
        name="Small",
        fontName="Helvetica",
        fontSize=8,
        leading=9
    )

    # =====================================================
    # AGRUPAR CANTIDADES
    # =====================================================
    cantidades = {}

    if df_estructuras is not None and not df_estructuras.empty:

        df_tmp = df_estructuras.copy()

        df_tmp["Estructura"] = (
            df_tmp["Estructura"]
            .astype(str)
            .str.strip()
        )

        df_tmp["Cantidad"] = pd.to_numeric(
            df_tmp["Cantidad"],
            errors="coerce"
        ).fillna(0)

        cantidades = (
            df_tmp.groupby("Estructura")["Cantidad"]
            .sum()
            .to_dict()
        )

    # =====================================================
    # CABECERA
    # =====================================================
    data = [[
        "DESCRIPCIÓN",
        "MATERIAL",
        "INSTALACIÓN",
        "TOTAL UNIT",
        "CANT",
        "TOTAL"
    ]]

    total_material_general = 0.0
    total_instalacion_general = 0.0
    total_cantidad_general = 0.0
    total_general = 0.0

    # =====================================================
    # FILAS
    # =====================================================
    for _, r in df_precios.iterrows():

        estructura = str(
            r.get("Estructura", "")
        ).strip()

        material = float(
            r.get("Material Unitario", 0)
        )

        mano_obra = float(
            r.get("Mano Obra Unitaria", 0)
        )

        total_unit = float(
            r.get("Total Unitario", 0)
        )

        # =================================================
        # CANTIDAD
        # =================================================
        cantidad = cantidades.get(estructura, None)

        if cantidad is None or cantidad == 0:

            cantidad = float(
                r.get("Cantidad", 0)
            )

        if cantidad <= 0:
            continue

        # =================================================
        # TOTAL
        # =================================================
        total = total_unit * cantidad

        # =================================================
        # DESCRIPCIÓN
        # =================================================
        if estructura.startswith("CONDUCTOR"):

            texto = (
                f"Suministro e instalación de "
                f"{estructura}"
            )

        else:

            texto = (
                f"Suministro e instalación de "
                f"estructura {estructura}"
            )

        descripcion = Paragraph(
            texto,
            style_small
        )

        total_material_general = 0.0
        total_instalacion_general = 0.0
        total_cantidad_general = 0.0
        total_general = 0.0

        # =================================================
        # FILA
        # =================================================
        data.append([
            "TOTAL",
            f"L {total_material_general:,.2f}",
            f"L {total_instalacion_general:,.2f}",
            "",
            f"{int(total_cantidad_general)}",
            f"L {total_general:,.2f}",
        ])

    # =====================================================
    # CONTROL VACÍO
    # =====================================================
    if len(data) == 1:

        data.append([
            "SIN DATOS",
            "-",
            "-",
            "-",
            "-",
            "-"
        ])

    # =====================================================
    # TOTAL GENERAL
    # =====================================================
    data.append([
        "",
        "",
        "",
        "",
        "TOTAL",
        f"L {total_general:,.2f}"
    ])

    # =====================================================
    # TABLA
    # =====================================================
    tabla = Table(
        data,
        colWidths=[240, 70, 70, 70, 50, 90],
        repeatRows=1
    )

    # =====================================================
    # ESTILO
    # =====================================================
    tabla.setStyle(estilo_tabla())

    return [tabla]


# =========================================================
# COTIZACIÓN SIMPLE
# =========================================================
def generar_cotizacion_desde_estructuras(
    doc,
    styles,
    df_precios
):

    from reportlab.platypus import (
        Table,
        Paragraph,
        Spacer
    )

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or df_precios.empty:

        elems.append(
            Paragraph(
                "SIN DATOS PARA COTIZACIÓN",
                styles["Normal"]
            )
        )

        return elems

    # =====================================================
    # TOTAL BASE
    # =====================================================
    if "Total Proyecto" in df_precios.columns:

        total_base = float(
            df_precios["Total Proyecto"].sum()
        )

    elif "Subtotal" in df_precios.columns:

        total_base = float(
            df_precios["Subtotal"].sum()
        )

    else:

        total_base = 0.0

    # =====================================================
    # CÁLCULOS
    # =====================================================
    ingenieria = total_base * 0.15

    subtotal = total_base + ingenieria

    isv = subtotal * 0.15

    total_final = subtotal + isv

    # =====================================================
    # TÍTULO
    # =====================================================
    elems.append(
        Paragraph(
            "<b>COTIZACIÓN DEL PROYECTO</b>",
            styles["Heading1"]
        )
    )

    elems.append(Spacer(1, 12))

    # =====================================================
    # TABLA
    # =====================================================
    data = [

        ["Concepto", "Monto (L)"],

        [
            "Suministro e instalación",
            f"L {total_base:,.2f}"
        ],

        [
            "Gastos de Ingeniería (15%)",
            f"L {ingenieria:,.2f}"
        ],

        [
            "SUBTOTAL",
            f"L {subtotal:,.2f}"
        ],

        [
            "ISV (15%)",
            f"L {isv:,.2f}"
        ],

        [
            "TOTAL PROYECTO",
            f"L {total_final:,.2f}"
        ],
    ]

    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.7,
            doc.width * 0.3
        ],
        repeatRows=1
    )

    # =====================================================
    # ESTILO
    # =====================================================
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)

    return elems
