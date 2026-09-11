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
    Cronograma secuencial de una cuadrilla.

    Agujeros:
        rendimiento REAL = 4 agujeros/día por defecto.
        No se vuelve a castigar con eficiencia.

    Resto:
        rendimiento nominal/hora x eficiencia.
    """
    params = _leer_parametros_operativos(entrada)
    ss = _leer_session_state()

    horas_jornada = params["horas_jornada"]
    eficiencia = min(
        max(_to_float(_get_valor(entrada, ss, "eficiencia_cronograma", 0.85), 0.85), 0.10),
        1.00,
    )

    rendimiento_agujeros_dia = max(
        _to_float(_get_valor(entrada, ss, "rendimiento_agujeros_dia", 4), 4), 0.01
    )
    rendimiento_mt_dia = max(
        _to_float(_get_valor(entrada, ss, "rendimiento_mt_dia", 400), 400), 0.01
    )
    rendimiento_bt_dia = max(
        _to_float(_get_valor(entrada, ss, "rendimiento_bt_dia", 300), 300), 0.01
    )
    dias_levantamiento = max(
        0, int(math.ceil(_to_float(_get_valor(entrada, ss, "dias_levantamiento", 1), 1)))
    )

    def dias_por_horas(cantidad: float, horas_unitarias: float) -> int:
        if cantidad <= 0 or horas_unitarias <= 0:
            return 0
        return int(math.ceil(cantidad * horas_unitarias / (horas_jornada * eficiencia)))

    def dias_por_rendimiento_real(cantidad: float, rendimiento: float) -> int:
        if cantidad <= 0 or rendimiento <= 0:
            return 0
        return int(math.ceil(cantidad / rendimiento))

    def dias_por_rendimiento_nominal(cantidad: float, rendimiento: float) -> int:
        if cantidad <= 0 or rendimiento <= 0:
            return 0
        return int(math.ceil(cantidad / (rendimiento * eficiencia)))

    def rendimiento_por_horas(horas_unitarias: float) -> float:
        return 0.0 if horas_unitarias <= 0 else (horas_jornada / horas_unitarias) * eficiencia

    n_postes = metricas["num_postes"]
    n_retenidas = metricas["num_retenidas"]
    n_mt = metricas["num_estructuras_mt"]
    n_bt = metricas["num_estructuras_bt"]
    n_trafos = metricas["num_transformadores"]
    n_luminarias = metricas["num_luminarias"]
    n_otras = metricas["num_otras_estructuras"]
    n_agujeros = n_postes + n_retenidas

    actividades = [
        ("Levantamiento", 1 if dias_levantamiento else 0, "global", dias_levantamiento, None),
        ("Agujeros", n_agujeros, "agujero",
         dias_por_rendimiento_real(n_agujeros, rendimiento_agujeros_dia),
         rendimiento_agujeros_dia),
        ("Postes", n_postes, "poste",
         dias_por_horas(n_postes, params["horas_por_poste"]),
         rendimiento_por_horas(params["horas_por_poste"])),
        ("Retenidas", n_retenidas, "retenida",
         dias_por_horas(n_retenidas, params["horas_por_retenida"]),
         rendimiento_por_horas(params["horas_por_retenida"])),
        ("Estructuras MT", n_mt, "estructura",
         dias_por_horas(n_mt, params["horas_por_estructura_mt"]),
         rendimiento_por_horas(params["horas_por_estructura_mt"])),
        ("Tendido MT", max(longitud_primario_m, 0), "m",
         dias_por_rendimiento_nominal(longitud_primario_m, rendimiento_mt_dia),
         rendimiento_mt_dia * eficiencia),
        ("Transformadores", n_trafos, "transformador",
         dias_por_horas(n_trafos, params["horas_por_transformador"]),
         rendimiento_por_horas(params["horas_por_transformador"])),
        ("Estructuras BT", n_bt, "estructura",
         dias_por_horas(n_bt, params["horas_por_estructura_bt"]),
         rendimiento_por_horas(params["horas_por_estructura_bt"])),
        ("Tendido BT", max(longitud_secundario_m, 0), "m",
         dias_por_rendimiento_nominal(longitud_secundario_m, rendimiento_bt_dia),
         rendimiento_bt_dia * eficiencia),
        ("Luminarias", n_luminarias, "luminaria",
         dias_por_horas(n_luminarias, params["horas_por_luminaria"]),
         rendimiento_por_horas(params["horas_por_luminaria"])),
        ("Otras estructuras", n_otras, "estructura",
         dias_por_horas(n_otras, params["horas_por_otra_estructura"]),
         rendimiento_por_horas(params["horas_por_otra_estructura"])),
    ]

    cronograma = []
    dia_actual = 1

    for nombre, cantidad, unidad, duracion, rendimiento in actividades:
        if duracion <= 0:
            inicio = fin = None
        else:
            inicio = dia_actual
            fin = inicio + duracion - 1
            dia_actual = fin + 1

        cronograma.append({
            "actividad": nombre,
            "duracion_dias": int(duracion),
            "cantidad": cantidad,
            "unidad": unidad,
            "rendimiento": rendimiento,
            "inicio": inicio,
            "fin": fin,
        })

    dias_totales = max((x["fin"] or 0 for x in cronograma), default=0)
    dur = {x["actividad"]: x["duracion_dias"] for x in cronograma}

    rendimientos = {
        "agujeros_dia": round(rendimiento_agujeros_dia, 2),
        "postes_dia": round(rendimiento_por_horas(params["horas_por_poste"]), 2),
        "retenidas_dia": round(rendimiento_por_horas(params["horas_por_retenida"]), 2),
        "estructuras_mt_dia": round(rendimiento_por_horas(params["horas_por_estructura_mt"]), 2),
        "estructuras_bt_dia": round(rendimiento_por_horas(params["horas_por_estructura_bt"]), 2),
        "transformadores_dia": round(rendimiento_por_horas(params["horas_por_transformador"]), 2),
        "luminarias_dia": round(rendimiento_por_horas(params["horas_por_luminaria"]), 2),
        "otras_estructuras_dia": round(rendimiento_por_horas(params["horas_por_otra_estructura"]), 2),
        "mt_m_dia": round(rendimiento_mt_dia * eficiencia, 2),
        "bt_m_dia": round(rendimiento_bt_dia * eficiencia, 2),
    }

    return {
        "dias_levantamiento": dur["Levantamiento"],
        "dias_agujeros": dur["Agujeros"],
        "dias_postes": dur["Postes"],
        "dias_retenidas": dur["Retenidas"],
        "dias_estructuras_mt": dur["Estructuras MT"],
        "dias_transformadores": dur["Transformadores"],
        "dias_estructuras_bt": dur["Estructuras BT"],
        "dias_primario": dur["Tendido MT"],
        "dias_secundario": dur["Tendido BT"],
        "dias_luminarias": dur["Luminarias"],
        "dias_otras_estructuras": dur["Otras estructuras"],
        "dias_estructuras": dur["Estructuras MT"] + dur["Estructuras BT"] + dur["Otras estructuras"],
        "dias_totales": int(dias_totales),
        "cronograma_resumen": cronograma,
        "rendimientos": rendimientos,
        "parametros_cronograma": {
            "horas_jornada": round(horas_jornada, 2),
            "eficiencia": round(eficiencia, 4),
            "num_cuadrillas": 1,
            "rendimiento_agujeros_dia": round(rendimiento_agujeros_dia, 2),
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


# =========================================================
# COSTOS OPERATIVOS POR ACTIVIDAD
# =========================================================

ACTIVIDADES_CUADRILLA = {
    "Postes": "Hincado y aplomado de postes",
    "Retenidas": "Instalación de retenidas",
    "Estructuras MT": "Armado e instalación de estructuras MT",
    "Tendido MT": "Tendido de conductor primario MT",
    "Transformadores": "Montaje de transformadores",
    "Estructuras BT": "Armado e instalación de estructuras BT",
    "Tendido BT": "Tendido de conductor secundario BT",
    "Luminarias": "Instalación de luminarias",
    "Otras estructuras": "Otras estructuras",
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
# MOTOR PRINCIPAL
# =========================================================

def _motor_costos(
    df_materiales_costos: pd.DataFrame,
    longitud_primario_m: float,
    longitud_secundario_m: float,
    metricas: Dict[str, int],
    precio_total_proyecto: float,
    entrada=None,
) -> Dict[str, Any]:
    costos_tabla = _clasificar_costos_desde_materiales(df_materiales_costos)
    costos_manuales = _extraer_costos_manuales(entrada)

    # Primero cronograma; después costos. Así ambos usan exactamente
    # las mismas duraciones y no divergen.
    tiempos = _calcular_tiempos(
        longitud_primario_m, longitud_secundario_m, metricas, entrada
    )
    costos_actividades = _calcular_costos_actividades(
        entrada,
        longitud_primario_m,
        longitud_secundario_m,
        metricas,
        tiempos=tiempos,
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

    subtotal = sum([
        costo_materiales,
        costo_cuadrilla,
        costo_agujeros,
        costo_grua,
        costo_flete,
        costo_enee,
        costo_ingenieria,
        costo_otros,
    ])

    porcentaje_contingencia = _to_float(
        costos_actividades["parametros_actividades"].get("porcentaje_contingencia", 5), 5
    )
    contingencia = subtotal * porcentaje_contingencia / 100
    costo_total_real = subtotal + contingencia

    # precio_total_proyecto se trata como VENTA NETA para rentabilidad.
    utilidad = precio_total_proyecto - costo_total_real
    margen_pct = (utilidad / precio_total_proyecto * 100) if precio_total_proyecto else 0.0

    kpis = _calcular_kpis(
        costo_total_real,
        utilidad,
        metricas["total_estructuras"],
        metricas["num_postes"],
        tiempos["dias_totales"],
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

    evaluacion = _evaluar_proyecto(utilidad, margen_pct)

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
        "detalle_costos_actividades": costos_actividades["detalle_costos_actividades"],
        "parametros_actividades": costos_actividades["parametros_actividades"],
        "subtotal_costos": round(subtotal, 2),
        "costo_total_real": round(costo_total_real, 2),

        # Compatibilidad + nombre semánticamente correcto
        "precio_venta": round(precio_total_proyecto, 2),
        "precio_venta_neta": round(precio_total_proyecto, 2),

        "utilidad": round(utilidad, 2),
        "margen_pct": round(margen_pct, 2),
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

        "porcentaje_materiales": round((costo_materiales / costo_total_real * 100) if costo_total_real else 0, 2),
        "porcentaje_cuadrilla": round((costo_cuadrilla / costo_total_real * 100) if costo_total_real else 0, 2),
        "porcentaje_grua": round((costo_grua / costo_total_real * 100) if costo_total_real else 0, 2),

        "distribucion_costos": _crear_distribucion_costos(costo_total_real, costos_consolidados),
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

        df_costos_materiales = getattr(entrada, "df_costos_materiales", None)
        if df_costos_materiales is None:
            df_costos_materiales = getattr(entrada, "df_materiales_costos", None)

        _validar_materiales(df_costos_materiales)

        precio_base = _to_float(getattr(entrada, "precio_venta_proyecto", 0))
        params = _leer_parametros_operativos(entrada)

        # Este valor representa la venta neta usada para medir rentabilidad.
        # Se mantiene la regla vigente de agregar logística/ingeniería
        # cuando el proyecto así lo configura.
        precio_venta_neta = precio_base
        if params["incluir_logistica_en_venta"]:
            precio_venta_neta += (
                params["costo_grua"]
                + params["costo_flete"]
                + params["costo_ingenieria"]
            )

        resultado = _motor_costos(
            df_materiales_costos=df_costos_materiales,
            longitud_primario_m=longitud_primario,
            longitud_secundario_m=longitud_secundario,
            metricas=metricas,
            precio_total_proyecto=precio_venta_neta,
            entrada=entrada,
        )

        debug_costos_proyecto = {
            "entrada": {
                "precio_base": precio_base,
                "precio_venta_neta": precio_venta_neta,
                "horas_grua": params["horas_grua"],
                "precio_hora_grua": params["precio_hora_grua"],
                "costo_grua": params["costo_grua"],
                "costo_flete_unitario": params["costo_flete_unitario"],
                "viajes_flete": params["viajes_flete"],
                "costo_flete": params["costo_flete"],
                "gastos_ingenieria": params["costo_ingenieria"],
                "incluir_logistica": params["incluir_logistica"],
                "incluir_logistica_en_venta": params["incluir_logistica_en_venta"],
                "porcentaje_contingencia": params["porcentaje_contingencia"],
                "metricas_estructuras": dict(metricas),
                "longitud_primario": longitud_primario,
                "longitud_secundario": longitud_secundario,
                "columnas_df_costos_materiales": list(df_costos_materiales.columns),
                "filas_df_costos_materiales": len(df_costos_materiales),
            },
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
            "debug_costos_proyecto": {"error": str(error)},
        }
