# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import traceback
import pandas as pd
import unicodedata

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

from costos_precios.orquestador_costos import ejecutar_costos, EntradaCostos
from exportadores.orquestador_reportes import generar_reportes, EntradaReportes
from entradas.base_datos import obtener_catalogo_materiales
from costos_precios.costos_proyecto import calcular_costos_proyecto


# =========================================================
# DEBUG SIMPLE (SIN RUIDO)
# =========================================================
def dbg(debug: dict, key: str, value: Any):
    debug[key] = value


# =========================================================
# HELPERS LIMPIOS
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


def limpiar_columna(texto: str) -> str:
    if texto is None:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).upper().strip()


def _extraer_tension(datos: Dict[str, Any]) -> float:
    t = datos.get("tension") or datos.get("nivel_de_tension")
    if t is None:
        raise ValueError("Tensión no definida")
    return float(t)


# =========================================================
# DF ESTRUCTURAS
# =========================================================
def adaptar_estructuras(df: pd.DataFrame) -> pd.DataFrame:

    if df is None:
        raise ValueError("df_estructuras None")

    df = df.copy()

    # 🔹 Normalizar nombres (SIN upper)
    df.columns = [str(c).strip() for c in df.columns]

    # 🔹 VALIDAR QUE EXISTE PUNTO (CRÍTICO)
    if "Punto" not in df.columns:
        raise ValueError(f"DF sin columna Punto: {list(df.columns)}")

    # 🔹 Definir CLAVE (SIEMPRE CODIGO)
    if "codigodeestructura" in df.columns:
        df["Estructura"] = df["codigodeestructura"]
    elif "CODIGO" in df.columns:
        df["Estructura"] = df["CODIGO"]
    elif "Estructura" in df.columns:
        df["Estructura"] = df["Estructura"]
    elif "ESTRUCTURA" in df.columns:
        df["Estructura"] = df["ESTRUCTURA"]
    else:
        raise ValueError(f"No se encontró columna válida de estructura: {list(df.columns)}")

    # 🔹 Forzar serie
    col = df["Estructura"]
    if isinstance(col, pd.DataFrame):
        col = col.iloc[:, 0]

    # 🔹 Limpieza
    df["Estructura"] = (
        col.astype(str)
           .str.upper()
           .str.strip()
    )

    # 🔹 ASEGURAR CANTIDAD
    if "Cantidad" not in df.columns:
        df["Cantidad"] = 1

    return df

# =========================================================
# MAPA INDICE (DESCRIPCIONES)
# =========================================================
def construir_mapa_indice(base: dict, debug: dict) -> dict:

    df_indice = base.get("INDICE") 

    if df_indice is None or not isinstance(df_indice, pd.DataFrame):
        dbg(debug, "INDICE", "NO_ENCONTRADO")
        return {}

    df_indice = df_indice.copy()
    df_indice.columns = [limpiar_columna(c) for c in df_indice.columns]

    dbg(debug, "INDICE_COLUMNS", list(df_indice.columns))

    col_codigo = None
    col_desc = None

    # 🔥 CORRECCIÓN AQUÍ
    for c in df_indice.columns:
        if "CODIGO" in c:
            col_codigo = c
        if "DESCRIP" in c or "ESTRUCTURA" in c:
            col_desc = c

    if not col_codigo or not col_desc:
        dbg(debug, "INDICE_ERROR", "COLUMNAS_NO_DETECTADAS")
        return {}

    df_indice[col_codigo] = df_indice[col_codigo].astype(str).str.upper().str.strip()
    df_indice[col_desc] = df_indice[col_desc].astype(str).str.strip()

    mapa = dict(zip(df_indice[col_codigo], df_indice[col_desc]))

    dbg(debug, "MAPA_SIZE", len(mapa))

    return mapa


# =========================================================
# APLICAR DESCRIPCIONES
# =========================================================
def aplicar_descripciones(df: pd.DataFrame, mapa: dict, debug: dict) -> pd.DataFrame:

    df = df.copy()

    # 1. Generas la descripción
    df["Descripcion"] = df["Estructura"].map(mapa).fillna("")

    # 2. Detectas cuáles NO tienen match
    sin_desc = df[df["Descripcion"] == ""]["Estructura"].unique()

    # 3. Métricas actuales (YA LAS TIENES)
    dbg(debug, "MATCH_OK", int((df["Descripcion"] != "").sum()))
    dbg(debug, "SIN_MATCH", list(sin_desc)[:15])

    # =====================================================
    # 🔥 AQUÍ VA TU AVISO (JUSTO AQUÍ)
    # =====================================================

    total = len(df)
    sin = len(sin_desc)

    if total > 0:
        porcentaje = round((sin / total) * 100, 2)
    else:
        porcentaje = 0

    dbg(debug, "AVISO_DESCRIPCION", {
        "sin_descripcion": sin,
        "total": total,
        "porcentaje": porcentaje,
        "ejemplos": list(sin_desc)[:10]
    })

    # 4. retornas normal
    return df

# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(salida_interfaz: SalidaInterfaz) -> ResultadoProyecto:

    debug: Dict[str, Any] = {}

    try:
        dbg(debug, "ETAPA", "INICIO")

        # =====================================================
        # 1. ENTRADAS
        # =====================================================
        salida = ejecutar_entradas(salida_interfaz)

        from interfaz.contratos import ResultadoProyecto

        if not salida.ok:
            return ResultadoProyecto(
            ok=False,
            errores=["No se generaron estructuras desde entradas"],
            warnings=salida.warnings
        )

        df_estructuras = adaptar_estructuras(salida.df_estructuras)

        dbg(debug, "DF_STRUCT", df_estructuras.shape)

        # =====================================================
        # 2. DESCRIPCIONES (FIX REAL)
        # =====================================================
        mapa = construir_mapa_indice(salida.base_datos or {}, debug)

        df_estructuras = aplicar_descripciones(df_estructuras, mapa, debug)

        # =====================================================
        # 3. PROYECTO
        # =====================================================
        entrada_proyecto = EntradaProyecto(
            base_datos=salida.base_datos,
            df_estructuras=df_estructuras,
            datos_proyecto=salida.datos_proyecto,
            calibre_mt=(salida.datos_proyecto or {}).get("calibre_mt", ""),
            tabla_conectores_mt=(salida.datos_proyecto or {}).get("tabla_conectores_mt", {}),
            df_cables=salida.df_cables,
            df_materiales_extra=salida.df_materiales_extra,
        )

        entrada_proyecto.validar()
        tension = _extraer_tension(entrada_proyecto.datos_proyecto)

        dbg(debug, "TENSION", tension)

        # =====================================================
        # 4. MATERIALES
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

        res_mat = ejecutar_materiales(entrada_mat)
        df_materiales = res_mat.df_materiales
        df_estructuras_pp = res_mat.df_estructuras_por_punto.copy()
       

        debug["res_mat_auditoria"] = {
            "tipo_res_mat": str(type(res_mat)),
            "ok": getattr(res_mat, "ok", None),
            "errores": getattr(res_mat, "errores", None),
            "warnings": getattr(res_mat, "warnings", None),

            "tipo_df_materiales": str(type(getattr(res_mat, "df_materiales", None))),
            "shape_df_materiales": (
                res_mat.df_materiales.shape
                if getattr(res_mat, "df_materiales", None) is not None
                else None
            ),

            "tipo_df_estructuras_por_punto": str(type(df_estructuras_pp_raw)),
            "shape_df_estructuras_por_punto": (
                df_estructuras_pp_raw.shape
                if df_estructuras_pp_raw is not None
                else None
            ),
        }

        df_estructuras_pp = aplicar_descripciones(df_estructuras_pp, mapa, debug)

        dbg(debug, "MATERIALES_ROWS", len(df_materiales))
        
        # =====================================================
        # 5. COSTOS
        # =====================================================
        df_catalogo = obtener_catalogo_materiales(salida.base_datos)
        import streamlit as st  # si no está arriba

        contratista = st.session_state.get("contratista", "C1")
        entrada_costos = EntradaCostos(
            df_materiales=df_materiales,
            df_catalogo=df_catalogo,
            df_estructuras=df_estructuras,
            df_materiales_por_estructura=res_mat.df_materiales_por_estructura,
            df_cables=salida.df_cables,
            contratista=contratista,
        )

        

        res_costos = ejecutar_costos(entrada_costos)
       

        dbg(debug, "COSTOS_OK", res_costos.get("ok"))
        dbg(debug, "COSTOS_ERRORES", res_costos.get("errores"))
        dbg(debug, "COSTOS_DEBUG", res_costos.get("debug"))

        df_precios = res_costos.get("df_precios_estructura")

        dbg(debug, "PRECIOS_OK", df_precios is not None)

        
        df_precios = res_costos.get("df_precios_estructura")

        dbg(debug, "PRECIOS_OK", df_precios is not None)

        # =====================================================
        # 6. COSTOS PROYECTO
        # =====================================================
        total = 0.0
        if df_precios is not None and not df_precios.empty:
            total = float(
                pd.to_numeric(df_precios["Total Proyecto"], errors="coerce")
                .fillna(0)
                .sum()
            )

        dbg(debug, "TOTAL_PROYECTO", total)

        entrada_cp = type("CP", (), {})()
        entrada_cp.df_estructuras = df_estructuras
        entrada_cp.df_cables = salida.df_cables
        entrada_cp.df_costos_materiales = res_costos.get("df_costos_materiales")
        entrada_cp.precio_venta_proyecto = total

        res_cp = calcular_costos_proyecto(entrada_cp)
        df_costos_materiales = res_costos.get("df_costos_materiales")

        # =====================================================
        # 🔥 FIX MATERIALES POR PUNTO (AQUÍ VA)
        # =====================================================
        df_mat_pp = res_mat.df_materiales_por_punto.copy()

        if "Punto" not in df_mat_pp.columns:
            df_mat_pp["Punto"] = "GLOBAL"
        
        # =====================================================
        # 7. REPORTES
        # =====================================================
        entrada_rep = EntradaReportes(
            df_estructuras=df_estructuras,
            df_estructuras_por_punto=df_estructuras_pp,
            df_materiales=df_materiales,
            df_materiales_por_punto=df_mat_pp,
            df_costos_materiales=df_costos_materiales,
            base_datos=salida.base_datos,
            costos={
                "df_costos_estructura": res_costos.get("df_costos_estructura"),
                "df_precios_estructura": df_precios,
                **res_cp
            },
            nombre_proyecto="Proyecto",
            datos_proyecto=salida.datos_proyecto,
            df_cables=salida.df_cables
        )

        reportes = generar_reportes(entrada_rep)

        dbg(debug, "FIN", "OK")

        return ResultadoProyecto(
            ok=True,
            errores=[],
            warnings=[],
            materiales=res_mat,
            costos=res_costos,
            reportes=reportes,
            debug=debug
        )

    except Exception as e:
        return _fail(str(e), {
            "traceback": traceback.format_exc(),
            **debug
        })
