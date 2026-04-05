# -*- coding: utf-8 -*-
"""
leer_dxf.py

Lectura de estructuras desde DXF (INPUT CRUDO CONTROLADO).
NO contiene lógica de negocio.
"""

from __future__ import annotations
import pandas as pd
import re


# =========================================================
# HELPERS
# =========================================================
def _limpiar_texto_basico(s: str) -> str:
    if s is None:
        return ""

    s = str(s)

    # limpiar saltos de línea DXF
    s = s.replace("\\P", " ")
    s = s.replace("\n", " ").replace("\r", " ")

    # normalizar espacios
    s = re.sub(r"\s+", " ", s).strip()

    return s


def _es_texto_util(s: str) -> bool:
    """
    Filtro mínimo para eliminar basura típica DXF.
    NO elimina posibles estructuras válidas.
    """
    if not s:
        return False

    s = s.strip()

    # basura común
    basura = {"", "-", ".", "...", "0", "N/A", "NONE"}
    if s.upper() in basura:
        return False

    # evitar coordenadas puras tipo "123.45"
    if re.match(r"^\d+(\.\d+)?$", s):
        return False

    return True


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def leer_dxf(archivo_dxf) -> pd.DataFrame:
    """
    Entrada:
        - ruta .dxf
        - archivo tipo Streamlit

    Salida:
        DataFrame crudo con:
            Texto
            Layer
            X
            Y
    """

    try:
        import ezdxf
    except ImportError:
        raise ImportError("Debes instalar ezdxf: pip install ezdxf")

    # -------------------------
    # CARGAR DXF
    # -------------------------
    try:
        if hasattr(archivo_dxf, "read"):
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(archivo_dxf.read())
                ruta = tmp.name

            doc = ezdxf.readfile(ruta)

        else:
            doc = ezdxf.readfile(archivo_dxf)

    except Exception as e:
        raise ValueError(f"No se pudo leer el DXF: {e}")

    msp = doc.modelspace()

    # -------------------------
    # EXTRAER TEXTOS
    # -------------------------
    filas = []

    for e in msp:

        if e.dxftype() not in ["TEXT", "MTEXT"]:
            continue

        try:
            # contenido
            if e.dxftype() == "TEXT":
                contenido = e.dxf.text
                punto = e.dxf.insert
            else:
                contenido = e.text
                punto = e.dxf.insert

            texto = _limpiar_texto_basico(contenido)

            if not _es_texto_util(texto):
                continue

            # posición
            x = float(punto[0]) if punto else None
            y = float(punto[1]) if punto else None

            layer = e.dxf.layer if hasattr(e.dxf, "layer") else ""

            filas.append({
                "Texto": texto,
                "Layer": layer,
                "X": x,
                "Y": y
            })

        except Exception:
            continue

    # -------------------------
    # DATAFRAME FINAL
    # -------------------------
    if not filas:
        return pd.DataFrame(columns=["Texto", "Layer", "X", "Y"])

    df = pd.DataFrame(filas)

    return df
