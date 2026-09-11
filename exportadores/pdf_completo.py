# -*- coding: utf-8 -*-
# exportadores/pdf_completo.py
from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
)
from reportlab.platypus.tables import TableStyle

from exportadores.pdf_base import styles, fondo_pagina
from exportadores.hoja_info import seccion_hoja_info
from exportadores.precios_estructura_pdf import generar_tabla_precios_estructura
from exportadores.cotizacion import generar_seccion_cotizacion_final
from exportadores.reporte_costos_proyecto import construir_bloque_costos


# =========================================================
# DEBUG
# =========================================================
def _log(msg: str) -> None:
    """Guarda mensajes simples de diagnóstico del PDF."""
    if "debug_pdf" not in st.session_state:
        st.session_state["debug_pdf"] = []

    st.session_state["debug_pdf"].append(msg)


# =========================================================
# HELPERS GENERALES
# =========================================================
def _df_valido(df) -> bool:
    """True cuando el objeto es un DataFrame no vacío."""
    return isinstance(df, pd.DataFrame) and not df.empty


def _to_float(valor, default: float = 0.0) -> float:
    """Conversión numérica segura."""
    try:
        if valor is None:
            return default
        return float(valor)
    except Exception:
        return default


# =========================================================
# PREPARAR DATAFRAME PARA COTIZACIÓN
# =========================================================
def _preparar_df_cotizacion(
    df_precios_estructura: pd.DataFrame,
) -> pd.DataFrame:
    """
    Asegura que exista la columna Subtotal para el generador
    de cotización, sin modificar el DataFrame original.
    """
    df_tmp = df_precios_estructura.copy()

    if "Subtotal" not in df_tmp.columns:

        if "Total Proyecto" in df_tmp.columns:
            df_tmp["Subtotal"] = df_tmp["Total Proyecto"]

        elif "TOTAL PROYECTO" in df_tmp.columns:
            df_tmp["Subtotal"] = df_tmp["TOTAL PROYECTO"]

        elif "Total" in df_tmp.columns:
            df_tmp["Subtotal"] = df_tmp["Total"]

        elif "TOTAL" in df_tmp.columns:
            df_tmp["Subtotal"] = df_tmp["TOTAL"]

        else:
            df_tmp["Subtotal"] = 0.0

    return df_tmp


# =========================================================
# EXTRAER COSTOS DE FORMA SEGURA
# =========================================================
def _extraer_costos(costos):
    """
    Extrae el resultado del motor de costos.

    Retorna:
        resultado_costos,
        df_materiales_costos,
        error
    """
    if not isinstance(costos, dict):
        return None, None, "costos no es un diccionario"

    if not costos.get("ok"):
        return (
            None,
            None,
            costos.get("error", "costos.ok es False"),
        )

    resultado = costos.get("resultado_costos_proyecto")

    # Compatibilidad con ambos nombres usados durante la refactorización.
    df_materiales_costos = costos.get("df_costos_materiales")

    if df_materiales_costos is None:
        df_materiales_costos = costos.get("df_materiales_costos")

    if not isinstance(resultado, dict):
        return (
            None,
            df_materiales_costos,
            "resultado_costos_proyecto no es válido",
        )

    return resultado, df_materiales_costos, None


# =========================================================
# PLAN DIARIO DE EJECUCIÓN
# =========================================================
def _responsable_actividad(actividad: str) -> str:
    """
    Define quién ejecuta cada actividad según el modelo actual.
    """
    actividad = str(actividad).strip().upper()

    if actividad == "AGUJEROS":
        return "Subcontrato local"

    if actividad == "LEVANTAMIENTO":
        return "Contratista"

    return "Cuadrilla principal"


