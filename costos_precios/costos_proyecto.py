# -*- coding: utf-8 -*-
from __future__ import annotations

import math

from typing import Dict, Any, Optional, Tuple
import pandas as pd


# =========================================================
# UTILIDADES SEGURAS
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


def _safe_sum(series: pd.Series) -> float:
    try:
        return float(
            pd.to_numeric(series, errors="coerce")
            .fillna(0)
            .sum()
        )
    except Exception:
        return 0.0


def _normalizar_texto(valor) -> str:
    if valor is None:
        return ""

    texto = str(valor).upper().strip()

    reemplazos = {
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ñ": "N",
    }

    for a, b in reemplazos.items():
        texto = texto.replace(a, b)

    return texto


def _obtener_columna(df: pd.DataFrame, posibles: list[str]) -> Optional[str]:
    if df is None or df.empty:
        return None

    columnas_norm = {
        _normalizar_texto(col): col
        for col in df.columns
    }

    for nombre in posibles:
        nombre_norm = _normalizar_texto(nombre)

        if nombre_norm in columnas_norm:
            return columnas_norm[nombre_norm]

    return None


def _leer_session_state() -> Dict[str, Any]:
    """
    Lee Streamlit de forma segura.
    Si el cálculo se ejecuta fuera de Streamlit, devuelve {}.
    """

    try:
        import streamlit as st
        return st.session_state
    except Exception:
        return {}


def _get_valor(
    entrada,
    ss: Dict[str, Any],
    nombre: str,
    default=0,
    alternativas: Optional[list[str]] = None,
):
    """
    Lee primero desde entrada y luego desde st.session_state.
    Permite alternativas de nombres para mantener compatibilidad.
    """

    alternativas = alternativas or []

    if entrada is not None and hasattr(entrada, nombre):
        return getattr(entrada, nombre)

    if nombre in ss:
        return ss.get(nombre)

    for alt in alternativas:
        if entrada is not None and hasattr(entrada, alt):
            return getattr(entrada, alt)

        if alt in ss:
            return ss.get(alt)

    return default


