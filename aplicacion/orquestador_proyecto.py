# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd

# =========================================================
# DOMINIO: ENTRADA DEL PROYECTO
# =========================================================
@dataclass
class EntradaProyecto:

    # =========================
    # BASE
    # =========================
    df_estructuras: pd.DataFrame

    # =========================
    # CONFIG PROYECTO
    # =========================
    ruta_materiales: Optional[str] = None
    tension: Optional[float] = None
    datos_proyecto: Optional[Dict[str, Any]] = None

    # =========================
    # NECESARIOS
    # =========================
    calibre_mt: Optional[str] = None
    tabla_conectores_mt: Optional[pd.DataFrame] = None

    # =========================
    # COSTOS
    # =========================
    df_precios_materiales: Optional[pd.DataFrame] = None
    df_costos_estructuras: Optional[pd.DataFrame] = None

    # =========================
    # VALIDACIÓN FUERTE
    # =========================
    def validar(self):
        if self.df_estructuras is None or self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")
        if not self.ruta_materiales:
            raise ValueError("ruta_materiales requerida")
        # calibre_mt opcional, ya no se valida aquí
        return True


# =========================================================
# DOMINIO: ENTRADA DE MATERIALES
# =========================================================
@dataclass(slots=True)
class EntradaMateriales:
    estructuras_df: pd.DataFrame
    tension: float

    datos_proyecto: Optional[Dict[str, Any]] = None
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None
    calibre_mt: Optional[str] = None
    tabla_conectores_mt: Optional[Dict[str, Any]] = None

    # ======================================================
    # VALIDACIÓN AUTOMÁTICA
    # ======================================================
    def __post_init__(self):
        if not isinstance(self.estructuras_df, pd.DataFrame):
            raise TypeError("estructuras_df debe ser DataFrame")
        if self.estructuras_df.empty:
            raise ValueError("estructuras_df está vacío")
        cols = {c.strip().upper(): c for c in self.estructuras_df.columns}
        col_est = cols.get("ESTRUCTURAS") or cols.get("ESTRUCTURA")
        if not col_est:
            raise ValueError(f"No existe columna de estructuras. Columnas: {list(self.estructuras_df.columns)}")
        self.estructuras_df = self.estructuras_df.rename(columns={col_est: "Estructura"})
        if "Estructura" not in self.estructuras_df.columns:
            raise ValueError("estructuras_df debe contener columna 'Estructura'")

        try:
            self.tension = float(self.tension)
        except Exception:
            raise ValueError(f"Tensión inválida: {self.tension}")
        if self.tension <= 0:
            raise ValueError("Tensión debe ser mayor que 0")

        if self.datos_proyecto is not None and not isinstance(self.datos_proyecto, dict):
            raise TypeError("datos_proyecto debe ser dict")
        if self.df_cables is not None and not isinstance(self.df_cables, pd.DataFrame):
            raise TypeError("df_cables debe ser DataFrame")
        if self.df_materiales_extra is not None and not isinstance(self.df_materiales_extra, pd.DataFrame):
            raise TypeError("df_materiales_extra debe ser DataFrame")
        if self.calibre_mt is not None:
            self.calibre_mt = str(self.calibre_mt).strip().upper()
        if self.tabla_conectores_mt is not None and not isinstance(self.tabla_conectores_mt, dict):
            raise TypeError("tabla_conectores_mt debe ser dict")


# =========================================================
# ORQUESTADOR PRINCIPAL
# =========================================================
from materiales.orquestador_materiales import ejecutar_materiales
from costos_precios.orquestador_costos import ejecutar_costos
from costos_precios.costos_por_estructura import calcular_costos_por_estructura


def ejecutar_proyecto(entrada: EntradaProyecto) -> Dict[str, Any]:

    # VALIDACIÓN FUERTE
    if not isinstance(entrada, EntradaProyecto):
        raise TypeError("entrada debe ser EntradaProyecto")
    entrada.validar()

    # =========================================
    # 1. MATERIALES
    # =========================================
    entrada_mat = EntradaMateriales(
        estructuras_df=entrada.df_estructuras,
        tension=entrada.tension or 0,
        datos_proyecto={"tension": entrada.tension, "calibre_mt": entrada.calibre_mt},
        df_cables=getattr(entrada, "df_cables", None),
        df_materiales_extra=getattr(entrada, "df_materiales_extra", None),
        calibre_mt=getattr(entrada, "calibre_mt", None),
        tabla_conectores_mt=getattr(entrada, "tabla_conectores_mt", None),
    )

    salida_materiales = ejecutar_materiales(entrada_mat)

    if (
        salida_materiales is None
        or salida_materiales.df_materiales is None
        or salida_materiales.df_materiales.empty
    ):
        raise ValueError("Error en cálculo de materiales")

    # =========================================
    # 2. GENERAR COSTOS DE ESTRUCTURAS AUTOMÁTICO
    # =========================================
    if entrada.df_costos_estructuras is None:
        conteo = dict(zip(
            entrada.df_estructuras["codigodeestructura"],
            entrada.df_estructuras["cantidad"]
        ))
        hojas_base = getattr(entrada, "hojas_base", {})

        entrada.df_costos_estructuras = calcular_costos_por_estructura(
            hojas_base=hojas_base,
            conteo=conteo,
            tension_ll=entrada.tension or 0,
            calibre_mt=entrada.calibre_mt or "",
            tabla_conectores_mt=entrada.tabla_conectores_mt or {},
            df_precios_materiales=entrada.df_precios_materiales
        )

    # =========================================
    # 3. COSTOS
    # =========================================
    try:
        salida_costos = ejecutar_costos({
            "df_resumen": salida_materiales.df_materiales,
            "df_estructuras_por_punto": getattr(
                salida_materiales, "df_estructuras_por_punto", None
            ),
            "df_costos_estructuras": entrada.df_costos_estructuras,
            "df_precios_materiales": entrada.df_precios_materiales,
        })
    except Exception as e:
        raise ValueError(f"Error en cálculo de costos: {str(e)}")

    # =========================================
    # 4. OUTPUT LIMPIO
    # =========================================
    return {
        "materiales": salida_materiales,
        "costos": salida_costos,
    }