def _descripcion_meta(
    actividad: str,
    cantidad: float,
    unidad: str,
) -> str:
    """
    Convierte una cantidad diaria en texto operativo legible.
    """
    actividad = str(actividad).strip()
    unidad = str(unidad or "").strip().lower()

    if actividad == "Levantamiento":
        return "Replanteo general del proyecto"

    cantidad = _to_float(cantidad)

    if unidad == "m":
        return f"{cantidad:,.0f} m"

    nombres = {
        "agujero": ("agujero", "agujeros"),
        "poste": ("poste", "postes"),
        "retenida": ("retenida", "retenidas"),
        "transformador": ("transformador", "transformadores"),
        "luminaria": ("luminaria", "luminarias"),
        "estructura": ("estructura", "estructuras"),
    }

    if unidad in nombres:
        singular, plural = nombres[unidad]
        texto = singular if cantidad == 1 else plural
        return f"{cantidad:,.0f} {texto}"

    return f"{cantidad:,.0f} {unidad}".strip()


def _repartir_cantidad_diaria(
    cantidad: float,
    dias: int,
) -> list[float]:
    """
    Reparte una cantidad total entre jornadas completas,
    manteniendo exactamente la cantidad total.

    Ejemplos:
        28 / 4  -> [7, 7, 7, 7]
        31 / 3  -> [11, 10, 10]
        722 / 3 -> [241, 241, 240]
        38 / 10 -> [4, 4, 4, 4, 4, 4, 4, 4, 3, 3]
    """
    if dias <= 0:
        return []

    total = int(round(max(_to_float(cantidad), 0.0)))

    base = total // dias
    resto = total % dias

    return [
        float(base + (1 if i < resto else 0))
        for i in range(dias)
    ]


def construir_plan_diario(cronograma: list) -> list[dict]:
    """
    Expande cronograma_resumen a una fila por día.
    No recalcula rendimientos ni duración.
    """
    if not isinstance(cronograma, list):
        return []

    filas = []

    for item in cronograma:

        if not isinstance(item, dict):
            continue

        actividad = str(item.get("actividad", "")).strip()
        duracion = int(_to_float(item.get("duracion_dias", 0)))
        inicio = item.get("inicio")
        cantidad = _to_float(item.get("cantidad", 0))
        unidad = str(item.get("unidad", "") or "")

        if duracion <= 0 or not inicio:
            continue

        reparto = _repartir_cantidad_diaria(
            cantidad,
            duracion,
        )

        for offset in range(duracion):

            dia = int(inicio) + offset

            cantidad_dia = (
                reparto[offset]
                if offset < len(reparto)
                else 0.0
            )

            filas.append({
                "dia": dia,
                "actividad": actividad,
                "meta": _descripcion_meta(
                    actividad,
                    cantidad_dia,
                    unidad,
                ),
                "responsable": _responsable_actividad(
                    actividad
                ),
            })

    return sorted(
        filas,
        key=lambda x: x["dia"],
    )


def tabla_plan_diario(cronograma):
    """
    Construye la tabla visual del plan diario.
    """
    plan = construir_plan_diario(cronograma)

    if not plan:
        return None

    data = [[
        "DÍA",
        "ACTIVIDAD",
        "META DEL DÍA",
        "RESPONSABLE",
    ]]

    for fila in plan:
        data.append([
            f"Día {fila['dia']}",
            fila["actividad"],
            fila["meta"],
            fila["responsable"],
        ])

    tabla = Table(
        data,
        colWidths=[55, 165, 150, 150],
        repeatRows=1,
    )

    tabla.setStyle(TableStyle([
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#1F3A5F"),
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white,
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold",
        ),
        (
            "FONTNAME",
            (0, 1),
            (-1, -1),
            "Helvetica",
        ),
        (
            "FONTSIZE",
            (0, 0),
            (-1, -1),
            8,
        ),
        (
            "ALIGN",
            (0, 0),
            (0, -1),
            "CENTER",
        ),
        (
            "ALIGN",
            (1, 0),
            (-1, 0),
            "CENTER",
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.4,
            colors.grey,
        ),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#F5F7FA"),
            ],
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]))

    return tabla


