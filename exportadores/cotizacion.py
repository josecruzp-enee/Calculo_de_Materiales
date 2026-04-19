# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from reportlab.platypus import Table, Paragraph, Spacer

# 🔥 IMPORT CLAVE
from exportadores.pdf_base import estilo_tabla


# =========================================================
# HELPERS
# =========================================================
def _fmt(valor: float) -> str:
    return f"L {valor:,.2f}"


# =========================================================
# COTIZACIÓN FINAL (UNIFICADA)
# =========================================================
def generar_seccion_cotizacion_final(doc, styles, df_precios):

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if df_precios is None or df_precios.empty:
        elems.append(Paragraph("SIN DATOS PARA COTIZACIÓN", styles["Normal"]))
        return elems

    # =====================================================
    # TOTAL BASE
    # =====================================================
    if "Subtotal" in df_precios.columns:
        total_base = float(df_precios["Subtotal"].sum())
    else:
        total_base = float(df_precios["Precio Total"].sum())

    # =====================================================
    # CÁLCULOS
    # =====================================================
    ingenieria = total_base * 0.15
    subtotal = total_base + ingenieria
    isv = subtotal * 0.15
    total_final = subtotal + isv

    # =====================================================
    # TABLA
    # =====================================================
    data = [
        ["Concepto", "Monto (L)"],
        ["Suministro e instalación", _fmt(total_base)],
        ["Gastos de Ingeniería (15%)", _fmt(ingenieria)],
        ["SUBTOTAL", _fmt(subtotal)],
        ["ISV (15%)", _fmt(isv)],
        ["TOTAL PROYECTO", _fmt(total_final)],
    ]

    tabla = Table(
        data,
        colWidths=[doc.width * 0.7, doc.width * 0.3],
        repeatRows=1
    )

    # 🔥 ESTILO GLOBAL (CLAVE)
    tabla.setStyle(estilo_tabla())

    elems.append(tabla)

    return elems
