from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import pandas as pd

@dataclass
class EntradaProyecto:

    # BASE OBLIGATORIA
    df_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)
    ruta_materiales: str = ""

    # CONFIGURACIÓN DEL PROYECTO
    tension: Optional[float] = None
    datos_proyecto: Dict[str, Any] = field(default_factory=dict)

    # NECESARIOS PARA CÁLCULOS
    calibre_mt: str = ""
    tabla_conectores_mt: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_cables: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_materiales_extra: pd.DataFrame = field(default_factory=pd.DataFrame)

    # COSTOS
    df_precios_materiales: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_costos_estructuras: pd.DataFrame = field(default_factory=pd.DataFrame)

    # VALIDACIÓN FUERTE
    def validar(self):
        if self.df_estructuras.empty:
            raise ValueError("df_estructuras vacío")
        if not self.ruta_materiales:
            raise ValueError("ruta_materiales requerida")
        return True
