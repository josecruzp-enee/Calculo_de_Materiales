# interfaz/contratos.py

from dataclasses import dataclass
import pandas as pd
from typing import Optional, Literal, Dict, Any


ModoEntrada = Literal["excel", "tabla", "pdf", "dxf", "manual"]


@dataclass
class SalidaInterfaz:
    """
    🔷 CONTRATO OFICIAL DE INTERFAZ → ENTRADAS
    """

    # =========================
    # CONTROL
    # =========================
    ok: bool
    errores: list[str]
    warnings: list[str]

    # =========================
    # TIPO DE ENTRADA
    # =========================
    tipo_entrada: ModoEntrada

    # =========================
    # DATA CRUDA (SIN PROCESAR)
    # =========================
    data_entrada: Any  # archivo, dataframe, texto, etc.

    # =========================
    # OPCIONALES
    # =========================
    datos_proyecto: Dict[str, Any]

    df_cables: Optional[pd.DataFrame]
    df_materiales_extra: Optional[pd.DataFrame]

    # =========================
    # DEBUG (NO CRÍTICO)
    # =========================
    debug: Dict[str, Any]
