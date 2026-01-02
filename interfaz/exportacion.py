# -*- coding: utf-8 -*-
# interfaz/exportacion.py

import re
from typing import List, Dict, Tuple, Optional

import numpy as _np
import pandas as pd
import streamlit as st

from modulo.procesar_materiales import procesar_materiales

# =============================================================================
# Regex precompiladas
# =============================================================================
_RE_SPLIT = re.compile(r"[+,;\n\r]+")   # incluye saltos de línea
_RE_SANIT = re.compile(r"[^A-Z0-9\-\.]")

COLUMNAS_ESTRUCTURAS = ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores","Luminarias"]

# =============================================================================
# Utils de saneo 1-D (blindaje definitivo para groupby)
# =============================================================================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas MultiIndex/Tuplas a texto plano 'a / b / c' y normaliza espacios."""
    flat = []
    for c in df.columns:
        if isinstance(c, tuple):
            flat.append(" / ".join(map(str, c)))
        else:
            flat.append(str(c))
    out = df.copy()
    out.columns = [s.strip() for s in flat]
    return out

def _dedup_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Hace únicos los nombres de columna agregando sufijos .1, .2, ... cuando se repiten."""
    cols = list(map(str, df.columns))
    seen: Dict[str, int] = {}
    newcols: List[str] = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            newcols.append(c)
        else:
            seen[c] += 1
            newcols.append(f"{c}.{seen[c]}")
    out = df.copy()
    out.columns = newcols
    return out

def _scalarize_cell(x) -> str:
    """Convierte cualquier valor no 1-D a string plano."""
    if isinstance(x, (list, tuple, set)):
        return ", ".join(map(str, x))
    if isinstance(x, _np.ndarray):
        return ", ".join(map(str, x.tolist()))
    if isinstance(x, (pd.Series, pd.DataFrame)):
        try:
            return ", ".join(map(str, pd.Series(x).squeeze().tolist()))
        except Exception:
            return str(x)
    if x is None:
        return ""
    return str(x)

def _to_int_safe(v) -> int:
    try:
        iv = int(float(v))
        return iv if iv >= 0 else 0
    except Exception:
        return 0

def coerce_expandido_para_groupby(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve SIEMPRE un DataFrame NUEVO y 1-D con columnas EXACTAS:
    ['Punto','codigodeestructura','cantidad'] listo para groupby.
    - flatten + dedup de nombres
    - asegura columnas mínimas
    - scalariza celdas
    - limpia sufijos de códigos '(...)' al final
    - cantidad → int (si no existe, usa 1 por fila)
    - reconstrucción desde arrays 1-D
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = _flatten_columns(df)
    df = _dedup_columns(df).copy()

    # Asegura columnas requeridas; si 'cantidad' no existe, la creamos = 1
    if "Punto" not in df.columns:
        df["Punto"] = ""
    if "codigodeestructura" not in df.columns:
        # si no existe, intenta derivarla de 'Estructura'
        if "Estructura" in df.columns:
            df["codigodeestructura"] = df["Estructura"]
        else:
            df["codigodeestructura"] = ""
    if "cantidad" not in df.columns:
        # si hay 'Cantidad', úsala; si no, será 1
        if "Cantidad" in df.columns:
            df["cantidad"] = df["Cantidad"]
        else:
            df["cantidad"] = 1

    p = df["Punto"].map(_scalarize_cell).map(str).str.strip()
    c = df["codigodeestructura"].map(_scalarize_cell).map(str).str.strip()
    # limpia sufijos "(E)" "(P)" "(R)" o cualquier paréntesis final
    c = c.str.replace(r"\s*\([^)]*\)\s*$", "", regex=True).str.strip()
    q = df["cantidad"].map(_to_int_safe).astype(int)

    mask = (c != "") & (q > 0)
    p, c, q = p[mask], c[mask], q[mask]

    out = pd.DataFrame({
        "Punto": _np.asarray(p.values, dtype=object),
        "codigodeestructura": _np.asarray(c.values, dtype=object),
        "cantidad": _np.asarray(q.values, dtype=_np.int64),
    }, columns=["Punto", "codigodeestructura", "cantidad"])

    return out.reset_index(drop=True)

# =============================================================================
# Helpers de expansión (si el DF de entrada está en ANCHO)
# =============================================================================
def _limpiar_listado(valor: str) -> list[str]:
    """Normaliza una celda de estructuras en lista limpia sin duplicados preservando orden."""
    if not valor or str(valor).strip().lower() == "seleccionar estructura":
        return []
    out = []
    for p in _RE_SPLIT.split(str(valor)):
        t = _RE_SANIT.sub("", p.strip().upper())
        if t and t not in {"SELECCIONAR", "ESTRUCTURA", "N/A", "NONE"}:
            out.append(t)
    vistos, res = set(), []
    for x in out:
        if x not in vistos:
            res.append(x)
            vistos.add(x)
    return res

def _expandir_estructuras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Si 'codigodeestructura' existe -> respeta como LARGO.
    Si no, crea df_expandido con una fila por (Punto, codigodeestructura) desde columnas ANCHO.
    """
    if "codigodeestructura" in df.columns:
        # ya es LARGO o casi; devuelve copia para coerce posterior
        base = df.copy()
        # si no hay 'cantidad', la agregamos en 1 para cada fila
        if "cantidad" not in base.columns:
            base["cantidad"] = 1
        return base

    # Caso ANCHO → construir listado por fila
    df2 = df.copy()
    df2["Estructura"] = df2.apply(
        lambda fila: sum((_limpiar_listado(fila.get(c, "")) for c in COLUMNAS_ESTRUCTURAS), []),
        axis=1
    )
    df2 = df2.explode("Estructura", ignore_index=True)
    df2 = df2[df2["Estructura"].notna() & (df2["Estructura"].astype(str).str.strip() != "")]
    df2["Estructura"] = df2["Estructura"].astype(str).str.strip().str.upper()
    df2.drop_duplicates(subset=["Punto", "Estructura"], inplace=True)
    df2.rename(columns={"Estructura": "codigodeestructura"}, inplace=True)
    df2["cantidad"] = 1
    return df2[["Punto", "codigodeestructura", "cantidad"]]

