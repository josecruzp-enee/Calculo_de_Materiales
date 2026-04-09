# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
import pandas as pd
from typing import Optional, Literal, Dict, Any, List


# =========================================================
# TIPOS BASE
# =========================================================
ModoEntrada = Literal["excel", "tabla", "pdf", "dxf", "manual"]


# =========================================================
# 🔷 CONTRATO INTERFAZ → ENTRADAS
# =========================================================
@dataclass
class SalidaInterfaz:
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    tipo_entrada: ModoEntrada = "manual"
    data_entrada: Any = None

    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO ENTRADAS → MATERIALES
# =========================================================
@dataclass
class SalidaEntradas:
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    df_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)

    base_datos: Dict[str, pd.DataFrame] = field(default_factory=dict)

    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO COSTOS
# =========================================================
@dataclass
class SalidaCostos:
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    df_costos_materiales: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_costos_mano_obra: pd.DataFrame = field(default_factory=pd.DataFrame)

    total_proyecto: float = 0.0

    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO FINAL DEL SISTEMA
# =========================================================
@dataclass(slots=True)
class ResultadoProyecto:
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    materiales: Optional[Any] = None
    costos: Optional[Any] = None
    reportes: Optional[Dict[str, Any]] = None

    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO MATERIALES (IMPORTANTE: NIVEL MÓDULO)
# =========================================================
@dataclass
class SalidaMateriales:
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    df_materiales: Optional[pd.DataFrame] = None
    df_resumen: Optional[pd.DataFrame] = None
