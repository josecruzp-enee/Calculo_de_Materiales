# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors


# =========================================================
# HELPERS
# =========================================================
def _fmt(valor: float) -> str:
    return f"L {valor:,.2f}"


# =========================================================
# COTIZACIÓN FINAL (ROBUSTA + DEBUG)
# =========================================================
def generar_seccion_cotizacion_final(
    doc,
    styles,
    df_precios,
    porcentaje_gestion: float = 0.02,
    porcentaje_imprevistos: float = 0.01,
    porcentaje_isv: float = 0.15,
):

    elems = []

    # =====================================================
    # VALIDACIONES
    # =====================================================
    if df_precios is None or df_precios.empty:
        raise ValueError("df_precios vacío")

    if "Subtotal" not in df_precios.columns:
        raise ValueError("df_precios no tiene columna 'Subtotal'")

    # =====================================================
    # DEBUG INICIAL
    # =====================================================
    try:
        debug_info = f"""
        DEBUG COTIZACIÓN:
        columnas: {list(df_precios.columns)}
        filas: {len(df_precios)}
        subtotal_raw: {df_precios["Subtotal"].head(5).tolist()}
        """
        elems.append(Paragraph(debug_info, styles["Normal"]))
        elems.append(Spacer(1, 6))
    except Exception as e:
        elems.append(Paragraph(f"ERROR DEBUG: {str(e)}", styles["Normal"]))

    # =====================================================
    # NORMALIZAR SUBTOTAL (CRÍTICO 🔥)
    # =====================================================
    df_tmp = df_precios.copy()

    # Convertir a string para limpieza segura
    df_tmp["Subtotal"] = df_tmp["Subtotal"].astype(str)

    # Limpiar formato moneda si existe
    df_tmp["Subtotal"] = (
        df_tmp["Subtotal"]
        .str.replace("L", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    # Convertir a número
    df_tmp["Subtotal"] = pd.to_numeric(df_tmp["Subtotal"], errors="coerce")

    # =====================================================
    # DEBUG POST-CONVERSIÓN
    # =====================================================
    elems.append(Paragraph(
        f"DEBUG Subtotal convertidos: {df_tmp['Subtotal'].head(5).tolist()}",
        styles["Normal"]
    ))
    elems.append(Spacer(1, 6))

    total_base = df_tmp["Subtotal"].fillna(0).sum()

    elems.append(Paragraph(
        f"DEBUG TOTAL BASE: {total_base}",
        styles["Normal"]
    ))
    elems.append(Spacer(1, 10))

    # =====================================================
    # VALIDACIÓN FINAL
    # =====================================================
    if total_base <= 0:
        elems.append(Paragraph("ERROR: Total base inválido", styles["Normal"]))
        return elems

    # =====================================================
    # CÁLCULOS COMERCIALES
    # =====================================================
    gestion = total_base * porcentaje_gestion
    imprevistos = total_base * porcentaje_imprevistos

    subtotal = total_base + gestion + imprevistos
    isv = subtotal * porcentaje_isv
    total_final = subtotal + isv

    # =====================================================
    # TÍTULO
    # =====================================================
    elems.append(Paragraph("<b>COTIZACIÓN DEL PROYECTO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 12))

    # =====================================================
    # TABLA
    # =====================================================
    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación del proyecto eléctrico", _fmt(total_base)],
        ["Gestión y aprobación ENEE (2%)", _fmt(gestion)],
        ["Imprevistos (1%)", _fmt(imprevistos)],
        ["SUBTOTAL", _fmt(subtotal)],
        ["ISV (15%)", _fmt(isv)],
        ["TOTAL OFERTA", _fmt(total_final)],
    ]

    tabla = Table(
        data,
        colWidths=[doc.width * 0.7, doc.width * 0.3]
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -3), (-1, -3), "Helvetica-Bold"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.darkblue),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 12))

    # =====================================================
    # NOTA
    # =====================================================
    elems.append(
        Paragraph(
            "<font size=8><i>"
            "Esta oferta incluye suministro de materiales, instalación, gestión ante ENEE "
            "y costos asociados para la ejecución del proyecto."
            "</i></font>",
            styles["Normal"]
        )
    )

    return elems
