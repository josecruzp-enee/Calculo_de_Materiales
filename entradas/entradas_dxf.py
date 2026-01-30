# -*- coding: utf-8 -*-
"""
entradas_dxf.py

Entrada desde DXF (ENEE): lectura y extracción de estructuras proyectadas.
"""

from __future__ import annotations

from typing import Optional, Dict, List, Any
import io
import re
import tempfile

import pandas as pd


COLUMNAS_BASE = ["Punto", "Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores", "Luminarias"]

RE_PUNTO_EN_TEXTO = re.compile(r"\bP(?:UNTO)?\s*[-#]?\s*(\d+)\b", re.IGNORECASE)

RE_COD_P = re.compile(
    r"""
    (?P<code>
        (?:PC|PM|PT)-[A-Z0-9"'\-]+
        |A-[A-Z0-9\-]+
        |B-[A-Z0-9\-]+
        |CT-[A-Z0-9\-]+
        |TS-[A-Z0-9\-]+
        |TD[A-Z0-9\-]*|TF[A-Z0-9\-]*|TR[A-Z0-9\-]*|TX[A-Z0-9\-]*
        |LL-[A-Z0-9\-]+|LS-[A-Z0-9\-]+
        |R-\d+[A-Z0-9\-]*
    )
    \s*\(\s*[Pp]\s*\)
    """,
    re.VERBOSE,
)

RE_MULT = re.compile(r"^\s*(\d+)\s*[x×]\s*(.+?)\s*$", flags=re.I)

RE_TOKEN = re.compile(
    r"""
    (?:PC|PM|PT)-[A-Z0-9"'\-]+
    |A-[A-Z0-9\-]+
    |B-[A-Z0-9\-]+
    |CT-[A-Z0-9\-]+
    |TS-[A-Z0-9\-]+
    |TD[A-Z0-9\-]*|TF[A-Z0-9\-]*|TR[A-Z0-9\-]*|TX[A-Z0-9\-]*
    |LL-[A-Z0-9\-]+|LS-[A-Z0-9\-]+
    |R-\d+[A-Z0-9\-]*
    """,
    re.VERBOSE,
)


def _limpiar(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", s)


def _clasificar(code: str) -> Optional[str]:
    c = (code or "").strip().upper()
    if c.startswith(("PC-", "PM-", "PT-")):
        return "Poste"
    if c.startswith("A-"):
        return "Primario"
    if c.startswith("B-"):
        return "Secundario"
    if c.startswith("R-"):
        return "Retenidas"
    if c.startswith("CT-"):
        return "Conexiones a tierra"
    if c.startswith(("TS-", "TD", "TF", "TR", "TX")):
        return "Transformadores"
    if c.startswith(("LL-", "LS-")):
        return "Luminarias"
    return None


def _add(bucket: Dict[str, Dict[str, int]], col: str, raw_item: str) -> None:
    item = _limpiar(raw_item)
    if not item:
        return

    m = RE_MULT.match(item)
    if m:
        qty = int(m.group(1))
        code = _limpiar(m.group(2))
        if code:
            bucket[col][code] = max(bucket[col].get(code, 0), qty)
        return

    bucket[col][item] = max(bucket[col].get(item, 0), 1)


def _bucket_to_row(punto: int, bucket: Dict[str, Dict[str, int]]) -> Dict[str, str]:
    row = {c: "" for c in COLUMNAS_BASE}
    row["Punto"] = f"Punto {punto}"

    for col in COLUMNAS_BASE:
        if col == "Punto":
            continue
        d = bucket.get(col, {})
        if not d:
            continue

        parts: List[str] = []
        for code in sorted(d.keys()):
            qty = int(d[code])
            parts.append(f"{qty}x {code}" if qty > 1 else code)

        row[col] = " ".join(parts)

    return row


def leer_dxf_bytes(data: bytes) -> Any:
    try:
        import ezdxf  # type: ignore
    except Exception as e:
        raise RuntimeError("Falta dependencia: ezdxf") from e

    # Intento 1: BytesIO
    try:
        stream = io.BytesIO(data)
        return ezdxf.readfile(stream)
    except Exception:
        pass

    # Intento 2: archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    return ezdxf.readfile(tmp_path)


def _texto_entidad(e: Any) -> str:
    try:
        if e.dxftype() == "MTEXT":
            return (e.plain_text() or "").strip()
    except Exception:
        pass
    try:
        if e.dxftype() == "TEXT":
            return (e.dxf.text or "").strip()
    except Exception:
        pass
    return ""


def _extraer_punto(texto: str) -> Optional[int]:
    m = RE_PUNTO_EN_TEXTO.search(texto or "")
    return int(m.group(1)) if m else None


def _extraer_codigos_proyectados(texto: str) -> List[str]:
    t = " ".join((texto or "").split())
    return [m.group("code").strip() for m in RE_COD_P.finditer(t) if m.group("code")]


def extraer_estructuras_desde_dxf(doc: Any, capa_objetivo: str = "") -> pd.DataFrame:
    msp = doc.modelspace()
    bloques: Dict[int, Dict[str, Dict[str, int]]] = {}

    for e in msp:
        if e.dxftype() not in ("MTEXT", "TEXT"):
            continue

        layer = (getattr(e.dxf, "layer", "") or "").strip()
        if capa_objetivo and layer.lower() != capa_objetivo.lower():
            continue

        txt = _texto_entidad(e)
        if not txt:
            continue

        punto = _extraer_punto(txt)
        if punto is None:
            continue

        cods = _extraer_codigos_proyectados(txt)
        if not cods:
            continue

        bloques.setdefault(punto, {c: {} for c in COLUMNAS_BASE if c != "Punto"})
        for c in cods:
            c = _limpiar(c)
            col = _clasificar(c)
            if col:
                _add(bloques[punto], col, c)

    rows = [_bucket_to_row(p, b) for p, b in sorted(bloques.items(), key=lambda x: x[0])]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    if not df.empty:
        cols = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    return df


def _tokenizar_celda(celda: str) -> List[str]:
    if not celda:
        return []
    t = " ".join(str(celda).split())
    return [m.group(0).strip() for m in RE_TOKEN.finditer(t)]


def explotar_codigos_largos(df_largo: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte CodigoEstructura como "R-02 R-04" -> dos filas.
    Espera columnas típicas: Punto, Tipo, CodigoEstructura, Cantidad.
    """
    if df_largo is None or df_largo.empty:
        return df_largo

    df = df_largo.copy()

    col_code = "CodigoEstructura" if "CodigoEstructura" in df.columns else "codigodeestructura"
    col_qty = "Cantidad" if "Cantidad" in df.columns else "cantidad"

    df["__tokens__"] = df[col_code].apply(_tokenizar_celda)
    df = df.explode("__tokens__").dropna(subset=["__tokens__"])
    df["__tokens__"] = df["__tokens__"].astype(str).str.strip()
    df = df[df["__tokens__"].str.len() > 0].copy()

    df[col_code] = df["__tokens__"]
    df.drop(columns=["__tokens__"], inplace=True)

    df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(1).astype(int)

    group_cols = ["Punto", col_code]
    if "Tipo" in df.columns:
        group_cols = ["Punto", "Tipo", col_code]

    df = df.groupby(group_cols, as_index=False)[col_qty].sum()
    return df
