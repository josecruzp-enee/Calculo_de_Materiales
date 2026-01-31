# -*- coding: utf-8 -*-
"""
core/costos_materiales.py

Contrato oficial para costos.

El servicio importa:
  - cargar_precios(archivo_materiales) -> DataFrame precios (normalizado)
  - calcular_costos_desde_resumen(df_resumen, precios_o_archivo) -> DataFrame costos

Soporta Excel base con hoja:
  - 'precios' (ideal) o 'Materiales' (tu caso actual)

Columnas de entrada típicas (flexibles):
  - Materiales: "Materiales" o "DESCRIPCIÓN DE MATERIALES" (u otras con "descrip")
  - Unidad: "Unidad"
  - Precio: "Precio Unitario" o "Costo Unitario" o "Costo ..."
  - Moneda: opcional ("Moneda"). Si no existe, se asume "L".

Salida df_costos:
  Materiales, Unidad, Cantidad, Precio Unitario, Costo, Moneda, Tiene_Precio
"""

from __future__ import annotations

import pandas as pd
import unicodedata


# -------------------------
# Normalización robusta
# -------------------------
def _norm_txt(s: object) -> str:
    """
    Normaliza texto para matching robusto:
    - strip
    - quita tildes/diacríticos
    - colapsa espacios
    - upper
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip()
    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )
    t = " ".join(t.split())
    return t.upper()


# -------------------------
# Lectura robusta de precios
# -------------------------
def cargar_precios(archivo_materiales: str) -> pd.DataFrame:
    """
    Lee precios desde el Excel base (precios o Materiales) y devuelve un DF listo
    para merge por claves normalizadas.

    Retorna columnas:
      Materiales_norm, Unidad_norm, Precio Unitario, Moneda
    """
    try:
        xls = pd.ExcelFile(archivo_materiales)

        # Prioridad: hoja 'precios' (ideal), si no, 'Materiales', si no, la primera.
        if "precios" in xls.sheet_names:
            hoja = "precios"
        elif "Materiales" in xls.sheet_names:
            hoja = "Materiales"
        elif "materiales" in xls.sheet_names:
            hoja = "materiales"
        else:
            hoja = xls.sheet_names[0]

        df = pd.read_excel(archivo_materiales, sheet_name=hoja)

        # Normalizar nombres de columnas (limpiar NBSP y espacios)
        df.columns = [str(c).replace("\u00A0", " ").strip() for c in df.columns]

        # Renombres flexibles → contrato interno
        ren = {}
        for c in df.columns:
            cc = c.lower().strip()

            # Materiales
            if cc.startswith("material") or "descrip" in cc:
                ren[c] = "Materiales"

            # Unidad
            elif cc.startswith("unidad"):
                ren[c] = "Unidad"

            # Precio (tu caso: "Costo Unitario")
            elif "precio" in cc or "costo unitario" in cc or cc.startswith("costo"):
                ren[c] = "Precio Unitario"

            # Moneda (opcional)
            elif "moneda" in cc:
                ren[c] = "Moneda"

        df = df.rename(columns=ren)

        # Defaults defensivos
        if "Materiales" not in df.columns:
            df["Materiales"] = ""
        if "Unidad" not in df.columns:
            df["Unidad"] = ""
        if "Precio Unitario" not in df.columns:
            df["Precio Unitario"] = 0.0
        if "Moneda" not in df.columns:
            df["Moneda"] = "L"  # Lempira por defecto

        # Limpiar valores base
        df["Materiales"] = df["Materiales"].astype(str).str.strip()
        df["Unidad"] = df["Unidad"].astype(str).str.strip()
        df["Moneda"] = df["Moneda"].astype(str).str.strip()
        df.loc[df["Moneda"].eq(""), "Moneda"] = "L"

        # Precio numérico (ya lo dejaste numérico en Excel)
        df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce").fillna(0.0)

        # Claves normalizadas para merge robusto
        df["Materiales_norm"] = df["Materiales"].map(_norm_txt)
        df["Unidad_norm"] = df["Unidad"].map(_norm_txt)

        # Nos quedamos solo con lo necesario para merge
        out = df[["Materiales_norm", "Unidad_norm", "Precio Unitario", "Moneda"]].copy()

        # Quitar duplicados por clave (si existieran), dejando el primero
        out = out.drop_duplicates(subset=["Materiales_norm", "Unidad_norm"], keep="first")

        return out

    except Exception:
        return pd.DataFrame(columns=["Materiales_norm", "Unidad_norm", "Precio Unitario", "Moneda"])


# -------------------------
# Construcción de costos desde resumen
# -------------------------
def calcular_costos_desde_resumen(df_resumen: pd.DataFrame, precios_o_archivo) -> pd.DataFrame:
    """
    Construye df_costos a partir de df_resumen (Materiales, Unidad, Cantidad).

    precios_o_archivo puede ser:
      A) DataFrame de precios (salida de cargar_precios)
      B) str ruta del archivo_materiales (para leer precios automáticamente)

    Retorna:
      Materiales, Unidad, Cantidad, Precio Unitario, Costo, Moneda, Tiene_Precio
    """
    if df_resumen is None or df_resumen.empty:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo", "Moneda", "Tiene_Precio"]
        )

    # Obtener tabla de precios
    if isinstance(precios_o_archivo, str):
        df_precios = cargar_precios(precios_o_archivo)
    else:
        df_precios = precios_o_archivo

    base = df_resumen.copy()
    base.columns = [str(c).replace("\u00A0", " ").strip() for c in base.columns]

    # Asegurar columnas mínimas
    for col, default in [("Materiales", ""), ("Unidad", ""), ("Cantidad", 0.0)]:
        if col not in base.columns:
            base[col] = default

    # Limpiar y tipar
    base["Materiales"] = base["Materiales"].astype(str).str.strip()
    base["Unidad"] = base["Unidad"].astype(str).str.strip()
    base["Cantidad"] = pd.to_numeric(base["Cantidad"], errors="coerce").fillna(0.0)

    # Claves normalizadas
    base["Materiales_norm"] = base["Materiales"].map(_norm_txt)
    base["Unidad_norm"] = base["Unidad"].map(_norm_txt)

    # Si no hay precios, devolver plantilla marcada como sin precio
    if df_precios is None or getattr(df_precios, "empty", True):
        base["Precio Unitario"] = pd.NA
        base["Moneda"] = "L"
        base["Tiene_Precio"] = False
        base["Costo"] = pd.NA
        return base[["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo", "Moneda", "Tiene_Precio"]]

    precios = df_precios.copy()
    for col, default in [("Materiales_norm", ""), ("Unidad_norm", ""), ("Precio Unitario", 0.0), ("Moneda", "L")]:
        if col not in precios.columns:
            precios[col] = default

    # Merge
    out = base.merge(
        precios[["Materiales_norm", "Unidad_norm", "Precio Unitario", "Moneda"]],
        on=["Materiales_norm", "Unidad_norm"],
        how="left",
    )

    # Tipar y calcular
    out["Precio Unitario"] = pd.to_numeric(out["Precio Unitario"], errors="coerce").fillna(0.0)
    out["Cantidad"] = pd.to_numeric(out["Cantidad"], errors="coerce").fillna(0.0)

    out["Tiene_Precio"] = out["Precio Unitario"] > 0
    out["Moneda"] = out["Moneda"].fillna("L").astype(str).str.strip()
    out.loc[out["Moneda"].eq(""), "Moneda"] = "L"

    out["Costo"] = (out["Precio Unitario"] * out["Cantidad"]).round(2)

    return out[["Materiales", "Unidad", "Cantidad", "Precio Unitario", "Costo", "Moneda", "Tiene_Precio"]]
