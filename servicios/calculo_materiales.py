# -*- coding: utf-8 -*-
"""
servicios/calculo_materiales.py

Orquestador: calcula materiales globales y por punto.
Devuelve dict 'resultados' con DFs + datos_proyecto.

Refactor:
- Separación por etapas (entradas, validación/normalización, cálculo global, cálculo por punto, extras)
- Helpers privados (_func) para que sea mantenible
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any, List

import pandas as pd
from core.costos_materiales import calcular_costos_desde_resumen
from core.costos_estructuras import calcular_costos_por_estructura


from core.cables_materiales import materiales_desde_cables

from entradas.excel_legacy import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
)

from core.conectores_mt import cargar_conectores_mt
from core.materiales_validacion import validar_datos_proyecto
from core.materiales_estructuras import calcular_materiales_estructura

from servicios.normalizacion_estructuras import (
    get_logger,
    normalizar_datos_proyecto,
    extraer_tension_ll_kv,
    limpiar_df_estructuras,
    construir_estructuras_por_punto_y_conteo,
)

from servicios.indice_estructuras import (
    cargar_indice_normalizado,
    construir_df_estructuras_resumen,
    construir_df_estructuras_por_punto,
)

from servicios.materiales_por_punto import (
    calcular_materiales_por_punto_con_cantidad,
)


# =============================================================================
# Modelos auxiliares
# =============================================================================

@dataclass(frozen=True)
class ContextoCalculo:
    """Contexto normalizado para el cálculo."""
    datos_proyecto: dict
    df_estructuras: pd.DataFrame
    tension_raw: str
    tension_ll: float
    calibre_mt: str


# =============================================================================
# Helpers: Entradas
# =============================================================================

def _cargar_entradas(
    *,
    archivo_estructuras=None,
    estructuras_df: Optional[pd.DataFrame] = None,
    datos_proyecto: Optional[dict] = None,
) -> Tuple[dict, pd.DataFrame]:
    """
    Obtiene datos_proyecto y df_estructuras desde:
      - archivo_estructuras (Excel) o
      - estructuras_df (DataFrame ya cargado)
    """
    if archivo_estructuras:
        dp = datos_proyecto or cargar_datos_proyecto(archivo_estructuras)
        df = cargar_estructuras_proyectadas(archivo_estructuras)
        return dp, df

    if estructuras_df is not None:
        dp = datos_proyecto or {}
        df = estructuras_df.copy()
        return dp, df

    raise ValueError("Debe proporcionar 'archivo_estructuras' o 'estructuras_df'.")


def _normalizar_y_validar_contexto(datos_proyecto: dict, df_estructuras: pd.DataFrame, log) -> ContextoCalculo:
    """
    Normaliza datos_proyecto, valida tensión/calibre, interpreta tensión LL.
    """
    dp = normalizar_datos_proyecto(datos_proyecto)

    tension_raw, calibre_mt = validar_datos_proyecto(dp)
    log(f"Tensión (raw): {tension_raw}   Calibre MT: {calibre_mt}")

    tension_ll = (
        extraer_tension_ll_kv(tension_raw)
        or extraer_tension_ll_kv(dp.get("nivel_de_tension"))
        or extraer_tension_ll_kv(dp.get("tension"))
    )
    if tension_ll is None:
        raise ValueError(f"No pude interpretar la tensión. Recibí: {tension_raw!r}")

    log(f"✅ Tensión normalizada (LL kV): {tension_ll}")

    return ContextoCalculo(
        datos_proyecto=dp,
        df_estructuras=df_estructuras,
        tension_raw=tension_raw,
        tension_ll=float(tension_ll),
        calibre_mt=str(calibre_mt).strip(),
    )


# =============================================================================
# Helpers: Limpieza / Conteo estructuras
# =============================================================================

def _limpiar_y_contar_estructuras(df_estructuras: pd.DataFrame, log):
    log("🔍 Limpieza inicial de estructuras...")

    # A) Precondición
    assert df_estructuras is not None, "A: df_estructuras llegó como None"
    assert not df_estructuras.empty, "A: df_estructuras llegó vacío"

    # B) Coerción ÚNICA a contrato CORE (aquí se resuelve ANCHO vs LARGO UI vs LARGO CORE)
    df = coerce_df_estructuras_largo(df_estructuras)

    # C) Postcondición contrato CORE
    assert df is not None and not df.empty, (
        "B: coerce_df_estructuras_largo devolvió vacío. "
        f"cols_in={list(df_estructuras.columns)}"
    )
    for c in ["Punto", "codigodeestructura", "cantidad"]:
        assert c in df.columns, f"C: falta {c}. cols={list(df.columns)}"

    # D) Normalización final (blindaje)
    df = df.copy()
    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip().str.upper()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)

    # E) Invariante
    assert (df["codigodeestructura"].str.len() > 0).all(), "E: hay codigodeestructura vacío"

    # F) Limpieza (si esto vacía, el culpable es limpiar_df_estructuras)
    df_unicas = limpiar_df_estructuras(df, log)
    assert df_unicas is not None, "F: limpiar_df_estructuras devolvió None"
    assert not df_unicas.empty, (
        "F: limpiar_df_estructuras está vaciando TODO. "
        f"Entrada rows={len(df)}; ejemplo={df['codigodeestructura'].head(15).tolist()}"
    )

    # G) Conteo (si esto queda vacío, el culpable es construir_estructuras_por_punto_y_conteo)
    estructuras_por_punto, conteo, tmp = construir_estructuras_por_punto_y_conteo(df_unicas, log)
    assert isinstance(conteo, dict), "G: conteo no es dict"
    assert len(conteo) > 0, (
        "G: construir_estructuras_por_punto_y_conteo devolvió conteo vacío. "
        f"Entrada rows={len(df_unicas)}; ejemplo={df_unicas['codigodeestructura'].head(15).tolist()}"
    )

    return df_unicas, conteo, tmp


# =============================================================================
# Helpers: Materiales globales
# =============================================================================

def _calcular_materiales_globales(
    *,
    archivo_materiales,
    conteo: dict,
    tension_ll: float,
    calibre_mt: str,
    tabla_conectores_mt: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula materiales globales (sumatoria por estructura) como DF explotado (no resumido).
    """
    df_lista: List[pd.DataFrame] = []

    for e, cantidad in conteo.items():
        df_mat = calcular_materiales_estructura(
            archivo_materiales,
            e,
            cantidad,
            tension_ll,
            calibre_mt,
            tabla_conectores_mt,
        )
        if df_mat is not None and not df_mat.empty:
            df_mat = df_mat.copy()
            df_mat["Unidad"] = df_mat["Unidad"].astype(str).str.strip()
            df_lista.append(df_mat)

    if not df_lista:
        return pd.DataFrame()

    return pd.concat(df_lista, ignore_index=True)


