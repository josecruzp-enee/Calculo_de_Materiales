# -*- coding: utf-8 -*-
"""
costos_precios/costos_proyecto.py

Motor interno de costos reales, productividad y cronograma.

OBJETIVO
--------
Calcular:

- costo real estimado del proyecto;
- costo de cuadrilla por actividad;
- logística;
- contingencia;
- utilidad y margen;
- indicadores operativos;
- cronograma secuencial de una cuadrilla.

CLASIFICACIÓN DE ACTIVIDADES
----------------------------
El modelo separa físicamente:

    POSTES
        PC-
        PCA-
        PM-

    RETENIDAS
        R-

    ESTRUCTURAS MT
        A-
        CT-
        CA-
        CS-
        ER-

    ESTRUCTURAS BT
        B-

    TRANSFORMADORES
        TS-
        TT-

    LUMINARIAS
        LL-

    OTRAS ESTRUCTURAS
        cualquier código no clasificado anteriormente.

CRONOGRAMA
----------
Se mantiene secuencial porque el modelo de ejecución actual
considera una cuadrilla trabajando una actividad a la vez.

Los tiempos específicos de MT, BT, transformadores y luminarias
pueden parametrizarse independientemente.

Si no existen parámetros específicos, utilizan como respaldo el
antiguo parámetro "horas_por_estructura", preservando la lógica
actual hasta que los rendimientos sean calibrados.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import pandas as pd


# =========================================================
# FAMILIAS DE ESTRUCTURAS
# =========================================================

PREFIJOS_POSTES = ("PC-", "PCA-", "PM-")
PREFIJOS_RETENIDAS = ("R-",)

PREFIJOS_ESTRUCTURAS_MT = (
    "A-",
    "CT-",
    "CA-",
    "CS-",
    "ER-",
)

PREFIJOS_ESTRUCTURAS_BT = (
    "B-",
)

PREFIJOS_TRANSFORMADORES = (
    "TS-",
    "TT-",
)

PREFIJOS_LUMINARIAS = (
    "LL-",
)


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
            pd.to_numeric(
                series,
                errors="coerce",
            )
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

    for origen, destino in reemplazos.items():
        texto = texto.replace(
            origen,
            destino,
        )

    return texto


def _obtener_columna(
    df: pd.DataFrame,
    posibles: list[str],
) -> Optional[str]:

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
    Orden de búsqueda:

    1. entrada
    2. session_state
    3. nombres alternativos
    4. default
    """

    alternativas = alternativas or []

    if entrada is not None and hasattr(entrada, nombre):
        return getattr(
            entrada,
            nombre,
        )

    if nombre in ss:
        return ss.get(nombre)

    for alt in alternativas:

        if entrada is not None and hasattr(entrada, alt):
            return getattr(
                entrada,
                alt,
            )

        if alt in ss:
            return ss.get(alt)

    return default


def _empieza_con(
    codigo: str,
    prefijos: tuple[str, ...],
) -> bool:

    codigo = _normalizar_texto(codigo)

    return codigo.startswith(prefijos)


# =========================================================
# CLASIFICAR ESTRUCTURA
# =========================================================

def _clasificar_codigo_estructura(
    codigo: str,
) -> str:
    """
    Clasifica un código dentro del modelo operativo.

    Retorna:
        poste
        retenida
        estructura_mt
        estructura_bt
        transformador
        luminaria
        otra
    """

    codigo = _normalizar_texto(codigo)

    if _empieza_con(codigo, PREFIJOS_POSTES):
        return "poste"

    if _empieza_con(codigo, PREFIJOS_RETENIDAS):
        return "retenida"

    if _empieza_con(codigo, PREFIJOS_TRANSFORMADORES):
        return "transformador"

    if _empieza_con(codigo, PREFIJOS_LUMINARIAS):
        return "luminaria"

    if _empieza_con(codigo, PREFIJOS_ESTRUCTURAS_MT):
        return "estructura_mt"

    if _empieza_con(codigo, PREFIJOS_ESTRUCTURAS_BT):
        return "estructura_bt"

    return "otra"


# =========================================================
# EXTRAER MÉTRICAS DE ESTRUCTURAS
# =========================================================

def _extraer_metricas_estructuras(
    df_estructuras_global: Optional[pd.DataFrame],
) -> Dict[str, int]:
    """
    Extrae cantidades físicas por familia.

    Ya NO utiliza una única cantidad genérica para todas
    las estructuras.
    """

    metricas = {
        "total_elementos": 0,
        "total_estructuras": 0,

        "num_postes": 0,
        "num_retenidas": 0,

        "num_estructuras_mt": 0,
        "num_estructuras_bt": 0,

        "num_transformadores": 0,
        "num_luminarias": 0,

        "num_otras_estructuras": 0,
    }

    if (
        df_estructuras_global is None
        or df_estructuras_global.empty
    ):
        return metricas

    df = df_estructuras_global.copy()

    col_estructura = _obtener_columna(
        df,
        [
            "Estructura",
            "Codigo",
            "Código",
            "codigodeestructura",
        ],
    )

    col_cantidad = _obtener_columna(
        df,
        [
            "Cantidad",
            "Cant",
            "CANT",
        ],
    )

    if not col_estructura or not col_cantidad:
        return metricas

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

    for _, row in df.iterrows():

        codigo = str(
            row[col_estructura]
        ).strip().upper()

        cantidad = int(
            max(
                _to_float(
                    row[col_cantidad],
                    0,
                ),
                0,
            )
        )

        if cantidad <= 0:
            continue

        metricas["total_elementos"] += cantidad

        familia = _clasificar_codigo_estructura(
            codigo
        )

        if familia == "poste":
            metricas["num_postes"] += cantidad

        elif familia == "retenida":
            metricas["num_retenidas"] += cantidad

        elif familia == "estructura_mt":
            metricas["num_estructuras_mt"] += cantidad

        elif familia == "estructura_bt":
            metricas["num_estructuras_bt"] += cantidad

        elif familia == "transformador":
            metricas["num_transformadores"] += cantidad

        elif familia == "luminaria":
            metricas["num_luminarias"] += cantidad

        else:
            metricas["num_otras_estructuras"] += cantidad

    metricas["total_estructuras"] = (
        metricas["num_estructuras_mt"]
        + metricas["num_estructuras_bt"]
        + metricas["num_otras_estructuras"]
    )

    return metricas


