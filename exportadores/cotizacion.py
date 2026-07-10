# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from exportadores.pdf_base import estilo_tabla


# =========================================================
# HELPERS NUMÉRICOS
# =========================================================
def _to_float(valor, default: float = 0.0) -> float:
    try:
        if valor is None:
            return default

        if isinstance(valor, str):
            valor = (
                valor.replace("L", "")
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

        return float(valor)

    except Exception:
        return default


def _fmt_lps(valor) -> str:
    try:
        return f"L {float(valor):,.2f}"
    except Exception:
        return "L 0.00"


def _separar_cotizacion(
    df_precios: pd.DataFrame,
    tasa_isv_materiales: float = 0.15,
) -> dict:
    """
    Separa los valores de la cotización en:

    - Materiales y costos operativos.
    - ISV aplicado únicamente a materiales.
    - Suministro total con ISV.
    - Mano de obra sin ISV.

    Conserva las cantidades especiales de los cables.
    """

    resultado_vacio = {
        "materiales_sin_isv": 0.0,
        "isv_materiales": 0.0,
        "suministro_con_isv": 0.0,
        "mano_obra": 0.0,
        "total_base": 0.0,
    }

    if (
        df_precios is None
        or not isinstance(df_precios, pd.DataFrame)
        or df_precios.empty
    ):
        return resultado_vacio

    df = df_precios.copy()

    columnas_numericas = [
        "Cantidad",
        "Cantidad Material",
        "Cantidad Mano Obra",
        "Material Unitario",
        "Mano Obra Unitaria",
        "Costo Operativo Unitario",
    ]

    for columna in columnas_numericas:

        if columna not in df.columns:
            df[columna] = 0.0

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce",
        ).fillna(0.0)

    # =====================================================
    # CANTIDADES
    # =====================================================
    # Los cables pueden tener cantidades diferentes para
    # material y mano de obra.
    #
    # Las estructuras utilizan la columna Cantidad.
    cantidad_material = df["Cantidad Material"].where(
        df["Cantidad Material"] > 0,
        df["Cantidad"],
    )

    cantidad_mano_obra = df["Cantidad Mano Obra"].where(
        df["Cantidad Mano Obra"] > 0,
        df["Cantidad"],
    )

    # =====================================================
    # MATERIALES
    # =====================================================
    materiales = float(
        (
            cantidad_material
            * df["Material Unitario"]
        ).sum()
    )

    # Los costos operativos ya forman parte del suministro
    # presentado en la tabla anterior.
    costos_operativos = float(
        (
            df["Cantidad"]
            * df["Costo Operativo Unitario"]
        ).sum()
    )

    materiales_sin_isv = (
        materiales
        + costos_operativos
    )

    # =====================================================
    # MANO DE OBRA
    # =====================================================
    mano_obra = float(
        (
            cantidad_mano_obra
            * df["Mano Obra Unitaria"]
        ).sum()
    )

    # =====================================================
    # ISV SOLO SOBRE MATERIALES
    # =====================================================
    isv_materiales = (
        materiales_sin_isv
        * tasa_isv_materiales
    )

    suministro_con_isv = (
        materiales_sin_isv
        + isv_materiales
    )

    total_base = (
        suministro_con_isv
        + mano_obra
    )

    return {
        "materiales_sin_isv": round(materiales_sin_isv, 2),
        "isv_materiales": round(isv_materiales, 2),
        "suministro_con_isv": round(suministro_con_isv, 2),
        "mano_obra": round(mano_obra, 2),
        "total_base": round(total_base, 2),
    }

# =========================================================
# LOGÍSTICA DESDE STREAMLIT
# =========================================================
def _leer_logistica_streamlit() -> dict:
    """
    Lee los valores comerciales definidos en la interfaz.
    Usa los mismos nombres que tu reporte de contratista.
    """

    incluir_logistica = st.session_state.get(
        "incluir_logistica",
        True,
    )

    if not incluir_logistica:
        return {
            "horas_grua": 0.0,
            "precio_hora_grua": 0.0,
            "total_grua": 0.0,
            "costo_flete": 0.0,
            "viajes_flete": 0.0,
            "total_flete": 0.0,
            "ingenieria": 0.0,
        }

    horas_grua = _to_float(
        st.session_state.get("horas_grua", 12)
    )

    precio_hora_grua = _to_float(
        st.session_state.get("precio_hora_grua", 1700)
    )

    costo_flete = _to_float(
        st.session_state.get("costo_flete", 25000)
    )

    viajes_flete = _to_float(
        st.session_state.get("viajes_flete", 1)
    )

    ingenieria = _to_float(
        st.session_state.get(
            "ingenieria",
            st.session_state.get("gastos_ingenieria", 25000),
        )
    )

    total_grua = horas_grua * precio_hora_grua
    total_flete = costo_flete * viajes_flete

    return {
        "horas_grua": horas_grua,
        "precio_hora_grua": precio_hora_grua,
        "total_grua": total_grua,
        "costo_flete": costo_flete,
        "viajes_flete": viajes_flete,
        "total_flete": total_flete,
        "ingenieria": ingenieria,
    }


# =========================================================
# HELPERS VISUALES
# =========================================================
def _agregar_notas(elems, styles):

    elems.append(Spacer(1, 12))

    elems.append(Paragraph("<b>Notas:</b>", styles["Normal"]))
    elems.append(Spacer(1, 4))

    elems.append(Paragraph(
        "- Los precios incluyen la instalación y suministro de los materiales, estructuras y equipos descritos en el presente documento.",
        styles["Normal"],
    ))

    elems.append(Paragraph(
        "- El total del proyecto incluye los costos comerciales de grúa, flete/rastra e ingeniería cuando apliquen.",
        styles["Normal"],
    ))

    elems.append(Paragraph(
        "- La gestión de permisos ante ENEE está incluida dentro del alcance definido para el proyecto.",
        styles["Normal"],
    ))

    elems.append(Paragraph(
        "- La presente oferta tiene una validez de 30 días calendario a partir de la fecha de emisión.",
        styles["Normal"],
    ))


