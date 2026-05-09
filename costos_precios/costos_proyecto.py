# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from typing import Dict, Any


# =========================================================
# 🔧 UTILIDADES SEGURAS
# =========================================================
def _safe_sum(series: pd.Series) -> float:

    try:

        return float(
            pd.to_numeric(
                series,
                errors="coerce"
            ).fillna(0).sum()
        )

    except Exception:

        return 0.0


# =========================================================
# 🔥 EXTRAER MÉTRICAS DE ESTRUCTURAS
# =========================================================
def _extraer_metricas_estructuras(
    df_estructuras_global: pd.DataFrame
):

    if (
        df_estructuras_global is None
        or df_estructuras_global.empty
    ):
        return 0, 0, 0

    df = df_estructuras_global.copy()

    if (
        "Estructura" not in df.columns
        or "Cantidad" not in df.columns
    ):
        return 0, 0, 0

    df["Estructura"] = (
        df["Estructura"]
        .astype(str)
        .str.upper()
    )

    df["Cantidad"] = pd.to_numeric(
        df["Cantidad"],
        errors="coerce"
    ).fillna(0)

    total_estructuras = int(
        df["Cantidad"].sum()
    )

    num_postes = int(
        df[
            df["Estructura"]
            .str.startswith("PC", na=False)
        ]["Cantidad"].sum()
    )

    num_retenidas = int(
        df[
            df["Estructura"]
            .str.startswith("R-", na=False)
        ]["Cantidad"].sum()
    )

    return (

        total_estructuras,

        num_postes,

        num_retenidas
    )


# =========================================================
# 🔥 EXTRAER LONGITUDES DE CABLE
# =========================================================
def _extraer_longitudes(
    df_cables: pd.DataFrame
):

    if (
        df_cables is None
        or df_cables.empty
    ):
        return 0.0, 0.0

    df = df_cables.copy()

    if "Tipo" not in df.columns:
        return 0.0, 0.0

    df["Tipo"] = (
        df["Tipo"]
        .astype(str)
        .str.upper()
    )

    # =====================================================
    # DETECTAR COLUMNA
    # =====================================================
    if "Total Cable (m)" in df.columns:

        df["Total Cable (m)"] = pd.to_numeric(
            df["Total Cable (m)"],
            errors="coerce"
        ).fillna(0)

        col_long = "Total Cable (m)"

    elif "Longitud" in df.columns:

        df["Longitud"] = pd.to_numeric(
            df["Longitud"],
            errors="coerce"
        ).fillna(0)

        col_long = "Longitud"

    else:

        return 0.0, 0.0

    # =====================================================
    # FILTRAR
    # =====================================================
    primario = df[
        df["Tipo"]
        .str.startswith("MT", na=False)
    ]

    secundario = df[
        df["Tipo"]
        .str.startswith("BT", na=False)
    ]

    return (

        float(primario[col_long].sum()),

        float(secundario[col_long].sum())
    )


# =========================================================
# 🔥 VALIDAR MATERIALES
# =========================================================
def _validar_materiales(
    df_materiales_costos: pd.DataFrame
):

    if (
        df_materiales_costos is None
        or df_materiales_costos.empty
    ):
        raise ValueError(
            "No hay materiales con costos"
        )

    if (
        "Costo Total"
        not in df_materiales_costos.columns
    ):
        raise ValueError(
            "df_materiales_costos debe tener 'Costo Total'"
        )


# =========================================================
# 🔥 CALCULAR TIEMPOS
# =========================================================
def _calcular_tiempos(
    longitud_primario_m,
    longitud_secundario_m,
    total_estructuras,
):

    dias_primario = (
        longitud_primario_m / 500
        if longitud_primario_m else 0
    )

    dias_secundario = (
        longitud_secundario_m / 300
        if longitud_secundario_m else 0
    )

    dias_estructura = (
        total_estructuras / 8
        if total_estructuras else 0
    )

    dias_totales = (

        dias_primario
        + dias_secundario
        + dias_estructura
    )

    return {

        "dias_primario": dias_primario,

        "dias_secundario": dias_secundario,

        "dias_estructura": dias_estructura,

        "dias_totales": dias_totales,
    }


# =========================================================
# 🔥 CALCULAR COSTOS OPERATIVOS
# =========================================================
# =========================================================
# 🔥 CALCULAR COSTOS OPERATIVOS
# =========================================================
def _calcular_costos_operativos():

    return {

        # =========================================
        # COSTOS MANUALES
        # =========================================
        # Estos costos ya se agregan en:
        # - tabla_presupuesto_general()
        # - cuadro_general_precios
        # - resumen comercial
        #
        # NO volver a calcular aquí.
        # =========================================

        "costo_cuadrilla": 0.0,

        "costo_agujeros": 0.0,

        "costo_grua": 0.0,

        "costo_enee": 0.0,
    }

# =========================================================
# 🔥 CALCULAR KPIs
# =========================================================
def _calcular_kpis(
    costo_total_real,
    utilidad,
    total_estructuras,
    num_postes,
    dias_totales,
):

    costo_por_estructura = (
        costo_total_real
        / total_estructuras
    ) if total_estructuras else 0

    utilidad_por_estructura = (
        utilidad
        / total_estructuras
    ) if total_estructuras else 0

    costo_por_poste = (
        costo_total_real
        / num_postes
    ) if num_postes else 0

    utilidad_diaria = (
        utilidad
        / dias_totales
    ) if dias_totales else 0

    return {

        "costo_por_estructura": round(
            costo_por_estructura,
            2
        ),

        "utilidad_por_estructura": round(
            utilidad_por_estructura,
            2
        ),

        "costo_por_poste": round(
            costo_por_poste,
            2
        ),

        "utilidad_diaria": round(
            utilidad_diaria,
            2
        ),
    }


