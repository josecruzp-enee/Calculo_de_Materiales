# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd
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
from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import (
    ejecutar_costos,
    EntradaCostos,
)

# 🔥 IMPORT CORRECTO
from exportadores.orquestador_reportes import generar_reportes, EntradaReportes


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

        debug_global["ETAPA"] = "INICIO"

        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        debug_global["ENTRADAS"] = {
            "ok": salida_entradas.ok,
            "df_estructuras": None if salida_entradas.df_estructuras is None else salida_entradas.df_estructuras.shape,
            "base_datos_keys": list(salida_entradas.base_datos.keys())[:10] if salida_entradas.base_datos else None,
        }

        if not salida_entradas.ok:
            return _fail("Error en Entradas", debug_global)

        df_estructuras = _adaptar_df_estructuras(
            salida_entradas.df_estructuras
        )

        debug_global["DF_ESTRUCTURAS_INICIAL"] = {
            "shape": df_estructuras.shape,
            "columns": list(df_estructuras.columns)
        }
        st.subheader("🔥 RAW DF ESTRUCTURAS")
        st.write(salida_entradas.df_estructuras)
        # =====================================================
        # 🔥 DESCRIPCIONES (SOLUCIÓN SIMPLE Y DIRECTA)
        # =====================================================
        try:
            df_indice = pd.read_excel(
                "data/Estructura_datos.xlsx",
                sheet_name="indice"
            )

            df_indice.columns = [c.strip().upper() for c in df_indice.columns]

            mapa = dict(zip(
                df_indice["CÓDIGO DE ESTRUCTURA"].astype(str).str.strip().str.upper(),
                df_indice["DESCRIPCIÓN"].astype(str).str.strip()
            ))

        except Exception:
            mapa = {}

        df_estructuras["Estructura"] = (
            df_estructuras["Estructura"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df_estructuras["Descripcion"] = (
            df_estructuras["Estructura"]
            .map(mapa)
            .fillna("")
        )

        debug_global["DESCRIPCIONES"] = {
            "total": len(df_estructuras),
            "con_descripcion": int((df_estructuras["Descripcion"] != "").sum()),
            "sin_descripcion": int((df_estructuras["Descripcion"] == "").sum()),
        }

        # =====================================================
        # 2. PROYECTO
        # =====================================================
        entrada_proyecto = EntradaProyecto(
            base_datos=salida_entradas.base_datos,
            df_estructuras=df_estructuras,
            datos_proyecto=salida_entradas.datos_proyecto,
            calibre_mt=(salida_entradas.datos_proyecto or {}).get("calibre_mt", ""),
            tabla_conectores_mt=(salida_entradas.datos_proyecto or {}).get("tabla_conectores_mt", {}),
            df_cables=salida_entradas.df_cables,
            df_materiales_extra=salida_entradas.df_materiales_extra,
        )

        entrada_proyecto.validar()
        tension = _extraer_tension(entrada_proyecto.datos_proyecto)

        debug_global["PROYECTO"] = {
            "tension": tension
        }

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

        debug_global["MATERIALES"] = {
            "df_materiales": None if df_materiales is None else df_materiales.shape
        }

        # =====================================================
        # 4. COSTOS
        # =====================================================
        entrada_costos = EntradaCostos(
            df_materiales=df_materiales,
            df_catalogo=salida_entradas.base_datos.get("MATERIALES", pd.DataFrame()),
            df_estructuras=df_estructuras,
            df_materiales_por_estructura=resultado_materiales.df_materiales_por_estructura,
            df_cables=salida_entradas.df_cables 
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        debug_global["COSTOS"] = {
            "df_precios": None if resultado_costos.get("df_precios_estructura") is None else "OK",
            "df_costos": None if resultado_costos.get("df_costos_estructura") is None else "OK"
        }

        # =====================================================
        # 5. REPORTES
        # =====================================================
        entrada_reportes = EntradaReportes(
            df_estructuras=df_estructuras,
            df_materiales=df_materiales,
            df_materiales_por_punto=resultado_materiales.df_materiales_por_punto,
            costos={
                "df_costos_estructura": resultado_costos.get("df_costos_estructura"),
                "df_precios_estructura": resultado_costos.get("df_precios_estructura"),
            },
            nombre_proyecto="Proyecto",
            datos_proyecto=salida_entradas.datos_proyecto,
            df_cables=salida_entradas.df_cables
        )

        reportes = generar_reportes(entrada_reportes)

        debug_global["REPORTES"] = {
            "archivos": list(reportes["archivos"].keys()),
            "errores": reportes["errores"]
        }

        # =====================================================
        # SALIDA FINAL
        # =====================================================
        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=resultado_materiales,
            costos=resultado_costos,
            reportes=reportes,
            debug=debug_global
        )

    except Exception as e:
        return _fail(str(e), {
            "traceback": traceback.format_exc(),
            **debug_global
        })
