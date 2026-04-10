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

    # 🔥 ALINEADO AL ORQUESTADOR REAL
    df_materiales_costos: Optional[pd.DataFrame] = None
    df_costos_estructura: Optional[pd.DataFrame] = None

    total_materiales: float = 0.0
    total_estructura: float = 0.0
    total_global: float = 0.0

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
    df_costos_estructura: Optional[pd.DataFrame] = None
    df_precios_estructura: Optional[pd.DataFrame] = None
    debug: Dict[str, Any] = field(default_factory=dict)


