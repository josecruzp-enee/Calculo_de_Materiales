# =========================
# Match de MATERIALES -> CABLES (para sumar longitudes)
# =========================
import re
from typing import Optional
import pandas as pd

_RE_ESP = re.compile(r"\s+")
_RE_QUOTES = re.compile(r"[“”]")
_RE_IGNORAR = re.compile(r"(?i)\bCONTROL\b|\bFOTOEL[ÉE]CTRICO\b")  # controles alumbrado

def _norm_txt(s: str) -> str:
    s = str(s or "")
    s = _RE_QUOTES.sub('"', s)
    s = s.replace("–", "-")
    s = s.upper().strip()
    s = _RE_ESP.sub(" ", s)
    return s

def es_material_ignorable(nombre_material: str) -> bool:
    return bool(_RE_IGNORAR.search(_norm_txt(nombre_material)))

def _float_safe(x, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d

def _col_material(df: pd.DataFrame) -> Optional[str]:
    for c in ("Material", "MATERIAL", "material", "Descripcion", "DESCRIPCION", "Descripción"):
        if c in df.columns:
            return c
    return None

def _col_unidad(df: pd.DataFrame) -> Optional[str]:
    for c in ("Unidad", "UNIDAD", "unidad"):
        if c in df.columns:
            return c
    return None

def _col_cantidad(df: pd.DataFrame) -> Optional[str]:
    for c in ("Cantidad", "CANTIDAD", "cantidad"):
        if c in df.columns:
            return c
    return None

def unidad_a_metros(unidad: str, cantidad: float) -> float:
    """
    Convierte:
      - Pie, Pies, FT -> metros
      - m -> metros
    Si es C/U, LB, etc -> 0 (no es cable por longitud)
    """
    u = _norm_txt(unidad)
    x = _float_safe(cantidad, 0.0)

    if x <= 0:
        return 0.0

    if u in ("M", "METRO", "METROS"):
        return x

    if u in ("PIE", "PIES", "FT", "FEET"):
        return x * 0.3048

    # No longitud
    return 0.0

def match_material_a_cable_oficial(nombre_material: str) -> Optional[Tuple[str, str]]:
    """
    Devuelve (TIPO, DESCRIPCION_OFICIAL) o None.
    TIPOS esperados: MT, BT, N, HP, RETENIDA, TIERRA, TRIPLEX
    """
    s = _norm_txt(nombre_material)
    if es_material_ignorable(s):
        return None

    # --- RETENIDA (acerado) ---
    if "CABLE ACERADO" in s:
        if "1/4" in s:
            return ("RETENIDA", CABLES_OFICIALES[("RETENIDA", "1/4")])
        if "5/16" in s:
            return ("RETENIDA", CABLES_OFICIALES[("RETENIDA", "5/16")])
        if "3/8" in s:
            return ("RETENIDA", CABLES_OFICIALES[("RETENIDA", "3/8")])

    # --- BT / HP WP ---
    if "FORRADO" in s and "WP" in s:
        if "266.8" in s and "MCM" in s:
            return ("BT", CABLES_OFICIALES[("BT", "266.8 MCM")])
        if "# 2" in s and "AWG" in s:
            return ("BT", CABLES_OFICIALES[("BT", "2 WP")])
        if "# 1/0" in s and "AWG" in s:
            return ("BT", CABLES_OFICIALES[("BT", "1/0 WP")])
        if "# 3/0" in s and "AWG" in s:
            return ("BT", CABLES_OFICIALES[("BT", "3/0 WP")])

    # --- Neutro (ACSR #2) ---
    if "ACSR" in s and "# 2" in s and "AWG" in s and "SPARROW" in s:
        return ("N", CABLES_OFICIALES[("N", "2 ACSR")])

    # --- MT ACSR ---
    if "ACSR" in s:
        if "# 1/0" in s and "AWG" in s:
            return ("MT", CABLES_OFICIALES[("MT", "1/0 ACSR")])
        if "# 2/0" in s and "AWG" in s:
            return ("MT", CABLES_OFICIALES[("MT", "2/0 ACSR")])
        if "# 3/0" in s and "AWG" in s:
            return ("MT", CABLES_OFICIALES[("MT", "3/0 ACSR")])
        if "# 4/0" in s and "AWG" in s:
            return ("MT", CABLES_OFICIALES[("MT", "4/0 ACSR")])
        if "266.8" in s and "MCM" in s:
            return ("MT", CABLES_OFICIALES[("MT", "266.8 MCM")])
        if "477" in s and "MCM" in s:
            return ("MT", CABLES_OFICIALES[("MT", "477 MCM")])
        if "556" in s and "MCM" in s:
            return ("MT", CABLES_OFICIALES[("MT", "556 MCM ACSR")])

    if "AAC" in s and "556" in s and "MCM" in s:
        return ("MT", CABLES_OFICIALES[("MT", "556 MCM AAC")])

    # --- TIERRA (cobre/copperweld) ---
    if "COPPERWELD" in s and "# 6" in s and "AWG" in s:
        return ("TIERRA", "Cable Bimetálico Copperweld # 6 AWG, 40%")
    if "CABLE DE COBRE" in s and "# 6" in s:
        return ("TIERRA", "Cable de Cobre # 6 Sólido")
    if "COBRE FORRADO" in s:
        if "# 14" in s and "AWG" in s:
            return ("TIERRA", "Cable de Cobre Forrado # 14 AWG")
        if "# 1/0" in s and "AWG" in s:
            return ("TIERRA", "Cable de Cobre Forrado # 1/0 AWG")
        if "# 3/0" in s and "AWG" in s:
            return ("TIERRA", "Cable de Cobre Forrado # 3/0 AWG")
        if "# 4/0" in s and "AWG" in s:
            return ("TIERRA", "Cable de Cobre Forrado # 4/0 AWG")

    # --- TRIPLEX ---
    if "TRIPLEX" in s:
        if "# 1/0" in s and "AWG" in s:
            return ("TRIPLEX", "Cable Triplex de Aluminio # 1/0 AWG")
        if "# 2" in s and "AWG" in s:
            return ("TRIPLEX", "Cable Triplex de Aluminio # 2 AWG")
        if "# 6" in s and "AWG" in s:
            return ("TRIPLEX", "Cable Triplex de Aluminio # 6 AWG")

    return None

def cables_desde_resumen_materiales(df_resumen: pd.DataFrame) -> pd.DataFrame:
    """
    Entrada: df con columnas tipo: Material | Unidad | Cantidad
    Salida: df con columnas tipo (como tu tabla PDF):
      Tipo | Configuración | Calibre | Longitud (m) | Total Cable (m)

    Nota:
    - Aquí Configuración se deja como "—" porque el resumen de materiales no trae 1F/2F/3F.
    - Total Cable (m) == Longitud (m) (porque no sabemos multiplicidad de fases)
    """
    if df_resumen is None or df_resumen.empty:
        return pd.DataFrame(columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])

    cm = _col_material(df_resumen)
    cu = _col_unidad(df_resumen)
    cc = _col_cantidad(df_resumen)
    if not cm or not cu or not cc:
        return pd.DataFrame(columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])

    rows = []
    for _, r in df_resumen.iterrows():
        mat = str(r.get(cm, "")).strip()
        if not mat or es_material_ignorable(mat):
            continue

        hit = match_material_a_cable_oficial(mat)
        if not hit:
            continue

        tipo, calibre_oficial = hit
        unidad = str(r.get(cu, "")).strip()
        cant = _float_safe(r.get(cc, 0), 0.0)

        metros = unidad_a_metros(unidad, cant)
        if metros <= 0:
            continue

        rows.append({
            "Tipo": tipo,
            "Configuración": "—",
            "Calibre": calibre_oficial,
            "Longitud (m)": round(metros, 2),
            "Total Cable (m)": round(metros, 2),
        })

    if not rows:
        return pd.DataFrame(columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])

    df = pd.DataFrame(rows)
    df = df.groupby(["Tipo", "Configuración", "Calibre"], as_index=False)[["Longitud (m)", "Total Cable (m)"]].sum()
    return df.sort_values(["Tipo", "Calibre"]).reset_index(drop=True)