def _resumir_materiales_globales(df_total: pd.DataFrame) -> pd.DataFrame:
    """
    Resumen global: groupby Materiales/Unidad.
    """
    if df_total is None or df_total.empty:
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    return df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()


# =============================================================================
# Helpers: Estructuras resumen / por punto
# =============================================================================

def _construir_dfs_estructuras(
    df_indice: pd.DataFrame,
    conteo: dict,
    tmp_explotado: pd.DataFrame,
    log,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Construye:
      - df_estructuras_resumen
      - df_estructuras_por_punto
    """
    df_estructuras_resumen = construir_df_estructuras_resumen(df_indice, conteo, log)
    df_estructuras_por_punto = construir_df_estructuras_por_punto(tmp_explotado, df_indice, log)
    return df_estructuras_resumen, df_estructuras_por_punto


# =============================================================================
# Helpers: Materiales por punto
# =============================================================================

def _calcular_materiales_por_punto(
    *,
    archivo_materiales,
    tmp_explotado: pd.DataFrame,
    tension_ll: float,
    tabla_conectores_mt: pd.DataFrame,
    datos_proyecto: dict,
    log,
) -> pd.DataFrame:
    """
    Materiales por punto (con cantidades por punto).
    """
    return calcular_materiales_por_punto_con_cantidad(
        archivo_materiales,
        tmp_explotado,
        tension_ll,
        tabla_conectores_mt,
        datos_proyecto,
        log=log,
    )


# =============================================================================
# Helpers: Materiales extra (manuales)
# =============================================================================

def _integrar_materiales_extra(df_resumen: pd.DataFrame, datos_proyecto: dict, log):
    """
    Integra materiales extra desde session_state (si corre en Streamlit).
    ✅ NO normaliza nombres (ya vienen uniformes).
    """
    try:
        import streamlit as st  # noqa
        materiales_extra = st.session_state.get("materiales_extra", [])
    except Exception:
        materiales_extra = []

    if materiales_extra:
        df_extra = pd.DataFrame(materiales_extra)

        df_out = pd.concat([df_resumen, df_extra], ignore_index=True)
        df_out = df_out.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        datos_proyecto["materiales_extra"] = df_extra
        log(f"✅ Se integraron {len(df_extra)} materiales adicionales manuales")
        return df_out, datos_proyecto

    datos_proyecto["materiales_extra"] = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    return df_resumen, datos_proyecto


# =============================================================================
# API pública (orquestador)
# =============================================================================

def calcular_materiales(
    archivo_estructuras=None,
    archivo_materiales=None,
    estructuras_df: Optional[pd.DataFrame] = None,
    datos_proyecto: Optional[dict] = None,
    df_cables: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Orquesta todo el pipeline y retorna el dict de resultados.
    """
    log = get_logger()

    # 1) Entradas
    dp_in, df_estructuras = _cargar_entradas(
        archivo_estructuras=archivo_estructuras,
        estructuras_df=estructuras_df,
        datos_proyecto=datos_proyecto,
    )

    # 2) Normalización / validación
    ctx = _normalizar_y_validar_contexto(dp_in, df_estructuras, log)

    # 3) Limpieza + conteo
    _, conteo, tmp_explotado = _limpiar_y_contar_estructuras(ctx.df_estructuras, log)

    # 4) Índice + conectores
    df_indice = cargar_indice_normalizado(archivo_materiales, log)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # 5) Materiales globales (estructuras)
    df_total = _calcular_materiales_globales(
        archivo_materiales=archivo_materiales,
        conteo=conteo,
        tension_ll=ctx.tension_ll,
        calibre_mt=ctx.calibre_mt,
        tabla_conectores_mt=tabla_conectores_mt,
    )

    # 5.1) Materiales desde cables (UI)
    df_mat_cables = materiales_desde_cables(df_cables)
    if df_mat_cables is not None and not df_mat_cables.empty:
        dfc = df_mat_cables.copy()

        if "Codigo" in dfc.columns and "Materiales" not in dfc.columns:
            dfc["Materiales"] = dfc["Codigo"].astype(str).str.strip()
        if "Unidad" not in dfc.columns:
            dfc["Unidad"] = "m"
        if "Cantidad" not in dfc.columns and "Total Cable (m)" in dfc.columns:
            dfc["Cantidad"] = pd.to_numeric(dfc["Total Cable (m)"], errors="coerce").fillna(0.0)

        for col in ["Materiales", "Unidad", "Cantidad"]:
            if col not in dfc.columns:
                dfc[col] = "" if col != "Cantidad" else 0.0

        dfc = dfc[["Materiales", "Unidad", "Cantidad"]].copy()
        df_total = pd.concat([df_total, dfc], ignore_index=True)

        ctx.datos_proyecto["cables_proyecto_df"] = df_cables
        log(f"✅ Materiales desde cables integrados ({len(dfc)} filas)")

    # 5.2) Resumen global
    df_resumen = _resumir_materiales_globales(df_total)

    # 6) Estructuras
    df_estructuras_resumen, df_estructuras_por_punto = _construir_dfs_estructuras(
        df_indice, conteo, tmp_explotado, log
    )

    # 7) Materiales por punto
    df_resumen_por_punto = _calcular_materiales_por_punto(
        archivo_materiales=archivo_materiales,
        tmp_explotado=tmp_explotado,
        tension_ll=ctx.tension_ll,
        tabla_conectores_mt=tabla_conectores_mt,
        datos_proyecto=ctx.datos_proyecto,
        log=log,
    )

    # 8) Materiales extra (manuales)
    df_resumen, dp_out = _integrar_materiales_extra(df_resumen, ctx.datos_proyecto, log)

    # 8.1) COSTOS (ANEXO) 
    #Costos de Materiales
    df_costos = None
    if archivo_materiales:
        try:
            df_costos = calcular_costos_desde_resumen(df_resumen, archivo_materiales)

            if df_costos is None or df_costos.empty:
                log("⚠️ df_costos vacío (no hubo match de precios)")
                df_costos = None
            else:
                log(f"✅ Costos calculados: {len(df_costos)} filas")
                if "Tiene_Precio" in df_costos.columns:
                    log(f"✅ Filas con precio: {int(df_costos['Tiene_Precio'].sum())}")

        except Exception as e:
            log(f"❌ Error calculando costos: {type(e).__name__}: {e}")
            df_costos = None
   
    #Costos de Estructuras
    df_costos_estructuras = None
    try:
        if archivo_materiales:
            df_costos_estructuras = calcular_costos_por_estructura(
                archivo_materiales=archivo_materiales,
                conteo=conteo,
                tension_ll=ctx.tension_ll,
                calibre_mt=ctx.calibre_mt,
                tabla_conectores_mt=tabla_conectores_mt,
                df_indice=df_indice,
            )
    except Exception as e:
        log(f"❌ Error costos por estructura: {type(e).__name__}: {e}")
        df_costos_estructuras = None



    
    # 9) Resultado final
    return {
        "datos_proyecto": dp_out,
        "tension_ll": ctx.tension_ll,
        "calibre_mt": ctx.calibre_mt,
        
        "df_resumen": df_resumen,
        "df_estructuras_resumen": df_estructuras_resumen,
        "df_estructuras_por_punto": df_estructuras_por_punto,
        "df_resumen_por_punto": df_resumen_por_punto,

        # 👇 ESTA ERA LA PIEZA QUE NO ESTABA LLEGANDO BIEN
        "df_costos_materiales": df_costos,
        "df_costos_estructuras": df_costos_estructuras,
        # debug
        "conteo": conteo,
        "tmp_explotado": tmp_explotado,
    }
