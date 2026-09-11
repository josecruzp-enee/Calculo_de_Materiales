# -*- coding: utf-8 -*-
"""
exportadores/cotizacion.py

Genera la sección de cotización comercial del proyecto.

Responsabilidades:
- Preparar datos recibidos.
- Consolidar suministro, mano de obra y costos comerciales.
- Renderizar la tabla de cotización en PDF.

No calcula materiales ni cantidades de estructuras.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from exportadores.pdf_base import estilo_tabla


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

TASA_ISV_MATERIALES = 0.15

# Espacio temporal para trabajos adicionales/desmontajes.
# No contiene datos específicos de ningún proyecto.
INCLUIR_ADICIONALES = False

ADICIONALES: list[dict[str, Any]] = [
    # Ejemplo:
    # {
    #     "descripcion": "Desmontaje de poste PC-35",
    #     "cantidad": 1,
    #     "precio_unitario": 2500,
    # },
]


# ==========================================================
# UTILIDADES
# ==========================================================

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

    except (TypeError, ValueError):
        return default


def _fmt_lps(valor) -> str:
    return f"L {_to_float(valor):,.2f}"


def _df_valido(df) -> bool:
    return isinstance(df, pd.DataFrame) and not df.empty


# ==========================================================
# PREPARACIÓN DE DATOS
# ==========================================================

COLUMNAS_NUMERICAS = (
    "Cantidad",
    "Cantidad Material",
    "Cantidad Mano Obra",
    "Material Unitario",
    "Mano Obra Unitaria",
    "Costo Operativo Unitario",
)


def _preparar_dataframe(df_precios: pd.DataFrame) -> pd.DataFrame:
    """Normaliza únicamente las columnas requeridas por la cotización."""

    if not _df_valido(df_precios):
        raise ValueError("df_precios inválido o vacío")

    df = df_precios.copy()

    for columna in COLUMNAS_NUMERICAS:
        if columna not in df.columns:
            df[columna] = 0.0

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce",
        ).fillna(0.0)

    return df


def _obtener_cantidades(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Obtiene cantidades comerciales.

    Permite que cables u otros conceptos tengan cantidades distintas
    para materiales y mano de obra.
    """

    cantidad_material = df["Cantidad Material"].where(
        df["Cantidad Material"] > 0,
        df["Cantidad"],
    )

    cantidad_mano_obra = df["Cantidad Mano Obra"].where(
        df["Cantidad Mano Obra"] > 0,
        df["Cantidad"],
    )

    return cantidad_material, cantidad_mano_obra


# ==========================================================
# SUMINISTRO Y MANO DE OBRA
# ==========================================================

def _calcular_suministro(
    df: pd.DataFrame,
    cantidad_material: pd.Series,
) -> dict:
    """Calcula materiales, costos operativos e ISV."""

    materiales = float(
        (cantidad_material * df["Material Unitario"]).sum()
    )

    costos_operativos = float(
        (df["Cantidad"] * df["Costo Operativo Unitario"]).sum()
    )

    suministro_sin_isv = materiales + costos_operativos
    isv = suministro_sin_isv * TASA_ISV_MATERIALES
    suministro_con_isv = suministro_sin_isv + isv

    return {
        "materiales": round(materiales, 2),
        "costos_operativos": round(costos_operativos, 2),
        "suministro_sin_isv": round(suministro_sin_isv, 2),
        "isv": round(isv, 2),
        "suministro_con_isv": round(suministro_con_isv, 2),
    }


def _calcular_mano_obra(
    df: pd.DataFrame,
    cantidad_mano_obra: pd.Series,
) -> float:
    """Calcula el total comercial de mano de obra."""

    total = (
        cantidad_mano_obra
        * df["Mano Obra Unitaria"]
    ).sum()

    return round(float(total), 2)


# ==========================================================
# ADICIONALES / DESMONTAJES
# ==========================================================

