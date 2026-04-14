# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd
from ayuda.debug import debug_guardar
import streamlit as st

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import ResultadoProyecto, SalidaInterfaz
from aplicacion.modelos_proyecto import EntradaProyecto

# =========================================================
# DOMINIO
# =========================================================
from entradas.orquestador_entradas import ejecutar_entradas
from entradas.base_datos import obtener_catalogo_materiales
from entradas.base_datos import cargar_catalogo_estructuras_desde_indice

from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import (
    ejecutar_costos,
    EntradaCostos,
)
from costos_precios.precio_estructura import calcular_precio_estructura
from costos_precios.costos_operativos import calcular_costos_operativos
from costos_precios.costos_estructuras import calcular_costos_por_estructura
from exportadores.orquestador_reportes import generar_reportes


# =========================================================
# HELPERS
# =========================================================
def _fail(msg: str, debug: Optional[dict] = None) -> ResultadoProyecto:
    return ResultadoProyecto(
        ok=False,
        errores=[msg],
        warnings=[],
        materiales=None,
        costos=None,
        reportes=None,
        debug=debug or {},
    )


def _extraer_tension(datos: Dict[str, Any]) -> float:
    t = datos.get("tension") or datos.get("nivel_de_tension")

    if t is None:
        raise ValueError("Tensión no definida")

    t = float(t)

    if t <= 0:
        raise ValueError("Tensión inválida")

    return t


def _adaptar_df_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    if df is None:
        raise ValueError("df_estructuras es None")

    df = df.copy()
    cols = set(df.columns)

    if {"Estructura", "Cantidad"}.issubset(cols):
        return df

    if {"codigodeestructura", "Cantidad"}.issubset(cols):
        return df.rename(columns={"codigodeestructura": "Estructura"})

    raise ValueError(f"df_estructuras inválido: {list(cols)}")


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_proyecto(salida_interfaz: SalidaInterfaz) -> ResultadoProyecto:

    debug_global: Dict[str, Any] = {}

    try:

        # =====================================================
        # 0. INTERFAZ
        # =====================================================
        debug_global["interfaz"] = {
            "ok": getattr(salida_interfaz, "ok", None),
            "tipo_entrada": getattr(salida_interfaz, "tipo_entrada", None),
            "datos_proyecto_keys": list((salida_interfaz.datos_proyecto or {}).keys())
        }

        if not salida_interfaz.ok:
            return _fail("SalidaInterfaz no válida", debug_global)

        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        if not salida_entradas.ok:
            debug_global["entradas_error"] = {
                "errores": salida_entradas.errores,
                "warnings": salida_entradas.warnings
            }
            return _fail("Error en Entradas", debug_global)

        df_estructuras = _adaptar_df_estructuras(
            salida_entradas.df_estructuras
        )

        # =====================================================
        # 🔥 FIX REAL: DESCRIPCIONES (AQUÍ VA Y SOLO AQUÍ)
        # =====================================================
        mapa = cargar_catalogo_estructuras_desde_indice(
            salida_entradas.base_datos
        )

        if df_estructuras is not None and not df_estructuras.empty:

            col = "Estructura" if "Estructura" in df_estructuras.columns else "codigodeestructura"

            # NORMALIZAR
            df_estructuras[col] = (
                df_estructuras[col]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            mapa_norm = {
                str(k).strip().upper(): v
                for k, v in mapa.items()
            }

            df_estructuras["Descripcion"] = (
                df_estructuras[col]
                .map(mapa_norm)
                .fillna("")
            )

            total = len(df_estructuras)
            vacias = (df_estructuras["Descripcion"] == "").sum()

            print(f"[DEBUG] Descripciones: {total - vacias}/{total}")

        # =====================================================
        # DEBUG
        # =====================================================
        debug_global["estructuras"] = {
            "is_none": df_estructuras is None,
            "shape": df_estructuras.shape if df_estructuras is not None else None,
            "columns": list(df_estructuras.columns) if df_estructuras is not None else None,
            "sample": df_estructuras.head(10).to_dict() if df_estructuras is not None else None
        }

        # =====================================================
        # 2. PROYECTO
        # =====================================================
        df_tmp = salida_entradas.df_cables
        df_cables = df_tmp if isinstance(df_tmp, pd.DataFrame) else None
        
        entrada_proyecto = EntradaProyecto(
            base_datos=salida_entradas.base_datos,
            df_estructuras=df_estructuras,
            datos_proyecto=salida_entradas.datos_proyecto,
            calibre_mt=(salida_entradas.datos_proyecto or {}).get("calibre_mt", ""),
            tabla_conectores_mt=(salida_entradas.datos_proyecto or {}).get("tabla_conectores_mt", {}),
            df_cables=df_cables,
            df_materiales_extra=salida_entradas.df_materiales_extra,
        )

        entrada_proyecto.validar()
        tension = _extraer_tension(entrada_proyecto.datos_proyecto)

        # =====================================================
        # 3. MATERIALES
        # =====================================================
        entrada_mat = EntradaMateriales(
            estructuras_df=df_estructuras,
            tension=tension,
            base_datos=entrada_proyecto.base_datos,
            datos_proyecto=entrada_proyecto.datos_proyecto,
            df_cables=entrada_proyecto.df_cables,
            df_materiales_extra=entrada_proyecto.df_materiales_extra,
            calibre_mt=entrada_proyecto.calibre_mt,
            tabla_conectores_mt=entrada_proyecto.tabla_conectores_mt,
        )

        resultado_materiales = ejecutar_materiales(entrada_mat)
        df_materiales = resultado_materiales.df_materiales

        debug_global["materiales"] = {
            "df_materiales_rows": len(df_materiales),
            "keys_por_estructura": list(
                resultado_materiales.df_materiales_por_estructura.keys()
            )[:20]
        }

        # =====================================================
        # RESTO SIN CAMBIOS
        # =====================================================
        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=resultado_materiales,
            costos=None,
            reportes=None,
            debug=debug_global
        )

    except Exception as e:

        debug_global["exception"] = {
            "error": str(e),
            "trace": traceback.format_exc()
        }

        return _fail(str(e), debug_global)
