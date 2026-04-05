# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py

from __future__ import annotations
import pandas as pd

# =========================
# MODELO
# =========================
from aplicacion.modelos_proyecto import EntradaProyecto

# =========================
# DOMINIO
# =========================
from entradas.orquestador_entradas import cargar_entrada
from materiales.orquestador_materiales import ejecutar_materiales

# =========================
# BASE
# =========================
from entradas.base_datos import cargar_base_datos, obtener_catalogo_materiales


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada_proyecto: EntradaProyecto):
    """
    Orquestador limpio SIN dependencia de UI.
    """

    errores: list[str] = []
    warnings: list[str] = []

    # =====================================================
    # VALIDACIONES BASE
    # =====================================================
    if entrada_proyecto.df_estructuras is None or entrada_proyecto.df_estructuras.empty:
        return None, ["No hay estructuras para procesar"], []

    if not entrada_proyecto.ruta_materiales:
        return None, ["No hay ruta de materiales definida"], []

    # =====================================================
    # NORMALIZAR ENTRADAS OPCIONALES
    # =====================================================
    df_cables = entrada_proyecto.df_cables
    if df_cables is not None and not isinstance(df_cables, pd.DataFrame):
        df_cables = None
        warnings.append("Cables ignorados (formato inválido)")

    df_materiales_extra = entrada_proyecto.df_materiales_extra
    if df_materiales_extra is not None and not isinstance(df_materiales_extra, pd.DataFrame):
        df_materiales_extra = None
        warnings.append("Materiales extra ignorados (formato inválido)")

    # =====================================================
    # 1. CONSTRUIR ENTRADA DE DOMINIO
    # =====================================================
    try:
        entrada = cargar_entrada(
            datos_fuente={
                "df_estructuras": entrada_proyecto.df_estructuras,
                "df_cables": df_cables,
                "df_materiales_extra": df_materiales_extra,
            },
            ruta_materiales=entrada_proyecto.ruta_materiales,
        )
    except Exception as e:
        return None, [f"Error construyendo entrada: {e}"], []

    # =====================================================
    # 2. BASE DE DATOS
    # =====================================================
    try:
        base = cargar_base_datos()
        catalogo = obtener_catalogo_materiales(base)

        if catalogo is None or catalogo.empty:
            warnings.append("Catálogo de materiales vacío")

    except Exception as e:
        return None, [f"Error cargando base de datos: {e}"], []

    # =====================================================
    # 3. MOTOR DE CÁLCULO
    # =====================================================
    try:
        resultado = ejecutar_materiales(
            entrada,
            catalogo=catalogo
        )
    except Exception as e:
        return None, [f"Error ejecutando cálculo: {e}"], []

    # =====================================================
    # 4. VALIDAR RESULTADO
    # =====================================================
    if resultado is None:
        return None, ["Resultado vacío"], []

    if not resultado.ok:
        return resultado, resultado.errores, resultado.warnings

    return resultado, errores, warnings
