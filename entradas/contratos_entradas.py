# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
import pandas as pd


# =========================================================
# 🔷 DTO ENTRADA INTERNA (PIPELINE)
# =========================================================
@dataclass
class EntradaPipeline:
    """
    Entrada limpia al pipeline del dominio entradas
    """

    tipo: str
    data: Any

    tension: float

    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    validar_catalogo: bool = True


# =========================================================
# 🔷 RESULTADO INTERNO DEL PIPELINE
# =========================================================
@dataclass
class ResultadoPipeline:
    """
    Resultado interno del dominio entradas
    """

    ok: bool = False

    estructuras_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    debug: Dict[str, Any] = field(default_factory=dict)
