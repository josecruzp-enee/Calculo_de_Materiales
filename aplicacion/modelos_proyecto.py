from dataclasses import dataclass
import pandas as pd

@dataclass
class EntradaProyecto:
    df_estructuras: pd.DataFrame
    df_cables: pd.DataFrame | None = None
    df_materiales_extra: pd.DataFrame | None = None
    ruta_materiales: str | None = None

    # 🔥 AGREGA ESTO
    tension: float | None = None
