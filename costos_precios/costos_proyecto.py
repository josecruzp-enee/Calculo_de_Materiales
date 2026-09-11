# -*- coding: utf-8 -*-
"""
costos_precios/costos_proyecto.py

Motor interno de costos reales, productividad y cronograma.

Criterios del modelo
--------------------
- Una cuadrilla principal.
- Cronograma secuencial, sin solapamientos.
- Los agujeros usan rendimiento REAL de campo (4 agujeros/día por defecto).
- Postes, retenidas, estructuras MT/BT, transformadores y luminarias
  se calculan por horas unitarias y eficiencia.
- MT y BT se separan tanto en cronograma como en costos.
- El costo de cuadrilla se basa en DÍAS EFECTIVOS DE OCUPACIÓN de la cuadrilla,
  no en horas teóricas aisladas. Así cronograma y costo hablan el mismo idioma.
- Agujeros, grúa, flete, permisos e ingeniería se mantienen como costos externos
  o específicos para evitar duplicación con la cuadrilla.
- Se conservan claves de salida antiguas que consumen los reportes actuales.

Este archivo alimenta:
- exportadores/reporte_costos_proyecto.py
- PDF completo / dashboard ejecutivo
- indicadores internos de rentabilidad y cronograma
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
PREFIJOS_ESTRUCTURAS_MT = ("A-", "CT-", "CA-", "CS-", "ER-")
PREFIJOS_ESTRUCTURAS_BT = ("B-",)
PREFIJOS_TRANSFORMADORES = ("TS-", "TT-")
PREFIJOS_LUMINARIAS = ("LL-",)


# =========================================================
# UTILIDADES
# =========================================================

def _to_float(valor, default: float = 0.0) -> float:
    try:
        if valor is None:
            return default
        if isinstance(valor, str):
            valor = valor.replace("L", "").replace(",", "").replace("%", "").strip()
        return float(valor)
    except Exception:
        return default


def _normalizar_texto(valor) -> str:
    texto = "" if valor is None else str(valor).upper().strip()
    for origen, destino in {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N"}.items():
        texto = texto.replace(origen, destino)
    return texto


def _obtener_columna(df: pd.DataFrame, posibles: list[str]) -> Optional[str]:
    if df is None or df.empty:
        return None
    columnas = {_normalizar_texto(c): c for c in df.columns}
    for nombre in posibles:
        encontrado = columnas.get(_normalizar_texto(nombre))
        if encontrado:
            return encontrado
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
    alternativas = alternativas or []

    if entrada is not None and hasattr(entrada, nombre):
        valor = getattr(entrada, nombre)
        if valor is not None:
            return valor

    if nombre in ss and ss.get(nombre) is not None:
        return ss.get(nombre)

    for alt in alternativas:
        if entrada is not None and hasattr(entrada, alt):
            valor = getattr(entrada, alt)
            if valor is not None:
                return valor
        if alt in ss and ss.get(alt) is not None:
            return ss.get(alt)

    return default


def costs_or_zero(costos: Dict[str, float], key: str) -> float:
    return _to_float(costos.get(key, 0))


# =========================================================
# CLASIFICACIÓN Y MÉTRICAS
# =========================================================

def _clasificar_codigo_estructura(codigo: str) -> str:
    cod = _normalizar_texto(codigo)

    if cod.startswith(PREFIJOS_POSTES):
        return "poste"
    if cod.startswith(PREFIJOS_RETENIDAS):
        return "retenida"
    if cod.startswith(PREFIJOS_TRANSFORMADORES):
        return "transformador"
    if cod.startswith(PREFIJOS_LUMINARIAS):
        return "luminaria"
    if cod.startswith(PREFIJOS_ESTRUCTURAS_MT):
        return "estructura_mt"
    if cod.startswith(PREFIJOS_ESTRUCTURAS_BT):
        return "estructura_bt"
    return "otra"


def _extraer_metricas_estructuras(
    df_estructuras_global: Optional[pd.DataFrame],
) -> Dict[str, int]:
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

    if df_estructuras_global is None or df_estructuras_global.empty:
        return metricas

    df = df_estructuras_global.copy()
    col_codigo = _obtener_columna(
        df, ["Estructura", "Codigo", "Código", "CODIGO", "codigodeestructura"]
    )
    col_cantidad = _obtener_columna(df, ["Cantidad", "Cant", "CANT"])

    if not col_codigo or not col_cantidad:
        return metricas

    df[col_cantidad] = pd.to_numeric(df[col_cantidad], errors="coerce").fillna(0)

    mapa = {
        "poste": "num_postes",
        "retenida": "num_retenidas",
        "estructura_mt": "num_estructuras_mt",
        "estructura_bt": "num_estructuras_bt",
        "transformador": "num_transformadores",
        "luminaria": "num_luminarias",
        "otra": "num_otras_estructuras",
    }

    for _, row in df.iterrows():
        cantidad = int(max(_to_float(row[col_cantidad]), 0))
        if cantidad <= 0:
            continue

        familia = _clasificar_codigo_estructura(row[col_codigo])
        metricas["total_elementos"] += cantidad
        metricas[mapa[familia]] += cantidad

    # "Total estructuras" se conserva para reportes actuales,
    # pero significa únicamente estructuras de armado MT/BT + otras.
    metricas["total_estructuras"] = (
        metricas["num_estructuras_mt"]
        + metricas["num_estructuras_bt"]
        + metricas["num_otras_estructuras"]
    )

    return metricas


# =========================================================
# LONGITUDES DE CABLE
# =========================================================

def _extraer_longitudes(
    df_cables: Optional[pd.DataFrame],
) -> tuple[float, float]:
    """
    Devuelve longitud física aproximada de trazado MT y BT.

    Mantiene la lógica usada actualmente por el proyecto:
    - MT: suma Total Cable (m).
    - BT: corrige por número de fases y por duplicación del tramo.
    """
    if df_cables is None or df_cables.empty:
        return 0.0, 0.0

    total_mt = 0.0
    total_bt = 0.0

    for _, cable in df_cables.iterrows():
        tipo = str(cable.get("Tipo", "")).upper().strip()
        longitud = _to_float(cable.get("Total Cable (m)", 0))
        if longitud <= 0:
            continue

        if tipo == "MT":
            total_mt += longitud

        elif tipo == "BT":
            fases = str(cable.get("Fases", "")).upper().strip()
            factor_fases = 3 if "3" in fases else 2 if "2" in fases else 1
            total_bt += (longitud / factor_fases) / 2

    return round(total_mt, 2), round(total_bt, 2)


# =========================================================
# VALIDACIÓN / CLASIFICACIÓN DE COSTOS DE MATERIALES
# =========================================================

def _validar_materiales(df_materiales_costos: Optional[pd.DataFrame]) -> None:
    if df_materiales_costos is None or df_materiales_costos.empty:
        raise ValueError("No hay materiales con costos.")

    if not _obtener_columna(df_materiales_costos, ["Costo Total", "Total", "Importe", "Monto"]):
        raise ValueError(
            "df_materiales_costos debe tener una columna de costo: "
            "'Costo Total', 'Total', 'Importe' o 'Monto'."
        )


def _clasificar_costos_desde_materiales(
    df_materiales_costos: pd.DataFrame,
) -> Dict[str, float]:
    """
    La tabla principal normalmente contiene materiales.
    Si aparecen rubros explícitos (grúa, flete, etc.) los separa.
    """
    df = df_materiales_costos.copy()
    col_costo = _obtener_columna(df, ["Costo Total", "Total", "Importe", "Monto"])
    col_desc = _obtener_columna(
        df,
        ["Descripción", "Descripcion", "Material", "Materiales", "Concepto", "Estructura", "Codigo", "Código"],
    )
    col_categoria = _obtener_columna(
        df, ["Categoria", "Categoría", "Rubro", "Tipo", "Clasificacion", "Clasificación"]
    )

    df[col_costo] = pd.to_numeric(df[col_costo], errors="coerce").fillna(0)

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
        monto = _to_float(row.get(col_costo, 0))
        texto = ""
        if col_desc:
            texto += " " + _normalizar_texto(row.get(col_desc, ""))
        if col_categoria:
            texto += " " + _normalizar_texto(row.get(col_categoria, ""))

        if "GRUA" in texto:
            costos["costo_grua"] += monto
        elif "FLETE" in texto or "TRANSPORTE" in texto:
            costos["costo_flete"] += monto
        elif "AGUJERO" in texto or "EXCAVACION" in texto:
            costos["costo_agujeros"] += monto
        elif "CUADRILLA" in texto or "MANO DE OBRA" in texto or "INSTALACION" in texto:
            costos["costo_cuadrilla"] += monto
        elif "INGENIERIA" in texto:
            costos["costo_ingenieria"] += monto
        elif "ENEE" in texto or "PERMISO" in texto or "GESTION" in texto:
            costos["costo_enee"] += monto
        else:
            costos["costo_materiales"] += monto

    return costos


def _extraer_costos_manuales(entrada) -> Dict[str, float]:
    if entrada is None:
        return {}

    return {
        "costo_cuadrilla_manual": _to_float(getattr(entrada, "costo_cuadrilla", 0)),
        "costo_agujeros_manual": _to_float(getattr(entrada, "costo_agujeros", 0)),
        "costo_grua_manual": _to_float(getattr(entrada, "costo_grua_manual", 0)),
        "costo_flete_manual": _to_float(getattr(entrada, "costo_flete_manual", 0)),
        "costo_enee_manual": _to_float(getattr(entrada, "costo_enee_manual", 0)),
        "costo_ingenieria_manual": _to_float(getattr(entrada, "costo_ingenieria_manual", 0)),
    }


# =========================================================
# PARÁMETROS OPERATIVOS
# =========================================================

def _leer_parametros_operativos(entrada=None) -> Dict[str, Any]:
    ss = _leer_session_state()

    def valor(nombre, default, alternativas=None):
        return _to_float(_get_valor(entrada, ss, nombre, default, alternativas), default)

    costo_agujero_unitario = valor("costo_agujero_unitario", 500)
    costo_cuadrilla_dia = valor("costo_cuadrilla_dia", 10000)
    horas_jornada = max(valor("horas_jornada", 8), 0.01)

    params = {
        "costo_agujero_unitario": costo_agujero_unitario,
        "costo_cuadrilla_dia": costo_cuadrilla_dia,
        "horas_jornada": horas_jornada,
        "costo_hora_cuadrilla": costo_cuadrilla_dia / horas_jornada,

        # Productividad
        "horas_por_poste": valor("horas_por_poste", 1.00),
        "horas_por_retenida": valor("horas_por_retenida", 0.75),
        "horas_por_estructura_mt": valor("horas_por_estructura_mt", 0.75),
        "horas_por_estructura_bt": valor("horas_por_estructura_bt", 0.50),
        "horas_por_transformador": valor("horas_por_transformador", 2.00),
        "horas_por_luminaria": valor("horas_por_luminaria", 0.50),
        "horas_por_otra_estructura": valor("horas_por_otra_estructura", 0.75),

        # Compatibilidad de reportes actuales
        "horas_por_estructura": valor("horas_por_estructura", 0.50),

        # Se conservan como parámetros opcionales de referencia.
        # El costo base del tendido ahora se obtiene de los días de cuadrilla.
        "costo_tendido_mt_m": valor("costo_tendido_mt_m", 0),
        "costo_tendido_bt_m": valor("costo_tendido_bt_m", 0),

        "horas_grua": valor("horas_grua", 0),
        "precio_hora_grua": valor("precio_hora_grua", 1500, ["costo_hora_grua"]),
        "costo_flete_unitario": valor("costo_flete", 0, ["flete_rastra"]),
        "viajes_flete": valor("viajes_flete", 1),
        "costo_enee": valor("costo_enee", 0),
        "costo_ingenieria": valor("gastos_ingenieria", 0, ["ingenieria"]),
        "porcentaje_contingencia": valor("porcentaje_contingencia", 5),
        "incluir_logistica": bool(_get_valor(entrada, ss, "incluir_logistica", True)),
        "incluir_logistica_en_venta": bool(
            _get_valor(entrada, ss, "incluir_logistica_en_venta", True)
        ),
    }

    if not params["incluir_logistica"]:
        params.update(
            horas_grua=0.0,
            precio_hora_grua=0.0,
            costo_flete_unitario=0.0,
            viajes_flete=0.0,
            costo_ingenieria=0.0,
        )

    params["costo_hora_grua"] = params["precio_hora_grua"]
    params["costo_grua"] = params["horas_grua"] * params["precio_hora_grua"]
    params["costo_flete"] = params["costo_flete_unitario"] * params["viajes_flete"]

    return params


# =========================================================
# CRONOGRAMA
# =========================================================

def _calcular_tiempos(
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
    entrada=None,
) -> Dict[str, Any]:
    """
    Cronograma con una cuadrilla principal y solapamiento controlado.

    Criterios:
    - Día 1: levantamiento.
    - Agujeros subcontratados a 4/día por defecto.
    - Se requieren 12 agujeros de poste como colchón inicial.
    - Los postes arrancan con ese colchón y los agujeros continúan en paralelo.
    - Los agujeros de retenidas se ejecutan después de completar los de postes.
    - Estructuras MT pueden correr en paralelo con agujeros de retenidas.
    - Retenidas arrancan cuando sus agujeros estén listos y la cuadrilla esté libre.
    - eficiencia = 1.00.
    """

    params = _leer_parametros_operativos(entrada)
    ss = _leer_session_state()

    horas_jornada = params["horas_jornada"]
    eficiencia = 1.00

    # =====================================================
    # PARÁMETROS
    # =====================================================
    rendimiento_agujeros_dia = max(
        _to_float(_get_valor(entrada, ss, "rendimiento_agujeros_dia", 4), 4),
        0.01,
    )
    rendimiento_mt_dia = max(
        _to_float(_get_valor(entrada, ss, "rendimiento_mt_dia", 400), 400),
        0.01,
    )
    rendimiento_bt_dia = max(
        _to_float(_get_valor(entrada, ss, "rendimiento_bt_dia", 300), 300),
        0.01,
    )
    agujeros_minimos_para_iniciar_postes = max(
        int(math.ceil(_to_float(
            _get_valor(
                entrada,
                ss,
                "agujeros_minimos_para_iniciar_postes",
                12,
            ),
            12,
        ))),
        1,
    )
    dias_levantamiento = max(
        0,
        int(math.ceil(_to_float(
            _get_valor(entrada, ss, "dias_levantamiento", 1),
            1,
        ))),
    )

    # =====================================================
    # HELPERS
    # =====================================================
    def dias_horas(cantidad: float, horas_unitarias: float) -> int:
        if cantidad <= 0 or horas_unitarias <= 0:
            return 0
        return int(math.ceil(
            cantidad * horas_unitarias / (horas_jornada * eficiencia)
        ))

    def dias_rend(cantidad: float, rendimiento: float) -> int:
        if cantidad <= 0 or rendimiento <= 0:
            return 0
        return int(math.ceil(cantidad / rendimiento))

    def rendimiento_horas(horas_unitarias: float) -> float:
        return (
            0.0
            if horas_unitarias <= 0
            else (horas_jornada / horas_unitarias) * eficiencia
        )

    def rango(inicio: Optional[int], duracion: int) -> tuple[Optional[int], Optional[int]]:
        if not inicio or duracion <= 0:
            return None, None
        return inicio, inicio + duracion - 1

    def actividad(
        nombre: str,
        cantidad: float,
        unidad: str,
        duracion: int,
        rendimiento: Optional[float],
        inicio: Optional[int],
    ) -> Dict[str, Any]:
        inicio, fin = rango(inicio, duracion)
        return {
            "actividad": nombre,
            "duracion_dias": int(duracion),
            "cantidad": cantidad,
            "unidad": unidad,
            "rendimiento": rendimiento,
            "inicio": inicio,
            "fin": fin,
        }

    # =====================================================
    # CANTIDADES
    # =====================================================
    n_postes = metricas["num_postes"]
    n_retenidas = metricas["num_retenidas"]
    n_mt = metricas["num_estructuras_mt"]
    n_bt = metricas["num_estructuras_bt"]
    n_trafos = metricas["num_transformadores"]
    n_luminarias = metricas["num_luminarias"]
    n_otras = metricas["num_otras_estructuras"]

    # =====================================================
    # DURACIONES
    # =====================================================
    dur = {
        "Levantamiento": dias_levantamiento,
        "Agujeros de postes": dias_rend(n_postes, rendimiento_agujeros_dia),
        "Postes": dias_horas(n_postes, params["horas_por_poste"]),
        "Agujeros de retenidas": dias_rend(n_retenidas, rendimiento_agujeros_dia),
        "Estructuras MT": dias_horas(n_mt, params["horas_por_estructura_mt"]),
        "Retenidas": dias_horas(n_retenidas, params["horas_por_retenida"]),
        "Tendido MT": dias_rend(longitud_primario_m, rendimiento_mt_dia),
        "Transformadores": dias_horas(n_trafos, params["horas_por_transformador"]),
        "Estructuras BT": dias_horas(n_bt, params["horas_por_estructura_bt"]),
        "Tendido BT": dias_rend(longitud_secundario_m, rendimiento_bt_dia),
        "Luminarias": dias_horas(n_luminarias, params["horas_por_luminaria"]),
        "Otras estructuras": dias_horas(n_otras, params["horas_por_otra_estructura"]),
    }

    # =====================================================
    # PROGRAMACIÓN
    # =====================================================
    inicios: Dict[str, Optional[int]] = {}

    inicios["Levantamiento"] = 1 if dur["Levantamiento"] > 0 else None
    _, fin_levantamiento = rango(
        inicios["Levantamiento"],
        dur["Levantamiento"],
    )
    fin_levantamiento = fin_levantamiento or 0

    inicios["Agujeros de postes"] = (
        fin_levantamiento + 1
        if dur["Agujeros de postes"] > 0
        else None
    )
    _, fin_agujeros_postes = rango(
        inicios["Agujeros de postes"],
        dur["Agujeros de postes"],
    )
    fin_agujeros_postes = fin_agujeros_postes or 0

    dias_colchon = (
        dias_rend(
            min(agujeros_minimos_para_iniciar_postes, n_postes),
            rendimiento_agujeros_dia,
        )
        if n_postes > 0
        else 0
    )

    inicios["Postes"] = (
        inicios["Agujeros de postes"] + dias_colchon
        if dur["Postes"] > 0 and inicios["Agujeros de postes"]
        else None
    )
    _, fin_postes = rango(inicios["Postes"], dur["Postes"])
    fin_postes = fin_postes or 0

    inicios["Agujeros de retenidas"] = (
        fin_agujeros_postes + 1
        if dur["Agujeros de retenidas"] > 0
        else None
    )
    _, fin_agujeros_retenidas = rango(
        inicios["Agujeros de retenidas"],
        dur["Agujeros de retenidas"],
    )
    fin_agujeros_retenidas = fin_agujeros_retenidas or 0

    inicios["Estructuras MT"] = (
        fin_postes + 1
        if dur["Estructuras MT"] > 0
        else None
    )
    _, fin_mt = rango(
        inicios["Estructuras MT"],
        dur["Estructuras MT"],
    )
    fin_mt = fin_mt or 0

    inicios["Retenidas"] = (
        max(fin_mt, fin_agujeros_retenidas) + 1
        if dur["Retenidas"] > 0
        else None
    )
    _, fin_retenidas = rango(
        inicios["Retenidas"],
        dur["Retenidas"],
    )
    fin_retenidas = fin_retenidas or 0

    secuencia = [
        ("Tendido MT", fin_retenidas),
        ("Transformadores", None),
        ("Estructuras BT", None),
        ("Tendido BT", None),
        ("Luminarias", None),
        ("Otras estructuras", None),
    ]

    fin_anterior = fin_retenidas
    for nombre, _ in secuencia:
        inicios[nombre] = (
            fin_anterior + 1
            if dur[nombre] > 0
            else None
        )
        _, fin_actual = rango(
            inicios[nombre],
            dur[nombre],
        )
        if fin_actual:
            fin_anterior = fin_actual

    # =====================================================
    # CRONOGRAMA
    # =====================================================
    cronograma = [
        actividad(
            "Levantamiento",
            1 if dias_levantamiento else 0,
            "global",
            dur["Levantamiento"],
            None,
            inicios["Levantamiento"],
        ),
        actividad(
            "Agujeros de postes",
            n_postes,
            "agujero",
            dur["Agujeros de postes"],
            rendimiento_agujeros_dia,
            inicios["Agujeros de postes"],
        ),
        actividad(
            "Postes",
            n_postes,
            "poste",
            dur["Postes"],
            rendimiento_horas(params["horas_por_poste"]),
            inicios["Postes"],
        ),
        actividad(
            "Agujeros de retenidas",
            n_retenidas,
            "agujero",
            dur["Agujeros de retenidas"],
            rendimiento_agujeros_dia,
            inicios["Agujeros de retenidas"],
        ),
        actividad(
            "Estructuras MT",
            n_mt,
            "estructura",
            dur["Estructuras MT"],
            rendimiento_horas(params["horas_por_estructura_mt"]),
            inicios["Estructuras MT"],
        ),
        actividad(
            "Retenidas",
            n_retenidas,
            "retenida",
            dur["Retenidas"],
            rendimiento_horas(params["horas_por_retenida"]),
            inicios["Retenidas"],
        ),
        actividad(
            "Tendido MT",
            max(longitud_primario_m, 0),
            "m",
            dur["Tendido MT"],
            rendimiento_mt_dia,
            inicios["Tendido MT"],
        ),
        actividad(
            "Transformadores",
            n_trafos,
            "transformador",
            dur["Transformadores"],
            rendimiento_horas(params["horas_por_transformador"]),
            inicios["Transformadores"],
        ),
        actividad(
            "Estructuras BT",
            n_bt,
            "estructura",
            dur["Estructuras BT"],
            rendimiento_horas(params["horas_por_estructura_bt"]),
            inicios["Estructuras BT"],
        ),
        actividad(
            "Tendido BT",
            max(longitud_secundario_m, 0),
            "m",
            dur["Tendido BT"],
            rendimiento_bt_dia,
            inicios["Tendido BT"],
        ),
        actividad(
            "Luminarias",
            n_luminarias,
            "luminaria",
            dur["Luminarias"],
            rendimiento_horas(params["horas_por_luminaria"]),
            inicios["Luminarias"],
        ),
        actividad(
            "Otras estructuras",
            n_otras,
            "estructura",
            dur["Otras estructuras"],
            rendimiento_horas(params["horas_por_otra_estructura"]),
            inicios["Otras estructuras"],
        ),
    ]

    dias_totales = max(
        (x["fin"] or 0 for x in cronograma),
        default=0,
    )

    # =====================================================
    # RENDIMIENTOS
    # =====================================================
    rendimientos = {
        "agujeros_dia": round(rendimiento_agujeros_dia, 2),
        "postes_dia": round(rendimiento_horas(params["horas_por_poste"]), 2),
        "retenidas_dia": round(rendimiento_horas(params["horas_por_retenida"]), 2),
        "estructuras_mt_dia": round(rendimiento_horas(params["horas_por_estructura_mt"]), 2),
        "estructuras_bt_dia": round(rendimiento_horas(params["horas_por_estructura_bt"]), 2),
        "transformadores_dia": round(rendimiento_horas(params["horas_por_transformador"]), 2),
        "luminarias_dia": round(rendimiento_horas(params["horas_por_luminaria"]), 2),
        "otras_estructuras_dia": round(rendimiento_horas(params["horas_por_otra_estructura"]), 2),
        "mt_m_dia": round(rendimiento_mt_dia, 2),
        "bt_m_dia": round(rendimiento_bt_dia, 2),
    }

    # =====================================================
    # OUTPUT
    # =====================================================
    return {
        "dias_levantamiento": dur["Levantamiento"],

        # Compatibilidad: suma de ambos frentes de agujeros.
        "dias_agujeros": (
            dur["Agujeros de postes"]
            + dur["Agujeros de retenidas"]
        ),

        "dias_agujeros_postes": dur["Agujeros de postes"],
        "dias_agujeros_retenidas": dur["Agujeros de retenidas"],

        "dias_postes": dur["Postes"],
        "dias_retenidas": dur["Retenidas"],
        "dias_estructuras_mt": dur["Estructuras MT"],
        "dias_transformadores": dur["Transformadores"],
        "dias_estructuras_bt": dur["Estructuras BT"],
        "dias_primario": dur["Tendido MT"],
        "dias_secundario": dur["Tendido BT"],
        "dias_luminarias": dur["Luminarias"],
        "dias_otras_estructuras": dur["Otras estructuras"],

        "dias_estructuras": (
            dur["Estructuras MT"]
            + dur["Estructuras BT"]
            + dur["Otras estructuras"]
        ),

        "dias_totales": int(dias_totales),
        "cronograma_resumen": cronograma,
        "rendimientos": rendimientos,

        "parametros_cronograma": {
            "horas_jornada": round(horas_jornada, 2),
            "eficiencia": 1.0,
            "num_cuadrillas": 1,

            "rendimiento_agujeros_dia": round(
                rendimiento_agujeros_dia,
                2,
            ),

            "agujeros_minimos_para_iniciar_postes": int(
                agujeros_minimos_para_iniciar_postes
            ),

            "horas_por_poste": round(params["horas_por_poste"], 4),
            "horas_por_retenida": round(params["horas_por_retenida"], 4),
            "horas_por_estructura_mt": round(params["horas_por_estructura_mt"], 4),
            "horas_por_transformador": round(params["horas_por_transformador"], 4),
            "horas_por_estructura_bt": round(params["horas_por_estructura_bt"], 4),
            "horas_por_luminaria": round(params["horas_por_luminaria"], 4),
            "horas_por_otra_estructura": round(params["horas_por_otra_estructura"], 4),

            "rendimiento_mt_dia": round(rendimiento_mt_dia, 2),
            "rendimiento_bt_dia": round(rendimiento_bt_dia, 2),
        },
    }

def _actividad_cuadrilla(
    nombre_reporte: str,
    dias: int,
    costo_dia: float,
    criterio: str,
) -> Dict[str, Any]:
    return {
        "actividad": nombre_reporte,
        "unidad": "día",
        "cantidad": float(dias),
        "precio_unitario": float(costo_dia),
        "total": float(dias * costo_dia),
        "criterio": criterio,
    }


def _calcular_costos_actividades(
    entrada,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
    tiempos: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Alinea costo y cronograma.

    La cuadrilla se costea por días realmente ocupados:
        costo actividad = días actividad x costo cuadrilla/día

    No se carga cuadrilla en:
    - apertura de agujeros (se trata como costo unitario externo);
    - grúa;
    - flete;
    - permisos;
    - ingeniería.

    Así se evita que una actividad de 5 días sea costeada como si fueran
    únicamente 28 horas teóricas.
    """
    params = _leer_parametros_operativos(entrada)
    tiempos = tiempos or _calcular_tiempos(
        longitud_primario_m, longitud_secundario_m, metricas, entrada
    )

    n_postes = metricas["num_postes"]
    n_retenidas = metricas["num_retenidas"]
    n_mt = metricas["num_estructuras_mt"]
    n_bt = metricas["num_estructuras_bt"]
    n_trafos = metricas["num_transformadores"]
    n_luminarias = metricas["num_luminarias"]
    n_otras = metricas["num_otras_estructuras"]
    n_agujeros = n_postes + n_retenidas

    costo_agujeros = n_agujeros * params["costo_agujero_unitario"]
    actividades = [{
        "actividad": "Apertura de agujeros",
        "unidad": "agujero",
        "cantidad": float(n_agujeros),
        "precio_unitario": params["costo_agujero_unitario"],
        "total": costo_agujeros,
        "criterio": f"{n_postes} postes + {n_retenidas} retenidas",
    }]

    cantidades = {
        "Postes": f"{n_postes} postes",
        "Retenidas": f"{n_retenidas} retenidas",
        "Estructuras MT": f"{n_mt} estructuras MT",
        "Tendido MT": f"{longitud_primario_m:.0f} m MT",
        "Transformadores": f"{n_trafos} transformadores",
        "Estructuras BT": f"{n_bt} estructuras BT",
        "Tendido BT": f"{longitud_secundario_m:.0f} m BT",
        "Luminarias": f"{n_luminarias} luminarias",
        "Otras estructuras": f"{n_otras} otras estructuras",
    }

    cronograma_por_nombre = {x["actividad"]: x for x in tiempos["cronograma_resumen"]}

    for nombre_crono, nombre_reporte in ACTIVIDADES_CUADRILLA.items():
        item = cronograma_por_nombre[nombre_crono]
        dias = int(item["duracion_dias"])
        if dias <= 0:
            continue

        actividades.append(
            _actividad_cuadrilla(
                nombre_reporte,
                dias,
                params["costo_cuadrilla_dia"],
                f"{cantidades[nombre_crono]} → {dias} día(s) de cuadrilla",
            )
        )

    if params["costo_grua"] > 0:
        actividades.append({
            "actividad": "Equipo grúa",
            "unidad": "hora",
            "cantidad": params["horas_grua"],
            "precio_unitario": params["precio_hora_grua"],
            "total": params["costo_grua"],
            "criterio": "Horas grúa x precio hora",
        })

    if params["costo_flete"] > 0:
        actividades.append({
            "actividad": "Flete / transporte",
            "unidad": "viaje",
            "cantidad": params["viajes_flete"],
            "precio_unitario": params["costo_flete_unitario"],
            "total": params["costo_flete"],
            "criterio": "Viajes x costo por viaje",
        })

    if params["costo_enee"] > 0:
        actividades.append({
            "actividad": "Gestiones ENEE / permisos",
            "unidad": "global",
            "cantidad": 1.0,
            "precio_unitario": params["costo_enee"],
            "total": params["costo_enee"],
            "criterio": "Gestión administrativa / permisos",
        })

    if params["costo_ingenieria"] > 0:
        actividades.append({
            "actividad": "Ingeniería y administración técnica",
            "unidad": "global",
            "cantidad": 1.0,
            "precio_unitario": params["costo_ingenieria"],
            "total": params["costo_ingenieria"],
            "criterio": "Diseño, revisión y coordinación técnica",
        })

    nombres_cuadrilla = set(ACTIVIDADES_CUADRILLA.values())
    costo_cuadrilla = sum(
        _to_float(x["total"]) for x in actividades if x["actividad"] in nombres_cuadrilla
    )

    parametros = {
        "costo_agujero_unitario": round(params["costo_agujero_unitario"], 2),
        "costo_cuadrilla_dia": round(params["costo_cuadrilla_dia"], 2),
        "horas_jornada": round(params["horas_jornada"], 2),
        "costo_hora_cuadrilla": round(params["costo_hora_cuadrilla"], 2),
        "horas_por_estructura": round(params["horas_por_estructura"], 2),
        "horas_por_poste": round(params["horas_por_poste"], 2),
        "horas_por_retenida": round(params["horas_por_retenida"], 2),
        "horas_por_estructura_mt": round(params["horas_por_estructura_mt"], 2),
        "horas_por_estructura_bt": round(params["horas_por_estructura_bt"], 2),
        "horas_por_transformador": round(params["horas_por_transformador"], 2),
        "horas_por_luminaria": round(params["horas_por_luminaria"], 2),
        "horas_por_otra_estructura": round(params["horas_por_otra_estructura"], 2),
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
        "criterio_costo_cuadrilla": "días de ocupación x costo cuadrilla/día",
    }

    return {
        "detalle_costos_actividades": actividades,
        "costo_agujeros": float(costo_agujeros),
        "costo_cuadrilla": float(costo_cuadrilla),
        "costo_grua": float(params["costo_grua"]),
        "costo_flete": float(params["costo_flete"]),
        "costo_enee": float(params["costo_enee"]),
        "costo_ingenieria": float(params["costo_ingenieria"]),
        "parametros_actividades": parametros,
    }


