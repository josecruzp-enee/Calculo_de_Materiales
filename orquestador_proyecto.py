# -*- coding: utf-8 -*-
# aplicacion/orquestador_proyecto.py
# ORQUESTADOR DE APLICACIÓN — coordina todo el flujo del sistema

from __future__ import annotations

import pandas as pd

# =========================
# ORQUESTADORES DE DOMINIO
# =========================
from entradas.orquestador_entradas import cargar_entrada
from materiales.orquestador_materiales import ejecutar_materiales

# =========================
# BASE DE DATOS / CATÁLOGO
# =========================
from entradas.base_datos import cargar_base_datos, obtener_catalogo_materiales


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def ejecutar_proyecto(
    df_estructuras: pd.DataFrame,
    session_state: dict
):
    """
    Orquesta todo el flujo del proyecto:

    UI → Entradas → Materiales → Resultado

    Retorna:
        resultado, errores, warnings
    """

    errores: list[str] = []
    warnings: list[str] = []

    # =====================================================
    # VALIDACIONES BÁSICAS
    # =====================================================
    if df_estructuras is None or df_estructuras.empty:
        return None, ["No hay estructuras para procesar"], []

    # =====================================================
    # 1. MATERIALES EXTRA
    # =====================================================
    try:
        materiales_extra = pd.DataFrame(
            session_state.get("materiales_extra", [])
        )
    except Exception:
        materiales_extra = pd.DataFrame()
        warnings.append("Materiales extra ignorados (formato inválido)")

    # =====================================================
    # 2. CABLES (OPCIONAL)
    # =====================================================
    df_cables = session_state.get("cables_proyecto_df")

    if df_cables is not None and not isinstance(df_cables, pd.DataFrame):
        df_cables = None
        warnings.append("Cables ignorados (no es DataFrame)")

    # =====================================================
    # 3. RUTA DE MATERIALES
    # =====================================================
    ruta_materiales = session_state.get("ruta_datos_materiales")

    if not ruta_materiales:
        return None, ["No hay ruta de materiales definida"], []

    # =====================================================
    # 4. ARMAR ENTRADA (DOMINIO ENTRADAS)
    # =====================================================
    try:
        entrada = cargar_entrada(
            datos_fuente={
                "df_estructuras": df_estructuras,
                "df_cables": df_cables,
                "df_materiales_extra": materiales_extra,
            },
            ruta_materiales=ruta_materiales,
        )
    except Exception as e:
        return None, [f"Error construyendo entrada: {e}"], []

    # =====================================================
    # 5. CARGAR BASE Y CATÁLOGO
    # =====================================================
    try:
        base = cargar_base_datos()
        catalogo = obtener_catalogo_materiales(base)

        if catalogo is None or catalogo.empty:
            warnings.append("Catálogo de materiales vacío")

    except Exception as e:
        return None, [f"Error cargando base de datos: {e}"], []

    # =====================================================
    # 6. EJECUTAR MOTOR (DOMINIO MATERIALES)
    # =====================================================
    try:
        resultado = ejecutar_materiales(
            entrada,
            catalogo=catalogo
        )
    except Exception as e:
        return None, [f"Error ejecutando cálculo: {e}"], []

    # =====================================================
    # 7. VALIDAR RESULTADO
    # =====================================================
    if resultado is None:
        return None, ["Resultado vacío"], []

    if not resultado.ok:
        return resultado, resultado.errores, resultado.warnings

    # =====================================================
    # 8. POST-PROCESO (SI NECESARIO)
    # =====================================================
    # Aquí podrías agregar:
    # - ajustes finales
    # - validaciones adicionales
    # - enriquecimiento de datos

    return resultado, errores, warnings
