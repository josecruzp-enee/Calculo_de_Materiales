# interfaz/estructuras_pdf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Dict, List
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

# -------------------------
# Regex base
# -------------------------
RE_PUNTO = re.compile(r"^\s*(?:P(?:UNTO)?\s*)?[-#]?\s*(\d+)\s*$", re.IGNORECASE)

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
    re.VERBOSE
)

RE_MULT = re.compile(r"^\s*(\d+)\s*[x×]\s*(.+?)\s*$", flags=re.I)


def _limpiar(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", s)


def _clasificar(code: str) -> Optional[str]:
    c = code.strip().upper()
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
        parts = []
        for code in sorted(d.keys()):
            qty = int(d[code])
            parts.append(f"{qty}x {code}" if qty > 1 else code)
        row[col] = " ".join(parts)
    return row


def _extraer_codigos_proyectados(linea: str) -> List[str]:
    t = " ".join((linea or "").split())
    return [m.group("code").strip() for m in RE_COD_P.finditer(t) if m.group("code")]


# -------------------------
# Parser textual por bloques
# -------------------------
def extraer_estructuras_desde_texto(texto: str) -> pd.DataFrame:
    if not texto:
        return pd.DataFrame(columns=COLUMNAS_BASE)

    # normalizar líneas
    raw_lines = [ln.strip() for ln in texto.splitlines()]
    lines = [_limpiar(ln) for ln in raw_lines if _limpiar(ln)]

    bloques: Dict[int, Dict[str, Dict[str, int]]] = {}
    punto_actual: Optional[int] = None

    for ln in lines:
        # detectar "P # n" / "Punto n" / "P- n"
        m = RE_PUNTO.match(ln)
        if m and (ln.upper().startswith("P") or ln.upper().startswith("PUNTO") or ln.strip().startswith(("#", "-", "P"))):
            punto_actual = int(m.group(1))
            bloques.setdefault(punto_actual, {c: {} for c in COLUMNAS_BASE if c != "Punto"})
            continue

        if punto_actual is None:
            continue

        # tomar solo líneas con códigos (P)
        cods = _extraer_codigos_proyectados(ln)
        if not cods:
            continue

        for c in cods:
            c = _limpiar(c)
            col = _clasificar(c)
            if col:
                _add(bloques[punto_actual], col, c)

    rows = [_bucket_to_row(p, b) for p, b in sorted(bloques.items(), key=lambda x: x[0])]
    df = pd.DataFrame(rows, columns=COLUMNAS_BASE)

    if not df.empty:
        cols = [c for c in COLUMNAS_BASE if c != "Punto"]
        df = df[df[cols].astype(str).apply(lambda r: any(v.strip() for v in r), axis=1)]

    return normalizar_columnas(df, COLUMNAS_BASE)


def extraer_estructuras_desde_pdf_textual(pdf) -> pd.DataFrame:
    # concatena texto de todas las páginas
    partes: List[str] = []
    for page in pdf.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            partes.append(t)
    texto = "\n".join(partes)
    return extraer_estructuras_desde_texto(texto)


# -------------------------
# UI Streamlit
# -------------------------
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
        df_ancho = extraer_estructuras_desde_pdf_textual(pdf)

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
