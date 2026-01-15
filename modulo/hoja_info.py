# -*- coding: utf-8 -*-
"""
hoja_info.py
Construcción de la Hoja de Información del Proyecto (sección PDF)
Autor: José Nikol Cruz
"""

from __future__ import annotations

import re
from datetime import datetime
from math import sqrt, floor
from typing import Dict, List, Optional, Tuple

import pandas as pd
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


# ==========================================================
# VALIDACIÓN
# ==========================================================
def _validar_dependencias(styleH, styleN, calibres_fn) -> None:
    if styleH is None or styleN is None or calibres_fn is None:
        raise ValueError(
            "Faltan styleH/styleN/_calibres_por_tipo. Debes pasarlos desde pdf_utils."
        )


# ==========================================================
# HELPERS BASE
# ==========================================================
def _float_safe(x, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d


def _formato_tension(vll) -> str:
    """
    Ej: 13.8 -> '7.9 LN / 13.8 LL KV' (LN truncado a 1 decimal).
    """
    try:
        vll = float(vll)
        vln = vll / sqrt(3)
        vln = floor(vln * 10) / 10
        return f"{vln:.1f} LN / {vll:.1f} LL KV"
    except Exception:
        return str(vll)


def _col_cantidad(df: Optional[pd.DataFrame]) -> Optional[str]:
    if df is None or df.empty:
        return None
    for c in ("Cantidad", "CANTIDAD", "cantidad"):
        if c in df.columns:
            return c
    return None


def _parse_n_fases(configuracion: str) -> int:
    s = (configuracion or "").strip().upper()
    m = re.search(r"(\d+)\s*F", s)
    return int(m.group(1)) if m else 1


# ==========================================================
# PARSERS DE CÓDIGOS
# ==========================================================
def _parse_ll_codigo(txt: str) -> Tuple[int, str]:
    """
    Devuelve (n_lamparas, etiqueta_potencia)
    - LL-1-50W      -> (1, '50 W')
    - LL-2-100W     -> (2, '100 W')
    - LL-1-28A50W   -> (1, '50 W')
    - LL-1-28-50W   -> (1, '28-50 W')
    """
    s = str(txt).upper().replace("–", "-")
    s = re.sub(r"\s+", "", s)

    m_n = re.search(r"\bLL-(\d+)-", s)
    n = int(m_n.group(1)) if m_n else 1

    # 28A50W -> potencia 50 W
    m = re.search(r"\bLL-\d+-(\d+)A(\d+)W\b", s)
    if m:
        return n, f"{m.group(2)} W"

    # 28-50W -> rango
    m = re.search(r"\bLL-\d+-(\d+)-(\d+)W\b", s)
    if m:
        return n, f"{m.group(1)}-{m.group(2)} W"

    # 50W -> simple
    m = re.search(r"\bLL-\d+-(\d+)W\b", s)
    if m:
        return n, f"{m.group(1)} W"

    return n, "SIN POTENCIA"


def _parse_transformador_codigo(txt: str) -> Optional[Tuple[str, float]]:
    """
    Acepta:
      TS-15KVA, TS-15 KVA, TS - 15 KVA, TT-37.5KVA ...
    Retorna: (prefijo, kva) o None
    """
    s = str(txt).upper().strip()
    m = re.match(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA$", s)
    if not m:
        return None
    pref = m.group(1)
    kva = _float_safe(m.group(2), 0.0)
    return pref, kva


# ==========================================================
# EXTRACTORES (RETORNAN DATOS, NO FLOWABLES)
# ==========================================================
def extraer_postes(df_estructuras: Optional[pd.DataFrame]) -> Tuple[Optional[Dict[str, int]], int]:
    """
    Retorna: (resumen_dict, total)
    resumen_dict: {"PC-30": 2, "PC-40": 1}
    """
    if df_estructuras is None or df_estructuras.empty or "codigodeestructura" not in df_estructuras.columns:
        return None, 0

    s = df_estructuras["codigodeestructura"].astype(str)
    postes = df_estructuras[s.str.contains(r"\b(PC|PT)\b", case=False, na=False)]
    if postes.empty:
        return None, 0

    resumen: Dict[str, int] = {}
    for _, r in postes.iterrows():
        cod = str(r.get("codigodeestructura", "")).strip()
        cant = int(_float_safe(r.get("Cantidad", 0), 0))
        if cod:
            resumen[cod] = resumen.get(cod, 0) + cant

    return (resumen if resumen else None), sum(resumen.values())


def extraer_transformadores(
    df_estructuras: Optional[pd.DataFrame],
    df_mat: Optional[pd.DataFrame],
) -> Tuple[int, List[str]]:
    """
    Retorna: (total_transformadores, capacidades_lista)
    total_transformadores = cantidad física (TS=1, TD=2, TT=3)
    capacidades_lista: ["TS-15 KVA", "TT-37.5 KVA", ...]
    """
    mult = {"TS": 1, "TD": 2, "TT": 3}

    # ---- 1) Desde ESTRUCTURAS (preferido) ----
    if df_estructuras is not None and not df_estructuras.empty and "codigodeestructura" in df_estructuras.columns:
        s = df_estructuras["codigodeestructura"].astype(str).str.upper().str.strip()

        ext = s.str.extract(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA$", expand=True)
        mask = ext[0].notna()
        if mask.any():
            qty = pd.to_numeric(df_estructuras.loc[mask, "Cantidad"], errors="coerce").fillna(0)
            pref = ext.loc[mask, 0]
            kva = pd.to_numeric(ext.loc[mask, 1], errors="coerce").fillna(0)

            total_t = int((qty * pref.map(mult)).sum())
            caps = sorted({f"{p}-{k:g} KVA" for p, k in zip(pref, kva)})
            return total_t, caps

    # ---- 2) Fallback: desde MATERIALES (solo si no hay en estructuras) ----
    if df_mat is not None and not df_mat.empty:
        # En tu pipeline, a veces el código viene como "Codigo" o "CODIGO".
        posibles_cols = [c for c in ("Codigo", "CODIGO", "cod", "COD", "Cod", "codigodeestructura") if c in df_mat.columns]
        col_busqueda = posibles_cols[0] if posibles_cols else ("Materiales" if "Materiales" in df_mat.columns else None)
        if col_busqueda:
            s = df_mat[col_busqueda].astype(str).str.upper().str.strip()
            ext = s.str.extract(r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b", expand=True)
            mask = ext[0].notna()
            if mask.any():
                cc = _col_cantidad(df_mat) or "Cantidad"
                df_tx = df_mat.loc[mask].copy()
                if cc not in df_tx.columns:
                    df_tx[cc] = 0
                df_tx[cc] = pd.to_numeric(df_tx[cc], errors="coerce").fillna(0)

                df_tx["_key"] = ext.loc[mask, 0] + "-" + ext.loc[mask, 1] + " KVA"
                bancos = df_tx.groupby("_key", as_index=False)[cc].max()

                total_t = 0
                for _, r in bancos.iterrows():
                    pref = str(r["_key"]).split("-")[0].upper()
                    total_t += int(_float_safe(r[cc], 0) * mult.get(pref, 1))

                return int(total_t), bancos["_key"].tolist()

    return 0, []


def extraer_luminarias(
    df_estructuras: Optional[pd.DataFrame],
    df_mat: Optional[pd.DataFrame],
) -> Tuple[int, Dict[str, int]]:
    """
    Retorna: (total, dict_potencias)
    dict_potencias: {"50 W": 2, "100 W": 1}

    PRIORIDAD:
    1) df_estructuras['codigodeestructura'] (lo correcto según tu lógica de "códigos")
    2) fallback en df_mat en columnas tipo Codigo/CODIGO (y si no, Materiales)
    """

    # -------------------------------
    # 1) Desde ESTRUCTURAS (preferido)
    # -------------------------------
    if df_estructuras is not None and not df_estructuras.empty and "codigodeestructura" in df_estructuras.columns:
        s = df_estructuras["codigodeestructura"].astype(str).str.upper().str.strip()

        # match LL-x-...W
        pat = r"^LL\s*-\s*\d+\s*-\s*(?:\d+\s*A\s*)?\d+(?:\s*-\s*\d+)?\s*W$"
        mask = s.str.match(pat, na=False)

        if mask.any():
            qty = pd.to_numeric(df_estructuras.loc[mask, "Cantidad"], errors="coerce").fillna(0)

            det: Dict[str, int] = {}
            for cod, q in zip(df_estructuras.loc[mask, "codigodeestructura"].astype(str), qty):
                n, pot = _parse_ll_codigo(cod)
                # Cantidad real = Cantidad(fila) * N del código
                real = int(round(_float_safe(q, 0) * n))
                if real > 0:
                    det[pot] = det.get(pot, 0) + real

            total = sum(det.values())
            return total, det

    # -----------------------------------------
    # 2) Fallback: buscar en df_mat por CÓDIGOS
    # -----------------------------------------
    if df_mat is None or df_mat.empty:
        return 0, {}

    posibles_cols = [c for c in ("Codigo", "CODIGO", "cod", "COD", "Cod", "codigodeestructura") if c in df_mat.columns]
    col_cod = posibles_cols[0] if posibles_cols else None
    cc = _col_cantidad(df_mat)
    if not col_cod or not cc:
        # Si no hay columna de código o cantidad, no podemos sumar confiable
        return 0, {}

    s = df_mat[col_cod].astype(str).str.upper().str.strip()
    pat = r"^LL\s*-\s*\d+\s*-\s*(?:\d+\s*A\s*)?\d+(?:\s*-\s*\d+)?\s*W$"
    mask = s.str.match(pat, na=False)
    if not mask.any():
        return 0, {}

    qty = pd.to_numeric(df_mat.loc[mask, cc], errors="coerce").fillna(0)

    det: Dict[str, int] = {}
    for cod, q in zip(df_mat.loc[mask, col_cod].astype(str), qty):
        n, pot = _parse_ll_codigo(cod)
        real = int(round(_float_safe(q, 0) * n))
        if real > 0:
            det[pot] = det.get(pot, 0) + real

    total = sum(det.values())
    return total, det


# ==========================================================
# BUILDERS (RETORNAN FLOWABLES)
# ==========================================================
def build_header(styleH) -> List:
    return [
        Paragraph("<b>Hoja de Información del Proyecto</b>", styleH),
        Spacer(1, 12),
    ]


def build_tabla_datos(
    datos_proyecto: dict,
    cables: list,
    nivel_tension_fmt: str,
    styleN,
    _calibres_por_tipo,
) -> List:
    calibre_primario_tab = _calibres_por_tipo(cables, "MT")
    calibre_secundario_tab = _calibres_por_tipo(cables, "BT")
    calibre_neutro_tab = _calibres_por_tipo(cables, "N")
    calibre_piloto_tab = _calibres_por_tipo(cables, "HP")
    calibre_retenidas_tab = _calibres_por_tipo(cables, "RETENIDA")

    calibre_primario = calibre_primario_tab or datos_proyecto.get("calibre_primario") or datos_proyecto.get("calibre_mt", "")
    calibre_secundario = calibre_secundario_tab or datos_proyecto.get("calibre_secundario", "")
    calibre_neutro = calibre_neutro_tab or datos_proyecto.get("calibre_neutro", "")
    calibre_piloto = calibre_piloto_tab or datos_proyecto.get("calibre_piloto", "")
    calibre_retenidas = calibre_retenidas_tab or datos_proyecto.get("calibre_retenidas", "")

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
        ["Nivel de Tensión (kV):", nivel_tension_fmt],
        ["Calibre Primario:", calibre_primario],
        ["Calibre Secundario:", calibre_secundario],
        ["Calibre Neutro:", calibre_neutro],
        ["Calibre Piloto:", calibre_piloto],
        ["Calibre Cable de Retenidas:", calibre_retenidas],
        ["Fecha de Informe:", datos_proyecto.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
        ["Responsable / Diseñador:", datos_proyecto.get("responsable", "N/A")],
        ["Empresa / Área:", datos_proyecto.get("empresa", "N/A")],
    ]

    t = Table(data, colWidths=[180, 300])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    return [t, Spacer(1, 18)]


def build_descripcion_general(
    datos_proyecto: dict,
    df_estructuras: Optional[pd.DataFrame],
    df_mat: Optional[pd.DataFrame],
    nivel_tension_fmt: str,
    primarios: list,
    bt: list,
    neutro: list,  # <- ya no lo usaremos para imprimir
    hp: list,
    styleN,
) -> List:
    lineas: List[str] = []

    # Postes
    resumen_postes, total_postes = extraer_postes(df_estructuras)
    if resumen_postes:
        partes = [f"{v} {k}" for k, v in resumen_postes.items()]
        lineas.append(f"Hincado de {', '.join(partes)} (Total: {total_postes} postes).")

    def _get_cfg(c: dict) -> str:
        # soporta "Configuración" o "Config"
        return str(c.get("Configuración", c.get("Config", "")) or "").strip().upper()

    def _get_total(c: dict) -> float:
        return _float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", c.get("Longitud", 0))))

    def _longitud_por_tramo(c: dict) -> float:
        # Total Cable ya viene = Longitud * conductores
        total = _get_total(c)
        cfg = _get_cfg(c)

        # Si cfg es 2F/3F, dividimos para expresar “metros de tramo”
        n_f = _parse_n_fases(cfg)
        if n_f > 1:
            return total / n_f
        return total

    def _nf(cfg: str) -> int:
        return _parse_n_fases(cfg)

    def _armar_linea(etiqueta: str, tension: str, cfg_txt: str, calibre: str, long_m: float) -> Optional[str]:
        if long_m <= 0 or not calibre:
            return None
        # evita comas vacías
        partes = [f"Construcción de {long_m:.0f} m de {etiqueta}", tension, cfg_txt, calibre]
        partes = [p for p in partes if str(p).strip()]
        return ", ".join(partes) + "."

    # =========================
    # 1) LP (MT): siempre nF+N
    # =========================
    for c in primarios:
        L = _longitud_por_tramo(c)
        cfg = _get_cfg(c)
        calibre = str(c.get("Calibre", "")).strip()
        nf = _nf(cfg)
        cfg_txt = f"{nf}F+N"
        l = _armar_linea("LP", nivel_tension_fmt, cfg_txt, calibre, L)
        if l:
            lineas.append(l)

    # ==========================================================
    # 2) LS (BT): se imprime con HP implícito si existe HP
    #    - longitud LS = longitud por tramo del BT (fases)
    #    - si hay HP y su longitud > BT, imprimimos excedente como HP+N a 120 V
    # ==========================================================
    # ¿hay HP en el proyecto?
    hp_existe = any(_longitud_por_tramo(h) > 0 for h in hp)

    # tomar el "HP mayor" (por si hay varias filas HP)
    L_hp_max = 0.0
    hp_calibre = ""
    hp_cfg = ""
    for h in hp:
        Lh = _longitud_por_tramo(h)
        if Lh > L_hp_max:
            L_hp_max = Lh
            hp_calibre = str(h.get("Calibre", "")).strip()
            hp_cfg = _get_cfg(h)

    # imprimir cada BT como LS
    for c in bt:
        L_bt = _longitud_por_tramo(c)
        cfg_bt = _get_cfg(c)
        calibre_bt = str(c.get("Calibre", "")).strip()
        nf_bt = _nf(cfg_bt)

        if L_bt <= 0 or not calibre_bt:
            continue

        cfg_ls = f"{nf_bt}F+HP+N" if hp_existe else f"{nf_bt}F+N"
        l = _armar_linea("LS", "120/240 V", cfg_ls, calibre_bt, L_bt)
        if l:
            lineas.append(l)

        # HP extra (solo excedente)
        if hp_existe and L_hp_max > L_bt and hp_calibre:
            L_extra = L_hp_max - L_bt
            # regla de negocio: HP extra siempre "HP+N" a 120 V
            l2 = _armar_linea("HP", "120 V", "HP+N", hp_calibre, L_extra)
            if l2:
                lineas.append(l2)

            # IMPORTANTE: para no repetir el excedente en cada BT si hay múltiples BT
            # consumimos el excedente una sola vez
            L_hp_max = L_bt

    # =========================
    # Transformadores
    # =========================
    total_t, caps = extraer_transformadores(df_estructuras, df_mat)
    if total_t > 0:
        cap_txt = ", ".join(caps) if caps else ""
        lineas.append(f"Instalación de {total_t} transformador(es) {f'({cap_txt})' if cap_txt else ''}.")

    # =========================
    # Luminarias
    # =========================
    total_l, det_l = extraer_luminarias(df_estructuras, df_mat)
    if total_l > 0:
        det = " y ".join([f"{v} de {k}" for k, v in sorted(det_l.items(), key=lambda x: x[0])])
        lineas.append(f"Instalación de {total_l} luminaria(s) de alumbrado público ({det}).")

    # Párrafo final
    descripcion_manual = (datos_proyecto.get("descripcion_proyecto", "") or "").strip()
    descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
    cuerpo_desc = (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto

    return [
        Paragraph("<b>Descripción general del Proyecto:</b>", styleN),
        Spacer(1, 6),
        Paragraph(cuerpo_desc, styleN),
        Spacer(1, 18),
    ]



# ==========================================================
# FUNCIÓN PÚBLICA (LA QUE LLAMA pdf_utils)
# ==========================================================
def hoja_info_proyecto(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
    *,
    styles=None,  # (lo dejas por compatibilidad aunque no se use aquí)
    styleN=None,
    styleH=None,
    _calibres_por_tipo=None,
):
    """
    Devuelve lista de flowables para insertar en el PDF.
    Esta función NO contiene toda la lógica adentro: solo orquesta.
    """
    _validar_dependencias(styleH, styleN, _calibres_por_tipo)

    tension_valor = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension") or ""
    nivel_tension_fmt = _formato_tension(tension_valor)

    cables = datos_proyecto.get("cables_proyecto", []) or []
    primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
    secundarios = [c for c in cables if str(c.get("Tipo", "")).upper() in ("BT", "HP", "N")]

    elems: List = []
    elems.extend(build_header(styleH))
    elems.extend(build_tabla_datos(datos_proyecto, cables, nivel_tension_fmt, styleN, _calibres_por_tipo))
    elems.extend(build_descripcion_general(datos_proyecto, df_estructuras, df_mat, nivel_tension_fmt, primarios, secundarios, styleN))
    return elems
