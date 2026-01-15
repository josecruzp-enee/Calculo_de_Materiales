# interfaz/estructuras_dxf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Dict, List, Any
import io
import re
import tempfile

import pandas as pd
import streamlit as st

from interfaz.estructuras_comunes import (
    COLUMNAS_BASE,
    normalizar_columnas,
    materializar_df_a_archivo,
    expand_wide_to_long,
)

# -------------------------
# Regex (alineado a tu estilo)
# -------------------------
# Punto dentro de texto: "P # 22", "P-22", "P 22", "Punto 22"
RE_PUNTO_EN_TEXTO = re.compile(r"\bP(?:UNTO)?\s*[-#]?\s*(\d+)\b", re.IGNORECASE)

# Captura códigos proyectados (P)
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

# Tokenizador: saca códigos aunque vengan pegados en una misma celda
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


def _extraer_codigos_proyectados(texto: str) -> List[str]:
    t = " ".join((texto or "").split())
    return [m.group("code").strip() for m in RE_COD_P.finditer(t) if m.group("code")]


def _extraer_punto(texto: str) -> Optional[int]:
    m = RE_PUNTO_EN_TEXTO.search(texto or "")
    return int(m.group(1)) if m else None


def _texto_entidad(e: Any) -> str:
    # MTEXT: plain_text() es lo más confiable
    try:
        if e.dxftype() == "MTEXT":
            return (e.plain_text() or "").strip()
    except Exception:
        pass

    # TEXT: dxf.text
    try:
        if e.dxftype() == "TEXT":
            return (e.dxf.text or "").strip()
    except Exception:
        pass

    # fallback
    try:
        return (getattr(e, "text", "") or "").strip()
    except Exception:
        return ""


def extraer_estructuras_desde_dxf(doc: Any, capa_objetivo: str = "Estructuras") -> pd.DataFrame:
    """
    Lee MTEXT/TEXT del modelspace.
    Detecta Punto dentro del mismo bloque y códigos (P) dentro del mismo bloque.
    """
    msp = doc.modelspace()
    bloques: Dict[int, Dict[str, Dict[str, int]]] = {}

    for e in msp:
        et = e.dxftype()
        if et not in ("MTEXT", "TEXT"):
            continue

        # filtro por capa
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

    return normalizar_columnas(df, COLUMNAS_BASE)


def _leer_dxf_streamlit(archivo) -> Any:
    """
    Lee DXF desde Streamlit uploader.
    Usa readfile(BytesIO) si funciona; si no, cae a archivo temporal.
    """
    import ezdxf  # type: ignore

    data = archivo.getvalue()

    # intento 1: BytesIO
    try:
        stream = io.BytesIO(data)
        return ezdxf.readfile(stream)
    except Exception:
        pass

    # intento 2: archivo temporal (estable en cloud)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    return ezdxf.readfile(tmp_path)


def _tokenizar_celda(celda: str) -> List[str]:
    if not celda:
        return []
    t = " ".join(str(celda).split())
    return [m.group(0).strip() for m in RE_TOKEN.finditer(t)]


def _explotar_codigos_largos(df_largo: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte CodigoEstructura como "R-02 R-04" -> dos filas.
    Trabaja con columnas típicas del pipeline: Punto, Tipo, CodigoEstructura, Cantidad.
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


def cargar_desde_dxf_enee() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    st.subheader("📐 Cargar estructuras desde DXF (ENEE)")

    archivo = st.file_uploader("Sube el DXF del plano", type=["dxf"], key="upl_dxf")
    if not archivo:
        return None, None

    try:
        import ezdxf  # noqa: F401  # type: ignore
    except Exception:
        st.error("Falta dependencia: ezdxf. Agrega 'ezdxf' a requirements.txt")
        return None, None

    # leer doc (arreglado)
    try:
        doc = _leer_dxf_streamlit(archivo)
    except Exception as e:
        st.error(f"No pude leer el DXF: {e}")
        return None, None

    capa = st.text_input(
        "Capa de estructuras (opcional)",
        value="Estructuras",
        help="Debe coincidir con el nombre de la capa en AutoCAD.",
        key="capa_estructuras_dxf",
    )

    df_ancho = extraer_estructuras_desde_dxf(doc, capa_objetivo=capa.strip() if capa else "")

    if df_ancho.empty:
        st.warning("Se leyó el DXF, pero no se encontraron estructuras PROYECTADAS (P) en esa capa.")
        st.info("Tip: verifica que el texto esté en la capa 'Estructuras' y que los códigos tengan '(P)'.")
        return None, None

    st.success(f"✅ Estructuras proyectadas detectadas: {len(df_ancho)} puntos")
    st.dataframe(df_ancho, use_container_width=True, hide_index=True)

    ruta_tmp = materializar_df_a_archivo(df_ancho, "dxf")

    # 1) wide -> long
    df_largo = expand_wide_to_long(df_ancho)
    # 2) ✅ rompe combinados: "R-02 R-04" => filas separadas
    df_largo = _explotar_codigos_largos(df_largo)

    st.caption("🔎 Vista LARGA (lo que consume el motor)")
    st.dataframe(df_largo, use_container_width=True, hide_index=True)

    return df_largo, ruta_tmp