# =============================================================================
# UI de conteo rápido y sección final
# =============================================================================
def _preview_conteo(df_expandido: pd.DataFrame) -> None:
    # 🔒 Blindaje: garantizamos 1-D y columnas exactas
    df_expandido = coerce_expandido_para_groupby(df_expandido)

    # Conteo por punto y código
    conteo = (
        df_expandido
        .groupby(["Punto", "codigodeestructura"], dropna=False)["cantidad"]
        .sum()
        .reset_index()
        .rename(columns={"cantidad": "Cantidad"})
        .sort_values(["Punto", "codigodeestructura"])
    )
    st.caption("Conteo rápido de estructuras por punto:")
    st.dataframe(conteo, use_container_width=True, hide_index=True)

def seccion_finalizar_calculo(df: pd.DataFrame) -> None:
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo", key="btn_finalizar_calculo"):
            st.session_state["calculo_finalizado"] = True
            st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")

# =============================================================================
# Sección principal de exportación
# =============================================================================
def seccion_exportacion(
    df: pd.DataFrame,
    modo_carga: str,
    ruta_estructuras: str | None,
    ruta_datos_materiales: str
) -> None:
    """Exportación de reportes PDF/Excel. Sincroniza cables, expande estructuras y genera PDFs."""
    if df.empty or not st.session_state.get("calculo_finalizado", False):
        return

    st.subheader("6. 📂 Exportación de Reportes")

    # -------------------------------------------------------------------------
    # Función local para formatear la tensión (L-N / L-L)
    # -------------------------------------------------------------------------
    def _formato_tension(v_ll):
        """Convierte 13.8 -> '7.96 L-N / 13.8 L-L kV', 34.5 -> '19.90 L-N / 34.5 L-L kV'."""
        try:
            v_ll = float(v_ll)
            v_ln = v_ll / _np.sqrt(3)
            return f"{v_ln:.1f} L-N / {v_ll:g} L-L kV"
        except Exception:
            return str(v_ll)

    # 1) Sincronizar datos de cables a datos_proyecto (con defaults suaves)
    if "cables_proyecto" in st.session_state:
        # Asegurar que datos_proyecto exista
        st.session_state.setdefault("datos_proyecto", {})
        st.session_state["datos_proyecto"]["cables_proyecto"] = st.session_state["cables_proyecto"]

        datos_cables = st.session_state["cables_proyecto"]
        if isinstance(datos_cables, list) and len(datos_cables) > 0:
            datos_cables = datos_cables[0]
        elif not isinstance(datos_cables, dict):
            datos_cables = {}

        # Preferir la tensión del proyecto; si no, alguna que venga de cables; si no, 13.8
        datos_dp = st.session_state.get("datos_proyecto", {})
        tension_ll = (
            datos_dp.get("nivel_de_tension")
            or datos_dp.get("tension")
            or datos_cables.get("nivel_de_tension")
            or datos_cables.get("tension")
            or 13.8
        )

        # Guardar en datos_proyecto (crudo, para que generar_pdfs lo formatee si quiere)
        st.session_state["datos_proyecto"]["tension"] = tension_ll
        st.session_state["datos_proyecto"]["nivel_de_tension"] = tension_ll

        # Formatear para mostrar en la UI
        tension_fmt = _formato_tension(tension_ll)

        # Calibre MT
        calibre_mt = (
            datos_cables.get("calibre_mt")
            or datos_cables.get("conductor_mt")
            or datos_cables.get("Calibre")
            or "1/0 ASCR"
        )
        st.session_state["datos_proyecto"]["calibre_mt"] = calibre_mt

        # Mensaje en pantalla
        st.info(f"🔧 Nivel de Tensión: **{tension_fmt}**  |  Calibre MT: **{calibre_mt}**")

    # 2) Expandir estructuras (ANCHO → LARGO si hace falta)
    df_expandido = _expandir_estructuras(df)

    # 2.1) Coerción 1-D ANTES de cualquier uso
    df_expandido = coerce_expandido_para_groupby(df_expandido)

    # 2.2) Preview
    _preview_conteo(df_expandido)

    # 3) Materiales adicionales → DataFrame
    if st.session_state.get("materiales_extra"):
        st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
            st.session_state["materiales_extra"]
        )
    else:
        st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
            columns=["Materiales", "Unidad", "Cantidad"]
        )

    # 4) Generar reportes
    if st.button("📥 Generar Reportes PDF", key="btn_generar_pdfs"):
        try:
            with st.spinner("⏳ Generando reportes, por favor espere..."):
                resultados_pdf = procesar_materiales(
                    archivo_estructuras=ruta_estructuras,
                    archivo_materiales=ruta_datos_materiales,
                    estructuras_df=df_expandido,  # ← ya limpio y 1-D
                    datos_proyecto=st.session_state.get("datos_proyecto", {})
                )

            st.session_state["pdfs_generados"] = resultados_pdf
            st.success("✅ Reportes generados correctamente")

            if isinstance(resultados_pdf, dict):
                st.info(f"📄 PDFs generados: {list(resultados_pdf.keys())}")
            else:
                st.warning("⚠️ El módulo procesar_materiales no devolvió un diccionario válido.")
        except Exception as e:
            st.error(f"❌ Error al generar reportes: {e}")

    # 5) Descarga
    if "pdfs_generados" in st.session_state:
        pdfs = st.session_state["pdfs_generados"]
        st.markdown("### 📥 Descarga de Reportes Generados")
        if isinstance(pdfs, dict):
            if pdfs.get("materiales"):
                st.download_button(
                    "📄 Descargar PDF de Materiales",
                    pdfs["materiales"],
                    "Resumen_Materiales.pdf",
                    "application/pdf",
                    key="dl_mat",
                )
            if pdfs.get("estructuras_global"):
                st.download_button(
                    "📄 Descargar PDF de Estructuras (Global)",
                    pdfs["estructuras_global"],
                    "Resumen_Estructuras.pdf",
                    "application/pdf",
                    key="dl_estr_glob",
                )
            if pdfs.get("estructuras_por_punto"):
                st.download_button(
                    "📄 Descargar PDF de Estructuras por Punto",
                    pdfs["estructuras_por_punto"],
                    "Estructuras_Por_Punto.pdf",
                    "application/pdf",
                    key="dl_estr_punto",
                )
            if pdfs.get("materiales_por_punto"):
                st.download_button(
                    "📄 Descargar PDF de Materiales por Punto",
                    pdfs["materiales_por_punto"],
                    "Materiales_Por_Punto.pdf",
                    "application/pdf",
                    key="dl_mat_punto",
                )
            if pdfs.get("completo"):
                st.download_button(
                    "📄 Descargar Informe Completo",
                    pdfs["completo"],
                    "Informe_Completo.pdf",
                    "application/pdf",
                    key="dl_full",
                )

