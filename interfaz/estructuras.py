# interfaz/estructuras.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
from typing import Optional, Tuple, List

import pandas as pd
import streamlit as st

# =============================================================================
# Configuración base y utilidades seguras
# =============================================================================

# Esquema mínimo esperado por el resto de la app
COLUMNAS_BASE: List[str] = [
    "Punto",
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]

def _normalizar_columnas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    """Asegura que existan todas las columnas base y devuelve df ordenado."""
    df = df.copy()
    for c in columnas:
        if c not in df.columns:
            df[c] = ""
    return df[columnas]

def _parsear_texto_a_df(texto: str, columnas: List[str]) -> pd.DataFrame:
    """Convierte texto pegado (CSV/TSV/; or |) en DataFrame y normaliza columnas."""
    txt = (texto or "").strip()
    if not txt:
        return pd.DataFrame(columns=columnas)

    df = None
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            break
        except Exception:
            df = None
    if df is None:
        try:
            df = pd.read_csv(io.StringIO(txt), delim_whitespace=True)
        except Exception:
            return pd.DataFrame(columns=columnas)
    return _normalizar_columnas(df, columnas)

# =============================================================================
# Modo: Excel
# =============================================================================

def cargar_desde_excel() -> Tuple[pd.DataFrame | None, str | None]:
    """
    Carga un Excel con estructuras.
    Devuelve (df, ruta/nombre). Si el usuario no sube nada, (None, None).
    """
    archivo = st.file_uploader("Archivo de estructuras (.xlsx)", type=["xlsx"], key="upl_estructuras")
    if not archivo:
        return None, None

    nombre = getattr(archivo, "name", "estructura_lista.xlsx")
    try:
        df = pd.read_excel(archivo)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None, nombre

    df = _normalizar_columnas(df, COLUMNAS_BASE)
    st.success(f"✅ Cargadas {len(df)} filas desde {nombre}")
    return df, nombre

# =============================================================================
# Modo: Pegar tabla (CSV/TSV)
# =============================================================================

def pegar_tabla() -> Tuple[pd.DataFrame | None, str | None]:
    """
    Permite pegar una tabla CSV/TSV en un TextArea.
    Devuelve (df, 'PEGA/TEXTO') si hay contenido; (None, None) si vacío.
    """
    texto_pegado = st.text_area("Pega aquí tu tabla (CSV/TSV)", height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return None, None

    df = _parsear_texto_a_df(texto_pegado, COLUMNAS_BASE)
    st.success(f"✅ Tabla cargada con {len(df)} filas")
    return df, "PEGA/TEXTO"

# =============================================================================
# Modo: Listas (UI simple para construir la tabla en sesión)
# =============================================================================

def _ensure_df_sesion():
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

def _form_point_editor():
    """
    Pequeña UI para construir/editar filas de COLUMNAS_BASE y guardarlas en sesión.
    """
    _ensure_df_sesion()
    df_actual = st.session_state["df_puntos"]

    st.subheader("🏗️ Estructuras del Proyecto (Listas)")
    st.caption("Completa los campos y usa “Agregar/Actualizar punto” para construir la tabla.")

    with st.form("frm_punto"):
        c1, c2 = st.columns([1, 2])
        with c1:
            punto = st.text_input("Punto", value="Punto 1")
        with c2:
            st.write(" ")

        colA, colB = st.columns(2)
        with colA:
            poste = st.text_input("Poste", value="")
            primario = st.text_input("Primario", value="")
            secundario = st.text_input("Secundario", value="")
        with colB:
            retenidas = st.text_input("Retenidas", value="")
            ctierra = st.text_input("Conexiones a tierra", value="")
            trafo = st.text_input("Transformadores", value="")

        agregado = st.form_submit_button("💾 Agregar / Actualizar punto", type="primary")
        if agregado:
            fila = {
                "Punto": punto.strip(),
                "Poste": poste.strip(),
                "Primario": primario.strip(),
                "Secundario": secundario.strip(),
                "Retenidas": retenidas.strip(),
                "Conexiones a tierra": ctierra.strip(),
                "Transformadores": trafo.strip(),
            }
            base = st.session_state["df_puntos"]
            # Reemplaza si ya existe el punto
            if not base.empty and fila["Punto"] in base["Punto"].values:
                base = base[base["Punto"] != fila["Punto"]]
            st.session_state["df_puntos"] = pd.concat([base, pd.DataFrame([fila])], ignore_index=True)
            st.success(f"✅ Guardado {fila['Punto']}")

    # Barra de acciones sobre la tabla
    df = st.session_state["df_puntos"]
    if not df.empty:
        st.markdown("---")
        st.markdown("#### 📑 Tabla de puntos")
        st.dataframe(df.sort_values(by="Punto"), use_container_width=True, hide_index=True)

        colx, coly, colz = st.columns(3)
        with colx:
            if st.button("🧹 Limpiar todo", use_container_width=True):
                st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
                st.success("✅ Tabla limpiada")
        with coly:
            if not df.empty:
                p_del = st.selectbox("❌ Punto a borrar", df["Punto"].tolist(), key="sel_borrar_punto")
                if st.button("Borrar punto", use_container_width=True):
                    st.session_state["df_puntos"] = df[df["Punto"] != p_del].reset_index(drop=True)
                    st.success(f"✅ Eliminado {p_del}")
        with colz:
            if not df.empty:
                st.download_button(
                    "⬇️ Descargar CSV",
                    df.sort_values(by="Punto").to_csv(index=False).encode("utf-8"),
                    file_name="estructuras_puntos.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

def listas_desplegables() -> Tuple[pd.DataFrame | None, str | None]:
    """
    Renderiza la UI simple de Listas y devuelve (df, 'UI/LISTAS') si hay datos;
    si no hay filas aún, (None, None).
    """
    _form_point_editor()
    df = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))
    if isinstance(df, pd.DataFrame) and not df.empty:
        df = _normalizar_columnas(df, COLUMNAS_BASE)
        return df, "UI/LISTAS"
    return None, None

# =============================================================================
# Función pública llamada por app.py
# =============================================================================

def seccion_entrada_estructuras(modo_carga: str) -> Tuple[pd.DataFrame | None, str | None]:
    """
    Devuelve siempre una tupla (df_estructuras, ruta_estructuras) según el modo:
      - "Excel"  -> carga desde file_uploader
      - "Pegar"  -> parsea texto CSV/TSV
      - otro     -> UI de Listas para construir df en sesión
    """
    modo = (modo_carga or "").strip().lower()

    if modo == "excel":
        return cargar_desde_excel()

    if modo == "pegar":
        return pegar_tabla()

    # Cualquier otro valor cae a la UI de listas
    return listas_desplegables()
