# interfaz/descripcion_dxf_enee.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, Any, Dict, List
import io
import re
import tempfile

import streamlit as st


# ==========================================================
# 1) Lectura DXF desde Streamlit (robusto en cloud)
# ==========================================================
def leer_dxf_streamlit(archivo) -> Any:
    """
    Lee DXF desde st.file_uploader.
    En cloud, lo más estable es escribir a tmp y usar ezdxf.readfile(path).
    """
    try:
        import ezdxf  # type: ignore
    except Exception as e:
        raise RuntimeError("Falta dependencia: ezdxf. Agrega 'ezdxf' a requirements.txt") from e

    data = archivo.getvalue()

    # Intento 1: archivo temporal (estable)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    return ezdxf.readfile(tmp_path)


# ==========================================================
# 2) Extraer texto de entidades (TEXT/MTEXT)
# ==========================================================
def _texto_entidad(e: Any) -> str:
    # MTEXT
    try:
        if e.dxftype() == "MTEXT":
            # plain_text() quita formato
            return (e.plain_text() or "").strip()
    except Exception:
        pass

    # TEXT
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


def _norm_keep_breaks(s: str) -> str:
    s = (s or "").replace("\xa0", " ")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _norm_line(s: str) -> str:
    s = (s or "").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ==========================================================