def _calcular_adicionales() -> tuple[float, list[dict]]:
    """
    Calcula conceptos manuales adicionales.

    Se deja como punto controlado para desmontajes,
    reubicaciones u otros trabajos extraordinarios.
    """

    if not INCLUIR_ADICIONALES:
        return 0.0, []

    detalle = []
    total = 0.0

    for item in ADICIONALES:
        descripcion = str(item.get("descripcion", "Trabajo adicional")).strip()
        cantidad = _to_float(item.get("cantidad"))
        precio_unitario = _to_float(item.get("precio_unitario"))

        if cantidad <= 0 or precio_unitario < 0:
            continue

        subtotal = cantidad * precio_unitario
        total += subtotal

        detalle.append({
            "descripcion": descripcion,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "total": subtotal,
        })

    return round(total, 2), detalle


# ==========================================================
# LOGÍSTICA / COSTOS COMERCIALES
# ==========================================================

def _leer_logistica_streamlit() -> dict:
    """
    Lee los parámetros comerciales definidos en la interfaz.

    Mantiene compatibilidad con el estado actual de la aplicación.
    """

    if not st.session_state.get("incluir_logistica", True):
        return {
            "horas_grua": 0.0,
            "precio_hora_grua": 0.0,
            "total_grua": 0.0,
            "costo_flete": 0.0,
            "viajes_flete": 0.0,
            "total_flete": 0.0,
            "ingenieria": 0.0,
        }

    horas_grua = _to_float(st.session_state.get("horas_grua", 12))
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

    return {
        "horas_grua": horas_grua,
        "precio_hora_grua": precio_hora_grua,
        "total_grua": round(horas_grua * precio_hora_grua, 2),
        "costo_flete": costo_flete,
        "viajes_flete": viajes_flete,
        "total_flete": round(costo_flete * viajes_flete, 2),
        "ingenieria": round(ingenieria, 2),
    }


# ==========================================================
# CONSOLIDACIÓN COMERCIAL
# ==========================================================

def _calcular_cotizacion(df_precios: pd.DataFrame) -> dict:
    """
    Consolida todos los componentes económicos de la cotización.

    Esta es la única función que arma el resultado comercial completo.
    """

    df = _preparar_dataframe(df_precios)

    cantidad_material, cantidad_mano_obra = _obtener_cantidades(df)

    suministro = _calcular_suministro(
        df,
        cantidad_material,
    )

    mano_obra = _calcular_mano_obra(
        df,
        cantidad_mano_obra,
    )

    total_adicionales, adicionales = _calcular_adicionales()
    logistica = _leer_logistica_streamlit()

    total_final = (
        suministro["suministro_con_isv"]
        + mano_obra
        + total_adicionales
        + logistica["total_grua"]
        + logistica["total_flete"]
        + logistica["ingenieria"]
    )

    return {
        **suministro,
        "mano_obra": mano_obra,
        "adicionales": adicionales,
        "total_adicionales": total_adicionales,
        "logistica": logistica,
        "total_final": round(total_final, 2),
    }


# ==========================================================
# CONSTRUCCIÓN DE FILAS
# ==========================================================

