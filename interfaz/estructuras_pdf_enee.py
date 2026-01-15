# interfaz/estructuras_pdf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Dict, List, Any
import re
import io

import pandas as pd
import streamlit as st

from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    materializar_df_a_archivo,
    expand_wide_to_long,
)

# -----------------------------
# Regex (tolerantes)
# -----------------------------
# Ancla de punto: "P # 12", "P-12", "P 12", "Punto 12"
_RE_ANCLA = re.compile(r"^\s*(?:P(?:UNTO)?\s*)?[-#:]?\s*(\d+)\s*$", re.IGNORECASE)

# Solo códigos proyectados (P)
_RE_COD_P = re.compile(
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

_RE_MULT = re.compile(r"^\s*(\d+)\s*[x×]\s*(.+?)\s*$", flags=re.I)


def _limpiar(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", s)


def _clasificar(code: str) -> Optional[str]:
    c = code.upper().strip()
    if c.startswith(("PC-", "PM-", "PT-")):
        return "Poste"
    if c.startswith("A-"):
        return "Primario"
    if c.startswith("B-"):
        return "Secundario"
    if c.startswith("R-") or re.match(r"^\d*\s*R[-\s]*\d+", c):
        return "Retenidas"
    if c.startswith("CT-"):
        return "Conexiones a tierra"
    if c.startswith(("TS-", "TD", "TF", "TR", "TX")):
        return "Transformadores"
    if c.startswith(("LL-", "LS-")):
        return "Luminarias"
    return None


def _add(bucket: Dict[str, Dict[str, int]], col: str, item: str) -> None:
    item = _limpiar(item)
    if not item:
        return
    m = _RE_MULT.match(item)
    if m:
        qty = int(m.group(1))
        code = _limpiar(m.group(2))
        if code:
            bucket[col][code] = max(bucket[col].get(code, 0), qty)
        return
    bucket[col][item] = max(bucket[col].get(item, 0), 1)


def _bucket_row(punto: int, bucket: Dict[str, Dict[str, int]]) -> Dict[str, str]:
    row = {c: "" for c in COLUMNAS_BASE}
    row["Punto"] = f"Punto {punto}"
    for col in COLUMNAS_BASE:
        if col == "Punto":
            continue
        codes = bucket.get(col, {})
        if not codes:
            continue
        parts = []
        for code in sorted(codes.keys()):
            qty = int(codes[code])
            parts.append(f"{qty}x {code}" if qty > 1 else code)
        row[col] = " ".join(parts)
    return row


def _extraer_codigos_P(texto: str) -> List[str]:
    t = " ".join((texto or "").split())
    return [m.group("code").strip() for m in _RE_COD_P.finditer(t) if m.group("code")]


def _words(pdf) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pi, page in enumerate(pdf.pages):
        ws = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
        for w in ws:
            w = dict(w)
            w["page_index"] = pi
            w["text"] = (w.get("text") or "").strip()
            if not w["text"]:
                continue
            out.append(w)
    # orden base por página y por y, x
    out.sort(key=lambda a: (a["page_index"], float(a.get("top", 0.0)), float(a.get("x0", 0.0))))
    return out


def _lineas(words: List[Dict[str, Any]], y_tol: float = 2.5) -> List[Dict[str, Any]]:
    # agrupa palabras en líneas por cercanía vertical
    lines: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    cur_y: Optional[float] = None
    cur_p: Optional[int] = None

    for w in words:
        y = float(w.get("top", 0.0))
        p = int(w.get("page_index", 0))
        if not cur:
            cur = [w]; cur_y = y; cur_p = p
            continue
        if p != cur_p or cur_y is None or abs(y - cur_y) > y_tol:
            lines.append(cur)
            cur = [w]; cur_y = y; cur_p = p
        else:
            cur.append(w)

    if cur:
        lines.append(cur)

    out: List[Dict[str, Any]] = []
    for g in lines:
        g.sort(key=lambda a: float(a.get("x0", 0.0)))
        text = " ".join([a["text"] for a in g if a.get("text")])
        x0 = min(float(a.get("x0", 0.0)) for a in g)
        x1 = max(float(a.get("x1", 0.0)) for a in g)
        top = min(float(a.get("top", 0.0)) for a in g)
        bottom = max(float(a.get("bottom", 0.0)) for a in g)
        out.append({
            "page_index": int(g[0].get("page_index", 0)),
            "text": _limpiar(text),
            "x0": x0, "x1": x1,
            "top": top, "bottom": bottom,
        })
    return out


def extraer_estructuras_pdf(pdf, dx: float = 85.0, dy: float = 230.0) -> pd.DataFrame:
    """
    Estrategia única:
    - Detecta anclas de punto (tolerantes).
    - Lee un rectángulo alrededor del ancla (como selección azul de Acrobat).
    - Dentro, extrae códigos con (P).
    """
    ws = _words(pdf)
    ls = _lineas(ws, y_tol=2.5)

    # indexar por página
    por_pagina: Dict[int, List[Dict[str, Any]]] = {}
    for ln in ls:
        por_pagina.setdefault(int(ln["page_index"]), []).append(ln)

    anclas: List[Dict[str, Any]] = []
    for ln in ls:
        m = _RE_ANCLA.match(ln["text"])
        if m:
            anclas.append({
                "page_index": int(ln["page_index"]),
                "punto": int(m.group(1)),
                "x0": float(ln["x0"]), "x1": float(ln["x1"]),
                "top": float(ln["top"]),
            })

    if not anclas:
        return pd.DataFrame(columns=COLUMNAS_BASE)

    anclas.sort(key=lambda a: (a["page_index"], a["top"], a["x0"]))

    bloques: Dict[int, Dict[str, Dict[str, int]]] = {}

    for a in anclas:
        pi = a["page_index"]
        punto = a["punto"]
        rx0 = a["x0"] - dx
        rx1 = a["x1"] + dx
        ry0 = a["top"] + 1.5
        ry1 = a["top"] + dy

        bucket = bloques.setdefault(punto, {c: {} for c in COLUMNAS_BASE if c != "Punto"})

        cands = []
        for ln in por_pagina.get(pi, []):
            y = float(ln["top"])
            if y < ry0 or y > ry1:
                continue
            x0, x1 = float(ln["x0"]), float(ln["x1"])
            if x1 < rx0 or x0 > rx1:
                continue
            cands.append(ln)

        cands.sort(key=lambda ln: (float(ln["top"]), float(ln["x0"])))

        for ln in cands:
            txt = ln["text"]
            # corta si ve otra ancla abajo
            m2 = _RE_ANCLA.match(txt)
            if m2 and float(ln["top"]) > a["top"] + 3.0:
                break

            for code in _extraer_codigos_P(txt):
                code = _limpiar(code)
                col = _clasificar(code)
                if col:
                    _add(bucket, col, code)

    rows = [_bucket_row(p, b) for p, b in bloques.items()]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    # filtrar vacíos
    if not df.empty:
        cols = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    # ordenar por número
    def _k(s: str) -> int:
        m = re.search(r"(\d+)", s)
        return int(m.group(1)) if m else 10**9

    if not df.empty:
        df = df.sort_values(by="Punto", key=lambda s: s.map(_k)).reset_index(drop=True)

    return normalizar_columnas(df, COLUMNAS_BASE)


def cargar_desde_pdf_enee() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    st.subheader("📄 Cargar estructuras desde PDF (ENEE)")

    archivo_pdf = st.file_uploader("Sube el PDF del plano", type=["pdf"], key="upl_pdf")
    if not archivo_pdf:
        return None, None

    try:
        import pdfplumber  # type: ignore
    except Exception:
        st.error("Falta dependencia: pdfplumber. Agrega 'pdfplumber' a requirements.txt")
        return None, None

    with pdfplumber.open(io.BytesIO(archivo_pdf.getvalue())) as pdf:
        df_ancho = extraer_estructuras_pdf(pdf, dx=85.0, dy=230.0)

    if df_ancho.empty:
        st.warning("Se leyó el PDF, pero no se encontraron estructuras PROYECTADAS (P).")
        return None, None

    st.success(f"✅ Estructuras proyectadas detectadas: {len(df_ancho)} puntos")
    st.dataframe(df_ancho, use_container_width=True, hide_index=True)

    ruta_tmp = materializar_df_a_archivo(df_ancho, "pdf")
    df_largo = expand_wide_to_long(df_ancho)

    st.caption("🔎 Vista LARGA (lo que consume el motor)")
    st.dataframe(df_largo, use_container_width=True, hide_index=True)

    return df_largo, ruta_tmp
