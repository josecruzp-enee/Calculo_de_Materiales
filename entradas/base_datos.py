# entradas/base_datos.py

# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
from pathlib import Path
from ayuda.debug import debug_guardar

# ==========================================================
# CONFIG
# ==========================================================
def obtener_ruta_base() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "Estructura_datos.xlsx"


def _norm_col(s: str) -> str:
    return (
        str(s)
        .strip()
        .upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
    )


# ==========================================================
# VALIDADOR
# ==========================================================
def _es_hoja_estructura(df: pd.DataFrame) -> bool:

    cols = [_norm_col(c) for c in df.columns]

    return (
        "MATERIALES" in cols
        and "UNIDAD" in cols
        and any(c in cols for c in ["13.8", "34.5"])
    )


# ==========================================================
# NORMALIZADOR
# ==========================================================
def _normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    df.columns = [_norm_col(c) for c in df.columns]

    mapa = {
        "MATERIAL": "MATERIALES",
        "DESCRIPCION": "MATERIALES",
        "DESCRIPCION DE MATERIALES": "MATERIALES",
        "UNIDAD": "UNIDAD",
        "CANTIDAD": "CANTIDAD",
    }

    df = df.rename(columns=lambda c: mapa.get(c, c))

    return df


# ==========================================================
# CARGA CENTRAL (ÚNICA)
# ==========================================================
def cargar_base_datos(ruta: Path | None = None) -> dict[str, pd.DataFrame]:

    ruta = ruta or obtener_ruta_base()

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    xls = pd.ExcelFile(ruta)
    debug_guardar("EXCEL_HOJAS_DETECTADAS", {
        "hojas_raw": xls.sheet_names[:10]  # primeras 10
    })
    hojas: dict[str, pd.DataFrame] = {}

    # ==========================================================
    # 🔍 DEBUG GENERAL
    # ==========================================================
    debug_guardar("BASE_DATOS_LECTURA", {
        "hojas_excel": xls.sheet_names
    })

    for hoja in xls.sheet_names:

        try:
            df = xls.parse(hoja)

            if df is None or df.empty:
                continue

            df = _normalizar_dataframe(df)
            nombre = _norm_col(hoja)

            # ==========================================================
            # 🔥 DETECCIÓN ROBUSTA DE HOJA ÍNDICE
            # ==========================================================
            cols = [_norm_col(c) for c in df.columns]

            col_codigo = next(
                (c for c in cols if "CODIGO" in c and "ESTRUCT" in c),
                None
            )

            col_desc = next(
                (c for c in cols if "DESCRIP" in c),
                None
            )

            es_indice = col_codigo is not None and col_desc is not None

            # ==========================================================
            # 🔍 DEBUG POR HOJA
            # ==========================================================
            debug_guardar(f"HOJA_{hoja}", {
                "nombre_normalizado": nombre,
                "columnas": cols[:10],
                "col_codigo_detectada": col_codigo,
                "col_desc_detectada": col_desc,
                "es_indice": es_indice,
                "shape": df.shape
            })

            # ==========================================================
            # 🔥 INCLUSIÓN DE HOJAS
            # ==========================================================
            if (
                _es_hoja_estructura(df)
                or nombre == "MATERIALES"
                or es_indice
                or "INDICE" in nombre   # 🔥 FORZAR ENTRADA DE LA HOJA INDICE
            ):
                hojas[nombre] = df

        except Exception as e:
            debug_guardar(f"ERROR_HOJA_{hoja}", str(e))
            continue

    # ==========================================================
    # 🔍 DEBUG FINAL
    # ==========================================================
    debug_guardar("BASE_DATOS_FINAL", {
        "hojas_cargadas": list(hojas.keys())
    })

    if not hojas:
        raise ValueError("No se encontró ninguna hoja válida")

    return hojas
# ==========================================================
# ACCESO
# ==========================================================
def obtener_hoja(data: dict, nombre: str) -> pd.DataFrame | None:
    return data.get(_norm_col(nombre))


def obtener_catalogo_materiales(data: dict) -> pd.DataFrame:

    df = data.get("MATERIALES")

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(
            columns=["Materiales", "Unidad", "Codigo", "Referencia", "Costo Unitario"]
        )

    df = _normalizar_dataframe(df)

    out = pd.DataFrame()

    # ✔ SIEMPRE EXISTE
    out["Materiales"] = df["MATERIALES"].astype(str).str.strip()

    # 🔥 FIX: usar Series vacía en vez de ""
    def safe_col(nombre):
        if nombre in df.columns:
            return df[nombre]
        return pd.Series([""] * len(df))

    out["Unidad"] = safe_col("UNIDAD").astype(str).str.strip()
    out["Codigo"] = safe_col("CODIGO").astype(str).str.strip()
    out["Referencia"] = safe_col("REFERENCIA").astype(str).str.strip()

    # 🔥 FIX CRÍTICO
    costo_col = None
    for c in df.columns:
        if "COSTO" in c:
            costo_col = c
            break

    if costo_col:
        out["Costo Unitario"] = pd.to_numeric(df[costo_col], errors="coerce")
    else:
       out["Costo Unitario"] = pd.Series([None] * len(df))

    faltantes = out[out["Costo Unitario"].isna()]

    debug_guardar("CATALOGO_COSTOS", {
        "total": len(out),
        "con_costo": int(out["Costo Unitario"].notna().sum()),
        "sin_costo": int(len(faltantes)),
    })
    return out.reset_index(drop=True)


# ==========================================================
# CATÁLOGO DE ESTRUCTURAS DESDE HOJA ÍNDICE (ROBUSTO)
# ==========================================================
def cargar_catalogo_estructuras_desde_indice(data: dict) -> dict:

    if not data:
        debug_guardar("INDICE_DEBUG", "data vacío")
        return {}

    from ayuda.debug import debug_guardar

    debug_guardar("INDICE_KEYS", list(data.keys()))

    for nombre, df in data.items():

        debug_guardar("INDICE_EVALUANDO_HOJA", nombre)

        if df is None:
            debug_guardar(f"INDICE_{nombre}_SKIP", "None")
            continue

        if df.empty:
            debug_guardar(f"INDICE_{nombre}_SKIP", "empty")
            continue

        df = df.copy()
        df.columns = [_norm_col(c) for c in df.columns]

        debug_guardar(f"INDICE_{nombre}_COLUMNAS", df.columns.tolist())

        # 🔥 DETECCIÓN DE COLUMNAS
        col_codigo = None
        col_desc = None

        for c in df.columns:
            c_lower = c.lower()

            if "cod" in c_lower:
                col_codigo = c

            if "desc" in c_lower:
                col_desc = c

        debug_guardar(f"INDICE_{nombre}_COL_CODIGO", col_codigo)
        debug_guardar(f"INDICE_{nombre}_COL_DESC", col_desc)

        if not col_codigo or not col_desc:
            debug_guardar(f"INDICE_{nombre}_NO_VALIDO", True)
            continue

        # 🔥 CONSTRUCCIÓN MAPA
        mapa = {}

        for _, r in df.iterrows():

            codigo = str(r.get(col_codigo, "")).strip().upper()
            desc = str(r.get(col_desc, "")).strip()

            if codigo and codigo != "NAN":
                mapa[codigo] = desc

        debug_guardar("MAPA_LEN", len(mapa))
        debug_guardar("MAPA_SAMPLE", list(mapa.items())[:5])
        debug_guardar("INDICE_USADO", nombre)

        return mapa

    debug_guardar("INDICE_ERROR_FINAL", "NO SE DETECTÓ NINGUNA HOJA VÁLIDA")

    return {}