# =========================================================
# KPIs / DISTRIBUCIÓN / EVALUACIÓN
# =========================================================

def _calcular_kpis(
    costo_total_real: float,
    utilidad: float,
    total_estructuras: int,
    num_postes: int,
    dias_totales: float,
) -> Dict[str, float]:
    """
    Conserva claves antiguas por compatibilidad.

    Semánticamente:
    - costo_por_estructura = costo global equivalente por estructura MT/BT.
    - costo_por_poste = costo global equivalente por poste.
    """
    return {
        "costo_por_estructura": round(costo_total_real / total_estructuras, 2) if total_estructuras else 0.0,
        "utilidad_por_estructura": round(utilidad / total_estructuras, 2) if total_estructuras else 0.0,
        "costo_por_poste": round(costo_total_real / num_postes, 2) if num_postes else 0.0,
        "utilidad_diaria": round(utilidad / dias_totales, 2) if dias_totales else 0.0,
        "costo_global_equivalente_por_estructura": round(costo_total_real / total_estructuras, 2) if total_estructuras else 0.0,
        "costo_global_equivalente_por_poste": round(costo_total_real / num_postes, 2) if num_postes else 0.0,
    }


def _crear_distribucion_costos(
    costo_total_real: float,
    costos: Dict[str, float],
) -> list[Dict[str, Any]]:
    rubros = [
        ("Materiales", costos.get("costo_materiales", 0)),
        ("Cuadrilla", costos.get("costo_cuadrilla", 0)),
        ("Agujeros", costos.get("costo_agujeros", 0)),
        ("Grúa", costos.get("costo_grua", 0)),
        ("Flete", costos.get("costo_flete", 0)),
        ("ENEE / Permisos", costos.get("costo_enee", 0)),
        ("Ingeniería", costos.get("costo_ingenieria", 0)),
        ("Otros", costos.get("costo_otros", 0)),
        ("Contingencia", costos.get("contingencia", 0)),
    ]

    salida = []
    for rubro, monto in rubros:
        monto = _to_float(monto)
        if monto <= 0:
            continue
        salida.append({
            "rubro": rubro,
            "monto": round(monto, 2),
            "porcentaje": round((monto / costo_total_real * 100) if costo_total_real else 0, 2),
        })
    return salida


