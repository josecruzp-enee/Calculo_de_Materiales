# -*- coding: utf-8 -*-
# interfaz/contratos.py

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
    """
    Interfaz entrega esto al dominio de entradas
    """

    # CONTROL
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # ENTRADA CRUDA
    tipo_entrada: ModoEntrada = "manual"
    data_entrada: Any = None

    # CONTEXTO
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    # OPCIONALES
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    # DEBUG
    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO ENTRADAS → MATERIALES
# =========================================================
@dataclass
class SalidaEntradas:
    """
    Entradas entrega esto a materiales
    """

    # CONTROL
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # DATA LIMPIA
    df_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)

    # CONTEXTO
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    # PASSTHROUGH
    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    # DEBUG
    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO MATERIALES → EXPORTADORES
# =========================================================
@dataclass
class SalidaMateriales:

    # CONTROL
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # RESULTADOS EXISTENTES (NO TOCAR)
    df_materiales: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_materiales_por_punto: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 🔥 NUEVO (SIN ROMPER)
    df_estructuras: Optional[pd.DataFrame] = None
    df_estructuras_por_punto: Optional[pd.DataFrame] = None
    descripcion_estructuras: Optional[Dict[str, Any]] = None

    # CONTEXTO
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    # DEBUG
    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO COSTOS → EXPORTADORES
# =========================================================
@dataclass
class SalidaCostos:
    """
    Costos / precios
    """

    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    df_costos_materiales: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_costos_mano_obra: pd.DataFrame = field(default_factory=pd.DataFrame)

    total_proyecto: float = 0.0

    debug: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 🔷 CONTRATO FINAL (PARA EXPORTACIÓN)
# =========================================================
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass(slots=True)
class ResultadoProyecto:
    """
    Salida única del sistema (orquestador_proyecto)

    ✔ Contrato fuerte
    ✔ Usado por UI
    ✔ No contiene lógica
    """

    # CONTROL
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # RESULTADOS DE DOMINIO
    materiales: Optional[Any] = None
    costos: Optional[Any] = None
    reportes: Optional[Dict[str, Any]] = None

    # DEBUG
    debug: Dict[str, Any] = field(default_factory=dict)

    debug: Dict[str, Any] = field(default_factory=dict)
