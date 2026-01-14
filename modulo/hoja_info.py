# -*- coding: utf-8 -*-
"""
hoja_info.py
Construcción de la Hoja de Información del Proyecto (sección PDF)
Autor: José Nikol Cruz
"""

from __future__ import annotations

import re
from datetime import datetime
import pandas as pd
from math import sqrt, floor
from xml.sax.saxutils import escape

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def hoja_info_proyecto(
    datos_proyecto,
    df_estructuras=None,
    df_mat=None,
    *,
    styles=None,
    styleN=None,
    styleH=None,
    _calibres_por_tipo=None
):
 

    def float_safe(x, d=0.0):
        try:
            return float(x)
        except Exception:
            return d

    def formato_tension(vll):
        """
        Ej: 13.8 -> '7.9 LN / 13.8 LL KV' (LN truncado a 1 decimal).
        """
        try:
            vll = float(vll)
            vln = vll / sqrt(3)
            vln = floor(vln * 10) / 10  # truncar 1 decimal
            return f"{vln:.1f} LN / {vll:.1f} LL KV"
        except Exception:
            return str(vll)

    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    # ==== DATOS DEL PROYECTO ====
    descripcion_manual = (datos_proyecto.get("descripcion_proyecto", "") or "").strip()
    tension_valor = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension") or ""
    nivel_tension_fmt = formato_tension(tension_valor)

    cables = datos_proyecto.get("cables_proyecto", []) or []
    primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
    secundarios = [c for c in cables if str(c.get("Tipo", "")).upper() in ("BT", "HP", "N")]
    retenidas = [c for c in cables if str(c.get("Tipo", "")).upper() == "RETENIDA"]

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

    tabla = Table(data, colWidths=[180, 300])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    elems.append(tabla)
    elems.append(Spacer(1, 18))

    # ==== DESCRIPCIÓN GENERAL ====
    lineas = []

    # --- Postes ---
    if df_estructuras is not None and not df_estructuras.empty:
        if "codigodeestructura" in df_estructuras.columns:
            postes = df_estructuras[
                df_estructuras["codigodeestructura"].astype(str).str.contains(r"\b(PC|PT)\b", case=False, na=False)
            ]
        else:
            postes = pd.DataFrame()

        if not postes.empty:
            resumen = {}
            for _, r in postes.iterrows():
                cod = r["codigodeestructura"]
                cant = int(float_safe(r.get("Cantidad", 0), 0))
                resumen[cod] = resumen.get(cod, 0) + cant

            partes = [f"{v} {k}" for k, v in resumen.items()]
            total = sum(resumen.values())
            lineas.append(f"Hincado de {', '.join(partes)} (Total: {total} postes).")

    # --- Primarios (LP) ---
    for c in primarios:
        long_total = float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1

        long_desc = (long_total / n_fases) if n_fases > 1 else long_total
        if long_desc > 0 and calibre:
            lineas.append(
                f"Construcción de {long_desc:.0f} m de LP, {nivel_tension_fmt}, {fase}, {calibre}."
            )

    # --- Secundarios (LS) ---
    for c in secundarios:
        long_total = float_safe(c.get("Total Cable (m)", 0))
        fase = str(c.get("Configuración", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        m = re.search(r"(\d+)\s*F", fase)
        n_fases = int(m.group(1)) if m else 1

        long_desc = (long_total / n_fases) if n_fases > 1 else long_total
        if long_desc > 0 and calibre:
            lineas.append(
                f"Construcción de {long_desc:.0f} m de LS, 120/240 V, {fase}, {calibre}."
            )

    # --- Transformadores (TS/TD/TT) ---
    total_t = 0
    capacidades = []
    mult = {"TS": 1, "TD": 2, "TT": 3}

    # 1) Buscar en ESTRUCTURAS (codigodeestructura)
    if df_estructuras is not None and not df_estructuras.empty and "codigodeestructura" in df_estructuras.columns:
        s = df_estructuras["codigodeestructura"].astype(str).str.upper().str.strip()
        # Acepta: TT-37.5KVA  / TT-37.5 KVA / TT - 37.5 KVA
        ext = s.str.extract(r"^(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA$", expand=True)
        mask = ext[0].notna()

        if mask.any():
            qty = pd.to_numeric(df_estructuras.loc[mask, "Cantidad"], errors="coerce").fillna(0)
            pref = ext.loc[mask, 0]
            kva = pd.to_numeric(ext.loc[mask, 1], errors="coerce").fillna(0)
            total_t = int((qty * pref.map(mult)).sum())

            # Lista de capacidades detectadas (ej: TT-37.5 KVA)
            capacidades = sorted({f"{p}-{k:g} KVA" for p, k in zip(pref, kva)})

    # 2) Fallback: buscar en MATERIALES (Materiales)
    if total_t == 0 and df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:
        s = df_mat["Materiales"].astype(str).str.upper().str.strip()
        ext = s.str.extract(r"\b(TS|TD|TT)\s*-\s*(\d+(?:\.\d+)?)\s*KVA\b", expand=True)
        mask = ext[0].notna()

        if mask.any():
            df_tx = df_mat.loc[mask].copy()
            if "Cantidad" in df_tx.columns:
                df_tx["Cantidad"] = pd.to_numeric(df_tx["Cantidad"], errors="coerce").fillna(0)
            else:
                df_tx["Cantidad"] = 0

            df_tx["_key"] = ext.loc[mask, 0] + "-" + ext.loc[mask, 1] + " KVA"
            bancos = df_tx.groupby("_key", as_index=False)["Cantidad"].max()

            total_t = 0
            for _, r in bancos.iterrows():
                pref = str(r["_key"]).split("-")[0].upper()
                total_t += float_safe(r["Cantidad"], 0) * mult.get(pref, 1)

            total_t = int(total_t)
            capacidades = bancos["_key"].tolist()

    if total_t > 0:
        cap_txt = ", ".join(capacidades) if capacidades else ""
        lineas.append(f"Instalación de {total_t} transformador(es) {f'({cap_txt})' if cap_txt else ''}.")

    # --- Luminarias (POR CÓDIGO LL-... NO POR PALABRAS) ---
    # Regla: LL-1-50W => 1 lámpara de 50W (y así)
    if df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:

        col_cant = "Cantidad" if "Cantidad" in df_mat.columns else ("CANTIDAD" if "CANTIDAD" in df_mat.columns else None)
        if col_cant is None:
            # si no hay columna cantidad, no podemos sumar con seguridad
            col_cant = "Cantidad"
            df_mat = df_mat.copy()
            df_mat[col_cant] = 0

        s_mat = df_mat["Materiales"].astype(str)

        # Acepta:
        # LL-1-50W
        # LL-2-100W
        # LL-1-28A50W  (interpreta potencia = 50W)
        # LL-1-28-50W  (interpreta potencia = 28-50W)
        pat_ll = r"\bLL\s*-\s*\d+\s*-\s*(?:\d+\s*A\s*)?\d+(?:\s*-\s*\d+)?\s*W\b"
        lums = df_mat[s_mat.str.contains(pat_ll, case=False, na=False)].copy()

        if not lums.empty:
            lums[col_cant] = pd.to_numeric(lums[col_cant], errors="coerce").fillna(0)

            def parse_ll(txt):
                """
                Devuelve (n_lamparas, etiqueta_potencia)
                - LL-1-50W -> (1, '50 W')
                - LL-1-28A50W -> (1, '50 W')
                - LL-1-28-50W -> (1, '28-50 W')
                """
                s = str(txt).upper().replace("–", "-")
                # Normalizar espacios
                s = re.sub(r"\s+", "", s)

                # Capturar N
                m_n = re.search(r"LL-(\d+)-", s)
                n = int(m_n.group(1)) if m_n else 1

                # Caso 28A50W -> potencia 50
                m = re.search(r"LL-\d+-(\d+)A(\d+)W", s)
                if m:
                    return n, f"{m.group(2)} W"

                # Caso 28-50W -> rango
                m = re.search(r"LL-\d+-(\d+)-(\d+)W", s)
                if m:
                    return n, f"{m.group(1)}-{m.group(2)} W"

                # Caso 50W -> simple
                m = re.search(r"LL-\d+-(\d+)W", s)
                if m:
                    return n, f"{m.group(1)} W"

                return n, "SIN POTENCIA"

            parsed = lums["Materiales"].map(parse_ll)
            lums["_n"] = parsed.map(lambda x: x[0])
            lums["_pot"] = parsed.map(lambda x: x[1])

            # Cantidad real de luminarias = Cantidad(fila) * N del código
            lums["_qty_real"] = lums[col_cant].astype(float) * lums["_n"].astype(float)

            resumen = (
                lums.groupby("_pot", as_index=True)["_qty_real"]
                    .sum()
                    .round()
                    .astype(int)
                    .sort_index()
            )

            total = int(resumen.sum())
            if total > 0:
                det = " y ".join([f"{v} de {k}" for k, v in resumen.items()])
                lineas.append(f"Instalación de {total} luminaria(s) de alumbrado público ({det}).")

    # ==== Párrafo final ====
    descripcion_auto = "<br/>".join([f"{i + 1}. {l}" for i, l in enumerate(lineas)])
    cuerpo_desc = (descripcion_manual + "<br/><br/>" + descripcion_auto) if descripcion_manual else descripcion_auto

    elems.append(Paragraph("<b>Descripción general del Proyecto:</b>", styleN))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(cuerpo_desc, styleN))
    elems.append(Spacer(1, 18))

    return elems
