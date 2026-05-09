# -*- coding: utf-8 -*-
from __future__ import annotations

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
        ["Estructura", "Codigo", "Código"],
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
def _extraer_longitudes(
    df_cables: Optional[pd.DataFrame],
) -> Tuple[float, float]:

    if df_cables is None or df_cables.empty:
        return 0.0, 0.0

    df = df_cables.copy()

    col_tipo = _obtener_columna(
        df,
        ["Tipo", "Tipo Cable", "Categoria", "Categoría"],
    )

    col_longitud = _obtener_columna(
        df,
        [
            "Total Cable (m)",
            "Longitud",
            "Longitud (m)",
            "Metros",
            "Cantidad",
        ],
    )

    if not col_tipo or not col_longitud:
        return 0.0, 0.0

    df[col_tipo] = (
        df[col_tipo]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df[col_longitud] = pd.to_numeric(
        df[col_longitud],
        errors="coerce",
    ).fillna(0)

    primario = df[
        df[col_tipo].str.startswith("MT", na=False)
        | df[col_tipo].str.contains("PRIMARIO", na=False)
    ]

    secundario = df[
        df[col_tipo].str.startswith("BT", na=False)
        | df[col_tipo].str.contains("SECUNDARIO", na=False)
    ]

    longitud_primario = float(primario[col_longitud].sum())
    longitud_secundario = float(secundario[col_longitud].sum())

    return longitud_primario, longitud_secundario


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
# CLASIFICAR COSTOS DESDE TABLA
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

        # -----------------------------
        # CLASIFICACIÓN OPERATIVA
        # -----------------------------
        if "GRUA" in texto or "GRÚA" in texto:
            costo_grua += monto

        elif "FLETE" in texto or "TRANSPORTE" in texto:
            costo_flete += monto

        elif "AGUJERO" in texto or "EXCAVACION" in texto or "EXCAVACIÓN" in texto:
            costo_agujeros += monto

        elif "CUADRILLA" in texto or "MANO DE OBRA" in texto or "INSTALACION" in texto:
            costo_cuadrilla += monto

        elif "INGENIERIA" in texto or "INGENIERÍA" in texto:
            costo_ingenieria += monto

        elif "ENEE" in texto or "PERMISO" in texto or "GESTION" in texto or "GESTIÓN" in texto:
            costo_enee += monto

        elif "MATERIAL" in texto or "SUMINISTRO" in texto:
            costo_materiales += monto

        else:
            # Por defecto se considera material,
            # porque df_materiales_costos normalmente viene del catálogo de materiales.
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
# COSTOS MANUALES DESDE ENTRADA
# =========================================================
def _extraer_costos_manuales(entrada) -> Dict[str, float]:

    return {
        "costo_cuadrilla_manual": _to_float(
            getattr(entrada, "costo_cuadrilla", 0)
        ),
        "costo_agujeros_manual": _to_float(
            getattr(entrada, "costo_agujeros", 0)
        ),
        "costo_grua_manual": _to_float(
            getattr(entrada, "costo_grua", 0)
        ),
        "costo_flete_manual": _to_float(
            getattr(entrada, "costo_flete", 0)
        ),
        "costo_enee_manual": _to_float(
            getattr(entrada, "costo_enee", 0)
        ),
        "costo_ingenieria_manual": _to_float(
            getattr(entrada, "gastos_ingenieria", 0)
        ),
    }


# =========================================================
# CALCULAR TIEMPOS
# =========================================================
def _calcular_tiempos(
    longitud_primario_m: float,
    longitud_secundario_m: float,
    total_estructuras: int,
    num_postes: int,
    num_retenidas: int,
) -> Dict[str, Any]:

    dias_levantamiento = 1

    dias_agujeros = max(
        0,
        round(num_postes / 10),
    )

    dias_postes = max(
        0,
        round(num_postes / 7),
    )

    dias_retenidas = max(
        0,
        round(num_retenidas / 6),
    )

    dias_estructuras = max(
        0,
        round(total_estructuras / 8),
    )

    dias_primario = max(
        0,
        round(longitud_primario_m / 500),
    ) if longitud_primario_m else 0

    dias_secundario = max(
        0,
        round(longitud_secundario_m / 300),
    ) if longitud_secundario_m else 0

    cronograma = []

    dia_actual = 1

    actividades = [
        ("Levantamiento", dias_levantamiento),
        ("Agujeros", dias_agujeros),
        ("Postes", dias_postes),
        ("Retenidas", dias_retenidas),
        ("Estructuras", dias_estructuras),
        ("Tendido MT", dias_primario),
        ("Tendido BT", dias_secundario),
    ]

    for actividad, duracion in actividades:
        if duracion <= 0:
            cronograma.append(
                {
                    "actividad": actividad,
                    "duracion_dias": 0,
                    "inicio": None,
                    "fin": None,
                }
            )
            continue

        inicio = dia_actual
        fin = dia_actual + duracion - 1

        cronograma.append(
            {
                "actividad": actividad,
                "duracion_dias": int(duracion),
                "inicio": int(inicio),
                "fin": int(fin),
            }
        )

        dia_actual = fin + 1

    dias_totales = max(
        [
            item["fin"] or 0
            for item in cronograma
        ]
    ) if cronograma else 0

    return {
        "dias_levantamiento": dias_levantamiento,
        "dias_agujeros": dias_agujeros,
        "dias_postes": dias_postes,
        "dias_retenidas": dias_retenidas,
        "dias_estructuras": dias_estructuras,
        "dias_primario": dias_primario,
        "dias_secundario": dias_secundario,
        "dias_totales": dias_totales,
        "cronograma_resumen": cronograma,
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
    ) if total_estructuras else 0

    utilidad_por_estructura = (
        utilidad / total_estructuras
    ) if total_estructuras else 0

    costo_por_poste = (
        costo_total_real / num_postes
    ) if num_postes else 0

    utilidad_diaria = (
        utilidad / dias_totales
    ) if dias_totales else 0

    return {
        "costo_por_estructura": round(costo_por_estructura, 2),
        "utilidad_por_estructura": round(utilidad_por_estructura, 2),
        "costo_por_poste": round(costo_por_poste, 2),
        "utilidad_diaria": round(utilidad_diaria, 2),
    }


# =========================================================
# DISTRIBUCIÓN DE COSTOS
# =========================================================
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
        ("Contingencia", costs_or_zero(costos, "contingencia")),
    ]

    salida = []

    for rubro, monto in rubros:
        monto = _to_float(monto)

        if abs(monto) <= 0:
            continue

        porcentaje = (
            monto / costo_total_real * 100
        ) if costo_total_real else 0

        salida.append(
            {
                "rubro": rubro,
                "monto": round(monto, 2),
                "porcentaje": round(porcentaje, 2),
            }
        )

    return salida


