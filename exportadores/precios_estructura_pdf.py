# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle

# 🔥 IMPORT DEL ESTILO GLOBAL
from exportadores.pdf_base import estilo_tabla

def _numero_seguro(valor, default=0.0) -> float:
    valor = pd.to_numeric(valor, errors="coerce")

    if pd.isna(valor):
        return default

    return float(valor)


def _int_seguro_pdf(valor, default=0) -> int:
    return int(_numero_seguro(valor, default)) 


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

        estructura = str(r.get("Estructura", "")).strip()

        material = float(r.get("Material Unitario", 0))
        mano_obra = float(r.get("Mano Obra Unitaria", 0))
        total_unit = float(r.get("Total Unitario", 0))

        # Si Total Unitario viene vacío o en cero, calcularlo
        if total_unit <= 0:
            total_unit = material + mano_obra

        # =================================================
        # CANTIDAD
        # =================================================
        cantidad = cantidades.get(estructura, None)

        if cantidad is None or cantidad == 0:
            cantidad = float(r.get("Cantidad", 0))

        if cantidad <= 0:
            continue

        # =================================================
        # TOTALES POR FILA
        # =================================================
        # =================================================
        # TOTALES POR FILA
        # =================================================

        cantidad_material = r.get("Cantidad Material", cantidad)

        if pd.isna(cantidad_material):
            cantidad_material = cantidad

        cantidad_material = float(cantidad_material)


        cantidad_mano_obra = r.get("Cantidad Mano Obra", cantidad_material)

        if pd.isna(cantidad_mano_obra):
            cantidad_mano_obra = cantidad_material

        cantidad_mano_obra = float(cantidad_mano_obra)

        total_material = material * cantidad_material
        total_instalacion = mano_obra * cantidad_mano_obra
        total = total_material + total_instalacion

        # Solo para mostrar en columna CANT
        cantidad = cantidad_material
        total_unit = material + mano_obra

        # =================================================
        # ACUMULADORES GENERALES
        # =================================================
        total_material_general += total_material
        total_instalacion_general += total_instalacion
        total_cantidad_general += cantidad
        total_general += total

        # =================================================
        # DESCRIPCIÓN
        # =================================================
        if estructura.startswith("CONDUCTOR"):
            texto = f"Suministro e instalación de {estructura}"
        else:
            texto = f"Suministro e instalación de estructura {estructura}"

        descripcion = Paragraph(texto, style_small)

        # =================================================
        # FILA NORMAL
        # =================================================
        descripcion = Paragraph(texto, style_small)

        data.append([
            descripcion,
            f"L {material:,.2f}",
            f"L {mano_obra:,.2f}",
            f"L {total_unit:,.2f}",
            f"{int(cantidad)}",
            f"L {total:,.2f}",
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
    # FILA TOTAL GENERAL CORREGIDA
    # =====================================================
    # =====================================================
    # TOTALES
    # =====================================================
    isv_materiales = total_material_general * 0.15

    subtotal_general = (
        total_material_general
        + total_instalacion_general
    )

    total_material_con_isv = (
        total_material_general
        + isv_materiales
    )

    total_general_con_isv = (
        total_material_con_isv
        + total_instalacion_general
    )

    # =====================================================
    # SUBTOTAL
    # =====================================================
    data.append([
        "SUBTOTAL",
        f"L {total_material_general:,.2f}",
        f"L {total_instalacion_general:,.2f}",
        "",
        f"{int(total_cantidad_general)}",
        f"L {subtotal_general:,.2f}",
    ])

    # =====================================================
    # ISV
    # =====================================================
    data.append([
        "ISV MATERIALES (15%)",
        f"L {isv_materiales:,.2f}",
        "",
        "",
        "",
        f"L {isv_materiales:,.2f}",
        ])

    # =====================================================
    # TOTAL GENERAL
    # =====================================================
    data.append([
        "TOTAL GENERAL",
        f"L {total_material_con_isv:,.2f}",
        f"L {total_instalacion_general:,.2f}",
        "",
        f"{int(total_cantidad_general)}",
        f"L {total_general_con_isv:,.2f}",
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