# =========================================================
# EXTRAER LONGITUDES DE CABLE
# MISMA LÓGICA UTILIZADA PARA CONTRATISTA C2
# =========================================================

def _extraer_longitudes(
    df_cables: Optional[pd.DataFrame],
) -> tuple[float, float]:

    if df_cables is None or df_cables.empty:
        return 0.0, 0.0

    total_mt = 0.0
    total_bt = 0.0
    total_n = 0.0

    for _, cable in df_cables.iterrows():

        tipo = str(
            cable.get("Tipo", "")
        ).upper().strip()

        try:
            longitud = float(
                cable.get(
                    "Total Cable (m)",
                    0,
                )
            )
        except Exception:
            continue

        if longitud <= 0:
            continue

        if tipo == "MT":
            total_mt += longitud

        elif tipo == "BT":

            fases = str(
                cable.get("Fases", "")
            ).upper().strip()

            factor = 1

            if "3" in fases:
                factor = 3

            elif "2" in fases:
                factor = 2

            longitud_real = (
                longitud / factor
            )

            total_bt += (
                longitud_real / 2
            )

        elif tipo == "N":
            total_n += longitud

    # Se conserva cálculo para futura separación del neutro.
    _n_extra = max(
        total_n - total_bt,
        0,
    )

    return (
        round(total_mt, 2),
        round(total_bt, 2),
    )


# =========================================================
# VALIDAR MATERIALES
# =========================================================

