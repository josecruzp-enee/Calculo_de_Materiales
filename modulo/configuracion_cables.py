# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Sección Streamlit para gestionar tramos de cable como TABLA editable.
Guarda en:
- st.session_state["cables_proyecto_df"]  (DataFrame)
- st.session_state["cables_proyecto"]     (lista de dicts)
- st.session_state["datos_proyecto"]["cables_proyecto"] (para PDF)

No se usan variables globales (solo imports).
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

# ReportLab (solo si generas PDF)
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# =========================
# Catálogos (getters)
# =========================
def get_tipos() -> list[str]:
    return ["MT", "BT", "N", "HP", "Retenida"]


def get_calibres() -> dict[str, list[str]]:
    return {
        "MT": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR", "266.8 MCM", "336 MCM"],
        "BT": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP"],
        "N":  ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ASCR"],
        "HP": ["2 WP", "1/0 WP", "2/0 WP"],
        "Retenida": ["1/4", "5/8", "3/4"],
    }


def get_configs_por_tipo() -> dict[str, list[str]]:
    return {
        "MT": ["1F", "2F", "3F"],
        "BT": ["1F", "2F", "3F"],
        "N":  ["N"],
        "HP": ["1F+N", "2F"],
        "Retenida": ["Única"],
    }


def get_configs_union() -> list[str]:
    # Unión para el editor (la validación real se hace por tipo)
    return ["Única", "N", "1F", "1F+N", "2F", "3F"]


def get_calibres_union() -> list[str]:
    cal = get_calibres()
    dedup = list(dict.fromkeys(c for lista in cal.values() for c in lista))
    return dedup


def get_mapa_legacy_tipos() -> dict[str, str]:
    # Para normalizar etiquetas antiguas a las actuales
    return {
        "Primario": "MT",
        "Secundario": "BT",
        "Neutro": "N",
        "Piloto": "HP",
        "Retenidas": "Retenida",
    }


# =========================
# Utilidades puras
# =========================
def conductores_de(cfg: str) -> int:
    """Número de conductores para calcular 'Total Cable (m)' según configuración."""
    if not isinstance(cfg, str):
        return 1
    c = cfg.strip().upper()
    if c in ("ÚNICA", "N", "1F"):
        return 1
    if c in ("1F+N", "2F"):
        return 2
    if c == "3F":
        return 3
    return 1


# =========================
# Estado y normalización
# =========================
def inicializar_df_cables_en_estado() -> None:
    """Crea en session_state un DataFrame vacío con columnas esperadas, si no existe."""
    if "cables_proyecto_df" not in st.session_state:
        st.session_state["cables_proyecto_df"] = pd.DataFrame(
            columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]
        )


def normalizar_tipos_existentes() -> None:
    """Normaliza etiquetas antiguas a las nuevas en todos los orígenes de estado."""
    m = get_mapa_legacy_tipos()

    df_prev = st.session_state.get("cables_proyecto_df")
    if isinstance(df_prev, pd.DataFrame) and not df_prev.empty and "Tipo" in df_prev.columns:
        st.session_state["cables_proyecto_df"]["Tipo"] = df_prev["Tipo"].replace(m)

    lista_prev = st.session_state.get("cables_proyecto")
    if isinstance(lista_prev, list) and lista_prev:
        for fila in lista_prev:
            if isinstance(fila, dict) and "Tipo" in fila and fila["Tipo"] in m:
                fila["Tipo"] = m[fila["Tipo"]]
        if df_prev is None or (hasattr(df_prev, "empty") and df_prev.empty):
            st.session_state["cables_proyecto_df"] = pd.DataFrame(lista_prev)

    datos = st.session_state.get("datos_proyecto", {})
    cp_dp = datos.get("cables_proyecto")
    if isinstance(cp_dp, list):
        for fila in cp_dp:
            if isinstance(fila, dict) and "Tipo" in fila and fila["Tipo"] in m:
                fila["Tipo"] = m[fila["Tipo"]]
        if st.session_state.get("cables_proyecto_df") is None or st.session_state["cables_proyecto_df"].empty:
            st.session_state["cables_proyecto_df"] = pd.DataFrame(cp_dp)


def asegurar_fila_inicial() -> None:
    """Si el DF está vacío, agrega una fila guía inicial."""
    df = st.session_state["cables_proyecto_df"]
    if df.empty:
        st.session_state["cables_proyecto_df"] = pd.DataFrame([{
            "Tipo": "MT", "Configuración": "1F", "Calibre": "1/0 ASCR",
            "Longitud (m)": 0.0, "Total Cable (m)": 0.0
        }])


# =========================
# Editor y validación
# =========================
def construir_editor_tabla() -> pd.DataFrame:
    """Muestra el editor de tabla y devuelve el DataFrame editado (sin validar por tipo)."""
    st.caption("Agrega/edita filas; el **Total** se calcula automáticamente según la configuración.")

    edited_df = st.data_editor(
        st.session_state["cables_proyecto_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn(
                "Tipo", options=get_tipos(), required=True, width="small",
                help="MT, BT, N (neutro), HP (piloto), Retenida",
            ),
            "Configuración": st.column_config.SelectboxColumn(
                "Configuración", options=get_configs_union(), required=True, width="small",
                help="MT/BT: 1F/2F/3F · N: N · HP: 1F+N/2F · Retenida: Única",
            ),
            "Calibre": st.column_config.SelectboxColumn(
                "Calibre", options=get_calibres_union(), required=True, width="medium",
            ),
            "Longitud (m)": st.column_config.NumberColumn(
                "Longitud (m)", min_value=0.0, step=10.0, format="%.2f",
            ),
            "Total Cable (m)": st.column_config.NumberColumn(
                "Total Cable (m)", disabled=True, format="%.2f",
                help="Longitud × Nº de conductores (autocalculado)",
            ),
        },
        hide_index=True,
    )
    return edited_df


