# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from math import sqrt, floor
from typing import List
import pandas as pd
from ayuda.debug import debug_guardar
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# ==========================================================
# NORMALIZADOR
# ==========================================================
def _normalizar_datos(d: dict) -> dict:
    return {
        "nombre_proyecto": d.get("nombre_proyecto") or d.get("nombre", "SIN NOMBRE"),
        "codigo_proyecto": d.get("codigo_proyecto") or d.get("codigo", "N/A"),
        "empresa": d.get("empresa", "N/A"),
        "tension": d.get("tension") or d.get("nivel_de_tension"),
        "fecha_informe": d.get("fecha_informe") or datetime.today().strftime("%Y-%m-%d"),
        "responsable": d.get("responsable", "N/A"),
        "cables_proyecto": d.get("cables_proyecto", []),
    }


# ==========================================================
# FORMATO TENSIÓN
# ==========================================================
def _formato_tension(vll):
    try:
        vll = float(vll)
        vln = vll / sqrt(3)
        vln = floor(vln * 10) / 10
        return f"{vln:.1f} / {vll:.1f} kV"
    except:
        return str(vll)


# ==========================================================
# CALIBRES AUTOMÁTICOS (SIMPLIFICADO PERO ÚTIL)
# ==========================================================
def _extraer_calibres(cables, tipo):
    for c in cables:
        if str(c.get("Tipo", "")).upper() == tipo:
            return c.get("Materiales") or c.get("Calibre") or ""
    return ""


# ==========================================================
# TABLA PRINCIPAL
# ==========================================================
def build_tabla(datos, cables, tension_fmt, styleN):

    calibre_primario = _extraer_calibres(cables, "MT")
    calibre_secundario = _extraer_calibres(cables, "BT")
    calibre_neutro = _extraer_calibres(cables, "N")
    calibre_piloto = _extraer_calibres(cables, "HP")

    data = [
        ["Nombre del Proyecto:", datos["nombre_proyecto"]],
        ["Código / Expediente:", datos["codigo_proyecto"]],
        ["Nivel de Tensión (kV):", tension_fmt],
        ["Calibre Primario:", calibre_primario],
        ["Calibre Secundario:", calibre_secundario],
        ["Calibre Neutro:", calibre_neutro],
        ["Calibre Piloto:", calibre_piloto],
        ["Fecha de Informe:", datos["fecha_informe"]],
        ["Responsable:", datos["responsable"]],
        ["Empresa:", datos["empresa"]],
    ]

    tabla = Table(data, colWidths=[200, 340])

    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#D9D9D9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [tabla, Spacer(1, 15)]