# =========================================================
# EXTRAER MÉTRICAS DE ESTRUCTURAS
# =========================================================
def _extraer_metricas_estructuras(
    df_estructuras_global: Optional[pd.DataFrame],
) -> Tuple[int, int, int]:

    if df_estructuras_global is None or df_estructuras_global.empty:
        return 0, 0, 0

    df = df_estructuras_global.copy()

    col_estructura = _obtener_columna(
        df,
        ["Estructura", "Codigo", "Código", "codigodeestructura"],
    )

    col_cantidad = _obtener_columna(
        df,
        ["Cantidad", "Cant", "CANT"],
    )

    if not col_estructura or not col_cantidad:
        return 0, 0, 0

    df[col_estructura] = (
        df[col_estructura]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df[col_cantidad] = pd.to_numeric(
        df[col_cantidad],
        errors="coerce",
    ).fillna(0)

    total_estructuras = int(df[col_cantidad].sum())

    num_postes = int(
        df[
            df[col_estructura].str.startswith("PC", na=False)
        ][col_cantidad].sum()
    )

    num_retenidas = int(
        df[
            df[col_estructura].str.startswith("R-", na=False)
        ][col_cantidad].sum()
    )

    return total_estructuras, num_postes, num_retenidas


# =========================================================
# EXTRAER LONGITUDES DE CABLE
# =========================================================
# =========================================================
# EXTRAER LONGITUDES DE CABLE
# MISMA LÓGICA QUE CONTRATISTA C2
# =========================================================
def _extraer_longitudes(
    df_cables: Optional[pd.DataFrame],
) -> Tuple[float, float]:

    if df_cables is None or df_cables.empty:
        return 0.0, 0.0

    total_mt = 0.0
    total_bt = 0.0
    total_n = 0.0

    for _, c in df_cables.iterrows():

        tipo = str(c.get("Tipo", "")).upper().strip()

        try:
            longitud = float(c.get("Total Cable (m)", 0))
        except Exception:
            continue

        if longitud <= 0:
            continue

        if tipo == "MT":
            total_mt += longitud

        elif tipo == "BT":
            fases = str(c.get("Fases", "")).upper().strip()

            factor = 1
            if "3" in fases:
                factor = 3
            elif "2" in fases:
                factor = 2

            longitud_real = longitud / factor
            total_bt += longitud_real / 2

        elif tipo == "N":
            total_n += longitud

    n_extra = max(total_n - total_bt, 0)

    # Aquí no se devuelve n_extra porque tu motor actual solo recibe MT y BT.
    # Si después querés cobrar el neutro extra separado, hay que ampliar el motor.
    return round(total_mt, 2), round(total_bt, 2)
# =========================================================
# VALIDAR MATERIALES
# =========================================================
def _validar_materiales(
    df_materiales_costos: Optional[pd.DataFrame],
) -> None:

    if df_materiales_costos is None or df_materiales_costos.empty:
        raise ValueError("No hay materiales con costos.")

    col_costo = _obtener_columna(
        df_materiales_costos,
        ["Costo Total", "Total", "Importe", "Monto"],
    )

    if not col_costo:
        raise ValueError(
            "df_materiales_costos debe tener una columna de costo: "
            "'Costo Total', 'Total', 'Importe' o 'Monto'."
        )


# =========================================================
# CLASIFICAR COSTOS DESDE TABLA DE MATERIALES
# =========================================================
def _clasificar_costos_desde_materiales(
    df_materiales_costos: pd.DataFrame,
) -> Dict[str, float]:

    df = df_materiales_costos.copy()

    col_costo = _obtener_columna(
        df,
        ["Costo Total", "Total", "Importe", "Monto"],
    )

    col_desc = _obtener_columna(
        df,
        [
            "Descripción",
            "Descripcion",
            "Material",
            "Concepto",
            "Estructura",
            "Codigo",
            "Código",
        ],
    )

    col_categoria = _obtener_columna(
        df,
        [
            "Categoria",
            "Categoría",
            "Rubro",
            "Tipo",
            "Clasificacion",
            "Clasificación",
        ],
    )

    df[col_costo] = pd.to_numeric(
        df[col_costo],
        errors="coerce",
    ).fillna(0)

    costo_materiales = 0.0
    costo_cuadrilla = 0.0
    costo_agujeros = 0.0
    costo_grua = 0.0
    costo_flete = 0.0
    costo_enee = 0.0
    costo_ingenieria = 0.0
    costo_otros = 0.0

    for _, row in df.iterrows():
        monto = _to_float(row.get(col_costo, 0))

        texto = ""

        if col_desc:
            texto += " " + _normalizar_texto(row.get(col_desc, ""))

        if col_categoria:
            texto += " " + _normalizar_texto(row.get(col_categoria, ""))

        if "GRUA" in texto:
            costo_grua += monto

        elif "FLETE" in texto or "TRANSPORTE" in texto:
            costo_flete += monto

        elif "AGUJERO" in texto or "EXCAVACION" in texto:
            costo_agujeros += monto

        elif (
            "CUADRILLA" in texto
            or "MANO DE OBRA" in texto
            or "INSTALACION" in texto
        ):
            costo_cuadrilla += monto

        elif "INGENIERIA" in texto:
            costo_ingenieria += monto

        elif (
            "ENEE" in texto
            or "PERMISO" in texto
            or "GESTION" in texto
        ):
            costo_enee += monto

        elif "MATERIAL" in texto or "SUMINISTRO" in texto:
            costo_materiales += monto

        else:
            costo_materiales += monto

    return {
        "costo_materiales": float(costo_materiales),
        "costo_cuadrilla": float(costo_cuadrilla),
        "costo_agujeros": float(costo_agujeros),
        "costo_grua": float(costo_grua),
        "costo_flete": float(costo_flete),
        "costo_enee": float(costo_enee),
        "costo_ingenieria": float(costo_ingenieria),
        "costo_otros": float(costo_otros),
    }


# =========================================================
# COSTOS MANUALES ADICIONALES
# =========================================================
def _extraer_costos_manuales(entrada) -> Dict[str, float]:
    """
    Estos son costos adicionales manuales.
    No son los valores principales de Streamlit de grúa/flete/ingeniería,
    para evitar duplicarlos.
    """

    return {
        "costo_cuadrilla_manual": _to_float(
            getattr(entrada, "costo_cuadrilla", 0)
        ),
        "costo_agujeros_manual": _to_float(
            getattr(entrada, "costo_agujeros", 0)
        ),
        "costo_grua_manual": _to_float(
            getattr(entrada, "costo_grua_manual", 0)
        ),
        "costo_flete_manual": _to_float(
            getattr(entrada, "costo_flete_manual", 0)
        ),
        "costo_enee_manual": _to_float(
            getattr(entrada, "costo_enee_manual", 0)
        ),
        "costo_ingenieria_manual": _to_float(
            getattr(entrada, "costo_ingenieria_manual", 0)
        ),
    }


# =========================================================
# LEER PARÁMETROS COMERCIALES / OPERATIVOS
# =========================================================
def _leer_parametros_operativos(entrada=None) -> Dict[str, float]:

    ss = _leer_session_state()

    costo_agujero_unitario = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_agujero_unitario",
            500,
        ),
        500,
    )

    costo_cuadrilla_dia = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_cuadrilla_dia",
            10000,
        ),
        10000,
    )

    horas_jornada = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_jornada",
            8,
        ),
        8,
    )

    horas_por_poste = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_poste",
            0.75,
        ),
        0.75,
    )

    horas_por_estructura = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_estructura",
            0.50,
        ),
        0.50,
    )

    horas_por_retenida = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_retenida",
            0.50,
        ),
        0.50,
    )

    costo_tendido_mt_m = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_tendido_mt_m",
            0,
        ),
        0,
    )

    costo_tendido_bt_m = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_tendido_bt_m",
            0,
        ),
        0,
    )

    horas_grua = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_grua",
            0,
        ),
        0,
    )

    precio_hora_grua = _to_float(
        _get_valor(
            entrada,
            ss,
            "precio_hora_grua",
            1500,
            alternativas=["costo_hora_grua"],
        ),
        1500,
    )

    costo_flete_unitario = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_flete",
            0,
            alternativas=["flete_rastra"],
        ),
        0,
    )

    viajes_flete = _to_float(
        _get_valor(
            entrada,
            ss,
            "viajes_flete",
            1,
        ),
        1,
    )

    costo_enee = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_enee",
            0,
        ),
        0,
    )

    costo_ingenieria = _to_float(
        _get_valor(
            entrada,
            ss,
            "gastos_ingenieria",
            0,
            alternativas=["ingenieria"],
        ),
        0,
    )

    porcentaje_contingencia = _to_float(
        _get_valor(
            entrada,
            ss,
            "porcentaje_contingencia",
            5,
        ),
        5,
    )

    incluir_logistica_en_venta = bool(
        _get_valor(
            entrada,
            ss,
            "incluir_logistica_en_venta",
            True,
        )
    )

    incluir_logistica = bool(
        _get_valor(
            entrada,
            ss,
            "incluir_logistica",
            True,
        )
    )

    if not incluir_logistica:
        horas_grua = 0.0
        precio_hora_grua = 0.0
        costo_flete_unitario = 0.0
        viajes_flete = 0.0
        costo_ingenieria = 0.0

    total_grua = horas_grua * precio_hora_grua
    total_flete = costo_flete_unitario * viajes_flete

    costo_hora_cuadrilla = (
        costo_cuadrilla_dia / horas_jornada
        if horas_jornada > 0
        else 0.0
    )

    return {
        "costo_agujero_unitario": costo_agujero_unitario,
        "costo_cuadrilla_dia": costo_cuadrilla_dia,
        "horas_jornada": horas_jornada,
        "costo_hora_cuadrilla": costo_hora_cuadrilla,
        "horas_por_poste": horas_por_poste,
        "horas_por_estructura": horas_por_estructura,
        "horas_por_retenida": horas_por_retenida,
        "costo_tendido_mt_m": costo_tendido_mt_m,
        "costo_tendido_bt_m": costo_tendido_bt_m,

        "horas_grua": horas_grua,
        "precio_hora_grua": precio_hora_grua,
        "costo_hora_grua": precio_hora_grua,
        "costo_grua": total_grua,

        "costo_flete_unitario": costo_flete_unitario,
        "viajes_flete": viajes_flete,
        "costo_flete": total_flete,

        "costo_enee": costo_enee,
        "costo_ingenieria": costo_ingenieria,
        "porcentaje_contingencia": porcentaje_contingencia,

        "incluir_logistica": incluir_logistica,
        "incluir_logistica_en_venta": incluir_logistica_en_venta,
    }


