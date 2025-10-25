# -*- coding: utf-8 -*-
# interfaz/estructuras.py

import time
import pandas as pd
import streamlit as st

from interfaz.base import COLUMNAS_BASE, resetear_desplegables
from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.entradas import cargar_estructuras_proyectadas


# ---------------------------------------------------------
#  Modo: Desde Excel
# ---------------------------------------------------------
def cargar_desde_excel():
    archivo_estructuras = st.file_uploader(
        "Archivo de estructuras", type=["xlsx"], key="upl_estructuras"
    )
    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
        try:
            df = cargar_estructuras_proyectadas(ruta_estructuras)
            st.success("✅ Hoja 'estructuras' leída correctamente")
            return df, ruta_estructuras
        except Exception as e:
            st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
    return pd.DataFrame(columns=COLUMNAS_BASE), None


# ---------------------------------------------------------
#  Modo: Pegar tabla
# ---------------------------------------------------------
def pegar_tabla():
    texto_pegado = st.text_area(
        "Pega aquí tu tabla CSV/tabulado", height=200, key="txt_pegar_tabla"
    )
    if texto_pegado:
        df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
        st.success(f"✅ Tabla cargada con {len(df)} filas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)


# ---------------------------------------------------------
#  Util: token para keys únicas de widgets
# ---------------------------------------------------------
def _ensure_key_token():
    """
    Crea/retorna un token único para prefijar keys de widgets y evitar
    que Streamlit recicle valores anteriores al editar un Punto.
    """
    if "keys_desplegables" not in st.session_state:
        st.session_state["keys_desplegables"] = {}
    if "token" not in st.session_state["keys_desplegables"]:
        st.session_state["keys_desplegables"]["token"] = str(int(time.time() * 1000))
    return st.session_state["keys_desplegables"]["token"]


# ---------------------------------------------------------
#  Modo: Listas desplegables
# ---------------------------------------------------------
def listas_desplegables():
    from modulo.desplegables import cargar_opciones, crear_desplegables
    opciones = cargar_opciones()

    st.subheader("3. 🏗️ Estructuras del Proyecto")

    # Si venimos de un rerun forzado, regenerar keys y limpiar el flag
    if st.session_state.get("reiniciar_desplegables", False):
        st.session_state["reiniciar_desplegables"] = False
        resetear_desplegables()
        try:
            st.rerun()
        except Exception as e:
            st.warning(f"No se pudo recargar automáticamente ({e})")

    # Data actual
    df_actual = st.session_state.get("df_puntos", pd.DataFrame(columns=COLUMNAS_BASE))
    if df_actual.empty:
        df_actual = pd.DataFrame(columns=COLUMNAS_BASE)
        st.session_state["df_puntos"] = df_actual
    puntos_existentes = df_actual["Punto"].unique().tolist()

    # Crear nuevo punto
    if st.button("🆕 Crear nuevo Punto"):
        nuevo_num = len(puntos_existentes) + 1
        st.session_state["punto_en_edicion"] = f"Punto {nuevo_num}"
        st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")
        resetear_desplegables()

    # Editor por punto
    if st.session_state.get("punto_en_edicion"):
        punto = st.session_state["punto_en_edicion"]
        st.markdown(f"### ✏️ Editando {punto}")

        # Prefijo único para las keys de los widgets
        token = _ensure_key_token()
        key_prefix = f"{punto}_{token}"

        # crear_desplegables puede ignorar key_prefix si no lo soporta; no pasa nada
        try:
            seleccion = crear_desplegables(opciones, key_prefix=key_prefix)
        except TypeError:
            # Versión antigua sin key_prefix
            seleccion = crear_desplegables(opciones)

        seleccion["Punto"] = punto

        st.markdown(
            "<hr style='border:0.5px solid #ddd; margin:0.7rem 0;'>",
            unsafe_allow_html=True,
        )

        # Por defecto: REEMPLAZAR completo (no concatenar)
        sumar_con_existente = st.toggle(
            "➕ Sumar con lo existente (+)",
            value=False,
            help="Si está desactivado, se REEMPLAZA completamente lo guardado en este Punto.",
            key=f"toggle_sumar_{key_prefix}",
        )

        if st.button(
            "💾 Guardar Estructura del Punto",
            type="primary",
            key=f"btn_guardar_estructura_{key_prefix}",
        ):
            # Si ya existía el punto, lo quitamos (en ambos modos)
            if punto in df_actual["Punto"].values:
                if sumar_con_existente:
                    # --- MODO SUMA: concatenar con lo que estaba ---
                    fila_existente = df_actual[df_actual["Punto"] == punto].iloc[0].to_dict()
                    for col in [
                        "Poste",
                        "Primario",
                        "Secundario",
                        "Retenidas",
                        "Conexiones a tierra",
                        "Transformadores",
                    ]:
                        anterior = str(fila_existente.get(col, "")).strip()
                        nuevo = str(seleccion.get(col, "")).strip()
                        if anterior and nuevo and anterior != nuevo:
                            seleccion[col] = f"{anterior} + {nuevo}"
                        elif anterior and not nuevo:
                            seleccion[col] = anterior

                # Remover fila previa para insertar la nueva versión
                df_actual = df_actual[df_actual["Punto"] != punto]

            # Insertar registro final (reemplazo total si toggle=Off)
            df_actual = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)

            # Ordenar por nº de Punto si aplica
            if "Punto" in df_actual.columns:
                try:
                    df_actual["orden"] = df_actual["Punto"].str.extract(r"(\d+)").astype(int)
                    df_actual = df_actual.sort_values("orden").drop(columns="orden")
                except Exception:
                    pass

            st.session_state["df_puntos"] = df_actual.reset_index(drop=True)

            st.success(
                f"✅ {punto} actualizado "
                + ("(**sumando** con lo existente)" if sumar_con_existente else "(**reemplazado**)")
            )

            # Clave: regenerar keys para no arrastrar valores viejos
            resetear_desplegables()
            st.session_state.pop("punto_en_edicion", None)
            st.session_state["reiniciar_desplegables"] = True
            try:
                st.rerun()
            except Exception as e:
                st.warning(f"No se pudo recargar automáticamente ({e})")

    # ===== Vista y acciones rápidas =====
    df = st.session_state["df_puntos"]
    if not df.empty:
        st.markdown("#### 📑 Vista de estructuras / materiales")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1.2])

        with col1:
            if st.button("🧹 Limpiar todo", key="btn_limpiar_todo"):
                st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
                st.session_state.pop("punto_en_edicion", None)
                resetear_desplegables()
                st.success("✅ Se limpiaron todas las estructuras/materiales")

        with col2:
            if df["Punto"].nunique() > 0:
                seleccionado = st.selectbox(
                    "📍 Punto a editar:",
                    df["Punto"].unique(),
                    key="select_editar_punto_fila",
                )
                if st.button("✏️ Editar Punto", key="btn_editar_punto_fila"):
                    st.session_state["punto_en_edicion"] = seleccionado
                    # Generar token nuevo para que los widgets no reciclen state
                    st.session_state["keys_desplegables"] = {"token": str(int(time.time() * 1000))}
                    resetear_desplegables()
                    try:
                        st.rerun()
                    except Exception as e:
                        st.warning(f"No se pudo recargar ({e})")

        with col3:
            punto_borrar = st.selectbox(
                "❌ Punto a borrar:",
                df["Punto"].unique(),
                key="select_borrar_punto_fila",
            )
            if st.button("Borrar Punto", key="btn_borrar_punto_fila"):
                st.session_state["df_puntos"] = df[df["Punto"] != punto_borrar].reset_index(drop=True)
                st.success(f"✅ Se eliminó {punto_borrar}")

    return df


# ---------------------------------------------------------
#  Entrada unificada (según modo)
# ---------------------------------------------------------
def seccion_entrada_estructuras(modo_carga: str):
    """Despacha al modo de carga seleccionado."""
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        df, ruta_estructuras = cargar_desde_excel()
    elif modo_carga == "Pegar tabla":
        df = pegar_tabla()
    elif modo_carga == "Listas desplegables":
        df = listas_desplegables()

    return df, ruta_estructuras
