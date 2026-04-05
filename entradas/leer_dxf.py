# -*- coding: utf-8 -*-
"""
leer_dxf.py
Lectura de estructuras desde archivo DXF (plano ENEE).

Devuelve DataFrame crudo (SIN normalizar).
"""

from __future__ import annotations
import pandas as pd


def leer_dxf(archivo_dxf) -> pd.DataFrame:
    """
    archivo_dxf:
        - ruta (.dxf)
        - archivo cargado (Streamlit)

    Retorna:
        DataFrame con estructuras detectadas
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
            # archivo tipo Streamlit (bytes)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(archivo_dxf.read())
                ruta = tmp.name
            doc = ezdxf.readfile(ruta)
        else:
            # ruta directa
            doc = ezdxf.readfile(archivo_dxf)

    except Exception as e:
        raise ValueError(f"No se pudo leer el DXF: {e}")

    msp = doc.modelspace()

    # -------------------------
    # EXTRAER TEXTOS
    # -------------------------
    textos = []

    for e in msp:

        if e.dxftype() in ["TEXT", "MTEXT"]:
            try:
                if e.dxftype() == "TEXT":
                    contenido = e.dxf.text
                else:
                    contenido = e.text

                if contenido:
                    textos.append(str(contenido).strip())

            except Exception:
                continue

    # -------------------------
    # CONVERTIR A DATAFRAME
    # -------------------------
    df = pd.DataFrame({"Texto": textos})

    return df
