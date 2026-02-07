# -*- coding: utf-8 -*-
# interfaz/exportacion.py

import re
from typing import List, Dict

import numpy as _np
import pandas as pd
import streamlit as st

from servicios.calculo_materiales import calcular_materiales
from exportadores.pdf_exportador import generar_pdfs
import traceback

# =============================================================================
# Regex precompiladas
# =============================================================================
_RE_SPLIT = re.compile(r"[+,;\n\r]+")   # incluye saltos de línea
_RE_SANIT = re.compile(r"[^A-Z0-9\-\.]")

COLUMNAS_ESTRUCTURAS = [
    "Poste", "Primario", "Secundario", "Retenidas",
    "Conexiones a tierra", "Transformadores", "Luminarias"
]

# =============================================================================
# Utils de saneo 1-D (blindaje definitivo para groupby)
# =============================================================================
def _aplanar_columnas(df: pd.DataFrame) -> pd.DataFrame:
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

def _hacer_columnas_unicas(df: pd.DataFrame) -> pd.DataFrame:
    """Hace únicos los nombres de columna agregando sufijos .1, .2, ... cuando se repiten."""
    cols = list(map(str, df.columns))
    vistos: Dict[str, int] = {}
    nuevas: List[str] = []
    for c in cols:
        if c not in vistos:
            vistos[c] = 0
            nuevas.append(c)
        else:
            vistos[c] += 1
            nuevas.append(f"{c}.{vistos[c]}")
    out = df.copy()
    out.columns = nuevas
    return out

def _valor_a_texto_plano(x) -> str:
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

def _a_entero_seguro(v) -> int:
    try:
        iv = int(float(v))
        return iv if iv >= 0 else 0
    except Exception:
        return 0

