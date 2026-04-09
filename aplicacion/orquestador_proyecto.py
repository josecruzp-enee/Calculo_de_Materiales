# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any
import pandas as pd
from pathlib import Path

# =========================================================
# CONTRATO
# =========================================================
from aplicacion.modelos_proyecto import EntradaProyecto

# =========================================================
# DOMINIOS
# =========================================================
from materiales.modelos.entrada import EntradaMateriales
from materiales.orquestador_materiales import ejecutar_materiales

from entradas.base_datos import cargar_base_datos


# =========================================================
# VALIDACIONES INTERNAS
# =========================================================
def _validar_df_estructuras(df: pd.DataFrame):
    if df is None or df.empty:
        raise ValueError("df_estructuras está vacío")

    cols = {c.strip().lower() for c in df.columns}

    if not {"estructura", "cantidad"} & cols:
        raise ValueError(
            f"df_estructuras no tiene columnas válidas: {df.columns}"
        )


def _validar_base_datos(base_datos: Dict[str, Any]):
    if not base_datos:
        raise ValueError("base_datos vacío")

    if not isinstance(base_datos, dict):
        raise TypeError("base_datos debe ser dict")

    if not any(isinstance(v, pd.DataFrame) for v in base_datos.values()):
        raise ValueError("base_datos no contiene hojas válidas")


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
def ejecutar_proyecto(entrada: EntradaProyecto) -> Dict[str, Any]:
    """
    Orquestador principal del proyecto.

    Responsabilidad:
        - Validar entrada
        - Cargar base de datos
        - Ejecutar cálculo de materiales
        - Retornar resultados estructurados

    NO hace:
        - Costos
        - Cálculos económicos
        - Lógica cruzada
    """

    # =====================================================
    # VALIDACIÓN FUERTE
    # =====================================================
    if not isinstance(entrada, EntradaProyecto):
        raise TypeError("entrada debe ser EntradaProyecto")

    entrada.validar()

    if entrada.tension is None:
        raise ValueError("tension es requerida")

    if not entrada.ruta_materiales:
        raise ValueError("ruta_materiales es requerida")

    _validar_df_estructuras(entrada.df_estructuras)

    # =====================================================
    # BASE DE DATOS
    # =====================================================
    ruta = Path(entrada.ruta_materiales)

    if not ruta.exists():
        raise FileNotFoundError(f"No existe archivo de materiales: {ruta}")

    try:
        base_datos = cargar_base_datos(ruta)
    except Exception as e:
        raise RuntimeError("Error cargando base de datos") from e

    _validar_base_datos(base_datos)

    # =====================================================
    # MATERIALES
    # =====================================================
    entrada_mat = EntradaMateriales(
        estructuras_df=entrada.df_estructuras,
        tension=entrada.tension,
        base_datos=base_datos,
        datos_proyecto=entrada.datos_proyecto,
        df_cables=entrada.df_cables,
        df_materiales_extra=entrada.df_materiales_extra,
        calibre_mt=entrada.calibre_mt,
        tabla_conectores_mt=entrada.tabla_conectores_mt,
    )

    salida_materiales = ejecutar_materiales(entrada_mat)

    # =====================================================
    # VALIDACIÓN RESULTADO
    # =====================================================
    if salida_materiales is None:
        raise RuntimeError("salida_materiales es None")

    if not salida_materiales.ok:
        raise RuntimeError(
            f"Error en materiales: {salida_materiales.errores}"
        )

    if (
        salida_materiales.df_materiales is None
        or salida_materiales.df_materiales.empty
    ):
        raise ValueError("df_materiales vacío")

    # =====================================================
    # OUTPUT NORMALIZADO
    # =====================================================
    resultado = {
        "ok": True,

        # 🔹 materiales
        "materiales": salida_materiales,
        "df_materiales": salida_materiales.df_materiales,
        "df_materiales_por_punto": salida_materiales.df_materiales_por_punto,

        # 🔹 estructuras
        "df_estructuras": salida_materiales.df_estructuras,
        "df_estructuras_por_punto": salida_materiales.df_estructuras_por_punto,
        "descripcion_estructuras": getattr(
            salida_materiales, "descripcion_estructuras", None
        ),

        # 🔹 metadata
        "nombre_proyecto": (
            entrada.datos_proyecto.get("nombre")
            if entrada.datos_proyecto else "Proyecto"
        ),

        # 🔹 debug
        "debug": getattr(salida_materiales, "debug", {}),
    }

    return resultado