def _validar_materiales(
    df_materiales_costos: Optional[pd.DataFrame],
) -> None:

    if (
        df_materiales_costos is None
        or df_materiales_costos.empty
    ):
        raise ValueError(
            "No hay materiales con costos."
        )

    col_costo = _obtener_columna(
        df_materiales_costos,
        [
            "Costo Total",
            "Total",
            "Importe",
            "Monto",
        ],
    )

    if not col_costo:
        raise ValueError(
            "df_materiales_costos debe tener una columna "
            "de costo: 'Costo Total', 'Total', "
            "'Importe' o 'Monto'."
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
        [
            "Costo Total",
            "Total",
            "Importe",
            "Monto",
        ],
    )

    col_desc = _obtener_columna(
        df,
        [
            "Descripción",
            "Descripcion",
            "Material",
            "Materiales",
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

    costos = {
        "costo_materiales": 0.0,
        "costo_cuadrilla": 0.0,
        "costo_agujeros": 0.0,
        "costo_grua": 0.0,
        "costo_flete": 0.0,
        "costo_enee": 0.0,
        "costo_ingenieria": 0.0,
        "costo_otros": 0.0,
    }

    for _, row in df.iterrows():

        monto = _to_float(
            row.get(col_costo, 0)
        )

        texto = ""

        if col_desc:
            texto += " " + _normalizar_texto(
                row.get(col_desc, "")
            )

        if col_categoria:
            texto += " " + _normalizar_texto(
                row.get(col_categoria, "")
            )

        if "GRUA" in texto:
            costos["costo_grua"] += monto

        elif (
            "FLETE" in texto
            or "TRANSPORTE" in texto
        ):
            costos["costo_flete"] += monto

        elif (
            "AGUJERO" in texto
            or "EXCAVACION" in texto
        ):
            costos["costo_agujeros"] += monto

        elif (
            "CUADRILLA" in texto
            or "MANO DE OBRA" in texto
            or "INSTALACION" in texto
        ):
            costos["costo_cuadrilla"] += monto

        elif "INGENIERIA" in texto:
            costos["costo_ingenieria"] += monto

        elif (
            "ENEE" in texto
            or "PERMISO" in texto
            or "GESTION" in texto
        ):
            costos["costo_enee"] += monto

        elif (
            "MATERIAL" in texto
            or "SUMINISTRO" in texto
        ):
            costos["costo_materiales"] += monto

        else:
            costos["costo_materiales"] += monto

    return {
        clave: float(valor)
        for clave, valor in costos.items()
    }


# =========================================================
# COSTOS MANUALES ADICIONALES
# =========================================================

def _extraer_costos_manuales(
    entrada,
) -> Dict[str, float]:
    """
    Costos adicionales manuales.

    Se mantienen separados de los parámetros principales
    para evitar duplicaciones.
    """

    return {
        "costo_cuadrilla_manual": _to_float(
            getattr(
                entrada,
                "costo_cuadrilla",
                0,
            )
        ),

        "costo_agujeros_manual": _to_float(
            getattr(
                entrada,
                "costo_agujeros",
                0,
            )
        ),

        "costo_grua_manual": _to_float(
            getattr(
                entrada,
                "costo_grua_manual",
                0,
            )
        ),

        "costo_flete_manual": _to_float(
            getattr(
                entrada,
                "costo_flete_manual",
                0,
            )
        ),

        "costo_enee_manual": _to_float(
            getattr(
                entrada,
                "costo_enee_manual",
                0,
            )
        ),

        "costo_ingenieria_manual": _to_float(
            getattr(
                entrada,
                "costo_ingenieria_manual",
                0,
            )
        ),
    }


# =========================================================
# LEER PARÁMETROS COMERCIALES / OPERATIVOS
# =========================================================

def _leer_parametros_operativos(
    entrada=None,
) -> Dict[str, Any]:

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

    # -----------------------------------------------------
    # PARÁMETROS DE PRODUCTIVIDAD
    # -----------------------------------------------------

    horas_por_poste = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_poste",
            0.75,
        ),
        0.75,
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

    # Valor histórico como respaldo.
    horas_por_estructura = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_estructura",
            0.50,
        ),
        0.50,
    )

    horas_por_estructura_mt = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_estructura_mt",
            horas_por_estructura,
        ),
        horas_por_estructura,
    )

    horas_por_estructura_bt = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_estructura_bt",
            horas_por_estructura,
        ),
        horas_por_estructura,
    )

    horas_por_transformador = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_transformador",
            horas_por_estructura,
        ),
        horas_por_estructura,
    )

    horas_por_luminaria = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_luminaria",
            horas_por_estructura,
        ),
        horas_por_estructura,
    )

    horas_por_otra_estructura = _to_float(
        _get_valor(
            entrada,
            ss,
            "horas_por_otra_estructura",
            horas_por_estructura,
        ),
        horas_por_estructura,
    )

    # -----------------------------------------------------
    # TENDIDO
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # GRÚA / LOGÍSTICA
    # -----------------------------------------------------

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
            alternativas=[
                "costo_hora_grua",
            ],
        ),
        1500,
    )

    costo_flete_unitario = _to_float(
        _get_valor(
            entrada,
            ss,
            "costo_flete",
            0,
            alternativas=[
                "flete_rastra",
            ],
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
            alternativas=[
                "ingenieria",
            ],
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

    total_grua = (
        horas_grua
        * precio_hora_grua
    )

    total_flete = (
        costo_flete_unitario
        * viajes_flete
    )

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
        "horas_por_retenida": horas_por_retenida,

        # Compatibilidad
        "horas_por_estructura": horas_por_estructura,

        # Nuevos parámetros
        "horas_por_estructura_mt": horas_por_estructura_mt,
        "horas_por_estructura_bt": horas_por_estructura_bt,
        "horas_por_transformador": horas_por_transformador,
        "horas_por_luminaria": horas_por_luminaria,
        "horas_por_otra_estructura": horas_por_otra_estructura,

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
# CREAR ACTIVIDAD HORARIA
# =========================================================

def _actividad_horas(
    nombre: str,
    cantidad_elementos: int,
    horas_unitarias: float,
    costo_hora: float,
    nombre_elemento: str,
) -> Dict[str, Any]:

    horas = (
        cantidad_elementos
        * horas_unitarias
    )

    return {
        "actividad": nombre,
        "unidad": "hora",
        "cantidad": horas,
        "precio_unitario": costo_hora,
        "total": horas * costo_hora,
        "criterio": (
            f"{cantidad_elementos} {nombre_elemento} "
            f"x {horas_unitarias} h/{nombre_elemento.rstrip('s')}"
        ),
    }


# =========================================================
# CALCULAR COSTOS REALES POR ACTIVIDAD
# =========================================================

def _calcular_costos_actividades(
    entrada,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
) -> Dict[str, Any]:

    params = _leer_parametros_operativos(
        entrada
    )

    costo_agujero_unitario = params[
        "costo_agujero_unitario"
    ]

    costo_hora_cuadrilla = params[
        "costo_hora_cuadrilla"
    ]

    num_postes = metricas["num_postes"]
    num_retenidas = metricas["num_retenidas"]

    num_mt = metricas["num_estructuras_mt"]
    num_bt = metricas["num_estructuras_bt"]

    num_transformadores = metricas[
        "num_transformadores"
    ]

    num_luminarias = metricas[
        "num_luminarias"
    ]

    num_otras = metricas[
        "num_otras_estructuras"
    ]

    cantidad_agujeros = (
        num_postes
        + num_retenidas
    )

    costo_agujeros = (
        cantidad_agujeros
        * costo_agujero_unitario
    )

    actividades = [
        {
            "actividad": "Apertura de agujeros",
            "unidad": "agujero",
            "cantidad": cantidad_agujeros,
            "precio_unitario": costo_agujero_unitario,
            "total": costo_agujeros,
            "criterio": (
                f"{num_postes} postes + "
                f"{num_retenidas} retenidas"
            ),
        },

        _actividad_horas(
            "Hincado y aplomado de postes",
            num_postes,
            params["horas_por_poste"],
            costo_hora_cuadrilla,
            "postes",
        ),

        _actividad_horas(
            "Instalación de retenidas",
            num_retenidas,
            params["horas_por_retenida"],
            costo_hora_cuadrilla,
            "retenidas",
        ),

        _actividad_horas(
            "Armado e instalación de estructuras MT",
            num_mt,
            params["horas_por_estructura_mt"],
            costo_hora_cuadrilla,
            "estructuras MT",
        ),

        _actividad_horas(
            "Montaje de transformadores",
            num_transformadores,
            params["horas_por_transformador"],
            costo_hora_cuadrilla,
            "transformadores",
        ),

        _actividad_horas(
            "Armado e instalación de estructuras BT",
            num_bt,
            params["horas_por_estructura_bt"],
            costo_hora_cuadrilla,
            "estructuras BT",
        ),

        _actividad_horas(
            "Instalación de luminarias",
            num_luminarias,
            params["horas_por_luminaria"],
            costo_hora_cuadrilla,
            "luminarias",
        ),

        _actividad_horas(
            "Otras estructuras",
            num_otras,
            params["horas_por_otra_estructura"],
            costo_hora_cuadrilla,
            "estructuras",
        ),

        {
            "actividad": "Tendido de conductor primario MT",
            "unidad": "m",
            "cantidad": longitud_primario_m,
            "precio_unitario": params["costo_tendido_mt_m"],
            "total": (
                longitud_primario_m
                * params["costo_tendido_mt_m"]
            ),
            "criterio": (
                "Longitud primaria x costo por metro"
            ),
        },

        {
            "actividad": "Tendido de conductor secundario BT",
            "unidad": "m",
            "cantidad": longitud_secundario_m,
            "precio_unitario": params["costo_tendido_bt_m"],
            "total": (
                longitud_secundario_m
                * params["costo_tendido_bt_m"]
            ),
            "criterio": (
                "Longitud secundaria x costo por metro"
            ),
        },

        {
            "actividad": "Equipo grúa",
            "unidad": "hora",
            "cantidad": params["horas_grua"],
            "precio_unitario": params["precio_hora_grua"],
            "total": params["costo_grua"],
            "criterio": (
                "Horas grúa x precio hora"
            ),
        },

        {
            "actividad": "Flete / transporte",
            "unidad": "viaje",
            "cantidad": params["viajes_flete"],
            "precio_unitario": params["costo_flete_unitario"],
            "total": params["costo_flete"],
            "criterio": (
                "Viajes x costo por viaje"
            ),
        },

        {
            "actividad": "Gestiones ENEE / permisos",
            "unidad": "global",
            "cantidad": (
                1
                if params["costo_enee"] > 0
                else 0
            ),
            "precio_unitario": params["costo_enee"],
            "total": params["costo_enee"],
            "criterio": (
                "Gestión administrativa / permisos"
            ),
        },

        {
            "actividad": "Ingeniería y administración técnica",
            "unidad": "global",
            "cantidad": (
                1
                if params["costo_ingenieria"] > 0
                else 0
            ),
            "precio_unitario": params["costo_ingenieria"],
            "total": params["costo_ingenieria"],
            "criterio": (
                "Diseño, revisión y coordinación técnica"
            ),
        },
    ]

    actividades = [
        item
        for item in actividades
        if _to_float(
            item.get("total", 0)
        ) > 0
    ]

    # -----------------------------------------------------
    # COSTOS DE CUADRILLA
    # -----------------------------------------------------

    nombres_cuadrilla = {
        "Hincado y aplomado de postes",
        "Instalación de retenidas",
        "Armado e instalación de estructuras MT",
        "Montaje de transformadores",
        "Armado e instalación de estructuras BT",
        "Instalación de luminarias",
        "Otras estructuras",
        "Tendido de conductor primario MT",
        "Tendido de conductor secundario BT",
    }

    costo_cuadrilla = sum(
        _to_float(
            item.get("total", 0)
        )
        for item in actividades
        if item.get("actividad") in nombres_cuadrilla
    )

    return {
        "detalle_costos_actividades": actividades,

        "costo_agujeros": float(
            costo_agujeros
        ),

        "costo_cuadrilla": float(
            costo_cuadrilla
        ),

        "costo_grua": float(
            params["costo_grua"]
        ),

        "costo_flete": float(
            params["costo_flete"]
        ),

        "costo_enee": float(
            params["costo_enee"]
        ),

        "costo_ingenieria": float(
            params["costo_ingenieria"]
        ),

        "parametros_actividades": {
            "costo_agujero_unitario": round(
                params["costo_agujero_unitario"],
                2,
            ),

            "costo_cuadrilla_dia": round(
                params["costo_cuadrilla_dia"],
                2,
            ),

            "horas_jornada": round(
                params["horas_jornada"],
                2,
            ),

            "costo_hora_cuadrilla": round(
                params["costo_hora_cuadrilla"],
                2,
            ),

            "horas_por_poste": round(
                params["horas_por_poste"],
                2,
            ),

            "horas_por_retenida": round(
                params["horas_por_retenida"],
                2,
            ),

            "horas_por_estructura_mt": round(
                params["horas_por_estructura_mt"],
                2,
            ),

            "horas_por_estructura_bt": round(
                params["horas_por_estructura_bt"],
                2,
            ),

            "horas_por_transformador": round(
                params["horas_por_transformador"],
                2,
            ),

            "horas_por_luminaria": round(
                params["horas_por_luminaria"],
                2,
            ),

            "horas_por_otra_estructura": round(
                params["horas_por_otra_estructura"],
                2,
            ),

            # Compatibilidad temporal
            "horas_por_estructura": round(
                params["horas_por_estructura"],
                2,
            ),

            "costo_tendido_mt_m": round(
                params["costo_tendido_mt_m"],
                2,
            ),

            "costo_tendido_bt_m": round(
                params["costo_tendido_bt_m"],
                2,
            ),

            "horas_grua": round(
                params["horas_grua"],
                2,
            ),

            "precio_hora_grua": round(
                params["precio_hora_grua"],
                2,
            ),

            "costo_hora_grua": round(
                params["costo_hora_grua"],
                2,
            ),

            "costo_grua": round(
                params["costo_grua"],
                2,
            ),

            "costo_flete_unitario": round(
                params["costo_flete_unitario"],
                2,
            ),

            "viajes_flete": round(
                params["viajes_flete"],
                2,
            ),

            "costo_flete": round(
                params["costo_flete"],
                2,
            ),

            "costo_enee": round(
                params["costo_enee"],
                2,
            ),

            "costo_ingenieria": round(
                params["costo_ingenieria"],
                2,
            ),

            "porcentaje_contingencia": round(
                params["porcentaje_contingencia"],
                2,
            ),

            "incluir_logistica": (
                params["incluir_logistica"]
            ),

            "incluir_logistica_en_venta": (
                params[
                    "incluir_logistica_en_venta"
                ]
            ),
        },
    }


# =========================================================
# CALCULAR TIEMPOS / CRONOGRAMA
# =========================================================

def _calcular_tiempos(
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
    entrada=None,
) -> Dict[str, Any]:
    """
    Cronograma secuencial para una cuadrilla.

    Actividades:
        levantamiento
        agujeros
        postes
        retenidas
        estructuras MT
        tendido MT
        transformadores
        estructuras BT
        tendido BT
        luminarias
        otras estructuras
    """

    params = _leer_parametros_operativos(
        entrada
    )

    ss = _leer_session_state()

    horas_jornada = max(
        _to_float(
            params.get(
                "horas_jornada",
                8,
            ),
            8,
        ),
        0.01,
    )

    eficiencia = _to_float(
        _get_valor(
            entrada,
            ss,
            "eficiencia_cronograma",
            0.85,
        ),
        0.85,
    )

    eficiencia = min(
        max(
            eficiencia,
            0.10,
        ),
        1.00,
    )

    # Se mantiene por compatibilidad,
    # aunque el modelo normal usa una cuadrilla.
    num_cuadrillas = int(
        max(
            1,
            _to_float(
                _get_valor(
                    entrada,
                    ss,
                    "num_cuadrillas",
                    1,
                ),
                1,
            ),
        )
    )

    rendimiento_agujeros_dia = max(
        _to_float(
            _get_valor(
                entrada,
                ss,
                "rendimiento_agujeros_dia",
                10,
            ),
            10,
        ),
        0.01,
    )

    rendimiento_mt_dia = max(
        _to_float(
            _get_valor(
                entrada,
                ss,
                "rendimiento_mt_dia",
                500,
            ),
            500,
        ),
        0.01,
    )

    rendimiento_bt_dia = max(
        _to_float(
            _get_valor(
                entrada,
                ss,
                "rendimiento_bt_dia",
                300,
            ),
            300,
        ),
        0.01,
    )

    dias_levantamiento = int(
        max(
            0,
            math.ceil(
                _to_float(
                    _get_valor(
                        entrada,
                        ss,
                        "dias_levantamiento",
                        1,
                    ),
                    1,
                )
            ),
        )
    )

    # -----------------------------------------------------
    # FUNCIONES DE DURACIÓN
    # -----------------------------------------------------

    def dias_por_horas(
        cantidad: float,
        horas_unitarias: float,
    ) -> int:

        if (
            cantidad <= 0
            or horas_unitarias <= 0
        ):
            return 0

        capacidad_diaria = (
            horas_jornada
            * num_cuadrillas
            * eficiencia
        )

        if capacidad_diaria <= 0:
            return 0

        return int(
            math.ceil(
                cantidad
                * horas_unitarias
                / capacidad_diaria
            )
        )

    def dias_por_rendimiento(
        cantidad: float,
        rendimiento_dia: float,
    ) -> int:

        if (
            cantidad <= 0
            or rendimiento_dia <= 0
        ):
            return 0

        capacidad_diaria = (
            rendimiento_dia
            * num_cuadrillas
            * eficiencia
        )

        if capacidad_diaria <= 0:
            return 0

        return int(
            math.ceil(
                cantidad
                / capacidad_diaria
            )
        )

    def rendimiento_por_horas(
        horas_unitarias: float,
    ) -> float:

        if horas_unitarias <= 0:
            return 0.0

        return (
            horas_jornada
            / horas_unitarias
            * num_cuadrillas
            * eficiencia
        )

    # -----------------------------------------------------
    # CANTIDADES
    # -----------------------------------------------------

    num_postes = metricas["num_postes"]
    num_retenidas = metricas["num_retenidas"]

    num_mt = metricas["num_estructuras_mt"]
    num_bt = metricas["num_estructuras_bt"]

    num_transformadores = metricas[
        "num_transformadores"
    ]

    num_luminarias = metricas[
        "num_luminarias"
    ]

    num_otras = metricas[
        "num_otras_estructuras"
    ]

    cantidad_agujeros = (
        num_postes
        + num_retenidas
    )

    # -----------------------------------------------------
    # DURACIONES
    # -----------------------------------------------------

    dias_agujeros = dias_por_rendimiento(
        cantidad_agujeros,
        rendimiento_agujeros_dia,
    )

    dias_postes = dias_por_horas(
        num_postes,
        params["horas_por_poste"],
    )

    dias_retenidas = dias_por_horas(
        num_retenidas,
        params["horas_por_retenida"],
    )

    dias_mt = dias_por_horas(
        num_mt,
        params["horas_por_estructura_mt"],
    )

    dias_bt = dias_por_horas(
        num_bt,
        params["horas_por_estructura_bt"],
    )

    dias_transformadores = dias_por_horas(
        num_transformadores,
        params["horas_por_transformador"],
    )

    dias_luminarias = dias_por_horas(
        num_luminarias,
        params["horas_por_luminaria"],
    )

    dias_otras = dias_por_horas(
        num_otras,
        params["horas_por_otra_estructura"],
    )

    dias_primario = dias_por_rendimiento(
        longitud_primario_m,
        rendimiento_mt_dia,
    )

    dias_secundario = dias_por_rendimiento(
        longitud_secundario_m,
        rendimiento_bt_dia,
    )

    # -----------------------------------------------------
    # ACTIVIDADES
    # -----------------------------------------------------

    actividades = [
        {
            "actividad": "Levantamiento",
            "duracion_dias": dias_levantamiento,
            "cantidad": (
                1
                if dias_levantamiento > 0
                else 0
            ),
            "unidad": "global",
            "rendimiento": None,
        },

        {
            "actividad": "Agujeros",
            "duracion_dias": dias_agujeros,
            "cantidad": cantidad_agujeros,
            "unidad": "agujero",
            "rendimiento": (
                rendimiento_agujeros_dia
                * num_cuadrillas
                * eficiencia
            ),
        },

        {
            "actividad": "Postes",
            "duracion_dias": dias_postes,
            "cantidad": num_postes,
            "unidad": "poste",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_poste"]
            ),
        },

        {
            "actividad": "Retenidas",
            "duracion_dias": dias_retenidas,
            "cantidad": num_retenidas,
            "unidad": "retenida",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_retenida"]
            ),
        },

        {
            "actividad": "Estructuras MT",
            "duracion_dias": dias_mt,
            "cantidad": num_mt,
            "unidad": "estructura",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_estructura_mt"]
            ),
        },

        {
            "actividad": "Tendido MT",
            "duracion_dias": dias_primario,
            "cantidad": max(
                _to_float(
                    longitud_primario_m
                ),
                0.0,
            ),
            "unidad": "m",
            "rendimiento": (
                rendimiento_mt_dia
                * num_cuadrillas
                * eficiencia
            ),
        },

        {
            "actividad": "Transformadores",
            "duracion_dias": dias_transformadores,
            "cantidad": num_transformadores,
            "unidad": "transformador",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_transformador"]
            ),
        },

        {
            "actividad": "Estructuras BT",
            "duracion_dias": dias_bt,
            "cantidad": num_bt,
            "unidad": "estructura",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_estructura_bt"]
            ),
        },

        {
            "actividad": "Tendido BT",
            "duracion_dias": dias_secundario,
            "cantidad": max(
                _to_float(
                    longitud_secundario_m
                ),
                0.0,
            ),
            "unidad": "m",
            "rendimiento": (
                rendimiento_bt_dia
                * num_cuadrillas
                * eficiencia
            ),
        },

        {
            "actividad": "Luminarias",
            "duracion_dias": dias_luminarias,
            "cantidad": num_luminarias,
            "unidad": "luminaria",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_luminaria"]
            ),
        },

        {
            "actividad": "Otras estructuras",
            "duracion_dias": dias_otras,
            "cantidad": num_otras,
            "unidad": "estructura",
            "rendimiento": rendimiento_por_horas(
                params["horas_por_otra_estructura"]
            ),
        },
    ]

    # -----------------------------------------------------
    # CRONOGRAMA SECUENCIAL
    # -----------------------------------------------------

    cronograma = []
    dia_actual = 1

    for item in actividades:

        duracion = int(
            item.get(
                "duracion_dias",
                0,
            )
        )

        if duracion <= 0:

            cronograma.append({
                **item,
                "inicio": None,
                "fin": None,
            })

            continue

        inicio = dia_actual
        fin = (
            inicio
            + duracion
            - 1
        )

        cronograma.append({
            **item,
            "inicio": int(inicio),
            "fin": int(fin),
        })

        dia_actual = fin + 1

    dias_totales = max(
        (
            item["fin"] or 0
            for item in cronograma
        ),
        default=0,
    )

    # -----------------------------------------------------
    # RENDIMIENTOS EFECTIVOS
    # -----------------------------------------------------

    rendimientos = {
        "agujeros_dia": round(
            rendimiento_agujeros_dia
            * num_cuadrillas
            * eficiencia,
            2,
        ),

        "postes_dia": round(
            rendimiento_por_horas(
                params["horas_por_poste"]
            ),
            2,
        ),

        "retenidas_dia": round(
            rendimiento_por_horas(
                params["horas_por_retenida"]
            ),
            2,
        ),

        "estructuras_mt_dia": round(
            rendimiento_por_horas(
                params["horas_por_estructura_mt"]
            ),
            2,
        ),

        "estructuras_bt_dia": round(
            rendimiento_por_horas(
                params["horas_por_estructura_bt"]
            ),
            2,
        ),

        "transformadores_dia": round(
            rendimiento_por_horas(
                params["horas_por_transformador"]
            ),
            2,
        ),

        "luminarias_dia": round(
            rendimiento_por_horas(
                params["horas_por_luminaria"]
            ),
            2,
        ),

        "otras_estructuras_dia": round(
            rendimiento_por_horas(
                params["horas_por_otra_estructura"]
            ),
            2,
        ),

        "mt_m_dia": round(
            rendimiento_mt_dia
            * num_cuadrillas
            * eficiencia,
            2,
        ),

        "bt_m_dia": round(
            rendimiento_bt_dia
            * num_cuadrillas
            * eficiencia,
            2,
        ),
    }

    return {
        "dias_levantamiento": dias_levantamiento,
        "dias_agujeros": dias_agujeros,
        "dias_postes": dias_postes,
        "dias_retenidas": dias_retenidas,

        "dias_estructuras_mt": dias_mt,
        "dias_estructuras_bt": dias_bt,

        "dias_transformadores": (
            dias_transformadores
        ),

        "dias_luminarias": dias_luminarias,

        "dias_otras_estructuras": dias_otras,

        "dias_primario": dias_primario,
        "dias_secundario": dias_secundario,

        # Compatibilidad con consumidores antiguos.
        "dias_estructuras": (
            dias_mt
            + dias_bt
            + dias_otras
        ),

        "dias_totales": int(
            dias_totales
        ),

        "cronograma_resumen": cronograma,
        "rendimientos": rendimientos,

        "parametros_cronograma": {
            "horas_jornada": round(
                horas_jornada,
                2,
            ),

            "eficiencia": round(
                eficiencia,
                4,
            ),

            "num_cuadrillas": num_cuadrillas,

            "horas_por_poste": round(
                params["horas_por_poste"],
                4,
            ),

            "horas_por_retenida": round(
                params["horas_por_retenida"],
                4,
            ),

            "horas_por_estructura_mt": round(
                params["horas_por_estructura_mt"],
                4,
            ),

            "horas_por_estructura_bt": round(
                params["horas_por_estructura_bt"],
                4,
            ),

            "horas_por_transformador": round(
                params["horas_por_transformador"],
                4,
            ),

            "horas_por_luminaria": round(
                params["horas_por_luminaria"],
                4,
            ),

            "horas_por_otra_estructura": round(
                params["horas_por_otra_estructura"],
                4,
            ),

            # Compatibilidad
            "horas_por_estructura": round(
                params["horas_por_estructura"],
                4,
            ),

            "rendimiento_agujeros_dia": round(
                rendimiento_agujeros_dia,
                2,
            ),

            "rendimiento_mt_dia": round(
                rendimiento_mt_dia,
                2,
            ),

            "rendimiento_bt_dia": round(
                rendimiento_bt_dia,
                2,
            ),
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
        costo_total_real
        / total_estructuras
        if total_estructuras
        else 0
    )

    utilidad_por_estructura = (
        utilidad
        / total_estructuras
        if total_estructuras
        else 0
    )

    costo_por_poste = (
        costo_total_real
        / num_postes
        if num_postes
        else 0
    )

    utilidad_diaria = (
        utilidad
        / dias_totales
        if dias_totales
        else 0
    )

    return {
        "costo_por_estructura": round(
            costo_por_estructura,
            2,
        ),

        "utilidad_por_estructura": round(
            utilidad_por_estructura,
            2,
        ),

        "costo_por_poste": round(
            costo_por_poste,
            2,
        ),

        "utilidad_diaria": round(
            utilidad_diaria,
            2,
        ),
    }


# =========================================================
# DISTRIBUCIÓN DE COSTOS
# =========================================================

def costs_or_zero(
    costos: Dict[str, float],
    key: str,
) -> float:

    return _to_float(
        costos.get(
            key,
            0,
        )
    )


def _crear_distribucion_costos(
    costo_total_real: float,
    costos: Dict[str, float],
) -> list[Dict[str, Any]]:

    rubros = [
        (
            "Materiales",
            costos.get(
                "costo_materiales",
                0,
            ),
        ),

        (
            "Cuadrilla",
            costs_or_zero(
                costos,
                "costo_cuadrilla",
            ),
        ),

        (
            "Agujeros",
            costs_or_zero(
                costos,
                "costo_agujeros",
            ),
        ),

        (
            "Grúa",
            costs_or_zero(
                costos,
                "costo_grua",
            ),
        ),

        (
            "Flete",
            costs_or_zero(
                costos,
                "costo_flete",
            ),
        ),

        (
            "ENEE / Permisos",
            costs_or_zero(
                costos,
                "costo_enee",
            ),
        ),

        (
            "Ingeniería",
            costs_or_zero(
                costos,
                "costo_ingenieria",
            ),
        ),

        (
            "Otros",
            costs_or_zero(
                costos,
                "costo_otros",
            ),
        ),

        (
            "Contingencia",
            costs_or_zero(
                costos,
                "contingencia",
            ),
        ),
    ]

    salida = []

    for rubro, monto in rubros:

        monto = _to_float(
            monto
        )

        if abs(monto) <= 0:
            continue

        porcentaje = (
            monto
            / costo_total_real
            * 100
            if costo_total_real
            else 0
        )

        salida.append({
            "rubro": rubro,
            "monto": round(
                monto,
                2,
            ),
            "porcentaje": round(
                porcentaje,
                2,
            ),
        })

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
                "El costo total estimado supera "
                "el valor de venta pactado del proyecto."
            ),
            "nivel": "critico",
        }

    if margen_pct < 10:
        return {
            "estado": "RENTABILIDAD BAJA",
            "mensaje": (
                "El proyecto tiene utilidad positiva, "
                "pero el margen es bajo."
            ),
            "nivel": "advertencia",
        }

    if margen_pct < 20:
        return {
            "estado": "RENTABLE",
            "mensaje": (
                "El proyecto presenta utilidad positiva "
                "con margen aceptable."
            ),
            "nivel": "aceptable",
        }

    return {
        "estado": "RENTABLE ALTO",
        "mensaje": (
            "El proyecto presenta una "
            "rentabilidad favorable."
        ),
        "nivel": "bueno",
    }


