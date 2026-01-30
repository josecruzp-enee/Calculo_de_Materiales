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
) -> Tuple[int, str, List[str]]:
    """
    Retorna:
      - total_transformadores: cantidad física (TS=1, TD=2, TT=3) sumada por bancos
      - resumen_conexion: string estilo "2 x TS-50 kVA + 1 x TD-50 kVA"
      - lista_bancos: ["TS-50 kVA", "TD-50 kVA", ...] (por si ocupás lista aparte)
    """
    mult = {"TS": 1, "TD": 2, "TT": 3}

    def _norm_key(pref: str, kva: float) -> str:
        # 50.0 -> 50 ; 37.5 -> 37.5
        kva_txt = f"{kva:g}"
        return f"{pref.upper()}-{kva_txt} kVA"

    def _orden_key(k: str):
        # "TS-50 kVA" -> ("TS", 50.0)
        m = re.match(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*kVA$", k, flags=re.IGNORECASE)
        if not m:
            return ("ZZ", 0.0)
        return (m.group(1).upper(), _float_safe(m.group(2), 0.0))

    # ==========================================================
    # 1) Desde ESTRUCTURAS (preferido)
    # ==========================================================
    if df_estructuras is not None and not df_estructuras.empty and "codigodeestructura" in df_estructuras.columns:
        s = df_estructuras["codigodeestructura"].astype(str).str.upper().str.strip()

        ext = s.str.extract(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA$", expand=True)
        mask = ext[0].notna()
        if mask.any():
            qty = pd.to_numeric(df_estructuras.loc[mask, "Cantidad"], errors="coerce").fillna(0)
            pref = ext.loc[mask, 0].astype(str).str.upper()
            kva = pd.to_numeric(ext.loc[mask, 1], errors="coerce").fillna(0)

            # bancos: conteo por tipo-capacidad (cantidad de bancos)
            bancos = {}
            for p, k, q in zip(pref, kva, qty):
                if q <= 0:
                    continue
                key = _norm_key(p, float(k))
                bancos[key] = bancos.get(key, 0) + int(round(float(q)))

            # total físico: bancos * multiplicador (TS=1, TD=2, TT=3)
            total_fisico = 0
            for key, nb in bancos.items():
                p = key.split("-", 1)[0].upper()
                total_fisico += int(nb * mult.get(p, 1))

            # resumen conexión: "N x KEY + M x KEY"
            partes = [f"{nb} x {key}" for key, nb in sorted(bancos.items(), key=lambda kv: _orden_key(kv[0]))]
            resumen = " + ".join(partes)
            return int(total_fisico), resumen, list(sorted(bancos.keys(), key=_orden_key))

    # ==========================================================
    # 2) Fallback: desde MATERIALES
    # ==========================================================
    if df_mat is not None and not df_mat.empty:
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

                bancos = {}
                for p, k, q in zip(ext.loc[mask, 0], ext.loc[mask, 1], df_tx[cc]):
                    if q <= 0:
                        continue
                    key = _norm_key(str(p), _float_safe(k, 0.0))
                    # En materiales puede repetirse; tomamos MAX por banco típico, pero aquí sumamos por seguridad:
                    bancos[key] = max(bancos.get(key, 0), int(round(float(q))))

                total_fisico = 0
                for key, nb in bancos.items():
                    p = key.split("-", 1)[0].upper()
                    total_fisico += int(nb * mult.get(p, 1))

                partes = [f"{nb} x {key}" for key, nb in sorted(bancos.items(), key=lambda kv: _orden_key(kv[0]))]
                resumen = " + ".join(partes)
                return int(total_fisico), resumen, list(sorted(bancos.keys(), key=_orden_key))

    return 0, "", []



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
    neutro: list,
    hp: list,
    styleN,
) -> List:
    lineas: List[str] = []

    # -----------------------------
    # Postes
    # -----------------------------
    resumen_postes, total_postes = extraer_postes(df_estructuras)
    if resumen_postes:
        partes = [f"{v} {k}" for k, v in resumen_postes.items()]
        lineas.append(f"Hincado de {', '.join(partes)} (Total: {total_postes} postes).")

    # -----------------------------
    # Helpers internos
    # -----------------------------
    def _calibre_corto(txt: str) -> str:
        """
        Reduce descripciones largas:
        'Cable de Aluminio ACSR # 1/0 AWG Raven' -> 'ACSR # 1/0 AWG Raven'
        'Cable de Aluminio Forrado WP # 3/0 AWG Fig' -> 'WP # 3/0 AWG Fig'
        """
        s = str(txt or "").strip()

        # quitar prefijos típicos
        s = re.sub(r"(?i)^\s*cable\s+de\s+aluminio\s+forrado\s+", "", s)
        s = re.sub(r"(?i)^\s*cable\s+de\s+aluminio\s+", "", s)
        s = re.sub(r"(?i)^\s*cable\s+", "", s)

        # normalizar espacios
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _get_cfg(c: dict) -> str:
        return str(c.get("Configuración", c.get("Config", "")) or "").strip().upper()

    def _get_calibre(c: dict) -> str:
        return _calibre_corto(str(c.get("Calibre", "") or "").strip())

    def _get_total_m(c: dict) -> float:
        # Preferimos Total Cable (m); si no existe, usamos Longitud (m) o Longitud
        return _float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", c.get("Longitud", 0.0))), 0.0)

    def _get_long_tramo(c: dict) -> float:
        """
        Convierte TotalCable(m) -> metros de tramo.
        - Si cfg es 2F/3F, dividimos entre nF (NO entre N/HP).
        """
        total = _get_total_m(c)
        cfg = _get_cfg(c)
        n_f = _parse_n_fases(cfg)  # detecta "2F", "3F", etc. default 1
        if n_f > 1:
            return total / n_f
        return total

    def _max_tramo(lista: list) -> float:
        if not lista:
            return 0.0
        return max((_get_long_tramo(c) for c in lista), default=0.0)

    def _cfg_fases_desde_lista(lista: list) -> int:
        """
        Toma nF del primer elemento con cfg útil.
        """
        for c in lista:
            cfg = _get_cfg(c)
            nf = _parse_n_fases(cfg)
            if nf >= 1:
                return nf
        return 1

    def _armar_linea(etiqueta: str, tension: str, cfg: str, desglose: str, long_m: float) -> Optional[str]:
        if long_m <= 0 or not desglose:
            return None

        partes = [f"Construcción de {long_m:.0f} m de {etiqueta}"]
        if tension:
            partes.append(tension)
        if cfg:
            partes.append(cfg)
        partes.append(desglose)

        return ", ".join(partes) + "."

    # ==========================================================
    # 1) LP (MT + N) -> POR CADA CONFIG (1F/2F/3F)
    #    - Longitud la define MT (tramo)
    #    - Neutro se asume acompaña (1 conductor) si existe
    # ==========================================================
    hay_n = _max_tramo(neutro) > 0
    cal_n = _get_calibre(neutro[0]) if neutro else ""

    # agrupar primarios por cfg (1F/2F/3F...)
    prim_por_cfg: Dict[str, list] = {}
    for c in primarios:
        cfg = _get_cfg(c)  # "1F" "2F" "3F" ...
        prim_por_cfg.setdefault(cfg, []).append(c)

    for cfg_mt, lista_mt in prim_por_cfg.items():
        if not cfg_mt:
            continue

        # tramo lo define MT (no neutro)
        tramo_lp = _max_tramo(lista_mt)
        nf_lp = _parse_n_fases(cfg_mt)

        cfg_lp = f"{nf_lp}F" + ("+N" if (hay_n and cal_n) else "")

        # desglose EXACTO (no sumar filas):
        # fases MT = nf_lp x calibre MT (tomamos el primero; en MT normalmente es el mismo)
        cal_mt = _get_calibre(lista_mt[0]) if lista_mt else ""
        partes = []
        if nf_lp > 0 and cal_mt:
            partes.append(f"{nf_lp} x {cal_mt}")
        if hay_n and cal_n:
            partes.append(f"1 x {cal_n}")

        desglose_lp = " + ".join(partes)

        l = _armar_linea("LP", nivel_tension_fmt, cfg_lp, desglose_lp, tramo_lp)
        if l:
            lineas.append(l)

    # ==========================================================
    # 2) LS (BT + (HP si cubre) + N)
    #    - LS se expresa por la longitud de FASES BT (tramo_bt)
    #    - HP se incluye en LS solo si HP >= BT
    # ==========================================================
    tramo_bt = _max_tramo(bt)
    nf_bt = _cfg_fases_desde_lista(bt)
    tramo_hp = _max_tramo(hp)

    hp_cubre_bt = (tramo_hp > 0) and (tramo_bt > 0) and (tramo_hp >= tramo_bt - 1e-6)

    cfg_ls = f"{nf_bt}F"
    if hp_cubre_bt:
        cfg_ls += "+HP"
    if hay_n and cal_n:
        cfg_ls += "+N"

    # desglose LS:
    # - fases BT = nf_bt x calibre BT (primera fila; típico es único)
    # - si HP cubre BT, sumamos 1 x calibre HP
    # - neutro 1 x calibre N
    partes_ls = []
    cal_bt = _get_calibre(bt[0]) if bt else ""
    if nf_bt > 0 and cal_bt and tramo_bt > 0:
        partes_ls.append(f"{nf_bt} x {cal_bt}")

    cal_hp = _get_calibre(hp[0]) if hp else ""
    if hp_cubre_bt and cal_hp:
        partes_ls.append(f"1 x {cal_hp}")

    if hay_n and cal_n:
        partes_ls.append(f"1 x {cal_n}")

    desglose_ls = " + ".join(partes_ls)

    l = _armar_linea("LS", "120/240 V", cfg_ls, desglose_ls, tramo_bt)
    if l:
        lineas.append(l)

    # ==========================================================
    # 3) HP extra (o todo HP si NO cubre BT)
    #    - tensión: 120 V
    # ==========================================================
    if tramo_hp > 0 and cal_hp:
        if hp_cubre_bt:
            hp_extra = max(0.0, tramo_hp - tramo_bt)
        else:
            hp_extra = tramo_hp

        if hp_extra > 0:
            cfg_hp = "HP" + ("+N" if (hay_n and cal_n) else "")
            partes_hp = [f"1 x {cal_hp}"]
            if hay_n and cal_n:
                partes_hp.append(f"1 x {cal_n}")
            desglose_hp = " + ".join(partes_hp)

            l = _armar_linea("HP", "120 V", cfg_hp, desglose_hp, hp_extra)
            if l:
                lineas.append(l)

    # ==========================================================
    # Transformadores
    # ==========================================================
    total_t, resumen_conexion, _caps = extraer_transformadores(df_estructuras, df_mat)
    if total_t > 0:
        # Ej: "Instalación de 2 transformador(es) en conexión 2 x TS-50 kVA."
        if resumen_conexion:
            if total_t == 1:
                lineas.append(f"Instalación de 1 transformador en conexión {resumen_conexion}.")
            else:
                lineas.append(f"Instalación de {total_t} transformador(es) en conexión {resumen_conexion}.")
        else:
            # fallback
            lineas.append(f"Instalación de {total_t} transformador(es).")

    # ==========================================================
    # Luminarias
    # ==========================================================
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
    styles=None,  # compatibilidad
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

    cables = datos_proyecto.get("cables_proyecto", []) or []
    primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
    bt       = [c for c in cables if str(c.get("Tipo", "")).upper() == "BT"]
    neutro   = [c for c in cables if str(c.get("Tipo", "")).upper() == "N"]
    hp       = [c for c in cables if str(c.get("Tipo", "")).upper() == "HP"]
    

    elems: List = []
    elems.extend(build_header(styleH))
    elems.extend(build_tabla_datos(datos_proyecto, cables, nivel_tension_fmt, styleN, _calibres_por_tipo))

    elems.extend(
        build_descripcion_general(
            datos_proyecto,
            df_estructuras,
            df_mat,
            nivel_tension_fmt,
            primarios,
            bt,
            neutro,
            hp,
            styleN,
        )
    )
    return elems