# =========================================================
# CALCULAR COSTOS REALES POR ACTIVIDAD
# =========================================================
def _calcular_costos_actividades(
    entrada,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
    num_postes: int,
    num_retenidas: int,
) -> Dict[str, Any]:

    params = _leer_parametros_operativos(entrada)

    costo_agujero_unitario = params["costo_agujero_unitario"]
    costo_hora_cuadrilla = params["costo_hora_cuadrilla"]

    horas_por_poste = params["horas_por_poste"]
    horas_por_estructura = params["horas_por_estructura"]
    horas_por_retenida = params["horas_por_retenida"]

    costo_tendido_mt_m = params["costo_tendido_mt_m"]
    costo_tendido_bt_m = params["costo_tendido_bt_m"]

    horas_grua = params["horas_grua"]
    precio_hora_grua = params["precio_hora_grua"]

    costo_grua = params["costo_grua"]
    costo_flete = params["costo_flete"]
    costo_enee = params["costo_enee"]
    costo_ingenieria = params["costo_ingenieria"]

    cantidad_agujeros = int(num_postes + num_retenidas)

    horas_postes = num_postes * horas_por_poste
    horas_estructuras = total_estructuras * horas_por_estructura
    horas_retenidas = num_retenidas * horas_por_retenida

    costo_agujeros = cantidad_agujeros * costo_agujero_unitario
    costo_hincado_postes = horas_postes * costo_hora_cuadrilla
    costo_armado_estructuras = horas_estructuras * costo_hora_cuadrilla
    costo_instalacion_retenidas = horas_retenidas * costo_hora_cuadrilla
    costo_tendido_mt = longitud_primario_m * costo_tendido_mt_m
    costo_tendido_bt = longitud_secundario_m * costo_tendido_bt_m

    actividades = [
        {
            "actividad": "Apertura de agujeros",
            "unidad": "agujero",
            "cantidad": cantidad_agujeros,
            "precio_unitario": costo_agujero_unitario,
            "total": costo_agujeros,
            "criterio": f"{num_postes} postes + {num_retenidas} retenidas",
        },
        {
            "actividad": "Hincado y aplomado de postes",
            "unidad": "hora",
            "cantidad": horas_postes,
            "precio_unitario": costo_hora_cuadrilla,
            "total": costo_hincado_postes,
            "criterio": f"{num_postes} postes x {horas_por_poste} h/poste",
        },
        {
            "actividad": "Armado e instalación de estructuras",
            "unidad": "hora",
            "cantidad": horas_estructuras,
            "precio_unitario": costo_hora_cuadrilla,
            "total": costo_armado_estructuras,
            "criterio": f"{total_estructuras} estructuras x {horas_por_estructura} h/estructura",
        },
        {
            "actividad": "Instalación de retenidas",
            "unidad": "hora",
            "cantidad": horas_retenidas,
            "precio_unitario": costo_hora_cuadrilla,
            "total": costo_instalacion_retenidas,
            "criterio": f"{num_retenidas} retenidas x {horas_por_retenida} h/retenida",
        },
        {
            "actividad": "Tendido de conductor primario MT",
            "unidad": "m",
            "cantidad": longitud_primario_m,
            "precio_unitario": costo_tendido_mt_m,
            "total": costo_tendido_mt,
            "criterio": "Longitud primaria x costo por metro",
        },
        {
            "actividad": "Tendido de conductor secundario BT",
            "unidad": "m",
            "cantidad": longitud_secundario_m,
            "precio_unitario": costo_tendido_bt_m,
            "total": costo_tendido_bt,
            "criterio": "Longitud secundaria x costo por metro",
        },
        {
            "actividad": "Equipo grúa",
            "unidad": "hora",
            "cantidad": horas_grua,
            "precio_unitario": precio_hora_grua,
            "total": costo_grua,
            "criterio": "Horas grúa x precio hora",
        },
        {
            "actividad": "Flete / transporte",
            "unidad": "viaje",
            "cantidad": params["viajes_flete"],
            "precio_unitario": params["costo_flete_unitario"],
            "total": costo_flete,
            "criterio": "Viajes x costo por viaje",
        },
        {
            "actividad": "Gestiones ENEE / permisos",
            "unidad": "global",
            "cantidad": 1 if costo_enee > 0 else 0,
            "precio_unitario": costo_enee,
            "total": costo_enee,
            "criterio": "Gestión administrativa / permisos",
        },
        {
            "actividad": "Ingeniería y administración técnica",
            "unidad": "global",
            "cantidad": 1 if costo_ingenieria > 0 else 0,
            "precio_unitario": costo_ingenieria,
            "total": costo_ingenieria,
            "criterio": "Diseño, revisión y coordinación técnica",
        },
    ]

    actividades = [
        item for item in actividades
        if _to_float(item.get("total", 0)) > 0
    ]

    costo_cuadrilla = (
        costo_hincado_postes
        + costo_armado_estructuras
        + costo_instalacion_retenidas
        + costo_tendido_mt
        + costo_tendido_bt
    )

    return {
        "detalle_costos_actividades": actividades,

        "costo_agujeros": float(costo_agujeros),
        "costo_cuadrilla": float(costo_cuadrilla),
        "costo_grua": float(costo_grua),
        "costo_flete": float(costo_flete),
        "costo_enee": float(costo_enee),
        "costo_ingenieria": float(costo_ingenieria),

        "parametros_actividades": {
            "costo_agujero_unitario": round(params["costo_agujero_unitario"], 2),
            "costo_cuadrilla_dia": round(params["costo_cuadrilla_dia"], 2),
            "horas_jornada": round(params["horas_jornada"], 2),
            "costo_hora_cuadrilla": round(params["costo_hora_cuadrilla"], 2),

            "horas_por_poste": round(params["horas_por_poste"], 2),
            "horas_por_estructura": round(params["horas_por_estructura"], 2),
            "horas_por_retenida": round(params["horas_por_retenida"], 2),

            "costo_tendido_mt_m": round(params["costo_tendido_mt_m"], 2),
            "costo_tendido_bt_m": round(params["costo_tendido_bt_m"], 2),

            "horas_grua": round(params["horas_grua"], 2),
            "precio_hora_grua": round(params["precio_hora_grua"], 2),
            "costo_hora_grua": round(params["costo_hora_grua"], 2),
            "costo_grua": round(params["costo_grua"], 2),

            "costo_flete_unitario": round(params["costo_flete_unitario"], 2),
            "viajes_flete": round(params["viajes_flete"], 2),
            "costo_flete": round(params["costo_flete"], 2),

            "costo_enee": round(params["costo_enee"], 2),
            "costo_ingenieria": round(params["costo_ingenieria"], 2),

            "porcentaje_contingencia": round(params["porcentaje_contingencia"], 2),
            "incluir_logistica": params["incluir_logistica"],
            "incluir_logistica_en_venta": params["incluir_logistica_en_venta"],
        },
    }