# =========================================================
# 🔥 MOTOR DE COSTOS REAL
# =========================================================
def _motor_costos(
    df_materiales,
    longitud_primario_m,
    longitud_secundario_m,
    total_estructuras,
    num_postes,
    num_retenidas,
    precio_total_proyecto,
):

    # =====================================================
    # COSTO MATERIALES
    # =====================================================
    costo_materiales = float(
        df_materiales["Costo Total"].sum()
    )

    # =====================================================
    # TIEMPOS
    # =====================================================
    tiempos = _calcular_tiempos(
        longitud_primario_m,
        longitud_secundario_m,
        total_estructuras,
    )

    dias_totales = tiempos["dias_totales"]

    # =====================================================
    # COSTOS OPERATIVOS
    # =====================================================
    costos = _calcular_costos_operativos()

    costo_cuadrilla = costos["costo_cuadrilla"]

    costo_agujeros = costos["costo_agujeros"]

    costo_grua = costos["costo_grua"]

    costo_enee = costos["costo_enee"]

    # =====================================================
    # SUBTOTAL
    # =====================================================
    subtotal = (

        costo_materiales
        + costo_cuadrilla
        + costo_agujeros
        + costo_grua
        + costo_enee
    )

    # =====================================================
    # CONTINGENCIA
    # =====================================================
    contingencia = (
        subtotal * 0.05
    )

    # =====================================================
    # COSTO TOTAL REAL
    # =====================================================
    costo_total_real = (
        subtotal
        + contingencia
    )

    # =====================================================
    # UTILIDAD
    # =====================================================
    utilidad = (
        precio_total_proyecto
        - costo_total_real
    )

    margen_pct = (
        (
            utilidad
            / precio_total_proyecto
        ) * 100
    ) if precio_total_proyecto else 0

    # =====================================================
    # KPIs
    # =====================================================
    kpis = _calcular_kpis(

        costo_total_real,

        utilidad,

        total_estructuras,

        num_postes,

        dias_totales,
    )

    # =====================================================
    # DISTRIBUCIÓN DE COSTOS
    # =====================================================
    porcentaje_materiales = (
        costo_materiales
        / costo_total_real * 100
    ) if costo_total_real else 0

    porcentaje_cuadrilla = (
        costo_cuadrilla
        / costo_total_real * 100
    ) if costo_total_real else 0

    porcentaje_grua = (
        costo_grua
        / costo_total_real * 100
    ) if costo_total_real else 0

    # =====================================================
    # RETORNO
    # =====================================================
    return {

        # =============================
        # COSTOS
        # =============================
        "costo_materiales": costo_materiales,

        "costo_cuadrilla": costo_cuadrilla,

        "costo_agujeros": costo_agujeros,

        "costo_grua": costo_grua,

        "costo_enee": costo_enee,

        "contingencia": contingencia,

        # =============================
        # RESULTADOS FINANCIEROS
        # =============================
        "costo_total_real": costo_total_real,

        "precio_venta": precio_total_proyecto,

        "utilidad": utilidad,

        "margen_pct": round(
            margen_pct,
            2
        ),

        # =============================
        # MÉTRICAS
        # =============================
        "dias_totales": round(
            dias_totales,
            2
        ),

        "num_postes": num_postes,

        "num_retenidas": num_retenidas,

        "total_estructuras": total_estructuras,

        "longitud_primario": longitud_primario_m,

        "longitud_secundario": longitud_secundario_m,

        # =============================
        # DISTRIBUCIÓN
        # =============================
        "porcentaje_materiales": round(
            porcentaje_materiales,
            2
        ),

        "porcentaje_cuadrilla": round(
            porcentaje_cuadrilla,
            2
        ),

        "porcentaje_grua": round(
            porcentaje_grua,
            2
        ),

        # =============================
        # KPIs
        # =============================
        **kpis
    }


# =========================================================
# 🔥 FUNCIÓN PRINCIPAL
# =========================================================
def calcular_costos_proyecto(
    entrada
) -> Dict[str, Any]:

    try:

        # =================================================
        # ESTRUCTURAS
        # =================================================
        df_estructuras_global = getattr(
            entrada,
            "df_estructuras",
            None
        )

        (
            total_estructuras,
            num_postes,
            num_retenidas

        ) = _extraer_metricas_estructuras(
            df_estructuras_global
        )

        # =================================================
        # CABLES
        # =================================================
        (
            longitud_primario,
            longitud_secundario

        ) = _extraer_longitudes(
            getattr(
                entrada,
                "df_cables",
                None
            )
        )

        # =================================================
        # MATERIALES
        # =================================================
        df_materiales_costos = getattr(
            entrada,
            "df_materiales_costos",
            None
        )

        _validar_materiales(
            df_materiales_costos
        )

        # =================================================
        # PRECIO VENTA FINAL
        # =================================================
        precio_base = getattr(
            entrada,
            "precio_venta_proyecto",
            0
        )

        gastos_ingenieria = getattr(
            entrada,
            "gastos_ingenieria",
            25000
        )

        precio_total = (
            precio_base
            + gastos_ingenieria
        )

        # =================================================
        # MOTOR
        # =================================================
        resultado = _motor_costos(

            df_materiales_costos,

            longitud_primario,

            longitud_secundario,

            total_estructuras,

            num_postes,

            num_retenidas,

            precio_total,
        )

        # =================================================
        # RETORNO OK
        # =================================================
        return {

            "ok": True,

            "resultado_costos_proyecto": resultado,

            "df_materiales_costos": (
                df_materiales_costos
            ),
        }

    except Exception as e:

        return {

            "ok": False,

            "error": str(e),

            "resultado_costos_proyecto": None
        }