def forzar_expandido_para_groupby(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve SIEMPRE un DataFrame NUEVO y 1-D con columnas EXACTAS:
    ['Punto','codigodeestructura','cantidad'] listo para groupby.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["Punto", "codigodeestructura", "cantidad"])

    df = _aplanar_columnas(df)
    df = _hacer_columnas_unicas(df).copy()

    # Asegura columnas requeridas
    if "Punto" not in df.columns:
        df["Punto"] = ""

    if "codigodeestructura" not in df.columns:
        if "Estructura" in df.columns:
            df["codigodeestructura"] = df["Estructura"]
        else:
            df["codigodeestructura"] = ""

    if "cantidad" not in df.columns:
        if "Cantidad" in df.columns:
            df["cantidad"] = df["Cantidad"]
        else:
            df["cantidad"] = 1

    p = df["Punto"].map(_valor_a_texto_plano).map(str).str.strip()
    c = df["codigodeestructura"].map(_valor_a_texto_plano).map(str).str.strip()
    c = c.str.replace(r"\s*\([^)]*\)\s*$", "", regex=True).str.strip()  # quita "(E)" etc al final
    q = df["cantidad"].map(_a_entero_seguro).astype(int)

    mask = (c != "") & (q > 0)
    p, c, q = p[mask], c[mask], q[mask]

    out = pd.DataFrame(
        {"Punto": _np.asarray(p.values, dtype=object),
         "codigodeestructura": _np.asarray(c.values, dtype=object),
         "cantidad": _np.asarray(q.values, dtype=_np.int64)},
        columns=["Punto", "codigodeestructura", "cantidad"]
    )
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
    Devuelve SIEMPRE un DF LARGO con columnas:
      ['Punto', 'codigodeestructura', 'cantidad']

    - Si ya viene largo (acepta variantes: 'codigodeestructura' o 'CodigoEstructura'):
      limpia, normaliza y agrupa.
    - Si viene ancho: construye lista desde COLUMNAS_ESTRUCTURAS, explode, limpia y agrupa.
    """
    cols_out = ["Punto", "codigodeestructura", "cantidad"]

    # Contrato vacío
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=cols_out)

    # Copia y soportar variantes típicas del UI
    base = df.copy()
    base = base.rename(columns={
        "CodigoEstructura": "codigodeestructura",
        "CódigoEstructura": "codigodeestructura",
        "Cantidad": "cantidad",
    })

    # --- Caso 1: ya viene LARGO ---
    if "codigodeestructura" in base.columns:
        if "Punto" not in base.columns:
            base["Punto"] = ""
        if "cantidad" not in base.columns:
            base["cantidad"] = 1

        base["Punto"] = base["Punto"].astype(str).str.strip()
        base["codigodeestructura"] = base["codigodeestructura"].astype(str).str.strip().str.upper()

        # quitar vacíos
        base = base[base["codigodeestructura"].ne("")]

        # cantidad segura
        base["cantidad"] = pd.to_numeric(base["cantidad"], errors="coerce").fillna(1).astype(int)
        base = base[base["cantidad"] > 0]

        # dedupe por punto+estructura
        base = (
            base.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
            .sum()
        )
        return base[cols_out]

    # --- Caso 2: viene ANCHO ---
    df2 = df.copy()

    if "Punto" not in df2.columns:
        df2["Punto"] = ""

    df2["Estructura"] = df2.apply(
        lambda fila: sum((_limpiar_listado(fila.get(c, "")) for c in COLUMNAS_ESTRUCTURAS), []),
        axis=1
    )

    df2 = df2.explode("Estructura", ignore_index=True)
    df2 = df2[df2["Estructura"].notna() & (df2["Estructura"].astype(str).str.strip() != "")]
    df2["Estructura"] = df2["Estructura"].astype(str).str.strip().str.upper()

    df2.rename(columns={"Estructura": "codigodeestructura"}, inplace=True)
    df2["cantidad"] = 1

    df2 = (
        df2.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )

    return df2[cols_out]



# =============================================================================
# UI de conteo rápido
# =============================================================================
def _vista_previa_conteo(df_expandido: pd.DataFrame) -> None:
    df_expandido = forzar_expandido_para_groupby(df_expandido)
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

# =============================================================================
# Sección FINALIZAR: calcula y guarda en session_state (NO exporta)
# =============================================================================
def seccion_finalizar_calculo(df: pd.DataFrame) -> None:
    st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")

    if df is None or df.empty:
        st.info("⚠️ No hay estructuras cargadas.")
        return

    with st.form("form_finalizar_calculo"):
        ejecutar = st.form_submit_button("✅ Finalizar Cálculo")

    if not ejecutar:
        if st.session_state.get("resultado_calculo"):
            st.success("✅ Ya hay resultados calculados. Puedes ir a Exportación.")
        else:
            st.caption("Presiona el botón para calcular materiales.")
        return

    try:
        # =============================================================
        # 1) Construir df_estructuras (LARGO) sin doble expansión
        # =============================================================
        cols = set(map(str, df.columns))
        if {"Punto", "codigodeestructura", "cantidad"}.issubset(cols):
            df_expandido = df.copy()
        else:
            df_expandido = _expandir_estructuras(df)

        # ✅ Normalizar nombres de columnas (soporta variantes del UI)
        df_expandido = df_expandido.rename(columns={
            "CodigoEstructura": "codigodeestructura",
            "CódigoEstructura": "codigodeestructura",
            "Cantidad": "cantidad",
        })

        df_expandido = forzar_expandido_para_groupby(df_expandido)

        # =============================================================
        # 1.1) Normalización dura (evita que limpieza interna deje 0 filas)
        # =============================================================
        if "Punto" in df_expandido.columns:
            df_expandido["Punto"] = df_expandido["Punto"].astype(str).str.strip()

        if "codigodeestructura" in df_expandido.columns:
            df_expandido["codigodeestructura"] = (
                df_expandido["codigodeestructura"]
                .astype(str)
                .str.replace("\u00a0", " ", regex=False)  # NBSP
                .str.strip()
            )
            # Quitar filas sin código
            df_expandido = df_expandido[df_expandido["codigodeestructura"].ne("")]

        if "cantidad" in df_expandido.columns:
            df_expandido["cantidad"] = (
                pd.to_numeric(df_expandido["cantidad"], errors="coerce")
                .fillna(1)
                .astype(int)
            )
            df_expandido = df_expandido[df_expandido["cantidad"] > 0]

        if df_expandido.empty:
            st.error("❌ Después de normalizar, no quedaron estructuras válidas (código/cantidad).")
            st.write("DEBUG df (entrada) shape:", df.shape)
            st.write("DEBUG df (entrada) cols:", list(df.columns))
            st.write("DEBUG df (entrada) head:", df.head(30))
            st.stop()

        # Guardar contrato definitivo
        st.session_state["df_estructuras"] = df_expandido

        # =============================================================
        # 2) Sincronizar materiales extra
        # =============================================================
        st.session_state.setdefault("datos_proyecto", {})
        if st.session_state.get("materiales_extra"):
            st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
                st.session_state["materiales_extra"]
            )
        else:
            st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
                columns=["Materiales", "Unidad", "Cantidad"]
            )

        # =============================================================
        # 3) Ruta de materiales
        # =============================================================
        ruta_materiales = st.session_state.get("ruta_datos_materiales")
        if not ruta_materiales:
            raise ValueError(
                "No está definida la ruta del archivo de materiales (ruta_datos_materiales)."
            )

        # =============================================================
        # 4) Cables (si existen)
        # =============================================================
        df_cables = st.session_state.get("cables_proyecto_df")

        # Debug útil
        st.write("DEBUG df_expandido shape:", df_expandido.shape)
        st.write("DEBUG df_expandido cols:", list(df_expandido.columns))
        st.write("DEBUG df_expandido head:", df_expandido.head(10))

        # =============================================================
        # 5) Calcular materiales
        # =============================================================
        resultado = calcular_materiales(
            estructuras_df=df_expandido,
            archivo_materiales=ruta_materiales,
            datos_proyecto=st.session_state.get("datos_proyecto", {}),
            df_cables=df_cables,
        )

        st.session_state["resultado_calculo"] = resultado
        st.session_state["calculo_finalizado"] = True
        st.session_state.pop("pdfs_generados", None)

        st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")

    except Exception as e:
        st.session_state["calculo_finalizado"] = False
        st.error(f"❌ Error al calcular: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        st.stop()


# =============================================================================
# Sección EXPORTACIÓN: SOLO genera PDFs desde resultado_calculo (NO recalcula)
# =============================================================================
def seccion_exportacion(
    df: pd.DataFrame,
    modo_carga: str,
    ruta_estructuras: str | None,
    ruta_datos_materiales: str
) -> None:
    st.subheader("6. 📂 Exportación de Reportes")
    # ✅ Parche: asegurar que "Finalizar" encuentre la ruta sin tocar app.py
    if isinstance(ruta_datos_materiales, str) and ruta_datos_materiales.strip():
        st.session_state["ruta_datos_materiales"] = ruta_datos_materiales.strip()

    resultado = st.session_state.get("resultado_calculo")
    if not resultado:
        st.warning("⚠️ Primero ve a la sección **Finalizar** y ejecuta el cálculo.")
        return

    df_prev = st.session_state.get("df_estructuras")
    if isinstance(df_prev, pd.DataFrame) and not df_prev.empty:
        _vista_previa_conteo(df_prev)
    else:
        df_expandido = forzar_expandido_para_groupby(_expandir_estructuras(df))
        _vista_previa_conteo(df_expandido)

    with st.form("form_generar_pdfs"):
        membrete_pdf = st.selectbox(
        "Membrete para los PDFs",
        ["SMART", "ENEE"],
        index=0 if st.session_state.get("membrete_pdf", "SMART") == "SMART" else 1,
    )
    st.session_state["membrete_pdf"] = membrete_pdf

        generar = st.form_submit_button("📥 Generar Reportes PDF")

    if generar:
        try:
            with st.spinner("⏳ Generando reportes, por favor espere..."):
                membrete_pdf = st.session_state.get("membrete_pdf", "SMART")
                pdfs = generar_pdfs(resultado, membrete_pdf=membrete_pdf)
            st.session_state["pdfs_generados"] = pdfs
            st.success("✅ Reportes generados correctamente")
        except Exception as e:
            st.error(f"❌ Error al generar PDFs: {type(e).__name__}: {e}")
            return

    pdfs = st.session_state.get("pdfs_generados")
    if not pdfs:
        st.info("Presiona **Generar Reportes PDF** para preparar las descargas.")
        return

    st.markdown("### 📥 Descarga de Reportes Generados")

    if pdfs.get("materiales"):
        st.download_button(
            "📄 Descargar PDF de Materiales",
            pdfs["materiales"],
            "Resumen_Materiales.pdf",
            "application/pdf",
            key="dl_mat"
        )
    if pdfs.get("estructuras_global"):
        st.download_button(
            "📄 Descargar PDF de Estructuras (Global)",
            pdfs["estructuras_global"],
            "Resumen_Estructuras.pdf",
            "application/pdf",
            key="dl_estr_glob"
        )
    if pdfs.get("estructuras_por_punto"):
        st.download_button(
            "📄 Descargar PDF de Estructuras por Punto",
            pdfs["estructuras_por_punto"],
            "Estructuras_Por_Punto.pdf",
            "application/pdf",
            key="dl_estr_punto"
        )
    if pdfs.get("materiales_por_punto"):
        st.download_button(
            "📄 Descargar PDF de Materiales por Punto",
            pdfs["materiales_por_punto"],
            "Materiales_Por_Punto.pdf",
            "application/pdf",
            key="dl_mat_punto"
        )
    if pdfs.get("completo"):
        st.download_button(
            "📄 Descargar Informe Completo",
            pdfs["completo"],
            "Informe_Completo.pdf",
            "application/pdf",
            key="dl_full"
        )
