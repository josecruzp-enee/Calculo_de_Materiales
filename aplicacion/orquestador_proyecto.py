# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py

from __future__ import annotations

import pandas as pd

from aplicacion.modelos_proyecto import EntradaProyecto

# =========================
# DOMINIO
# =========================
from materiales.orquestador_materiales import ejecutar_materiales
from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

# =========================
# BASE
# =========================
from entradas.base_datos import cargar_base_datos, obtener_catalogo_materiales


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada_proyecto: EntradaProyecto) -> ResultadoMateriales:
    """
    Flujo maestro:
    Entradas → Validación → Cálculos → Consolidación → Salidas
    """

    debug = {}

    # =====================================================
    # 1. VALIDACIÓN
    # =====================================================
    errores = _validar_entrada(entrada_proyecto)
    if errores:
        return _resultado_error("Validación fallida", errores, debug)

    # =====================================================
    # 2. NORMALIZACIÓN DE OPCIONALES
    # =====================================================
    df_cables, df_materiales_extra = _normalizar_opcionales(entrada_proyecto)

    # =====================================================
    # 3. CARGA BASE DE DATOS
    # =====================================================
    base, catalogo, error_base = _cargar_base()
    if error_base:
        return _resultado_error("Error base de datos", [error_base], debug)

    # =====================================================
    # 4. CONSTRUIR ENTRADA A MATERIALES (BUILDER)
    # =====================================================
    entrada_materiales, error_builder = _construir_entrada_materiales(
        entrada_proyecto,
        base,
        df_cables,
        df_materiales_extra
    )

    if error_builder:
        return _resultado_error("Error construyendo entrada", [error_builder], debug)

    # =====================================================
    # DEBUG (ANTES DE CÁLCULO)
    # =====================================================
    debug["entrada_materiales"] = {
        "tension": entrada_materiales.tension,
        "estructuras_shape": entrada_materiales.estructuras_df.shape,
        "tiene_base": entrada_materiales.hojas_base is not None,
        "cables": None if entrada_materiales.df_cables is None else "OK",
        "materiales_extra": None if entrada_materiales.df_materiales_extra is None else "OK",
    }

    # =====================================================
    # 5. CÁLCULO
    # =====================================================
    resultado, error_calculo = _ejecutar_materiales_safe(
        entrada_materiales,
        catalogo
    )

    if error_calculo:
        return _resultado_error("Error en cálculo", [error_calculo], debug)

    # =====================================================
    # 6. CONSOLIDACIÓN
    # =====================================================
    resultado.debug = debug  # 🔥 útil para Streamlit

    return resultado


# =========================================================
# VALIDACIÓN
# =========================================================
def _validar_entrada(entrada: EntradaProyecto) -> list[str]:

    errores = []

    if entrada is None:
        errores.append("EntradaProyecto es None")
        return errores

    if entrada.df_estructuras is None or entrada.df_estructuras.empty:
        errores.append("No hay estructuras")

    if not entrada.ruta_materiales:
        errores.append("Ruta de materiales no definida")

    return errores


# =========================================================
# NORMALIZACIÓN OPCIONALES
# =========================================================
def _normalizar_opcionales(entrada: EntradaProyecto):

    df_cables = entrada.df_cables
    if df_cables is not None and not hasattr(df_cables, "empty"):
        df_cables = None

    df_materiales_extra = entrada.df_materiales_extra
    if df_materiales_extra is not None and not hasattr(df_materiales_extra, "empty"):
        df_materiales_extra = None

    return df_cables, df_materiales_extra


# =========================================================
# BASE DE DATOS
# =========================================================
def _cargar_base():

    try:
        base = cargar_base_datos()
        catalogo = obtener_catalogo_materiales(base)
        return base, catalogo, None
    except Exception as e:
        return None, None, str(e)


# =========================================================
# BUILDER MATERIALS
# =========================================================
def _construir_entrada_materiales(
    entrada_proyecto: EntradaProyecto,
    base,
    df_cables,
    df_materiales_extra
):

    try:

        tension = getattr(entrada_proyecto, "tension", None)
        if not tension:
            tension = 34.5  # ⚡ default robusto

        entrada = EntradaMateriales(
            estructuras_df=entrada_proyecto.df_estructuras,
            tension=tension,
            hojas_base=base,
            df_cables=df_cables,
            df_materiales_extra=df_materiales_extra,
        )

        return entrada, None

    except Exception as e:
        return None, str(e)


# =========================================================
# EJECUCIÓN SEGURA
# =========================================================
def _ejecutar_materiales_safe(entrada, catalogo):

    try:
        resultado = ejecutar_materiales(
            entrada,
            catalogo=catalogo
        )
        return resultado, None

    except Exception as e:
        return None, str(e)


# =========================================================
# RESULTADO ERROR
# =========================================================
def _resultado_error(titulo, errores, debug):

    return ResultadoMateriales(
        False,
        _df_vacio(),
        [f"{titulo}: {e}" for e in errores],
        [],
        debug=debug
    )


# =========================================================
# DF VACÍO
# =========================================================
def _df_vacio():
    return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