def _filas_cotizacion(resultado: dict) -> list:
    """Convierte el resultado comercial en filas para el PDF."""

    logistica = resultado["logistica"]

    filas = [
        ["Concepto", "Monto (L)"],
        [
            "Suministro de materiales (ISV incluido)",
            _fmt_lps(resultado["suministro_con_isv"]),
        ],
        [
            "Mano de obra e instalación",
            _fmt_lps(resultado["mano_obra"]),
        ],
    ]

    # ------------------------------------------------------
    # Adicionales / desmontajes
    # ------------------------------------------------------
    if resultado["total_adicionales"] > 0:
        filas.append([
            "Trabajos adicionales / desmontajes",
            _fmt_lps(resultado["total_adicionales"]),
        ])

    # ------------------------------------------------------
    # Grúa
    # ------------------------------------------------------
    if logistica["total_grua"] > 0:
        descripcion = (
            f"Equipo Grúa "
            f"({logistica['horas_grua']:,.0f} h x "
            f"{_fmt_lps(logistica['precio_hora_grua'])})"
        )

        filas.append([
            descripcion,
            _fmt_lps(logistica["total_grua"]),
        ])

    # ------------------------------------------------------
    # Flete
    # ------------------------------------------------------
    if logistica["total_flete"] > 0:
        descripcion = (
            f"Flete / rastra "
            f"({logistica['viajes_flete']:,.0f} viaje(s) x "
            f"{_fmt_lps(logistica['costo_flete'])})"
        )

        filas.append([
            descripcion,
            _fmt_lps(logistica["total_flete"]),
        ])

    # ------------------------------------------------------
    # Ingeniería
    # ------------------------------------------------------
    if logistica["ingenieria"] > 0:
        filas.append([
            "Gastos de Ingeniería",
            _fmt_lps(logistica["ingenieria"]),
        ])

    filas.append([
        "TOTAL PROYECTO",
        _fmt_lps(resultado["total_final"]),
    ])

    return filas


# ==========================================================
# ESTILOS
# ==========================================================

def _estilo_cotizacion(tabla: Table) -> None:
    """Aplica únicamente los estilos particulares de la cotización."""

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        ("ALIGN", (1, 1), (1, -1), "RIGHT"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))


def _titulo_cotizacion(styles):
    """Crea el estilo del título sin modificar los estilos globales."""

    estilo = styles["Heading1"].clone("titulo_cotizacion")
    estilo.alignment = TA_CENTER
    return estilo


# ==========================================================
# NOTAS
# ==========================================================

NOTAS_COTIZACION = (
    "Los precios incluyen la instalación y suministro de los materiales, "
    "estructuras y equipos descritos en el presente documento.",

    "El total del proyecto incluye los costos comerciales de grúa, "
    "flete/rastra e ingeniería cuando apliquen.",

    "La gestión de permisos ante ENEE está incluida dentro del alcance "
    "definido para el proyecto.",

    "La presente oferta tiene una validez de 30 días calendario a partir "
    "de la fecha de emisión.",
)


def _agregar_notas(elems, styles) -> None:
    elems.append(Spacer(1, 12))
    elems.append(Paragraph("<b>Notas:</b>", styles["Normal"]))
    elems.append(Spacer(1, 4))

    for nota in NOTAS_COTIZACION:
        elems.append(
            Paragraph(f"- {nota}", styles["Normal"])
        )


# ==========================================================
# FUNCIÓN PÚBLICA
# ==========================================================

def generar_seccion_cotizacion_final(
    doc,
    styles,
    df_precios: pd.DataFrame,
):
    """
    Genera los flowables ReportLab correspondientes a la cotización.

    Esta función coordina:
        datos -> cálculo comercial -> filas -> tabla -> notas
    """

    elems = []

    if not _df_valido(df_precios):
        elems.append(
            Paragraph(
                "SIN DATOS PARA COTIZACIÓN",
                styles["Normal"],
            )
        )
        return elems

    # ------------------------------------------------------
    # Título
    # ------------------------------------------------------
    elems.append(
        Paragraph(
            "COTIZACIÓN DEL PROYECTO",
            _titulo_cotizacion(styles),
        )
    )
    elems.append(Spacer(1, 10))

    # ------------------------------------------------------
    # Resultado comercial
    # ------------------------------------------------------
    resultado = _calcular_cotizacion(df_precios)
    data = _filas_cotizacion(resultado)

    # ------------------------------------------------------
    # Tabla
    # ------------------------------------------------------
    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.70,
            doc.width * 0.30,
        ],
        repeatRows=1,
    )

    tabla.setStyle(estilo_tabla())
    _estilo_cotizacion(tabla)

    elems.append(tabla)

    # ------------------------------------------------------
    # Notas
    # ------------------------------------------------------
    _agregar_notas(elems, styles)

    return elems