# ==========================================================
# DESCRIPCIÓN INTELIGENTE
# ==========================================================
def build_descripcion(df_estructuras, styleN):

    lineas = []

    if df_estructuras is not None and not df_estructuras.empty:

        # POSTES
        postes = df_estructuras[df_estructuras["codigodeestructura"].str.contains("PC", na=False)]
        if not postes.empty:
            total = int(postes["Cantidad"].sum())
            lineas.append(f"Hincado de {total} postes.")

        # TRANSFORMADORES
        trafos = df_estructuras[df_estructuras["codigodeestructura"].str.contains("TS", na=False)]
        if not trafos.empty:
            total = int(trafos["Cantidad"].sum())
            lineas.append(f"Instalación de {total} transformador(es).")

        # LUMINARIAS
        lum = df_estructuras[df_estructuras["codigodeestructura"].str.contains("LL", na=False)]
        if not lum.empty:
            total = int(lum["Cantidad"].sum())
            lineas.append(f"Instalación de {total} luminarias.")

    if not lineas:
        lineas.append("No se cuenta con información suficiente.")

    texto = "<br/>".join([f"{i+1}. {l}" for i, l in enumerate(lineas)])

    return [
        Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
        Spacer(1, 6),
        Paragraph(texto, styleN),
        Spacer(1, 12),
    ]


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================
# =========================================================
# HOJA INFO PROFESIONAL (RECUPERADA)
# =========================================================
# =========================================================
# HOJA DE INFORMACIÓN DEL PROYECTO (VERSIÓN FINAL)
# =========================================================
def hoja_info_proyecto(
    datos_proyecto: dict,
    df_estructuras: pd.DataFrame = None,
    df_mat_por_estructura: dict = None,  # se mantiene por compatibilidad
):

    debug_guardar("HOJA_INFO_USO", {
        "mensaje": "NUEVA FUNCION EJECUTADA"
    })

    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]

    elems = []

    # =====================================================
    # HEADER
    # =====================================================
    elems.append(Paragraph("Hoja de Información del Proyecto", styleH))
    elems.append(Spacer(1, 12))

    datos = datos_proyecto or {}

    # =====================================================
    # FORMATO TENSIÓN
    # =====================================================
    def _formato_tension(t):
        if not t:
            return "N/A"
        return str(t)

    tension_fmt = _formato_tension(datos.get("tension"))

    # =====================================================
    # 🔥 CALIBRES DESDE UI (FUENTE CORRECTA)
    # =====================================================
    def extraer_calibres_desde_cables(datos_proyecto):

        prim = ""
        sec = ""
        neu = ""
        pil = ""

        cables = datos_proyecto.get("cables_proyecto", [])

        for c in cables:
            tipo = str(c.get("Tipo", "")).upper()
            calibre = str(c.get("Calibre", "")).strip()

            if tipo == "MT" and not prim:
                prim = calibre

            elif tipo == "BT" and not sec:
                sec = calibre

        return prim, sec, neu, pil

    prim, sec, neu, pil = extraer_calibres_desde_cables(datos)

    # =====================================================
    # TABLA
    # =====================================================
    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "SIN NOMBRE")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "N/A")],
        ["Nivel de Tensión (kV):", tension_fmt],
        ["Calibre Primario:", prim],
        ["Calibre Secundario:", sec],
        ["Calibre Neutro:", neu],
        ["Calibre Piloto:", pil],
        ["Fecha de Informe:", datos.get("fecha_informe", "N/A")],
        ["Responsable:", datos.get("responsable", "N/A")],
        ["Empresa:", datos.get("empresa", "N/A")],
    ]

    tabla = Table(data, colWidths=[200, 320])

    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 12))

    # =====================================================
    # DESCRIPCIÓN GENERAL
    # =====================================================
    lineas = []

    if isinstance(df_estructuras, pd.DataFrame) and not df_estructuras.empty:

        df = df_estructuras.copy()
        df["cod"] = df["codigodeestructura"].astype(str).str.upper()

        # -------------------------------------------------
        # POSTES
        # -------------------------------------------------
        postes = df[df["cod"].str.contains("PC")]

        if not postes.empty:
            resumen = postes.groupby("cod")["Cantidad"].sum().reset_index()

            partes = [
                f'{r["Cantidad"]} {r["cod"]}'
                for _, r in resumen.iterrows()
            ]

            total = int(postes["Cantidad"].sum())

            lineas.append(
                f"Hincado de {', '.join(partes)} (Total: {total} postes)."
            )

        # -------------------------------------------------
        # TRANSFORMADORES
        # -------------------------------------------------
        trafos = df[df["cod"].str.contains("TS")]

        if not trafos.empty:
            resumen = trafos.groupby("cod")["Cantidad"].sum().reset_index()

            partes = [
                f'{r["Cantidad"]} x {r["cod"]}'
                for _, r in resumen.iterrows()
            ]

            total = int(trafos["Cantidad"].sum())

            lineas.append(
                f"Instalación de {total} transformador(es) en conexión {', '.join(partes)}."
            )

        # -------------------------------------------------
        # LUMINARIAS
        # -------------------------------------------------
        lum = df[df["cod"].str.contains("LL")]

        if not lum.empty:
            total = int(lum["Cantidad"].sum())

            lineas.append(
                f"Instalación de {total} luminarias."
            )

    # =====================================================
    # RENDER DESCRIPCIÓN
    # =====================================================
    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))

    for i, l in enumerate(lineas):
        elems.append(Paragraph(f"{i+1}. {l}", styleN))
        elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 12))

    return elems

def seccion_hoja_info(datos_proyecto, df_estructuras, df_mat):
    return hoja_info_proyecto(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras,
        df_mat_por_estructura=df_mat,
    )