# =========================================================
# MOTOR DE COSTOS REAL DEL CONTRATISTA
# =========================================================

def _motor_costos(
    df_materiales_costos: pd.DataFrame,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
    precio_total_proyecto: float,
    entrada=None,
) -> Dict[str, Any]:

    # -----------------------------------------------------
    # COSTOS BASE
    # -----------------------------------------------------

    costos_tabla = (
        _clasificar_costos_desde_materiales(
            df_materiales_costos
        )
    )

    costos_actividades = (
        _calcular_costos_actividades(
            entrada=entrada,
            longitud_primario_m=(
                longitud_primario_m
            ),
            longitud_secundario_m=(
                longitud_secundario_m
            ),
            metricas=metricas,
        )
    )

    costos_manuales = (
        _extraer_costos_manuales(
            entrada
        )
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

    # -----------------------------------------------------
    # CONSOLIDACIÓN
    # -----------------------------------------------------

    costo_materiales = (
        costos_tabla["costo_materiales"]
    )

    costo_cuadrilla = (
        costos_tabla["costo_cuadrilla"]
        + costos_actividades["costo_cuadrilla"]
        + costs_or_zero(
            costos_manuales,
            "costo_cuadrilla_manual",
        )
    )

    costo_agujeros = (
        costos_tabla["costo_agujeros"]
        + costos_actividades["costo_agujeros"]
        + costs_or_zero(
            costos_manuales,
            "costo_agujeros_manual",
        )
    )

    costo_grua = (
        costos_tabla["costo_grua"]
        + costos_actividades["costo_grua"]
        + costs_or_zero(
            costos_manuales,
            "costo_grua_manual",
        )
    )

    costo_flete = (
        costos_tabla["costo_flete"]
        + costos_actividades["costo_flete"]
        + costs_or_zero(
            costos_manuales,
            "costo_flete_manual",
        )
    )

    costo_enee = (
        costos_tabla["costo_enee"]
        + costos_actividades["costo_enee"]
        + costs_or_zero(
            costos_manuales,
            "costo_enee_manual",
        )
    )

    costo_ingenieria = (
        costos_tabla["costo_ingenieria"]
        + costos_actividades["costo_ingenieria"]
        + costs_or_zero(
            costos_manuales,
            "costo_ingenieria_manual",
        )
    )

    costo_otros = (
        costos_tabla["costo_otros"]
    )

    # -----------------------------------------------------
    # CRONOGRAMA
    # -----------------------------------------------------

    tiempos = _calcular_tiempos(
        longitud_primario_m=(
            longitud_primario_m
        ),
        longitud_secundario_m=(
            longitud_secundario_m
        ),
        metricas=metricas,
        entrada=entrada,
    )

    dias_totales = tiempos[
        "dias_totales"
    ]

    # -----------------------------------------------------
    # TOTAL DE COSTOS
    # -----------------------------------------------------

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

    params = costos_actividades.get(
        "parametros_actividades",
        {},
    )

    porcentaje_contingencia = _to_float(
        params.get(
            "porcentaje_contingencia",
            5,
        ),
        5,
    )

    contingencia = (
        subtotal
        * porcentaje_contingencia
        / 100
    )

    costo_total_real = (
        subtotal
        + contingencia
    )

    utilidad = (
        precio_total_proyecto
        - costo_total_real
    )

    margen_pct = (
        utilidad
        / precio_total_proyecto
        * 100
        if precio_total_proyecto
        else 0
    )

    # -----------------------------------------------------
    # KPIs
    # -----------------------------------------------------

    total_estructuras = metricas[
        "total_estructuras"
    ]

    num_postes = metricas[
        "num_postes"
    ]

    kpis = _calcular_kpis(
        costo_total_real=costo_total_real,
        utilidad=utilidad,
        total_estructuras=total_estructuras,
        num_postes=num_postes,
        dias_totales=dias_totales,
    )

    # -----------------------------------------------------
    # DISTRIBUCIÓN
    # -----------------------------------------------------

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

    distribucion_costos = (
        _crear_distribucion_costos(
            costo_total_real=(
                costo_total_real
            ),
            costos=(
                costos_consolidados
            ),
        )
    )

    evaluacion = _evaluar_proyecto(
        utilidad=utilidad,
        margen_pct=margen_pct,
    )

    porcentaje_materiales = (
        costo_materiales
        / costo_total_real
        * 100
        if costo_total_real
        else 0
    )

    porcentaje_cuadrilla = (
        costo_cuadrilla
        / costo_total_real
        * 100
        if costo_total_real
        else 0
    )

    porcentaje_grua = (
        costo_grua
        / costo_total_real
        * 100
        if costo_total_real
        else 0
    )

    # -----------------------------------------------------
    # SALIDA
    # -----------------------------------------------------

    return {
        "costo_materiales": round(
            costo_materiales,
            2,
        ),

        "costo_cuadrilla": round(
            costo_cuadrilla,
            2,
        ),

        "costo_agujeros": round(
            costo_agujeros,
            2,
        ),

        "costo_grua": round(
            costo_grua,
            2,
        ),

        "costo_flete": round(
            costo_flete,
            2,
        ),

        "costo_enee": round(
            costo_enee,
            2,
        ),

        "costo_ingenieria": round(
            costo_ingenieria,
            2,
        ),

        "costo_otros": round(
            costo_otros,
            2,
        ),

        "contingencia": round(
            contingencia,
            2,
        ),

        "porcentaje_contingencia": round(
            porcentaje_contingencia,
            2,
        ),

        "detalle_costos_actividades": (
            costos_actividades[
                "detalle_costos_actividades"
            ]
        ),

        "parametros_actividades": (
            costos_actividades[
                "parametros_actividades"
            ]
        ),

        "subtotal_costos": round(
            subtotal,
            2,
        ),

        "costo_total_real": round(
            costo_total_real,
            2,
        ),

        "precio_venta": round(
            precio_total_proyecto,
            2,
        ),

        "utilidad": round(
            utilidad,
            2,
        ),

        "margen_pct": round(
            margen_pct,
            2,
        ),

        "dias_totales": round(
            dias_totales,
            2,
        ),

        # -------------------------------------------------
        # MÉTRICAS COMPATIBLES
        # -------------------------------------------------

        "num_postes": int(
            metricas["num_postes"]
        ),

        "num_retenidas": int(
            metricas["num_retenidas"]
        ),

        "total_estructuras": int(
            metricas["total_estructuras"]
        ),

        # -------------------------------------------------
        # NUEVAS MÉTRICAS
        # -------------------------------------------------

        "total_elementos": int(
            metricas["total_elementos"]
        ),

        "num_estructuras_mt": int(
            metricas["num_estructuras_mt"]
        ),

        "num_estructuras_bt": int(
            metricas["num_estructuras_bt"]
        ),

        "num_transformadores": int(
            metricas["num_transformadores"]
        ),

        "num_luminarias": int(
            metricas["num_luminarias"]
        ),

        "num_otras_estructuras": int(
            metricas["num_otras_estructuras"]
        ),

        "metricas_estructuras": dict(
            metricas
        ),

        "longitud_primario": round(
            longitud_primario_m,
            2,
        ),

        "longitud_secundario": round(
            longitud_secundario_m,
            2,
        ),

        "porcentaje_materiales": round(
            porcentaje_materiales,
            2,
        ),

        "porcentaje_cuadrilla": round(
            porcentaje_cuadrilla,
            2,
        ),

        "porcentaje_grua": round(
            porcentaje_grua,
            2,
        ),

        "distribucion_costos": (
            distribucion_costos
        ),

        "cronograma_resumen": (
            tiempos["cronograma_resumen"]
        ),

        "tiempos": tiempos,

        "evaluacion": evaluacion,

        "estado_proyecto": (
            evaluacion["estado"]
        ),

        "mensaje_evaluacion": (
            evaluacion["mensaje"]
        ),

        "nivel_evaluacion": (
            evaluacion["nivel"]
        ),

        **kpis,
    }


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================

def calcular_costos_proyecto(
    entrada,
) -> Dict[str, Any]:

    try:

        # -------------------------------------------------
        # ESTRUCTURAS
        # -------------------------------------------------

        df_estructuras_global = getattr(
            entrada,
            "df_estructuras",
            None,
        )

        metricas = (
            _extraer_metricas_estructuras(
                df_estructuras_global
            )
        )

        # -------------------------------------------------
        # CABLES
        # -------------------------------------------------

        (
            longitud_primario,
            longitud_secundario,
        ) = _extraer_longitudes(
            getattr(
                entrada,
                "df_cables",
                None,
            )
        )

        # -------------------------------------------------
        # MATERIALES CON COSTOS
        # -------------------------------------------------

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

        # -------------------------------------------------
        # PRECIO DE VENTA
        # -------------------------------------------------

        precio_base = _to_float(
            getattr(
                entrada,
                "precio_venta_proyecto",
                0,
            )
        )

        params = _leer_parametros_operativos(
            entrada
        )

        costo_grua = params[
            "costo_grua"
        ]

        costo_flete = params[
            "costo_flete"
        ]

        gastos_ingenieria = params[
            "costo_ingenieria"
        ]

        incluir_logistica_en_venta = params[
            "incluir_logistica_en_venta"
        ]

        if incluir_logistica_en_venta:

            precio_total = (
                precio_base
                + costo_grua
                + costo_flete
                + gastos_ingenieria
            )

        else:
            precio_total = precio_base

        # -------------------------------------------------
        # MOTOR PRINCIPAL
        # -------------------------------------------------

        resultado = _motor_costos(
            df_materiales_costos=(
                df_costos_materiales
            ),
            longitud_primario_m=(
                longitud_primario
            ),
            longitud_secundario_m=(
                longitud_secundario
            ),
            metricas=metricas,
            precio_total_proyecto=(
                precio_total
            ),
            entrada=entrada,
        )

        # -------------------------------------------------
        # DEBUG
        # -------------------------------------------------

        debug_costos_proyecto = {
            "entrada": {
                "precio_base": precio_base,
                "precio_total": precio_total,

                "horas_grua": (
                    params["horas_grua"]
                ),

                "precio_hora_grua": (
                    params["precio_hora_grua"]
                ),

                "costo_grua": costo_grua,

                "costo_flete_unitario": (
                    params[
                        "costo_flete_unitario"
                    ]
                ),

                "viajes_flete": (
                    params["viajes_flete"]
                ),

                "costo_flete": costo_flete,

                "gastos_ingenieria": (
                    gastos_ingenieria
                ),

                "incluir_logistica": (
                    params["incluir_logistica"]
                ),

                "incluir_logistica_en_venta": (
                    incluir_logistica_en_venta
                ),

                "porcentaje_contingencia": (
                    params[
                        "porcentaje_contingencia"
                    ]
                ),

                "metricas_estructuras": dict(
                    metricas
                ),

                "longitud_primario": (
                    longitud_primario
                ),

                "longitud_secundario": (
                    longitud_secundario
                ),

                "columnas_df_costos_materiales": (
                    list(
                        df_costos_materiales.columns
                    )
                ),

                "filas_df_costos_materiales": (
                    len(
                        df_costos_materiales
                    )
                ),
            },

            "resultado": resultado,
        }

        return {
            "ok": True,

            "resultado_costos_proyecto": (
                resultado
            ),

            "df_costos_materiales": (
                df_costos_materiales
            ),

            "debug_costos_proyecto": (
                debug_costos_proyecto
            ),
        }

    except Exception as error:

        return {
            "ok": False,

            "error": str(error),

            "resultado_costos_proyecto": None,

            "debug_costos_proyecto": {
                "error": str(error),
            },
        }
