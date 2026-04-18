# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# =========================================================
# LIMPIAR TEXTO CALIBRE
# =========================================================
def _limpiar(txt: str) -> str:
    return str(txt).replace("Cable de Aluminio", "").replace("Forrado", "").strip()


# =========================================================
# EXTRAER CALIBRES
# =========================================================
def extraer_calibres(datos):

    prim = ""
    sec = ""
    neu = ""
    pil = ""

    cables = datos.get("cables_proyecto", [])

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


# =========================================================
# AGRUPAR CABLES (FORMATO PROFESIONAL)
# =========================================================
def _formato_conductores(cables, tipo_busqueda):

    grupo = {}

    for c in cables:
        tipo = str(c.get("Tipo", "")).upper()

        if tipo != tipo_busqueda:
            continue

        calibre = _limpiar(c.get("Calibre", ""))
        fases = int(c.get("Conductores", 1))

        clave = calibre

        grupo[clave] = grupo.get(clave, 0) + fases

    partes = [f"{v} x {k}" for k, v in grupo.items()]

    return " + ".join(partes)


# =========================================================
# HOJA DE INFORMACIÓN
# =========================================================
def hoja_info_(datos_proyecto, df_estructuras=None):

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
    cables = datos.get("cables_proyecto", [])

    prim, sec, neu, pil = extraer_calibres(datos)

    # =====================================================
    # TABLA
    # =====================================================
    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "SIN NOMBRE")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "N/A")],
        ["Nivel de Tensión (kV):", tension_fmt],
        ["Calibre Primario:", calibre_primario or "N/A"],
        ["Calibre Secundario:", calibre_secundario or "N/A"],
        ["Calibre Neutro:", calibre_neutro or "N/A"],
        ["Calibre Piloto:", calibre_piloto or "N/A"],
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
    # DESCRIPCIÓN
    # =====================================================
    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))

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
            partes = [f'{r["Cantidad"]} {r["cod"]}' for _, r in resumen.iterrows()]
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
            partes = [f'{r["Cantidad"]} x {r["cod"]}' for _, r in resumen.iterrows()]
            total = int(trafos["Cantidad"].sum())

            lineas.append(
                f"Instalación de {total} transformador(es) en conexión {', '.join(partes)}."
            )

        # -------------------------------------------------
        # LUMINARIAS (MEJORADO)
        # -------------------------------------------------
        lum = df[df["cod"].str.contains("LL")]

        if not lum.empty:
            resumen = lum.groupby("cod")["Cantidad"].sum().reset_index()
            partes = [f'{r["Cantidad"]} x {r["cod"]}' for _, r in resumen.iterrows()]
            total = int(lum["Cantidad"].sum())

            lineas.append(
                f"Instalación de {total} luminarias tipo {', '.join(partes)}."
            )

    # -------------------------------------------------
    # LÍNEAS ELÉCTRICAS
    # -------------------------------------------------
    if cables:

        for tipo_busqueda, nombre in [("MT", "LP"), ("BT", "LS")]:

            long_total = sum(
                float(c.get("Longitud", 0))
                for c in cables
                if str(c.get("Tipo", "")).upper() == tipo_busqueda
            )

            if long_total <= 0:
                continue

            conductores = _formato_conductores(cables, tipo_busqueda)

            neutro = _formato_conductores(cables, "N")
            piloto = _formato_conductores(cables, "HP")

            partes_extra = []

            if neutro:
                partes_extra.append(neutro)

            if piloto:
                partes_extra.append(piloto)

            extra = " + ".join(partes_extra)

            desc = f"Construcción de {int(long_total)} m de {nombre}, {conductores}"

            if extra:
                desc += f" + {extra}"

            lineas.append(desc)

    # =====================================================
    # RENDER
    # =====================================================
    for i, l in enumerate(lineas):
        elems.append(Paragraph(f"{i+1}. {l}", styleN))
        elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 12))

    return elems