# =========================================================
# PDF COMPLETO
# =========================================================
def generar_pdf_completo(
    df_materiales,
    df_estructuras,
    df_precios_estructura,
    datos_proyecto,
    costos=None,
):
    """
    Genera el reporte completo del proyecto.

    Secciones:
        1. Ficha general
        2. Presupuesto de estructuras
        3. Cotización
        4. Costos / rentabilidad
        5. Plan diario de ejecución

    El cronograma se toma del motor de costos.
    Este archivo NO recalcula duración ni productividad.
    """

    _log("📄 INICIO PDF COMPLETO")

    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=120,
        bottomMargin=50,
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
    )

    template = PageTemplate(
        id="normal",
        frames=[frame],
        onPage=fondo_pagina,
    )

    doc.addPageTemplates([template])

    elems = []

    # =====================================================
    # 1. HOJA DE INFORMACIÓN
    # =====================================================
    _log("📌 PDF: agregando hoja de información")

    elems.extend(
        seccion_hoja_info(
            datos_proyecto=datos_proyecto,
            df_estructuras=df_estructuras,
            df_mat=df_materiales,
            doc_width=doc.width,
        )
    )

    elems.append(PageBreak())

    # =====================================================
    # 2. PRESUPUESTO
    # =====================================================
    _log("📌 PDF: agregando presupuesto de estructuras")

    elems.append(
        Paragraph(
            "PRESUPUESTO DE ESTRUCTURAS",
            styles["Heading1"],
        )
    )

    elems.append(Spacer(1, 10))

    if _df_valido(df_precios_estructura):

        elems.extend(
            generar_tabla_precios_estructura(
                df_precios_estructura,
                df_estructuras,
            )
        )

    else:
        elems.append(
            Paragraph(
                "No se dispone de información de precios de estructuras.",
                styles["Normal"],
            )
        )

    elems.append(PageBreak())

    # =====================================================
    # 3. COTIZACIÓN
    # =====================================================
    _log("📌 PDF: agregando cotización")

    if _df_valido(df_precios_estructura):

        df_tmp = _preparar_df_cotizacion(
            df_precios_estructura
        )

        elems.extend(
            generar_seccion_cotizacion_final(
                doc,
                styles,
                df_tmp,
            )
        )

    else:
        elems.append(
            Paragraph(
                "No se puede generar la cotización por falta de precios.",
                styles["Normal"],
            )
        )

    elems.append(PageBreak())

    # =====================================================
    # 4. COSTOS DE PROYECTO
    # =====================================================
    _log("📌 PDF: agregando costos internos")

    elems.append(
        Paragraph(
            "COSTOS DE PROYECTO",
            styles["Heading1"],
        )
    )

    elems.append(Spacer(1, 10))

    (
        resultado_costos,
        df_materiales_costos,
        error_costos,
    ) = _extraer_costos(costos)

    if error_costos:

        _log(
            f"⚠️ PDF: no se agregó bloque de costos: {error_costos}"
        )

        elems.append(
            Paragraph(
                (
                    "No se dispone del cálculo de costos de proyecto."
                    f"<br/><br/><b>Detalle:</b> {error_costos}"
                ),
                styles["Normal"],
            )
        )

    else:

        construir_bloque_costos(
            elems,
            styles,
            resultado_costos,
            df_materiales_costos,
        )

        _log(
            "✅ PDF: bloque de costos agregado correctamente"
        )

    # =====================================================
    # 5. PLAN DIARIO DE EJECUCIÓN
    # =====================================================
    if (
        not error_costos
        and isinstance(resultado_costos, dict)
    ):

        cronograma = resultado_costos.get(
            "cronograma_resumen",
            []
        )

        tabla_plan = tabla_plan_diario(
            cronograma
        )

        if tabla_plan is not None:

            elems.append(PageBreak())

            _log(
                "📌 PDF: agregando plan diario de ejecución"
            )

            elems.append(
                Paragraph(
                    "PLAN DIARIO DE EJECUCIÓN",
                    styles["Heading1"],
                )
            )

            elems.append(
                Spacer(
                    1,
                    10,
                )
            )

            elems.append(
                Paragraph(
                    (
                        "Programación referencial elaborada a partir de "
                        "los rendimientos promedio de campo considerados "
                        "para la ejecución del proyecto."
                    ),
                    styles["Normal"],
                )
            )

            elems.append(
                Spacer(
                    1,
                    10,
                )
            )

            elems.append(
                tabla_plan
            )

            _log(
                "✅ PDF: plan diario agregado correctamente"
            )

    # =====================================================
    # BUILD
    # =====================================================
    doc.build(elems)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    _log("✅ PDF GENERADO")

    return pdf_bytes
