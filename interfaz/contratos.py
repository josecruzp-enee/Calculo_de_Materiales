# interfaz/contratos.py

from dataclasses import dataclass, field
import pandas as pd
from typing import Optional, Literal, Dict, Any, List


ModoEntrada = Literal["excel", "tabla", "pdf", "dxf", "manual"]


@dataclass
class SalidaInterfaz:
    """
    🔷 CONTRATO OFICIAL DE INTERFAZ → ENTRADAS
    """

    # =========================
    # CONTROL
    # =========================
    ok: bool = False
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # =========================
    # TIPO DE ENTRADA
    # =========================
    tipo_entrada: ModoEntrada = "manual"

    # =========================
    # DATA CRUDA (SIN PROCESAR)
    # =========================
    data_entrada: Any = None  # archivo, dataframe, texto, etc.

    # =========================
    # OPCIONALES
    # =========================
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    df_cables: Optional[pd.DataFrame] = None
    df_materiales_extra: Optional[pd.DataFrame] = None

    # =========================
    # DEBUG (NO CRÍTICO)
    # =========================
    debug: Dict[str, Any] = field(default_factory=dict)
