from typing import Optional, Dict, Any

@dataclass
class EntradaProyecto:
    df_estructuras: pd.DataFrame
    df_cables: pd.DataFrame | None = None
    df_materiales_extra: pd.DataFrame | None = None
    ruta_materiales: str | None = None
    tension: float | None = None

    # 👇 ESTE ES EL FIX
    datos_proyecto: Optional[Dict[str, Any]] = None