def _estilo_cotizacion(tabla):

    tabla.setStyle(TableStyle([

        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        # Alineación de montos
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),

        # Total final
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),

    ]))


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def generar_seccion_cotizacion_final(
    doc,
    styles,
    df_precios
):

    elems = []

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if (
        df_precios is None
        or not isinstance(df_precios, pd.DataFrame)
        or df_precios.empty
    ):
        elems.append(
            Paragraph(
                "SIN DATOS PARA COTIZACIÓN",
                styles["Normal"],
            )
        )
        return elems

    # =====================================================
    # TÍTULO CENTRADO
    # =====================================================
    styleTitulo = styles["Heading1"].clone(
        "titulo_cotizacion"
    )
    styleTitulo.alignment = TA_CENTER

    elems.append(
        Paragraph(
            "COTIZACIÓN DEL PROYECTO",
            styleTitulo,
        )
    )
    elems.append(Spacer(1, 10))

    # =====================================================
    # PREPARAR DATAFRAME
    # =====================================================
    df = df_precios.copy()

    columnas_numericas = [
        "Cantidad",
        "Cantidad Material",
        "Cantidad Mano Obra",
        "Material Unitario",
        "Mano Obra Unitaria",
        "Costo Operativo Unitario",
    ]

    for columna in columnas_numericas:

        if columna not in df.columns:
            df[columna] = 0.0

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce",
        ).fillna(0.0)

    # =====================================================
    # CANTIDADES DE MATERIAL Y MANO DE OBRA
    # =====================================================
    # Para estructuras se utiliza Cantidad.
    # Para cables se utilizan las cantidades específicas.
    cantidad_material = df["Cantidad Material"].where(
        df["Cantidad Material"] > 0,
        df["Cantidad"],
    )

    cantidad_mano_obra = df["Cantidad Mano Obra"].where(
        df["Cantidad Mano Obra"] > 0,
        df["Cantidad"],
    )

    # =====================================================
    # SUMINISTRO DE MATERIALES SIN ISV
    # =====================================================
    total_materiales = float(
        (
            cantidad_material
            * df["Material Unitario"]
        ).sum()
    )

    # Los costos operativos forman parte del suministro
    # mostrado en la tabla detallada anterior.
    total_costos_operativos = float(
        (
            df["Cantidad"]
            * df["Costo Operativo Unitario"]
        ).sum()
    )

    suministro_sin_isv = (
        total_materiales
        + total_costos_operativos
    )

    # =====================================================
    # ISV ÚNICAMENTE SOBRE SUMINISTRO
    # =====================================================
    tasa_isv_materiales = 0.15

    isv_materiales = (
        suministro_sin_isv
        * tasa_isv_materiales
    )

    suministro_con_isv = (
        suministro_sin_isv
        + isv_materiales
    )

    # =====================================================
    # MANO DE OBRA SIN ISV
    # =====================================================
    total_mano_obra = float(
        (
            cantidad_mano_obra
            * df["Mano Obra Unitaria"]
        ).sum()
    )

    # =====================================================
    # LOGÍSTICA STREAMLIT
    # =====================================================
    logistica = _leer_logistica_streamlit()

    horas_grua = logistica["horas_grua"]
    precio_hora_grua = logistica["precio_hora_grua"]
    total_grua = logistica["total_grua"]

    costo_flete = logistica["costo_flete"]
    viajes_flete = logistica["viajes_flete"]
    total_flete = logistica["total_flete"]

    ingenieria = logistica["ingenieria"]

    # =====================================================
    # TOTAL FINAL
    # =====================================================
    total_final = (
        suministro_con_isv
        + total_mano_obra
        + total_grua
        + total_flete
        + ingenieria
    )

    # =====================================================
    # DATA
    # =====================================================
    data = [
        [
            "Concepto",
            "Monto (L)",
        ],
        [
            "Suministro de materiales (ISV incluido)",
            _fmt_lps(suministro_con_isv),
        ],
        [
            "Mano de obra e instalación",
            _fmt_lps(total_mano_obra),
        ],
    ]

    if total_grua > 0:
        data.append([
            (
                f"Equipo Grúa "
                f"({horas_grua:,.0f} h x "
                f"{_fmt_lps(precio_hora_grua)})"
            ),
            _fmt_lps(total_grua),
        ])

    if total_flete > 0:
        data.append([
            (
                f"Flete / rastra "
                f"({viajes_flete:,.0f} viaje(s) x "
                f"{_fmt_lps(costo_flete)})"
            ),
            _fmt_lps(total_flete),
        ])

    if ingenieria > 0:
        data.append([
            "Gastos de Ingeniería",
            _fmt_lps(ingenieria),
        ])

    data.append([
        "TOTAL PROYECTO",
        _fmt_lps(total_final),
    ])

    # =====================================================
    # TABLA
    # =====================================================
    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.7,
            doc.width * 0.3,
        ],
        repeatRows=1,
    )

    tabla.setStyle(estilo_tabla())
    _estilo_cotizacion(tabla)

    elems.append(tabla)

    # =====================================================
    # NOTAS
    # =====================================================
    _agregar_notas(
        elems,
        styles,
    )

    return elems
