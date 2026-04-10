# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd
import streamlit as st  # 🔥 agregado

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

from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import (
    ejecutar_costos,
    EntradaCostos,
)

from costos_precios.costos_estructuras import calcular_costos_por_estructura
from exportadores.orquestador_reportes import generar_reportes


# =========================================================
# HELPERS
# =========================================================
def _fail(msg: str) -> ResultadoProyecto:
    return ResultadoProyecto(
        ok=False,
        errores=[msg],
        warnings=[],
        materiales=None,
        costos=None,
        reportes=None,
        debug={}
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

    try:

        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida_entradas = ejecutar_entradas(salida_interfaz)

        if not salida_entradas.ok:
            st.write("❌ Error en entradas:", salida_entradas.errores)
            return _fail("Error en entradas")

        st.write("✔ Entradas OK")

        st.write("👉 Tipo df_estructuras:",
                 type(salida_entradas.df_estructuras))

        df_estructuras = _adaptar_df_estructuras(
            salida_entradas.df_estructuras
        )

        st.write("👉 Shape estructuras:", df_estructuras.shape)

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

        if not resultado_materiales.ok:
            st.write("❌ Error en materiales:", resultado_materiales.errores)
            return _fail("Error en materiales")

        df_materiales = resultado_materiales.df_materiales

        st.write("👉 Shape materiales:", df_materiales.shape)

        st.write("👉 Materiales por estructura:",
                 len(resultado_materiales.descripcion_estructuras))

        # =====================================================
        # 4. CATÁLOGO
        # =====================================================
        df_catalogo = obtener_catalogo_materiales(
            entrada_proyecto.base_datos
        )

        # =====================================================
        # 5. COSTOS
        # =====================================================
        entrada_costos = EntradaCostos(
            df_materiales=df_materiales,
            df_catalogo=df_catalogo,
            df_estructuras=df_estructuras,
            df_materiales_por_estructura=resultado_materiales.descripcion_estructuras,
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        # =====================================================
        # 6. COSTOS POR ESTRUCTURA
        # =====================================================
        df_costos_estructura = calcular_costos_por_estructura(
            df_estructuras=df_estructuras,
            df_materiales_por_estructura=resultado_materiales.descripcion_estructuras,
            df_precios_materiales=df_catalogo
        )

        if df_costos_estructura is None or df_costos_estructura.empty:
            st.write("❌ No se generaron costos por estructura")
        else:
            st.write("✔ Costos por estructura OK")
            st.write("👉 Shape costos:", df_costos_estructura.shape)

        # =====================================================
        # 7. REPORTES
        # =====================================================
        resultado_reportes = generar_reportes({
            "df_estructuras": df_estructuras,
            "df_materiales": df_materiales,
            "costos": resultado_costos,
            "costos_estructura": df_costos_estructura,
        })

        # =====================================================
        # 8. SALIDA
        # =====================================================
        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=resultado_materiales,
            costos=resultado_costos,
            df_costos_estructura=df_costos_estructura,
            reportes=resultado_reportes,
            debug={}
        )

    except Exception as e:

        st.write("❌ ERROR GLOBAL:", str(e))
        st.write(traceback.format_exc())

        return _fail(str(e))
