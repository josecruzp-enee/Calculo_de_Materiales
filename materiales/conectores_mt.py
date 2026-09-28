# -*- coding: utf-8 -*-
"""
materiales/conectores_mt.py

Ajuste del conector base de MT según calibre global.

SOLO reemplaza:
    CONECTOR DE COMPRESIÓN YC 25A25 (1/0-1/0)

Reglas:
    1/0 ACSR  -> sin cambio
    3/0 ACSR  -> YC 28A28 (3/0-3/0)
    266.8 MCM -> YPC 33R33R (266.8-266.8)
    477 MCM   -> YHN-525 (4/0-477)

No modifica ningún otro conector.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, List, Any

import pandas as pd


# =========================================================
# REGLAS MT
# =========================================================
CONECTORES_MT = {
    "3/0": "CONECTOR DE COMPRESIÓN YC 28A28 (3/0-3/0)",
    "266.8": "CONECTOR DE COMPRESIÓN YPC 33R33R (266.8-266.8)",
    "477": "CONECTOR DE COMPRESIÓN YHN-525 (4/0-477)",
}


# =========================================================
# NORMALIZACIÓN
# =========================================================
def _norm(s: str) -> str:
    s = str(s or "")

    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

    return s.upper().strip()


def _token_calibre(cal: str) -> str:
    """
    Convierte diferentes formas del calibre a un token estándar.

    Ejemplos:
        1/0 ACSR     -> 1/0
        3/0 ACSR     -> 3/0
        266.8 MCM    -> 266.8
        477 MCM      -> 477
    """

    s = _norm(cal)

    # MCM
    m = re.search(r"(\d+(?:\.\d+)?)\s*MCM", s)
    if m:
        return m.group(1)

    # #1/0, #3/0, etc.
    m = re.search(r"#\s*([0-9]+\/0|[0-9]+)", s)
    if m:
        return m.group(1)

    # 1/0 AWG, 3/0 AWG
    m = re.search(r"\b([0-9]+\/0|[0-9]+)\s*AWG\b", s)
    if m:
        return m.group(1)

    # 1/0 ACSR, 3/0 ACSR
    m = re.search(r"\b([0-9]+\/0)\s*(?:ACSR|ASCR|AAC)?\b", s)
    if m:
        return m.group(1)

    # fallback
    t = s.replace(" ", "")

    for suf in ("ACSR", "ASCR", "AAC", "MCM", "AWG"):
        t = t.replace(suf, "")

    return t.strip()


def _es_1_0(calibre_mt: str) -> bool:
    return _token_calibre(calibre_mt) == "1/0"


def _es_estructura_mt(estructura: str) -> bool:
    e = _norm(estructura)

    return (
        e == "MT"
        or e.startswith("A")
        or e.startswith("TH")
        or e.startswith("ER")
        or e.startswith("TM")
    )


# =========================================================
# ADAPTADOR DE TABLA
# =========================================================
def _a_dataframe(tabla: Any) -> pd.DataFrame:
    """
    Hace compatible este módulo con el contrato actual.

    Acepta:
        - DataFrame
        - dict de columnas
        - dict que contiene uno o más DataFrames

    Si no puede obtener una tabla válida, devuelve DataFrame vacío.
    """

    if tabla is None:
        return pd.DataFrame()

    # Ya viene como DataFrame
    if isinstance(tabla, pd.DataFrame):
        return tabla.copy()

    # Viene como dict
    if isinstance(tabla, dict):

        # -------------------------------------------------
        # 1. Buscar específicamente una hoja "conectores"
        # -------------------------------------------------
        for clave, valor in tabla.items():

            if _norm(clave) == "CONECTORES":

                if isinstance(valor, pd.DataFrame):
                    return valor.copy()

                try:
                    df = pd.DataFrame(valor)
                    if not df.empty:
                        return df
                except Exception:
                    pass

        # -------------------------------------------------
        # 2. Puede ser directamente un dict de columnas
        # -------------------------------------------------
        try:
            df = pd.DataFrame(tabla)

            if not df.empty:
                return df

        except Exception:
            pass

        # -------------------------------------------------
        # 3. Buscar cualquier DataFrame que parezca tabla
        #    de conectores
        # -------------------------------------------------
        for valor in tabla.values():

            if not isinstance(valor, pd.DataFrame):
                continue

            columnas = [_norm(c) for c in valor.columns]

            tiene_calibre = any("CALIBRE" in c for c in columnas)
            tiene_codigo = any(
                "CODIGO" in c or c.startswith("COD")
                for c in columnas
            )
            tiene_desc = any("DESC" in c for c in columnas)

            if tiene_calibre and (tiene_codigo or tiene_desc):
                return valor.copy()

    return pd.DataFrame()


def _normalizar_tabla(tabla: Any) -> pd.DataFrame:

    df = _a_dataframe(tabla)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Calibre",
                "Código",
                "Descripción",
                "Estructuras aplicables",
            ]
        )

    df = df.copy()

    rename_map = {}

    for col in df.columns:

        c = _norm(col)

        if c.startswith("CALIBRE"):
            rename_map[col] = "Calibre"

        elif c.startswith("COD") or c == "CODIGO":
            rename_map[col] = "Código"

        elif "DESC" in c:
            rename_map[col] = "Descripción"

        elif "APLIC" in c or "ESTRUCT" in c:
            rename_map[col] = "Estructuras aplicables"

    df = df.rename(columns=rename_map)

    for c in (
        "Calibre",
        "Código",
        "Descripción",
        "Estructuras aplicables",
    ):
        if c not in df.columns:
            df[c] = ""

    return df[
        [
            "Calibre",
            "Código",
            "Descripción",
            "Estructuras aplicables",
        ]
    ].copy()


# =========================================================
# CARGA DESDE EXCEL
# =========================================================
def cargar_conectores_mt(archivo_materiales: str) -> pd.DataFrame:

    try:

        df = pd.read_excel(
            archivo_materiales,
            sheet_name="conectores"
        )

        return _normalizar_tabla(df)

    except Exception:

        return _normalizar_tabla(None)


# =========================================================
# BÚSQUEDA EN TABLA
# =========================================================
def buscar_conector_por_calibre(
    calibre_mt: str,
    tabla_conectores: Any = None,
) -> Optional[str]:

    tok = _token_calibre(calibre_mt)

    if not tok:
        return None

    # 1/0 nunca se reemplaza
    if tok == "1/0":
        return None

    # -----------------------------------------------------
    # PRIMERO intentar usar la tabla recibida
    # -----------------------------------------------------
    df = _normalizar_tabla(tabla_conectores)

    if not df.empty:

        # Caso específico 477
        if tok == "477":

            for _, row in df.iterrows():

                calibre = _token_calibre(
                    str(row.get("Calibre", "") or "")
                )

                codigo = _norm(
                    str(row.get("Código", "") or "")
                )

                desc = str(
                    row.get("Descripción", "") or ""
                ).strip()

                if (
                    calibre == "477"
                    and codigo == "YHN-525"
                    and desc
                ):
                    return desc

        # Casos generales
        for _, row in df.iterrows():

            calibre_fila = _token_calibre(
                str(row.get("Calibre", "") or "")
            )

            desc = str(
                row.get("Descripción", "") or ""
            ).strip()

            if calibre_fila == tok and desc:
                return desc

    # -----------------------------------------------------
    # FALLBACK CONTROLADO
    #
    # Si la tabla no llegó o no encontró el registro,
    # utilizamos las reglas MT conocidas.
    # -----------------------------------------------------
    return CONECTORES_MT.get(tok)


# =========================================================
# DETECTOR DEL CONECTOR BASE
# =========================================================
def _es_yc25a25_base(material: str) -> bool:

    m = _norm(material)

    # Debe ser YC25A25
    tiene_codigo = (
        re.search(r"\bYC\s*25A25\b", m) is not None
        or "YC25A25" in m.replace(" ", "")
    )

    # Debe corresponder a 1/0 - 1/0
    tiene_calibre = (
        re.search(
            r"\(\s*1/0\s*[-–]\s*1/0\s*\)",
            m
        ) is not None
    )

    return tiene_codigo and tiene_calibre


# =========================================================
# REEMPLAZO
# =========================================================
def reemplazar_solo_yc25a25_mt(
    lista_materiales: List[str],
    estructura: str,
    calibre_mt_global: str,
    tabla_conectores: Any = None,
) -> List[str]:

    mats = list(lista_materiales or [])

    # No es MT
    if not _es_estructura_mt(estructura):
        return mats

    # 1/0 mantiene el material original
    if _es_1_0(calibre_mt_global):
        return mats

    reemplazo = buscar_conector_por_calibre(
        calibre_mt=calibre_mt_global,
        tabla_conectores=tabla_conectores,
    )

    if not reemplazo:
        return mats

    out: List[str] = []

    for mat in mats:

        if _es_yc25a25_base(mat):
            out.append(reemplazo)
        else:
            out.append(mat)

    return out
