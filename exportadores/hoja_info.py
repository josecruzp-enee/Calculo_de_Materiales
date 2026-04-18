# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from math import sqrt, floor
import pandas as pd
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
# LIMPIAR TEXTO CALIBRE
# ==========================================================
def _limpiar(txt: str) -> str:
    return str(txt).replace("Cable de Aluminio", "").replace("Forrado", "").strip()


# ==========================================================
# EXTRAER CALIBRES COMPLETO
# ==========================================================
def extraer_calibres(cables):

    prim = ""
    sec = ""
    neu = ""
    pil = ""

    for c in cables:
        tipo = str(c.get("Tipo", "")).upper()
        calibre = _limpiar(c.get("Calibre", ""))

        if tipo == "MT" and not prim:
            prim = calibre
        elif tipo == "BT" and not sec:
            sec = calibre
        elif tipo == "N" and not neu:
            neu = calibre
        elif tipo == "HP" and not pil:
            pil = calibre

    return prim, sec, neu, pil


# ==========================================================
# FORMATO CONDUCTORES (3 x ACSR + 1 x N)
# ==========================================================
def _formato_conductores(cables, tipo_busqueda):

    grupo = {}

    for c in cables:
        tipo = str(c.get("Tipo", "")).upper()

        if tipo != tipo_busqueda:
            continue

        calibre = _limpiar(c.get("Calibre", ""))
        fases = int(c.get("Conductores", 1))

        grupo[calibre] = grupo.get(calibre, 0) + fases

    return " + ".join([f"{v} x {k}" for k, v in grupo.items()])


# ==========================================================
# TABLA PRINCIPAL
# ==========================================================
def build_tabla(datos, cables, tension_fmt, styleN):

    prim, sec, neu, pil = extraer_calibres(cables)

    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "SIN NOMBRE")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "N/A")],
        ["Nivel de Tensión (kV):", tension_fmt],
        ["Calibre Primario:", prim or "N/A"],
        ["Calibre Secundario:", sec or "N/A"],
        ["Calibre Neutro:", neu or "N/A"],
        ["Calibre Piloto:", pil or "N/A"],
        ["Fecha de Informe:", datos.get("fecha_informe", "N/A")],
        ["Responsable:", datos.get("responsable", "N/A")],
        ["Empresa:", datos.get("empresa", "N/A")],
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
# DESCRIPCIÓN INTELIGENTE (PRO)
# ==========================================================
def build_descripcion(df_estructuras, cables, styleN):

    lineas = []

    if isinstance(df_estructuras, pd.DataFrame) and not df_estructuras.empty:

        df = df_estructuras.copy()
        df["cod"] = df["codigodeestructura"].astype(str).str.upper()

        # POSTES
        postes = df[df["cod"].str.contains("PC")]
        if not postes.empty:
            total = int(postes["Cantidad"].sum())
            lineas.append(f"Hincado de {total} postes.")

        # TRANSFORMADORES
        trafos = df[df["cod"].str.contains("TS")]
        if not trafos.empty:
            total = int(trafos["Cantidad"].sum())
            lineas.append(f"Instalación de {total} transformador(es).")

        # LUMINARIAS (MEJORADO)
        lum = df[df["cod"].str.contains("LL")]
        if not lum.empty:
            resumen = lum.groupby("cod")["Cantidad"].sum().reset_index()
            partes = [f'{r["Cantidad"]} x {r["cod"]}' for _, r in resumen.iterrows()]
            lineas.append(f"Instalación de luminarias tipo {', '.join(partes)}.")

    # =====================================================
    # LÍNEAS ELÉCTRICAS
    # =====================================================
    if cables:

        for tipo, nombre in [("MT", "LP"), ("BT", "LS")]:

            long_total = sum(
                float(c.get("Longitud", 0))
                for c in cables
                if str(c.get("Tipo", "")).upper() == tipo
            )

            if long_total <= 0:
                continue

            conductores = _formato_conductores(cables, tipo)
            neutro = _formato_conductores(cables, "N")
            piloto = _formato_conductores(cables, "HP")

            extra = " + ".join([x for x in [neutro, piloto] if x])

            desc = f"Construcción de {int(long_total)} m de {nombre}, {conductores}"

            if extra:
                desc += f" + {extra}"

            lineas.append(desc)

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
def hoja_info_proyecto(datos_proyecto, df_estructuras=None, df_mat=None):

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]

    elems = []

    datos = _normalizar_datos(datos_proyecto)
    cables = datos.get("cables_proyecto", [])

    tension_fmt = _formato_tension(datos.get("tension"))

    elems.append(Paragraph("Hoja de Información del Proyecto", styleH))
    elems.append(Spacer(1, 12))

    elems.extend(build_tabla(datos, cables, tension_fmt, styleN))
    elems.extend(build_descripcion(df_estructuras, cables, styleN))

    return elems


# ==========================================================
# WRAPPER (NO ROMPER IMPORTS)
# ==========================================================
def seccion_hoja_info(datos_proyecto, df_estructuras, df_mat):
    return hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat)