def costs_or_zero(costos: Dict[str, float], key: str) -> float:
    return _to_float(costos.get(key, 0))


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
                "El costo total estimado supera el valor de venta del proyecto."
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
        "mensaje": (
            "El proyecto presenta una rentabilidad favorable."
        ),
        "nivel": "bueno",
    }


# =========================================================
# MOTOR DE COSTOS REAL
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

    # =====================================================
    # COSTOS DESDE TABLA
    # =====================================================
    costos_tabla = _clasificar_costos_desde_materiales(
        df_materiales_costos
    )

    # =====================================================
    # COSTOS MANUALES
    # =====================================================
    costos_manuales = _extraer_costos_manuales(
        entrada
    ) if entrada is not None else {
        "costo_cuadrilla_manual": 0,
        "costo_agujeros_manual": 0,
        "costo_grua_manual": 0,
        "costo_flete_manual": 0,
        "costo_enee_manual": 0,
        "costo_ingenieria_manual": 0,
    }

    # =====================================================
    # CONSOLIDACIÓN
    # =====================================================
    costo_materiales = costos_tabla["costo_materiales"]

    costo_cuadrilla = (
        costos_tabla["costo_cuadrilla"]
        + costos_manuales["costo_cuadrilla_manual"]
    )

    costo_agujeros = (
        costos_tabla["costo_agujeros"]
        + costos_manuales["costo_agujeros_manual"]
    )

    costo_grua = (
        costos_tabla["costo_grua"]
        + costos_manuales["costo_grua_manual"]
    )

    costo_flete = (
        costos_tabla["costo_flete"]
        + costos_manuales["costo_flete_manual"]
    )

    costo_enee = (
        costos_tabla["costo_enee"]
        + costos_manuales["costo_enee_manual"]
    )

    costo_ingenieria = (
        costos_tabla["costo_ingenieria"]
        + costos_manuales["costo_ingenieria_manual"]
    )

    costo_otros = costos_tabla["costo_otros"]

    # =====================================================
    # TIEMPOS
    # =====================================================
    tiempos = _calcular_tiempos(
        longitud_primario_m=longitud_primario_m,
        longitud_secundario_m=longitud_secundario_m,
        total_estructuras=total_estructuras,
        num_postes=num_postes,
        num_retenidas=num_retenidas,
    )

    dias_totales = tiempos["dias_totales"]

    # =====================================================
    # SUBTOTAL
    # =====================================================
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

    # =====================================================
    # CONTINGENCIA
    # =====================================================
    porcentaje_contingencia = _to_float(
        getattr(entrada, "porcentaje_contingencia", 5)
    ) if entrada is not None else 5

    contingencia = subtotal * (porcentaje_contingencia / 100)

    # =====================================================
    # COSTO TOTAL REAL
    # =====================================================
    costo_total_real = subtotal + contingencia

    # =====================================================
    # RESULTADOS FINANCIEROS
    # =====================================================
    utilidad = precio_total_proyecto - costo_total_real

    margen_pct = (
        utilidad / precio_total_proyecto * 100
    ) if precio_total_proyecto else 0

    # =====================================================
    # KPIs
    # =====================================================
    kpis = _calcular_kpis(
        costo_total_real=costo_total_real,
        utilidad=utilidad,
        total_estructuras=total_estructuras,
        num_postes=num_postes,
        dias_totales=dias_totales,
    )

    # =====================================================
    # COSTOS CONSOLIDADOS
    # =====================================================
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

    # =====================================================
    # PORCENTAJES DIRECTOS PARA COMPATIBILIDAD CON PDF ACTUAL
    # =====================================================
    porcentaje_materiales = (
        costo_materiales / costo_total_real * 100
    ) if costo_total_real else 0

    porcentaje_cuadrilla = (
        costo_cuadrilla / costo_total_real * 100
    ) if costo_total_real else 0

    porcentaje_grua = (
        costo_grua / costo_total_real * 100
    ) if costo_total_real else 0

    # =====================================================
    # RETORNO
    # =====================================================
    return {
        # =============================
        # COSTOS
        # =============================
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

        # =============================
        # RESULTADOS FINANCIEROS
        # =============================
        "subtotal_costos": round(subtotal, 2),
        "costo_total_real": round(costo_total_real, 2),
        "precio_venta": round(precio_total_proyecto, 2),
        "utilidad": round(utilidad, 2),
        "margen_pct": round(margen_pct, 2),

        # =============================
        # MÉTRICAS
        # =============================
        "dias_totales": round(dias_totales, 2),
        "num_postes": int(num_postes),
        "num_retenidas": int(num_retenidas),
        "total_estructuras": int(total_estructuras),
        "longitud_primario": round(longitud_primario_m, 2),
        "longitud_secundario": round(longitud_secundario_m, 2),

        # =============================
        # DISTRIBUCIÓN SIMPLE
        # =============================
        "porcentaje_materiales": round(porcentaje_materiales, 2),
        "porcentaje_cuadrilla": round(porcentaje_cuadrilla, 2),
        "porcentaje_grua": round(porcentaje_grua, 2),

        # =============================
        # DISTRIBUCIÓN DETALLADA
        # =============================
        "distribucion_costos": distribucion_costos,

        # =============================
        # CRONOGRAMA
        # =============================
        "cronograma_resumen": tiempos["cronograma_resumen"],
        "tiempos": tiempos,

        # =============================
        # EVALUACIÓN
        # =============================
        "evaluacion": evaluacion,
        "estado_proyecto": evaluacion["estado"],
        "mensaje_evaluacion": evaluacion["mensaje"],
        "nivel_evaluacion": evaluacion["nivel"],

        # =============================
        # KPIs
        # =============================
        **kpis,
    }


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def calcular_costos_proyecto(
    entrada,
) -> Dict[str, Any]:

    try:
        # =================================================
        # ESTRUCTURAS
        # =================================================
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

        # =================================================
        # CABLES
        # =================================================
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

        # =================================================
        # MATERIALES / COSTOS
        # =================================================
        df_materiales_costos = getattr(
            entrada,
            "df_materiales_costos",
            None,
        )

        _validar_materiales(
            df_materiales_costos
        )

        # =================================================
        # PRECIO DE VENTA FINAL
        # =================================================
        precio_base = _to_float(
            getattr(
                entrada,
                "precio_venta_proyecto",
                0,
            )
        )

        gastos_ingenieria = _to_float(
            getattr(
                entrada,
                "gastos_ingenieria",
                0,
            )
        )

        incluir_ingenieria_en_venta = getattr(
            entrada,
            "incluir_ingenieria_en_venta",
            True,
        )

        if incluir_ingenieria_en_venta:
            precio_total = precio_base + gastos_ingenieria
        else:
            precio_total = precio_base

        # =================================================
        # MOTOR
        # =================================================
        resultado = _motor_costos(
            df_materiales_costos=df_materiales_costos,
            longitud_primario_m=longitud_primario,
            longitud_secundario_m=longitud_secundario,
            total_estructuras=total_estructuras,
            num_postes=num_postes,
            num_retenidas=num_retenidas,
            precio_total_proyecto=precio_total,
            entrada=entrada,
        )

        # =================================================
        # DEBUG VISIBLE PARA STREAMLIT
        # =================================================
        debug_costos_proyecto = {
            "entrada": {
                "precio_base": precio_base,
                "gastos_ingenieria": gastos_ingenieria,
                "precio_total": precio_total,
                "total_estructuras": total_estructuras,
                "num_postes": num_postes,
                "num_retenidas": num_retenidas,
                "longitud_primario": longitud_primario,
                "longitud_secundario": longitud_secundario,
                "columnas_df_materiales_costos": list(
                    df_materiales_costos.columns
                ),
                "filas_df_materiales_costos": len(
                    df_materiales_costos
                ),
            },
            "resultado": resultado,
        }

        # =================================================
        # RETORNO OK
        # =================================================
        return {
            "ok": True,
            "resultado_costos_proyecto": resultado,
            "df_materiales_costos": df_materiales_costos,
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