# =========================================================
# CALCULAR TIEMPOS / CRONOGRAMA
# =========================================================
def _calcular_tiempos(
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
    num_postes: int,
    num_retenidas: int,
    entrada=None,
) -> Dict[str, Any]:
    """
    Calcula la duración estimada del proyecto usando una sola lógica
    de productividad para costos y cronograma.

    - Postes, estructuras y retenidas usan las horas unitarias ya
      definidas en los parámetros operativos.
    - Agujeros y tendidos usan rendimientos físicos por jornada.
    - Se aplica un factor de eficiencia.
    - Se admite más de una cuadrilla.
    - Las duraciones se redondean hacia arriba.
    - Por compatibilidad, el cronograma sigue siendo secuencial.
    """

    params = _leer_parametros_operativos(entrada)
    ss = _leer_session_state()

    horas_jornada = max(_to_float(params.get("horas_jornada", 8), 8), 0.01)
    horas_por_poste = max(_to_float(params.get("horas_por_poste", 0.75), 0.75), 0.0)
    horas_por_estructura = max(_to_float(params.get("horas_por_estructura", 0.50), 0.50), 0.0)
    horas_por_retenida = max(_to_float(params.get("horas_por_retenida", 0.50), 0.50), 0.0)

    eficiencia = _to_float(
        _get_valor(entrada, ss, "eficiencia_cronograma", 0.85),
        0.85,
    )
    eficiencia = min(max(eficiencia, 0.10), 1.00)

    num_cuadrillas = int(
        max(
            1,
            _to_float(
                _get_valor(entrada, ss, "num_cuadrillas", 1),
                1,
            ),
        )
    )

    rendimiento_agujeros_dia = max(
        _to_float(
            _get_valor(entrada, ss, "rendimiento_agujeros_dia", 10),
            10,
        ),
        0.01,
    )

    rendimiento_mt_dia = max(
        _to_float(
            _get_valor(entrada, ss, "rendimiento_mt_dia", 500),
            500,
        ),
        0.01,
    )

    rendimiento_bt_dia = max(
        _to_float(
            _get_valor(entrada, ss, "rendimiento_bt_dia", 300),
            300,
        ),
        0.01,
    )

    dias_levantamiento = int(
        max(
            0,
            math.ceil(
                _to_float(
                    _get_valor(entrada, ss, "dias_levantamiento", 1),
                    1,
                )
            ),
        )
    )

    def dias_por_horas(cantidad: float, horas_unitarias: float) -> int:
        if cantidad <= 0 or horas_unitarias <= 0:
            return 0

        capacidad_diaria = horas_jornada * num_cuadrillas * eficiencia
        if capacidad_diaria <= 0:
            return 0

        return int(math.ceil((cantidad * horas_unitarias) / capacidad_diaria))

    def dias_por_rendimiento(cantidad: float, rendimiento_dia: float) -> int:
        if cantidad <= 0 or rendimiento_dia <= 0:
            return 0

        capacidad_diaria = rendimiento_dia * num_cuadrillas * eficiencia
        if capacidad_diaria <= 0:
            return 0

        return int(math.ceil(cantidad / capacidad_diaria))

    cantidad_agujeros = int(max(num_postes + num_retenidas, 0))

    dias_agujeros = dias_por_rendimiento(cantidad_agujeros, rendimiento_agujeros_dia)
    dias_postes = dias_por_horas(num_postes, horas_por_poste)
    dias_retenidas = dias_por_horas(num_retenidas, horas_por_retenida)
    dias_estructuras = dias_por_horas(total_estructuras, horas_por_estructura)
    dias_primario = dias_por_rendimiento(longitud_primario_m, rendimiento_mt_dia)
    dias_secundario = dias_por_rendimiento(longitud_secundario_m, rendimiento_bt_dia)

    rendimiento_postes_nominal = (
        horas_jornada / horas_por_poste if horas_por_poste > 0 else 0.0
    )
    rendimiento_retenidas_nominal = (
        horas_jornada / horas_por_retenida if horas_por_retenida > 0 else 0.0
    )
    rendimiento_estructuras_nominal = (
        horas_jornada / horas_por_estructura if horas_por_estructura > 0 else 0.0
    )

    actividades = [
        {
            "actividad": "Levantamiento",
            "duracion_dias": dias_levantamiento,
            "cantidad": 1 if dias_levantamiento > 0 else 0,
            "unidad": "global",
            "rendimiento": None,
        },
        {
            "actividad": "Agujeros",
            "duracion_dias": dias_agujeros,
            "cantidad": cantidad_agujeros,
            "unidad": "agujero",
            "rendimiento": rendimiento_agujeros_dia,
        },
        {
            "actividad": "Postes",
            "duracion_dias": dias_postes,
            "cantidad": int(max(num_postes, 0)),
            "unidad": "poste",
            "rendimiento": rendimiento_postes_nominal,
        },
        {
            "actividad": "Retenidas",
            "duracion_dias": dias_retenidas,
            "cantidad": int(max(num_retenidas, 0)),
            "unidad": "retenida",
            "rendimiento": rendimiento_retenidas_nominal,
        },
        {
            "actividad": "Estructuras",
            "duracion_dias": dias_estructuras,
            "cantidad": int(max(total_estructuras, 0)),
            "unidad": "estructura",
            "rendimiento": rendimiento_estructuras_nominal,
        },
        {
            "actividad": "Tendido MT",
            "duracion_dias": dias_primario,
            "cantidad": max(_to_float(longitud_primario_m), 0.0),
            "unidad": "m",
            "rendimiento": rendimiento_mt_dia,
        },
        {
            "actividad": "Tendido BT",
            "duracion_dias": dias_secundario,
            "cantidad": max(_to_float(longitud_secundario_m), 0.0),
            "unidad": "m",
            "rendimiento": rendimiento_bt_dia,
        },
    ]

    cronograma = []
    dia_actual = 1

    for item in actividades:
        duracion = int(item.get("duracion_dias", 0))

        if duracion <= 0:
            cronograma.append({
                **item,
                "inicio": None,
                "fin": None,
            })
            continue

        inicio = dia_actual
        fin = inicio + duracion - 1

        cronograma.append({
            **item,
            "inicio": int(inicio),
            "fin": int(fin),
        })

        dia_actual = fin + 1

    dias_totales = max(
        (item["fin"] or 0 for item in cronograma),
        default=0,
    )

    rendimientos = {
        "agujeros_dia": round(
            rendimiento_agujeros_dia * num_cuadrillas * eficiencia, 2
        ),
        "postes_dia": round(
            rendimiento_postes_nominal * num_cuadrillas * eficiencia, 2
        ),
        "retenidas_dia": round(
            rendimiento_retenidas_nominal * num_cuadrillas * eficiencia, 2
        ),
        "estructuras_dia": round(
            rendimiento_estructuras_nominal * num_cuadrillas * eficiencia, 2
        ),
        "mt_m_dia": round(
            rendimiento_mt_dia * num_cuadrillas * eficiencia, 2
        ),
        "bt_m_dia": round(
            rendimiento_bt_dia * num_cuadrillas * eficiencia, 2
        ),
    }

    return {
        "dias_levantamiento": dias_levantamiento,
        "dias_agujeros": dias_agujeros,
        "dias_postes": dias_postes,
        "dias_retenidas": dias_retenidas,
        "dias_estructuras": dias_estructuras,
        "dias_primario": dias_primario,
        "dias_secundario": dias_secundario,
        "dias_totales": int(dias_totales),
        "cronograma_resumen": cronograma,
        "rendimientos": rendimientos,
        "parametros_cronograma": {
            "horas_jornada": round(horas_jornada, 2),
            "eficiencia": round(eficiencia, 4),
            "num_cuadrillas": num_cuadrillas,
            "horas_por_poste": round(horas_por_poste, 4),
            "horas_por_estructura": round(horas_por_estructura, 4),
            "horas_por_retenida": round(horas_por_retenida, 4),
            "rendimiento_agujeros_dia": round(rendimiento_agujeros_dia, 2),
            "rendimiento_mt_dia": round(rendimiento_mt_dia, 2),
            "rendimiento_bt_dia": round(rendimiento_bt_dia, 2),
        },
    }


