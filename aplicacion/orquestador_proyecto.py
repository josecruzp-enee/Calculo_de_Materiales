# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py

from __future__ import annotations

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

# =========================
# MODELO DE SALIDA
# =========================
from materiales.modelos.salida import ResultadoMateriales


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada_proyecto: EntradaProyecto) -> ResultadoMateriales:
    """
    Orquestador limpio del sistema completo.

    Flujo:
    EntradaProyecto → Materiales → ResultadoMateriales
    """

    # =====================================================
    # 1. VALIDACIÓN
    # =====================================================
    if entrada_proyecto is None:
        return ResultadoMateriales(False, _df_vacio(), ["EntradaProyecto es None"], [])

    if entrada_proyecto.df_estructuras is None or entrada_proyecto.df_estructuras.empty:
        return ResultadoMateriales(False, _df_vacio(), ["No hay estructuras"], [])

    if not entrada_proyecto.ruta_materiales:
        return ResultadoMateriales(False, _df_vacio(), ["Ruta de materiales no definida"], [])

    # =====================================================
    # 2. NORMALIZAR OPCIONALES
    # =====================================================
    df_cables = entrada_proyecto.df_cables
    if df_cables is not None and not hasattr(df_cables, "empty"):
        df_cables = None

    df_materiales_extra = entrada_proyecto.df_materiales_extra
    if df_materiales_extra is not None and not hasattr(df_materiales_extra, "empty"):
        df_materiales_extra = None

    # =====================================================
    # 3. BASE DE DATOS
    # =====================================================
    try:
        base = cargar_base_datos()
        catalogo = obtener_catalogo_materiales(base)
    except Exception as e:
        return ResultadoMateriales(
            False,
            _df_vacio(),
            [f"Error cargando base de datos: {e}"],
            []
        )

    # =====================================================
    # 4. EJECUCIÓN DIRECTA (SIN NORMALIZAR OTRA VEZ)
    # =====================================================
    try:
        resultado = ejecutar_materiales(
            entrada_proyecto,   # 🔥 usamos directo
            catalogo=catalogo
        )
    except Exception as e:
        return ResultadoMateriales(
            False,
            _df_vacio(),
            [f"Error en cálculo: {e}"],
            []
        )

    return resultado

# =========================================================
# HELPERS
# =========================================================
def _df_vacio():
    import pandas as pd
    return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