def procesar_filas_cables(edited_df: pd.DataFrame) -> pd.DataFrame:
    """Valida por tipo, ajusta configuración/calibre y calcula totales. Devuelve DataFrame limpio."""
    configs_por_tipo = get_configs_por_tipo()
    calibres_por_tipo = get_calibres()
    calibres_union = get_calibres_union()

    processed_rows = []
    for _, row in edited_df.fillna("").iterrows():
        if not row.get("Tipo"):
            continue

        tipo = str(row["Tipo"]).strip()
        cfg_permitidas = configs_por_tipo.get(tipo, ["Única"])

        cfg = str(row["Configuración"]).strip() if row.get("Configuración") else cfg_permitidas[0]
        if cfg not in cfg_permitidas:
            cfg = cfg_permitidas[0]

        cal_list = calibres_por_tipo.get(tipo, calibres_union)
        cal = str(row["Calibre"]).strip() if row.get("Calibre") else (cal_list[0] if cal_list else "")
        if cal not in cal_list and cal_list:
            cal = cal_list[0]

        try:
            L = float(row.get("Longitud (m)", 0.0))
        except Exception:
            L = 0.0

        total = L * conductores_de(cfg)

        processed_rows.append({
            "Tipo": tipo,
            "Configuración": cfg,
            "Calibre": cal,
            "Longitud (m)": L,
            "Total Cable (m)": total,
        })

    return pd.DataFrame(processed_rows, columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])


def persistir_cables_en_estado(df_out: pd.DataFrame) -> None:
    """Persiste df_out y su lista equivalente en session_state, incluyendo datos_proyecto."""
    st.session_state["cables_proyecto_df"] = df_out.copy()
    lista = df_out.to_dict(orient="records")
    st.session_state["cables_proyecto"] = lista
    st.session_state.setdefault("datos_proyecto", {})
    st.session_state["datos_proyecto"]["cables_proyecto"] = lista


def mostrar_total_global(df_out: pd.DataFrame) -> None:
    """Muestra el total global de cable si hay datos."""
    if not df_out.empty:
        total_global = df_out["Total Cable (m)"].sum()
        st.markdown(f"**🧮 Total Global de Cable:** {total_global:,.2f} m")


# =========================
# 1️⃣ Sección Streamlit (tabla)
# =========================
def seccion_cables():
    """Interfaz Streamlit como TABLA editable para configurar tramos de cable."""
    st.markdown("### 2️⃣ ⚡ Configuración y calibres de conductores (tabla)")

    inicializar_df_cables_en_estado()
    normalizar_tipos_existentes()
    asegurar_fila_inicial()

    edited_df = construir_editor_tabla()
    df_out = procesar_filas_cables(edited_df)

    persistir_cables_en_estado(df_out)
    mostrar_total_global(df_out)

    # Contrato actual: retorna lista de dicts
    return st.session_state["cables_proyecto"]


# =========================
# 2️⃣ Tabla para PDF (ReportLab)
# =========================
def tabla_cables_pdf(datos_proyecto):
    """
    Genera elementos ReportLab (tabla + totales) para insertar en el PDF.
    Lee de datos_proyecto["cables_proyecto"] y, si existe, refleja lo último en session_state.
    """
    elems = []
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading2"]

    # Prioriza versión en memoria si existe
    if st.session_state.get("cables_proyecto"):
        datos_proyecto = dict(datos_proyecto or {})
        datos_proyecto["cables_proyecto"] = st.session_state["cables_proyecto"]

    filas = (datos_proyecto or {}).get("cables_proyecto", [])
    if not filas:
        return elems

    df = pd.DataFrame(filas, columns=["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"])
    if df.empty:
        return elems

    elems.append(Spacer(1, 0.2 * inch))
    elems.append(Paragraph("⚡ Configuración y Calibres de Conductores", styleH))
    elems.append(Spacer(1, 0.1 * inch))

    data = [["Tipo", "Configuración", "Calibre", "Longitud (m)", "Total Cable (m)"]]
    for _, row in df.iterrows():
        data.append([
            str(row.get("Tipo", "")),
            str(row.get("Configuración", "")),
            str(row.get("Calibre", "")),
            f"{float(row.get('Longitud (m)', 0.0)):.2f}",
            f"{float(row.get('Total Cable (m)', 0.0)):.2f}",
        ])

    tabla = Table(data, colWidths=[1.2 * inch] * 5)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 0.15 * inch))

    total_global = df["Total Cable (m)"].sum()
    elems.append(Paragraph(f"🧮 <b>Total Global de Cable:</b> {total_global:,.2f} m", styleN))
    elems.append(Spacer(1, 0.25 * inch))
    return elems