# =========================================================
# CALCULAR KPIs
# =========================================================
def _calcular_kpis(
    costo_total_real: float,
    utilidad: float,
    total_estructuras: int,
    num_postes: int,
    dias_totales: float,
) -> Dict[str, float]:

    costo_por_estructura = (
        costo_total_real / total_estructuras
        if total_estructuras
        else 0
    )

    utilidad_por_estructura = (
        utilidad / total_estructuras
        if total_estructuras
        else 0
    )

    costo_por_poste = (
        costo_total_real / num_postes
        if num_postes
        else 0
    )

    utilidad_diaria = (
        utilidad / dias_totales
        if dias_totales
        else 0
    )

    return {
        "costo_por_estructura": round(costo_por_estructura, 2),
        "utilidad_por_estructura": round(utilidad_por_estructura, 2),
        "costo_por_poste": round(costo_por_poste, 2),
        "utilidad_diaria": round(utilidad_diaria, 2),
    }


# =========================================================
# DISTRIBUCIÓN DE COSTOS
# =========================================================
def costs_or_zero(costos: Dict[str, float], key: str) -> float:
    return _to_float(costos.get(key, 0))


def _crear_distribucion_costos(
    costo_total_real: float,
    costos: Dict[str, float],
) -> list[Dict[str, Any]]:

    rubros = [
        ("Materiales", costos.get("costo_materiales", 0)),
        ("Cuadrilla", costs_or_zero(costos, "costo_cuadrilla")),
        ("Agujeros", costs_or_zero(costos, "costo_agujeros")),
        ("Grúa", costs_or_zero(costos, "costo_grua")),
        ("Flete", costs_or_zero(costos, "costo_flete")),
        ("ENEE / Permisos", costs_or_zero(costos, "costo_enee")),
        ("Ingeniería", costs_or_zero(costos, "costo_ingenieria")),
        ("Otros", costs_or_zero(costos, "costo_otros")),
        ("Contingencia", costs_or_zero(costos, "contingencia")),
    ]

    salida = []

    for rubro, monto in rubros:
        monto = _to_float(monto)

        if abs(monto) <= 0:
            continue

        porcentaje = (
            monto / costo_total_real * 100
            if costo_total_real
            else 0
        )

        salida.append(
            {
                "rubro": rubro,
                "monto": round(monto, 2),
                "porcentaje": round(porcentaje, 2),
            }
        )

    return salida


