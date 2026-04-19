# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# =========================================================
# HELPERS
# =========================================================
def _plural(palabra, n):
    return palabra if n == 1 else palabra + "es"


def _formatear_calibre(txt: str) -> str:
    """
    Convierte:
    ACSR #1/0 AWG Raven →
    Cable de Aluminio ACSR #1/0 AWG Raven
    """

    txt = str(txt).strip()

    if not txt:
        return ""

    if "Cable de" in txt:
        return txt

    if "ACSR" in txt:
        return f"Cable de Aluminio {txt}"

    if "WP" in txt:
        return f"Cable de Aluminio Forrado {txt}"

    return txt


# =========================================================
# CALIBRES
# =========================================================
def extraer_calibres(datos):

    prim = sec = neu = pil = ""
    cables = datos.get("cables_proyecto", [])

    for c in cables:
        tipo = str(c.get("Tipo", "")).upper()
        calibre = _formatear_calibre(c.get("Calibre", ""))

        if tipo == "MT" and not prim:
            prim = calibre
        elif tipo == "BT" and not sec:
            sec = calibre
        elif tipo == "N" and not neu:
            neu = calibre
        elif tipo == "HP" and not pil:
            pil = calibre

    return prim, sec, neu, pil


def _formato_conductores(cables, tipo_busqueda):

    grupo = {}

    for c in cables:
        if str(c.get("Tipo", "")).upper() != tipo_busqueda:
            continue

        calibre = str(c.get("Calibre", "")).strip()
        fases = int(c.get("Conductores", 1))

        grupo[calibre] = grupo.get(calibre, 0) + fases

    return " + ".join([f"{v} x {k}" for k, v in grupo.items()])


# =========================================================
# BLOQUES DESCRIPCIÓN
# =========================================================
def _desc_postes(df):

    postes = df[df["cod"].str.contains("PC")]
    if postes.empty:
        return None

    resumen = postes.groupby("cod")["Cantidad"].sum().reset_index()
    partes = [f'{int(r["Cantidad"])} {r["cod"]}' for _, r in resumen.iterrows()]
    total = int(postes["Cantidad"].sum())

    return f"Hincado de {', '.join(partes)} (Total: {total} postes)."


def _desc_transformadores(df):

    trafos = df[df["cod"].str.contains("TS")]
    if trafos.empty:
        return None

    resumen = trafos.groupby("cod")["Cantidad"].sum().reset_index()
    partes = [f'{int(r["Cantidad"])} x {r["cod"]}' for _, r in resumen.iterrows()]
    total = int(trafos["Cantidad"].sum())

    tipo_txt = _plural("transformador", total)

    return f"Instalación de {total} {tipo_txt} en conexión {', '.join(partes)}."


def _desc_luminarias(df):

    lum = df[df["cod"].str.contains("LL")]
    if lum.empty:
        return None

    total = int(lum["Cantidad"].sum())

    potencias = []
    for cod in lum["cod"]:
        cod = str(cod).upper()
        if "W" in cod:
            try:
                potencias.append(cod.split("-")[-1])
            except:
                pass

    potencias = list(dict.fromkeys(potencias))

    if potencias:
        return f"Instalación de {total} luminarias tipo LED de {' / '.join(potencias)}."
    else:
        return f"Instalación de {total} luminarias tipo LED."


def _desc_lineas(cables):

    lineas = []

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

    return lineas


# =========================================================
# TABLA
# =========================================================
def _build_tabla(datos, prim, sec, neu, pil):

    data = [
        ["Nombre del Proyecto:", datos.get("nombre_proyecto", "SIN NOMBRE")],
        ["Código / Expediente:", datos.get("codigo_proyecto", "N/A")],
        ["Nivel de Tensión (kV):", datos.get("tension", "N/A")],
        ["Calibre Primario:", prim or "N/A"],
        ["Calibre Secundario:", sec or "N/A"],
        ["Calibre Neutro:", neu or "N/A"],
        ["Calibre Piloto:", pil or "N/A"],
        ["Fecha de Informe:", datos.get("fecha_informe", "N/A")],
        ["Responsable:", datos.get("responsable", "N/A")],
        ["Empresa:", datos.get("empresa", "N/A")],
    ]

    tabla = Table(data, colWidths=[200, 320])

    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))

    return tabla


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def hoja_info_proyecto(datos_proyecto, df_estructuras=None):

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]

    elems = []

    elems.append(Paragraph("Hoja de Información del Proyecto", styleH))
    elems.append(Spacer(1, 12))

    datos = datos_proyecto or {}
    cables = datos.get("cables_proyecto", [])

    prim, sec, neu, pil = extraer_calibres(datos)

    elems.append(_build_tabla(datos, prim, sec, neu, pil))
    elems.append(Spacer(1, 12))

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))

    lineas = []

    if isinstance(df_estructuras, pd.DataFrame) and not df_estructuras.empty:

        df = df_estructuras.copy()
        df["cod"] = df["codigodeestructura"].astype(str).str.upper()

        for fn in [_desc_postes, _desc_transformadores, _desc_luminarias]:
            res = fn(df)
            if res:
                lineas.append(res)

    lineas.extend(_desc_lineas(cables))

    if not lineas:
        lineas.append("No se cuenta con información suficiente.")

    for i, l in enumerate(lineas):
        elems.append(Paragraph(f"{i+1}. {l}", styleN))
        elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 12))

    return elems


# =========================================================
# WRAPPER
# =========================================================
def seccion_hoja_info(datos_proyecto, df_estructuras, df_mat):
    return hoja_info_proyecto(
        datos_proyecto=datos_proyecto,
        df_estructuras=df_estructuras
    )
