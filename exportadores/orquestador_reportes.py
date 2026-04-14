# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import pandas as pd
import traceback

from interfaz.contratos import ResultadoProyecto, SalidaInterfaz
from aplicacion.modelos_proyecto import EntradaProyecto

from entradas.orquestador_entradas import ejecutar_entradas
from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from costos_precios.orquestador_costos import ejecutar_costos, EntradaCostos

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
        # ================= ENTRADAS =================
        salida = ejecutar_entradas(salida_interfaz)
        if not salida.ok:
            return _fail("Error en Entradas", debug_global)

        df = _adaptar_df_estructuras(salida.df_estructuras)

        # ================= DESCRIPCIONES =================
        df_indice = salida.base_datos.get("indice")
        if df_indice is not None and "Estructura" in df.columns:
            mapa = dict(zip(
                df_indice["Código de Estructura"].astype(str).str.strip().str.upper(),
                df_indice["Descripción"].astype(str).str.strip()
            ))

            df["Estructura"] = (
                df["Estructura"].astype(str).str.strip().str.upper()
            )

            df["Descripcion"] = df["Estructura"].map(mapa).fillna("")

        # ================= PROYECTO =================
        entrada = EntradaProyecto(
            base_datos=salida.base_datos,
            df_estructuras=df,
            datos_proyecto=salida.datos_proyecto,
            calibre_mt=(salida.datos_proyecto or {}).get("calibre_mt", ""),
            tabla_conectores_mt=(salida.datos_proyecto or {}).get("tabla_conectores_mt", {}),
            df_cables=salida.df_cables,
            df_materiales_extra=salida.df_materiales_extra,
        )

        entrada.validar()
        tension = _extraer_tension(entrada.datos_proyecto)

        # ================= MATERIALES =================
        entrada_mat = EntradaMateriales(
            estructuras_df=df,
            tension=tension,
            base_datos=entrada.base_datos,
            datos_proyecto=entrada.datos_proyecto,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            calibre_mt=entrada.calibre_mt,
            tabla_conectores_mt=entrada.tabla_conectores_mt,
        )

        resultado_materiales = ejecutar_materiales(entrada_mat)
        df_materiales = resultado_materiales.df_materiales

        # ================= COSTOS =================
        entrada_costos = EntradaCostos(
            df_materiales=df_materiales,
            df_catalogo=salida.base_datos.get("catalogo", pd.DataFrame()),
            df_estructuras=df,
            df_materiales_por_estructura=resultado_materiales.df_materiales_por_estructura,
        )

        resultado_costos = ejecutar_costos(entrada_costos)

        # ================= REPORTES (CORRECTO) =================
        entrada_reportes = EntradaReportes(
            df_estructuras=df,
            df_materiales=df_materiales,
            df_materiales_por_punto=resultado_materiales.df_materiales_por_punto,
            costos={
                "df_costos_estructura": resultado_costos.get("df_costos_estructura"),
                "df_precios_estructura": resultado_costos.get("df_precios_estructura"),
            },
            nombre_proyecto="Proyecto",
            datos_proyecto=salida.datos_proyecto,
        )

        reportes = generar_reportes(entrada_reportes)

        # ================= SALIDA =================
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
        return _fail(str(e), {"trace": traceback.format_exc()})