# =========================================================
# EVALUACIÓN EJECUTIVA
# =========================================================
def _evaluar_proyecto(
    utilidad: float,
    margen_pct: float,
) -> Dict[str, str]:

    if utilidad < 0:
        return {
            "estado": "NO RENTABLE",
            "mensaje": (
                "El costo total estimado supera el valor de venta pactado del proyecto."
            ),
            "nivel": "critico",
        }

    if margen_pct < 10:
        return {
            "estado": "RENTABILIDAD BAJA",
            "mensaje": (
                "El proyecto tiene utilidad positiva, pero el margen es bajo."
            ),
            "nivel": "advertencia",
        }

    if margen_pct < 20:
        return {
            "estado": "RENTABLE",
            "mensaje": (
                "El proyecto presenta utilidad positiva con margen aceptable."
            ),
            "nivel": "aceptable",
        }

    return {
        "estado": "RENTABLE ALTO",
        "mensaje": "El proyecto presenta una rentabilidad favorable.",
        "nivel": "bueno",
    }


# =========================================================
# MOTOR DE COSTOS REAL DEL CONTRATISTA
# =========================================================
def _motor_costos(
    df_materiales_costos: pd.DataFrame,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
    num_postes: int,
    num_retenidas: int,
    precio_total_proyecto: float,
    entrada=None,
) -> Dict[str, Any]:

    costos_tabla = _clasificar_costos_desde_materiales(
        df_materiales_costos
    )

    costos_actividades = _calcular_costos_actividades(
        entrada=entrada,
        longitud_primario_m=longitud_primario_m,
        longitud_secundario_m=longitud_secundario_m,
        total_estructuras=total_estructuras,
        num_postes=num_postes,
        num_retenidas=num_retenidas,
    )

    costos_manuales = (
        _extraer_costos_manuales(entrada)
        if entrada is not None
        else {
            "costo_cuadrilla_manual": 0,
            "costo_agujeros_manual": 0,
            "costo_grua_manual": 0,
            "costo_flete_manual": 0,
            "costo_enee_manual": 0,
            "costo_ingenieria_manual": 0,
        }
    )

    costo_materiales = costos_tabla["costo_materiales"]

    costo_cuadrilla = (
        costos_tabla["costo_cuadrilla"]
        + costos_actividades["costo_cuadrilla"]
        + costs_or_zero(costos_manuales, "costo_cuadrilla_manual")
    )

    costo_agujeros = (
        costos_tabla["costo_agujeros"]
        + costos_actividades["costo_agujeros"]
        + costs_or_zero(costos_manuales, "costo_agujeros_manual")
    )

    costo_grua = (
        costos_tabla["costo_grua"]
        + costos_actividades["costo_grua"]
        + costs_or_zero(costos_manuales, "costo_grua_manual")
    )

    costo_flete = (
        costos_tabla["costo_flete"]
        + costos_actividades["costo_flete"]
        + costs_or_zero(costos_manuales, "costo_flete_manual")
    )

    costo_enee = (
        costos_tabla["costo_enee"]
        + costos_actividades["costo_enee"]
        + costs_or_zero(costos_manuales, "costo_enee_manual")
    )

    costo_ingenieria = (
        costos_tabla["costo_ingenieria"]
        + costos_actividades["costo_ingenieria"]
        + costs_or_zero(costos_manuales, "costo_ingenieria_manual")
    )

    costo_otros = costos_tabla["costo_otros"]

    tiempos = _calcular_tiempos(
        longitud_primario_m=longitud_primario_m,
        longitud_secundario_m=longitud_secundario_m,
        total_estructuras=total_estructuras,
        num_postes=num_postes,
        num_retenidas=num_retenidas,
        entrada=entrada,
    )

    dias_totales = tiempos["dias_totales"]

    subtotal = (
        costo_materiales
        + costo_cuadrilla
        + costo_agujeros
        + costo_grua
        + costo_flete
        + costo_enee
        + costo_ingenieria
        + costo_otros
    )

    params = costos_actividades.get("parametros_actividades", {})

    porcentaje_contingencia = _to_float(
        params.get("porcentaje_contingencia", 5),
        5,
    )

    contingencia = subtotal * (porcentaje_contingencia / 100)

    costo_total_real = subtotal + contingencia

    utilidad = precio_total_proyecto - costo_total_real

    margen_pct = (
        utilidad / precio_total_proyecto * 100
        if precio_total_proyecto
        else 0
    )

    kpis = _calcular_kpis(
        costo_total_real=costo_total_real,
        utilidad=utilidad,
        total_estructuras=total_estructuras,
        num_postes=num_postes,
        dias_totales=dias_totales,
    )

    costos_consolidados = {
        "costo_materiales": costo_materiales,
        "costo_cuadrilla": costo_cuadrilla,
        "costo_agujeros": costo_agujeros,
        "costo_grua": costo_grua,
        "costo_flete": costo_flete,
        "costo_enee": costo_enee,
        "costo_ingenieria": costo_ingenieria,
        "costo_otros": costo_otros,
        "contingencia": contingencia,
    }

    distribucion_costos = _crear_distribucion_costos(
        costo_total_real=costo_total_real,
        costos=costos_consolidados,
    )

    evaluacion = _evaluar_proyecto(
        utilidad=utilidad,
        margen_pct=margen_pct,
    )

    porcentaje_materiales = (
        costo_materiales / costo_total_real * 100
        if costo_total_real
        else 0
    )

    porcentaje_cuadrilla = (
        costo_cuadrilla / costo_total_real * 100
        if costo_total_real
        else 0
    )

    porcentaje_grua = (
        costo_grua / costo_total_real * 100
        if costo_total_real
        else 0
    )

    return {
        "costo_materiales": round(costo_materiales, 2),
        "costo_cuadrilla": round(costo_cuadrilla, 2),
        "costo_agujeros": round(costo_agujeros, 2),
        "costo_grua": round(costo_grua, 2),
        "costo_flete": round(costo_flete, 2),
        "costo_enee": round(costo_enee, 2),
        "costo_ingenieria": round(costo_ingenieria, 2),
        "costo_otros": round(costo_otros, 2),
        "contingencia": round(contingencia, 2),
        "porcentaje_contingencia": round(porcentaje_contingencia, 2),

        "detalle_costos_actividades": (
            costos_actividades["detalle_costos_actividades"]
        ),
        "parametros_actividades": (
            costos_actividades["parametros_actividades"]
        ),

        "subtotal_costos": round(subtotal, 2),
        "costo_total_real": round(costo_total_real, 2),
        "precio_venta": round(precio_total_proyecto, 2),
        "utilidad": round(utilidad, 2),
        "margen_pct": round(margen_pct, 2),

        "dias_totales": round(dias_totales, 2),
        "num_postes": int(num_postes),
        "num_retenidas": int(num_retenidas),
        "total_estructuras": int(total_estructuras),
        "longitud_primario": round(longitud_primario_m, 2),
        "longitud_secundario": round(longitud_secundario_m, 2),

        "porcentaje_materiales": round(porcentaje_materiales, 2),
        "porcentaje_cuadrilla": round(porcentaje_cuadrilla, 2),
        "porcentaje_grua": round(porcentaje_grua, 2),

        "distribucion_costos": distribucion_costos,

        "cronograma_resumen": tiempos["cronograma_resumen"],
        "tiempos": tiempos,

        "evaluacion": evaluacion,
        "estado_proyecto": evaluacion["estado"],
        "mensaje_evaluacion": evaluacion["mensaje"],
        "nivel_evaluacion": evaluacion["nivel"],

        **kpis,
    }


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_costos_proyecto(
    entrada,
) -> Dict[str, Any]:

    try:
        df_estructuras_global = getattr(
            entrada,
            "df_estructuras",
            None,
        )

        (
            total_estructuras,
            num_postes,
            num_retenidas,
        ) = _extraer_metricas_estructuras(
            df_estructuras_global
        )

        (
            longitud_primario,
            longitud_secundario,
        ) = _extraer_longitudes(
            getattr(entrada, "df_cables", None)
        )

        df_costos_materiales = getattr(
            entrada,
            "df_costos_materiales",
            None,
        )

        if df_costos_materiales is None:
            df_costos_materiales = getattr(
                entrada,
                "df_materiales_costos",
                None,
            )

        _validar_materiales(
            df_costos_materiales
        )

        precio_base = _to_float(
            getattr(
                entrada,
                "precio_venta_proyecto",
                0,
            )
        )

        params = _leer_parametros_operativos(entrada)

        costo_grua = params["costo_grua"]
        costo_flete = params["costo_flete"]
        gastos_ingenieria = params["costo_ingenieria"]

        incluir_logistica_en_venta = params["incluir_logistica_en_venta"]

        if incluir_logistica_en_venta:
            precio_total = (
                precio_base
                + costo_grua
                + costo_flete
                + gastos_ingenieria
            )
        else:
            precio_total = precio_base

        resultado = _motor_costos(
            df_materiales_costos=df_costos_materiales,
            longitud_primario_m=longitud_primario,
            longitud_secundario_m=longitud_secundario,
            total_estructuras=total_estructuras,
            num_postes=num_postes,
            num_retenidas=num_retenidas,
            precio_total_proyecto=precio_total,
            entrada=entrada,
        )

        debug_costos_proyecto = {
            "entrada": {
                "precio_base": precio_base,
                "precio_total": precio_total,
                "horas_grua": params["horas_grua"],
                "precio_hora_grua": params["precio_hora_grua"],
                "costo_grua": costo_grua,
                "costo_flete_unitario": params["costo_flete_unitario"],
                "viajes_flete": params["viajes_flete"],
                "costo_flete": costo_flete,
                "gastos_ingenieria": gastos_ingenieria,
                "incluir_logistica": params["incluir_logistica"],
                "incluir_logistica_en_venta": incluir_logistica_en_venta,
                "porcentaje_contingencia": params["porcentaje_contingencia"],
                "total_estructuras": total_estructuras,
                "num_postes": num_postes,
                "num_retenidas": num_retenidas,
                "longitud_primario": longitud_primario,
                "longitud_secundario": longitud_secundario,
                "columnas_df_costos_materiales": list(
                    df_costos_materiales.columns
                ),
                "filas_df_costos_materiales": len(
                    df_costos_materiales
                ),
            },
            "resultado": resultado,
        }

        return {
            "ok": True,
            "resultado_costos_proyecto": resultado,
            "df_costos_materiales": df_costos_materiales,
            "debug_costos_proyecto": debug_costos_proyecto,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "resultado_costos_proyecto": None,
            "debug_costos_proyecto": {
                "error": str(e),
            },
        }