def _evaluar_proyecto(utilidad: float, margen_pct: float) -> Dict[str, str]:
    if utilidad < 0:
        return {
            "estado": "NO RENTABLE",
            "mensaje": "El costo total estimado supera el valor de venta neta del proyecto.",
            "nivel": "critico",
        }
    if margen_pct < 10:
        return {
            "estado": "RENTABILIDAD BAJA",
            "mensaje": "El proyecto tiene utilidad positiva, pero el margen es bajo.",
            "nivel": "advertencia",
        }
    if margen_pct < 20:
        return {
            "estado": "RENTABLE",
            "mensaje": "El proyecto presenta utilidad positiva con margen aceptable.",
            "nivel": "aceptable",
        }
    return {
        "estado": "RENTABLE ALTO",
        "mensaje": "El proyecto presenta una rentabilidad favorable.",
        "nivel": "bueno",
    }

# =========================================================
# ECONOMÍA: CLIENTE VS CONTRATISTA
# =========================================================

def _sumar_columna_segura(
    df: Optional[pd.DataFrame],
    columnas: list[str],
) -> Optional[float]:
    """
    Suma la primera columna existente de la lista.
    Devuelve None si ninguna existe.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None

    col = _obtener_columna(df, columnas)
    if not col:
        return None

    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _resolver_base_materiales_cliente(
    entrada,
    df_materiales_costos: pd.DataFrame,
) -> float:
    """
    Obtiene la base de materiales que forma parte del costo global del cliente.

    Prioridad:
    1. valor explícito en entrada;
    2. df_precios_estructura, si está disponible;
    3. costo valorizado de materiales como respaldo.
    """
    for nombre in (
        "materiales_cliente",
        "total_materiales_cliente",
        "precio_materiales_proyecto",
        "subtotal_materiales",
    ):
        valor = _to_float(getattr(entrada, nombre, 0))
        if valor > 0:
            return valor

    df_precios = getattr(entrada, "df_precios_estructura", None)

    # Intentamos primero columnas de total material del proyecto.
    total = _sumar_columna_segura(
        df_precios,
        [
            "Material Proyecto",
            "Total Material",
            "Material Total",
            "TOTAL MATERIAL",
        ],
    )
    if total is not None and total > 0:
        return total

    # Si solo existe material unitario + cantidad, lo calculamos.
    if isinstance(df_precios, pd.DataFrame) and not df_precios.empty:
        col_mat = _obtener_columna(
            df_precios,
            ["Material Unitario", "Costo Material Unitario", "Material"],
        )
        col_cant = _obtener_columna(
            df_precios,
            ["Cantidad", "Cant", "CANT"],
        )
        if col_mat and col_cant:
            material = pd.to_numeric(df_precios[col_mat], errors="coerce").fillna(0)
            cantidad = pd.to_numeric(df_precios[col_cant], errors="coerce").fillna(0)
            total = float((material * cantidad).sum())
            if total > 0:
                return total

    # Respaldo compatible con el flujo actual.
    costos = _clasificar_costos_desde_materiales(df_materiales_costos)
    return float(costos.get("costo_materiales", 0.0))


def _resolver_ingreso_contratista(
    entrada,
    precio_base_cliente: float,
    base_materiales_cliente: float,
) -> float:
    """
    Ingreso pactado por ejecución del contratista.

    Prioridad:
    1. ingreso explícito;
    2. dataframe de precios, si expone mano de obra;
    3. diferencia entre subtotal cliente sin ISV y materiales.

    El tercer caso mantiene funcionando el flujo actual, donde
    precio_venta_proyecto contiene materiales + instalación.
    """
    for nombre in (
        "ingreso_contratista",
        "precio_contratista",
        "precio_ejecucion_contratista",
        "mano_obra_venta",
        "total_mano_obra_venta",
    ):
        valor = _to_float(getattr(entrada, nombre, 0))
        if valor > 0:
            return valor

    df_precios = getattr(entrada, "df_precios_estructura", None)

    total = _sumar_columna_segura(
        df_precios,
        [
            "Mano Obra Proyecto",
            "Total Mano Obra",
            "Instalacion Total",
            "Instalación Total",
        ],
    )
    if total is not None and total > 0:
        return total

    if isinstance(df_precios, pd.DataFrame) and not df_precios.empty:
        col_mo = _obtener_columna(
            df_precios,
            ["Mano Obra Unitaria", "Instalación", "Instalacion"],
        )
        col_cant = _obtener_columna(df_precios, ["Cantidad", "Cant", "CANT"])
        if col_mo and col_cant:
            mo = pd.to_numeric(df_precios[col_mo], errors="coerce").fillna(0)
            cantidad = pd.to_numeric(df_precios[col_cant], errors="coerce").fillna(0)
            total = float((mo * cantidad).sum())
            if total > 0:
                return total

    # Fallback para el flujo actual.
    return max(precio_base_cliente - base_materiales_cliente, 0.0)


def _calcular_economia_cliente(
    *,
    precio_base_cliente: float,
    base_materiales_cliente: float,
    params: Dict[str, Any],
    entrada,
) -> Dict[str, float]:
    """
    Mundo 1: inversión total requerida al cliente.

    El cliente absorbe:
    - materiales;
    - ISV sobre materiales;
    - ejecución contratada;
    - grúa;
    - flete;
    - ingeniería;
    - permisos / gestiones;
    - otros cargos explícitos del cliente.
    """
    ss = _leer_session_state()

    tasa_isv = _to_float(
        _get_valor(
            entrada,
            ss,
            "tasa_isv_materiales",
            0.15,
            alternativas=["isv_materiales"],
        ),
        0.15,
    )

    # Acepta 15 o 0.15.
    if tasa_isv > 1:
        tasa_isv /= 100.0

    isv_materiales = base_materiales_cliente * max(tasa_isv, 0.0)

    otros_cliente = _to_float(
        _get_valor(
            entrada,
            ss,
            "otros_costos_cliente",
            0,
        )
    )

    inversion_total = (
        precio_base_cliente
        + isv_materiales
        + params["costo_grua"]
        + params["costo_flete"]
        + params["costo_ingenieria"]
        + params["costo_enee"]
        + otros_cliente
    )

    ejecucion_contratada = max(
        precio_base_cliente - base_materiales_cliente,
        0.0,
    )

    return {
        "materiales_sin_isv": round(base_materiales_cliente, 2),
        "isv_materiales": round(isv_materiales, 2),
        "ejecucion_contratada": round(ejecucion_contratada, 2),
        "grua": round(params["costo_grua"], 2),
        "flete": round(params["costo_flete"], 2),
        "ingenieria": round(params["costo_ingenieria"], 2),
        "permisos_enee": round(params["costo_enee"], 2),
        "otros": round(otros_cliente, 2),
        "inversion_total_cliente": round(inversion_total, 2),
        "tasa_isv_materiales": round(tasa_isv, 4),
    }


def _calcular_economia_contratista(
    *,
    ingreso_contratista: float,
    costo_cuadrilla: float,
    costo_agujeros: float,
    costos_manuales: Dict[str, float],
    porcentaje_contingencia: float,
    entrada,
) -> Dict[str, float]:
    """
    Mundo 2: costo real y rentabilidad del contratista.

    Por defecto NO incluye:
    - materiales;
    - grúa;
    - flete;
    - ingeniería facturada al cliente;
    - permisos del cliente.

    Esos rubros solo entran aquí si se registran explícitamente
    como costos propios del contratista.
    """
    ss = _leer_session_state()

    herramientas = _to_float(
        _get_valor(entrada, ss, "costo_herramientas_contratista", 0)
    )
    combustible = _to_float(
        _get_valor(entrada, ss, "costo_combustible_contratista", 0)
    )
    movilizacion = _to_float(
        _get_valor(entrada, ss, "costo_movilizacion_contratista", 0)
    )
    viaticos = _to_float(
        _get_valor(entrada, ss, "costo_viaticos_contratista", 0)
    )
    supervision = _to_float(
        _get_valor(entrada, ss, "costo_supervision_contratista", 0)
    )
    administracion = _to_float(
        _get_valor(entrada, ss, "costo_administracion_contratista", 0)
    )
    otros = _to_float(
        _get_valor(entrada, ss, "otros_costos_contratista", 0)
    )

    # Costos externos solo si realmente los absorbe el contratista.
    grua_propia = _to_float(
        _get_valor(entrada, ss, "costo_grua_contratista", 0)
    )
    flete_propio = _to_float(
        _get_valor(entrada, ss, "costo_flete_contratista", 0)
    )
    ingenieria_propia = _to_float(
        _get_valor(entrada, ss, "costo_ingenieria_contratista", 0)
    )

    # Manuales que ya existían: solo sumamos los que representan
    # costo propio de ejecución, evitando reutilizar grúa/flete/ingeniería
    # del cliente automáticamente.
    costo_manual_cuadrilla = costs_or_zero(
        costos_manuales, "costo_cuadrilla_manual"
    )
    costo_manual_agujeros = costs_or_zero(
        costos_manuales, "costo_agujeros_manual"
    )

    base_ejecucion = sum([
        costo_cuadrilla,
        costo_agujeros,
        costo_manual_cuadrilla,
        costo_manual_agujeros,
        herramientas,
        combustible,
        movilizacion,
        viaticos,
        supervision,
        administracion,
        otros,
        grua_propia,
        flete_propio,
        ingenieria_propia,
    ])

    contingencia = base_ejecucion * max(porcentaje_contingencia, 0.0) / 100.0
    costo_total = base_ejecucion + contingencia

    utilidad = ingreso_contratista - costo_total
    margen = (
        utilidad / ingreso_contratista * 100
        if ingreso_contratista > 0
        else 0.0
    )

    return {
        "ingreso_contratista": round(ingreso_contratista, 2),
        "costo_cuadrilla": round(costo_cuadrilla + costo_manual_cuadrilla, 2),
        "costo_agujeros": round(costo_agujeros + costo_manual_agujeros, 2),
        "herramientas": round(herramientas, 2),
        "combustible": round(combustible, 2),
        "movilizacion": round(movilizacion, 2),
        "viaticos": round(viaticos, 2),
        "supervision": round(supervision, 2),
        "administracion": round(administracion, 2),
        "grua_propia": round(grua_propia, 2),
        "flete_propio": round(flete_propio, 2),
        "ingenieria_propia": round(ingenieria_propia, 2),
        "otros": round(otros, 2),
        "subtotal_ejecucion": round(base_ejecucion, 2),
        "contingencia_contratista": round(contingencia, 2),
        "costo_real_contratista": round(costo_total, 2),
        "utilidad_contratista": round(utilidad, 2),
        "margen_contratista_pct": round(margen, 2),
    }


# =========================================================
# MOTOR PRINCIPAL
# =========================================================

def _motor_costos(
    df_materiales_costos: pd.DataFrame,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
    precio_base_cliente: float,
    entrada=None,
) -> Dict[str, Any]:
    """
    Consolida DOS mundos independientes:

    1. Economía global del cliente.
    2. Economía / rentabilidad real del contratista.

    El cronograma y la productividad son comunes a ambos.
    """
    costos_tabla = _clasificar_costos_desde_materiales(df_materiales_costos)
    costos_manuales = _extraer_costos_manuales(entrada)

    tiempos = _calcular_tiempos(
        longitud_primario_m,
        longitud_secundario_m,
        metricas,
        entrada,
    )

    costos_actividades = _calcular_costos_actividades(
        entrada,
        longitud_primario_m,
        longitud_secundario_m,
        metricas,
        tiempos=tiempos,
    )

    params = _leer_parametros_operativos(entrada)

    # -----------------------------------------------------
    # MUNDO CLIENTE
    # -----------------------------------------------------
    base_materiales_cliente = _resolver_base_materiales_cliente(
        entrada,
        df_materiales_costos,
    )

    economia_cliente = _calcular_economia_cliente(
        precio_base_cliente=precio_base_cliente,
        base_materiales_cliente=base_materiales_cliente,
        params=params,
        entrada=entrada,
    )

    # -----------------------------------------------------
    # MUNDO CONTRATISTA
    # -----------------------------------------------------
    ingreso_contratista = _resolver_ingreso_contratista(
        entrada,
        precio_base_cliente,
        base_materiales_cliente,
    )

    porcentaje_contingencia = _to_float(
        costos_actividades["parametros_actividades"].get(
            "porcentaje_contingencia",
            5,
        ),
        5,
    )

    economia_contratista = _calcular_economia_contratista(
        ingreso_contratista=ingreso_contratista,
        costo_cuadrilla=costos_actividades["costo_cuadrilla"],
        costo_agujeros=costos_actividades["costo_agujeros"],
        costos_manuales=costos_manuales,
        porcentaje_contingencia=porcentaje_contingencia,
        entrada=entrada,
    )

    utilidad = economia_contratista["utilidad_contratista"]
    margen_pct = economia_contratista["margen_contratista_pct"]
    costo_real_contratista = economia_contratista["costo_real_contratista"]

    evaluacion = _evaluar_proyecto(utilidad, margen_pct)

    kpis = _calcular_kpis(
        costo_real_contratista,
        utilidad,
        metricas["total_estructuras"],
        metricas["num_postes"],
        tiempos["dias_totales"],
    )

    # Distribución SOLO del contratista.
    costos_contratista_distribucion = {
        "costo_materiales": 0.0,
        "costo_cuadrilla": economia_contratista["costo_cuadrilla"],
        "costo_agujeros": economia_contratista["costo_agujeros"],
        "costo_grua": economia_contratista["grua_propia"],
        "costo_flete": economia_contratista["flete_propio"],
        "costo_enee": 0.0,
        "costo_ingenieria": economia_contratista["ingenieria_propia"],
        "costo_otros": sum([
            economia_contratista["herramientas"],
            economia_contratista["combustible"],
            economia_contratista["movilizacion"],
            economia_contratista["viaticos"],
            economia_contratista["supervision"],
            economia_contratista["administracion"],
            economia_contratista["otros"],
        ]),
        "contingencia": economia_contratista["contingencia_contratista"],
    }

    # -----------------------------------------------------
    # SALIDA
    # -----------------------------------------------------
    return {
        # =============================
        # NUEVOS BLOQUES CONCEPTUALES
        # =============================
        "economia_cliente": economia_cliente,
        "economia_contratista": economia_contratista,

        "inversion_total_cliente": economia_cliente["inversion_total_cliente"],
        "materiales_cliente_sin_isv": economia_cliente["materiales_sin_isv"],
        "isv_materiales_cliente": economia_cliente["isv_materiales"],
        "ejecucion_contratada_cliente": economia_cliente["ejecucion_contratada"],

        "ingreso_contratista": economia_contratista["ingreso_contratista"],
        "costo_real_contratista": costo_real_contratista,
        "utilidad_contratista": utilidad,
        "margen_contratista_pct": margen_pct,
        "contingencia_contratista": economia_contratista["contingencia_contratista"],

        # =============================
        # COMPATIBILIDAD CON REPORTES
        # Ahora estas claves representan al CONTRATISTA.
        # =============================
        "precio_venta": economia_contratista["ingreso_contratista"],
        "precio_venta_neta": economia_contratista["ingreso_contratista"],
        "subtotal_costos": economia_contratista["subtotal_ejecucion"],
        "costo_total_real": costo_real_contratista,
        "contingencia": economia_contratista["contingencia_contratista"],
        "porcentaje_contingencia": round(porcentaje_contingencia, 2),
        "utilidad": utilidad,
        "margen_pct": margen_pct,

        # Costos propios del contratista
        "costo_materiales": 0.0,
        "costo_cuadrilla": economia_contratista["costo_cuadrilla"],
        "costo_agujeros": economia_contratista["costo_agujeros"],
        "costo_grua": economia_contratista["grua_propia"],
        "costo_flete": economia_contratista["flete_propio"],
        "costo_enee": 0.0,
        "costo_ingenieria": economia_contratista["ingenieria_propia"],
        "costo_otros": costos_contratista_distribucion["costo_otros"],

        # Referencias globales del cliente, sin mezclarlas con rentabilidad
        "costo_materiales_global": round(costos_tabla["costo_materiales"], 2),
        "costo_grua_cliente": round(params["costo_grua"], 2),
        "costo_flete_cliente": round(params["costo_flete"], 2),
        "costo_ingenieria_cliente": round(params["costo_ingenieria"], 2),
        "costo_enee_cliente": round(params["costo_enee"], 2),

        "detalle_costos_actividades": costos_actividades[
            "detalle_costos_actividades"
        ],
        "parametros_actividades": costos_actividades[
            "parametros_actividades"
        ],

        "dias_totales": int(tiempos["dias_totales"]),

        "num_postes": int(metricas["num_postes"]),
        "num_retenidas": int(metricas["num_retenidas"]),
        "total_estructuras": int(metricas["total_estructuras"]),
        "total_elementos": int(metricas["total_elementos"]),
        "num_estructuras_mt": int(metricas["num_estructuras_mt"]),
        "num_estructuras_bt": int(metricas["num_estructuras_bt"]),
        "num_transformadores": int(metricas["num_transformadores"]),
        "num_luminarias": int(metricas["num_luminarias"]),
        "num_otras_estructuras": int(metricas["num_otras_estructuras"]),
        "metricas_estructuras": dict(metricas),

        "longitud_primario": round(longitud_primario_m, 2),
        "longitud_secundario": round(longitud_secundario_m, 2),

        "porcentaje_materiales": 0.0,
        "porcentaje_cuadrilla": round(
            (
                economia_contratista["costo_cuadrilla"]
                / costo_real_contratista
                * 100
            )
            if costo_real_contratista
            else 0,
            2,
        ),
        "porcentaje_grua": round(
            (
                economia_contratista["grua_propia"]
                / costo_real_contratista
                * 100
            )
            if costo_real_contratista
            else 0,
            2,
        ),

        "distribucion_costos": _crear_distribucion_costos(
            costo_real_contratista,
            costos_contratista_distribucion,
        ),

        "cronograma_resumen": tiempos["cronograma_resumen"],
        "tiempos": tiempos,

        "evaluacion": evaluacion,
        "estado_proyecto": evaluacion["estado"],
        "mensaje_evaluacion": evaluacion["mensaje"],
        "nivel_evaluacion": evaluacion["nivel"],

        **kpis,
    }


# =========================================================
# FUNCIÓN PÚBLICA
# =========================================================

def calcular_costos_proyecto(entrada) -> Dict[str, Any]:
    try:
        metricas = _extraer_metricas_estructuras(
            getattr(entrada, "df_estructuras", None)
        )

        longitud_primario, longitud_secundario = _extraer_longitudes(
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

        _validar_materiales(df_costos_materiales)

        # En el flujo actual este subtotal representa:
        # materiales sin ISV + ejecución contratada.
        precio_base_cliente = _to_float(
            getattr(
                entrada,
                "precio_venta_proyecto",
                0,
            )
        )

        resultado = _motor_costos(
            df_materiales_costos=df_costos_materiales,
            longitud_primario_m=longitud_primario,
            longitud_secundario_m=longitud_secundario,
            metricas=metricas,
            precio_base_cliente=precio_base_cliente,
            entrada=entrada,
        )

        debug_costos_proyecto = {
            "entrada": {
                "precio_base_cliente": precio_base_cliente,
                "metricas_estructuras": dict(metricas),
                "longitud_primario": longitud_primario,
                "longitud_secundario": longitud_secundario,
                "columnas_df_costos_materiales": list(
                    df_costos_materiales.columns
                ),
                "filas_df_costos_materiales": len(
                    df_costos_materiales
                ),
            },
            "economia_cliente": resultado.get(
                "economia_cliente",
                {},
            ),
            "economia_contratista": resultado.get(
                "economia_contratista",
                {},
            ),
            "resultado": resultado,
        }

        return {
            "ok": True,
            "resultado_costos_proyecto": resultado,
            "df_costos_materiales": df_costos_materiales,
            "debug_costos_proyecto": debug_costos_proyecto,
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