# 3) Extraer BLOQUE DESCRIPCIÓN desde DXF
# ==========================================================
RE_DESC = re.compile(r"\bDESCRIPCI[ÓO]N\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)

def extraer_descripcion_desde_dxf(doc: Any, capa: str = "") -> str:
    """
    Busca en TEXT/MTEXT un bloque que contenga 'DESCRIPCIÓN:'.
    Si 'capa' se da, filtra por esa capa.
    """
    msp = doc.modelspace()

    candidatos: List[str] = []

    for e in msp:
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue

        layer = (getattr(e.dxf, "layer", "") or "").strip()
        if capa and layer.lower() != capa.lower():
            continue

        txt = _texto_entidad(e)
        if not txt:
            continue

        txt2 = _norm_keep_breaks(txt)
        if re.search(r"\bDESCRIPCI[ÓO]N\s*:", txt2, flags=re.IGNORECASE):
            candidatos.append(txt2)

    if not candidatos:
        return ""

    # Elegimos el candidato más largo (normalmente la caja completa)
    best = max(candidatos, key=len)

    # Extraer solo lo que viene después de DESCRIPCIÓN:
    m = RE_DESC.search(best)
    if not m:
        return best.strip()

    tail = m.group(1).strip()

    # Cortar si vienen otros labels debajo
    corte = re.split(
        r"\n\s*(?:REVIS[ÓO]\s*:|APROB[ÓO]\s*:|CONTENIDO\s*:|NOTAS\s*:|OBSERVACIONES\s*:)\s*",
        tail,
        flags=re.IGNORECASE,
        maxsplit=1,
    )[0]

    return _norm_keep_breaks(corte)


# ==========================================================
# 4) Parsear la descripción a datos estructurados
# ==========================================================
def _to_int(s: str) -> int:
    s = (s or "").strip()
    s = s.replace(".", "").replace(",", "")
    return int(s)

def parsear_descripcion_plano(texto: str) -> Dict[str, Any]:
    """
    Devuelve datos típicos:
    - primaria_m, primaria_kv, primaria_fases, primaria_cond
    - secundaria_m, secundaria_v, secundaria_fases, secundaria_cond
    - transfo_cant, transfo_kva, transfo_prim_kv, transfo_sec_v
    - lum_cant, lum_w
    """
    t = _norm_line(texto)
    out: Dict[str, Any] = {}

    # Primaria: "Construcción de 190 m de línea Primaria, 19.9/34.5 KV; ..."
    m = re.search(
        r"(?:Construcci[óo]n|Extensi[óo]n)\s+de\s+([\d\.,]+)\s*(?:m|metros)\s+de\s+l[ií]nea\s+Primaria\s*,?\s*"
        r"([\d\.]+(?:/\d\.?\d*)?)\s*KV\s*[,;]?\s*([123]F\+N)?\s*[,;]?\s*(.*?)(?:\.|$)",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        out["primaria_m"] = _to_int(m.group(1))
        out["primaria_kv"] = m.group(2)
        out["primaria_fases"] = (m.group(3) or "").upper()
        out["primaria_cond"] = _norm_line(m.group(4))

    # Secundaria: "Construcción de 1,062 m de Línea Secundaria 2F+N, 120/240 V. ..."
    m = re.search(
        r"(?:Construcci[óo]n|Extensi[óo]n)\s+de\s+([\d\.,]+)\s*(?:m|metros)\s+de\s+(?:L[ií]nea\s+Secundaria|LS)\s*,?\s*"
        r"([123]F\+N)?\s*[,;]?\s*([\d\/]+)\s*V\s*[,;]?\s*(.*?)(?:\.|$)",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        out["secundaria_m"] = _to_int(m.group(1))
        out["secundaria_fases"] = (m.group(2) or "").upper()
        out["secundaria_v"] = m.group(3)
        out["secundaria_cond"] = _norm_line(m.group(4))

    # Luminarias: "Instalación de 25 luminarias Led de 29 W"
    m = re.search(r"Instalaci[óo]n\s+de\s+(\d+)\s+luminarias?.*?(\d+)\s*W", t, flags=re.IGNORECASE)
    if m:
        out["lum_cant"] = int(m.group(1))
        out["lum_w"] = int(m.group(2))

    # Transformadores: "Instalación de dos transformadores ... TS-50 KVA ... 7.9/13.8 KV-120/240 V"
    m = re.search(
        r"Instalaci[óo]n\s+de\s+(\d+)\s+transformadores?",
        t,
        flags=re.IGNORECASE,
    )
    out["transfo_cant"] = int(m.group(1)) if m else 0

    m = re.search(r"\bTS[-\s]*([0-9]+(?:\.[0-9]+)?)\s*KVA\b", t, flags=re.IGNORECASE)
    if m:
        out["transfo_kva"] = float(m.group(1))

    m = re.search(
        r"([\d\.]+(?:/\d\.?\d*)?)\s*KV\s*[-–]\s*([\d\/]+)\s*V",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        out["transfo_prim_kv"] = m.group(1)
        out["transfo_sec_v"] = m.group(2)

    # si no dijo cantidad pero sí hay TS, asumimos 1
    if out.get("transfo_cant", 0) == 0 and out.get("transfo_kva"):
        out["transfo_cant"] = 1

    return out


# ==========================================================
# 5) Generar tu "Descripción general del proyecto"
# ==========================================================
def construir_descripcion_general(datos: Dict[str, Any]) -> str:
    lines: List[str] = ["Descripción general del Proyecto:"]
    n = 1

    if datos.get("primaria_m"):
        s = f"{n}. Construcción de {datos['primaria_m']} m de línea Primaria"
        if datos.get("primaria_kv"):
            s += f", {datos['primaria_kv']} KV"
        if datos.get("primaria_fases"):
            s += f", {datos['primaria_fases']}"
        if datos.get("primaria_cond"):
            s += f", {datos['primaria_cond']}"
        s += "."
        lines.append(s)
        n += 1

    if datos.get("secundaria_m"):
        s = f"{n}. Construcción de {datos['secundaria_m']} m de línea Secundaria/LS"
        if datos.get("secundaria_fases"):
            s += f", {datos['secundaria_fases']}"
        if datos.get("secundaria_v"):
            s += f", {datos['secundaria_v']} V"
        if datos.get("secundaria_cond"):
            s += f", {datos['secundaria_cond']}"
        s += "."
        lines.append(s)
        n += 1

    if datos.get("transfo_cant", 0) > 0 and datos.get("transfo_kva"):
        s = f"{n}. Instalación de {datos['transfo_cant']} transformador(es) (TS-{int(datos['transfo_kva'])} KVA)"
        if datos.get("transfo_prim_kv") and datos.get("transfo_sec_v"):
            s += f", {datos['transfo_prim_kv']} KV-{datos['transfo_sec_v']} V"
        s += "."
        lines.append(s)
        n += 1

    if datos.get("lum_cant"):
        s = f"{n}. Instalación de {datos['lum_cant']} luminaria(s)"
        if datos.get("lum_w"):
            s += f" de {datos['lum_w']} W"
        s += "."
        lines.append(s)
        n += 1

    if len(lines) == 1:
        lines.append("(No se pudo generar automáticamente desde la descripción del plano.)")

    return "\n".join(lines)


# ==========================================================
# 6) Sección Streamlit lista para tu app
# ==========================================================
def seccion_descripcion_desde_dxf_enee() -> Optional[str]:
    st.subheader("🧾 Descripción del Proyecto (desde DXF)")

    archivo = st.file_uploader("Sube el DXF del plano", type=["dxf"], key="upl_dxf_desc")
    if not archivo:
        return None

    # (opcional) capa donde está el texto del rótulo
    capa = st.text_input(
        "Capa del rótulo (opcional)",
        value="",
        help="Si lo sabes, pon la capa donde está el texto de 'DESCRIPCIÓN'. Si lo dejas vacío, busca en todas.",
        key="capa_desc_dxf",
    ).strip()

    try:
        doc = leer_dxf_streamlit(archivo)
    except Exception as e:
        st.error(str(e))
        return None

    bloque = extraer_descripcion_desde_dxf(doc, capa=capa)

    if not bloque.strip():
        st.warning("No encontré un bloque con 'DESCRIPCIÓN:' en TEXT/MTEXT.")
        st.info("Tip: revisa que el rótulo sea texto real (TEXT/MTEXT) y no un bloque raro sin texto.")
        return None

    st.markdown("### Bloque detectado (DESCRIPCIÓN):")
    st.text_area("Texto", bloque, height=220)

    datos = parsear_descripcion_plano(bloque)
    st.markdown("### Datos extraídos (debug):")
    st.json(datos)

    desc_final = construir_descripcion_general(datos)
    st.markdown("### Descripción general generada:")
    st.text_area("Resultado", desc_final, height=220)

    return desc_final
