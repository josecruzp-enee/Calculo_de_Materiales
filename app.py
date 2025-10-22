# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import re

from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.entradas import cargar_estructuras_proyectadas, cargar_catalogo_materiales
from modulo.configuracion_cables import seccion_cables
from modulo.estilos_app import aplicar_estilos
from modulo.procesar_materiales import procesar_materiales  # ✅ usamos este directamente



COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores"
]

BASE_DIR = os.path.dirname(__file__)
RUTA_DATOS_MATERIALES = os.path.join(BASE_DIR, "modulo", "Estructura_datos.xlsx")


def resetear_desplegables():
    claves_base = ["sel_poste", "sel_primario", "sel_secundario",
                   "sel_retenidas", "sel_tierra", "sel_transformador"]

    for key in claves_base:
        if key in st.session_state:
            del st.session_state[key]

    import time
    st.session_state["keys_desplegables"] = {
        key: f"{key}_{int(time.time() * 1000)}" for key in claves_base
    }


def seccion_datos_proyecto():
    formulario_datos_proyecto()
    mostrar_datos_formateados()


def seccion_entrada_estructuras(modo_carga):
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        df, ruta_estructuras = cargar_desde_excel()
    elif modo_carga == "Pegar tabla":
        df = pegar_tabla()
    elif modo_carga == "Listas desplegables":
        df = listas_desplegables()

    return df, ruta_estructuras


def cargar_desde_excel():
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"], key="upl_estructuras")
    if archivo_estructuras:
        ruta_estructuras = guardar_archivo_temporal(archivo_estructuras)
        try:
            df = cargar_estructuras_proyectadas(ruta_estructuras)
            st.success("✅ Hoja 'estructuras' leída correctamente")
            return df, ruta_estructuras
        except Exception as e:
            st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
    return pd.DataFrame(columns=COLUMNAS_BASE), None


def pegar_tabla():
    texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200, key="txt_pegar_tabla")
    if texto_pegado:
        df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
        st.success(f"✅ Tabla cargada con {len(df)} filas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)


def listas_desplegables():
    from modulo.desplegables import cargar_opciones, crear_desplegables
    opciones = cargar_opciones()

    st.subheader("3. 🏗️ Estructuras del Proyecto")

    if st.session_state.get("reiniciar_desplegables", False):
        st.session_state["reiniciar_desplegables"] = False
        resetear_desplegables()
        try:
            st.rerun()
        except Exception as e:
            st.warning(f"No se pudo recargar automáticamente ({e})")

    df_actual = st.session_state["df_puntos"]
    puntos_existentes = df_actual["Punto"].unique().tolist()

    if st.button("🆕 Crear nuevo Punto"):
        nuevo_num = len(puntos_existentes) + 1
        st.session_state["punto_en_edicion"] = f"Punto {nuevo_num}"
        st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")
        resetear_desplegables()

    if st.session_state.get("punto_en_edicion"):
        punto = st.session_state["punto_en_edicion"]
        st.markdown(f"### ✏️ Editando {punto}")

        seleccion = crear_desplegables(opciones)
        seleccion["Punto"] = punto
        st.markdown("<hr style='border:0.5px solid #ddd; margin:0.7rem 0;'>", unsafe_allow_html=True)

        if st.button("💾 Guardar Estructura del Punto", type="primary", key="btn_guardar_estructura"):
            if punto in df_actual["Punto"].values:
                fila_existente = df_actual[df_actual["Punto"] == punto].iloc[0].to_dict()
                for col in ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores"]:
                    anterior = str(fila_existente.get(col, "")).strip()
                    nuevo = str(seleccion.get(col, "")).strip()
                    if anterior and nuevo and anterior != nuevo:
                        seleccion[col] = anterior + " + " + nuevo
                    elif anterior and not nuevo:
                        seleccion[col] = anterior
                df_actual = df_actual[df_actual["Punto"] != punto]

            df_actual = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)
            df_actual["orden"] = df_actual["Punto"].str.extract(r'(\d+)').astype(int)
            df_actual = df_actual.sort_values("orden").drop(columns="orden")
            st.session_state["df_puntos"] = df_actual.reset_index(drop=True)

            st.success(f"✅ {punto} actualizado correctamente")
            resetear_desplegables()
            st.session_state.pop("punto_en_edicion", None)
            st.session_state["reiniciar_desplegables"] = True
            try:
                st.rerun()
            except Exception as e:
                st.warning(f"No se pudo recargar automáticamente ({e})")

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
                    key="select_editar_punto_fila"
                )
                if st.button("✏️ Editar Punto", key="btn_editar_punto_fila"):
                    st.session_state["punto_en_edicion"] = seleccionado
                    resetear_desplegables()
                    try:
                        st.rerun()
                    except Exception as e:
                        st.warning(f"No se pudo recargar ({e})")

        with col3:
            punto_borrar = st.selectbox(
                "❌ Punto a borrar:",
                df["Punto"].unique(),
                key="select_borrar_punto_fila"
            )
            if st.button("Borrar Punto", key="btn_borrar_punto_fila"):
                st.session_state["df_puntos"] = df[df["Punto"] != punto_borrar].reset_index(drop=True)
                st.success(f"✅ Se eliminó {punto_borrar}")

    return df


def seccion_adicionar_material():
    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto que no estén asociados a estructuras específicas.")

    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    catalogo_df = cargar_catalogo_materiales(RUTA_DATOS_MATERIALES)
    if catalogo_df.empty:
        st.warning("⚠️ No se pudo cargar el catálogo de materiales.")
        return

    catalogo_df["Etiqueta"] = catalogo_df.apply(
        lambda x: f"{x['Descripcion']} – {x['Unidad']}" if pd.notna(x["Unidad"]) else x["Descripcion"],
        axis=1
    )
    opciones_materiales = catalogo_df["Etiqueta"].tolist()

    with st.form("form_adicionar_material"):
        col1, col2 = st.columns([3, 1])
        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=[""] + opciones_materiales,
                index=0,
                placeholder="Ejemplo: BOMBILLO PARA LÁMPARA – C/U",
                key="sel_material_extra"
            )
        with col2:
            cantidad = st.number_input("🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra")

        agregar = st.form_submit_button("➕ Agregar Material")

    if agregar and etiqueta_sel:
        partes = etiqueta_sel.split(" – ")
        material = partes[0].strip()
        unidad = partes[1].strip() if len(partes) > 1 else ""
        st.session_state["materiales_extra"].append({
            "Materiales": material,
            "Unidad": unidad,
            "Cantidad": int(cantidad)
        })
        st.success(f"✅ Material agregado: {material} ({cantidad} {unidad})")

    if st.session_state["materiales_extra"]:
        st.markdown("### 📋 Materiales adicionales añadidos")
        st.dataframe(pd.DataFrame(st.session_state["materiales_extra"]), use_container_width=True, hide_index=True)


def seccion_finalizar_calculo(df):
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo", key="btn_finalizar_calculo"):
            st.session_state["calculo_finalizado"] = True
            st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")


def seccion_exportacion(df, modo_carga, ruta_estructuras, ruta_datos_materiales):
    """
    Sección de exportación de reportes PDF y Excel.
    Corrige:
    - Estructuras duplicadas
    - Nombres con comas o símbolos
    """
    if not df.empty and st.session_state.get("calculo_finalizado", False):
        st.subheader("6. 📂 Exportación de Reportes")

        # --- Sincronizar cables del proyecto ---
        if "cables_proyecto" in st.session_state:
            st.session_state["datos_proyecto"]["cables_proyecto"] = st.session_state["cables_proyecto"]

            datos_cables = st.session_state["cables_proyecto"]

            if isinstance(datos_cables, list) and len(datos_cables) > 0:
                datos_cables = datos_cables[0]
            elif not isinstance(datos_cables, dict):
                datos_cables = {}

            tension = (
                datos_cables.get("tension")
                or datos_cables.get("nivel_de_tension")
                or 13.8
            )
            calibre_mt = (
                datos_cables.get("calibre_mt")
                or datos_cables.get("conductor_mt")
                or datos_cables.get("Calibre")
                or "1/0 ASCR"
            )

            st.session_state["datos_proyecto"]["tension"] = tension
            st.session_state["datos_proyecto"]["calibre_mt"] = calibre_mt

            st.info(f"🔧 Nivel de tensión: {tension} kV  |  Calibre MT: {calibre_mt}")

        columnas_estructuras = [
            "Poste", "Primario", "Secundario",
            "Retenidas", "Conexiones a tierra", "Transformadores"
        ]

        df_expandido = df.copy()

        # ✅ FUNCIÓN CORREGIDA
        def limpiar_estructuras(fila):
            estructuras = []
            for col in columnas_estructuras:
                valor = str(fila.get(col, '')).strip()
                if not valor or valor.lower() == 'seleccionar estructura':
                    continue
                partes = re.split(r'[+,;]', valor)
                for p in partes:
                    p = p.strip().upper()
                    # 🔧 elimina comas, paréntesis, símbolos y espacios internos
                    p = re.sub(r"[^A-Z0-9\-\.]", "", p)
                    if p and p not in ['SELECCIONAR', 'ESTRUCTURA', 'N/A', 'NONE']:
                        estructuras.append(p)
            return list(dict.fromkeys(estructuras))

        # === Expandir estructuras ===
        df_expandido["Estructura"] = df_expandido.apply(limpiar_estructuras, axis=1)
        df_expandido = df_expandido.explode("Estructura", ignore_index=True)
        df_expandido = df_expandido[
            df_expandido["Estructura"].notna() & (df_expandido["Estructura"].str.strip() != "")
        ]

        df_expandido["Estructura"] = df_expandido["Estructura"].str.strip().str.upper()
        df_expandido.drop_duplicates(subset=["Punto", "Estructura"], inplace=True)

        df_expandido.rename(columns={"Estructura": "codigodeestructura"}, inplace=True)

        # === Vista previa ===
        conteo_preview = (
            df_expandido.groupby(["Punto", "codigodeestructura"])
            .size()
            .reset_index(name="Cantidad")
        )
        st.caption("Conteo rápido de estructuras por punto (sin duplicados):")
        st.dataframe(conteo_preview, use_container_width=True, hide_index=True)

        # === Materiales adicionales ===
        if st.session_state.get("materiales_extra"):
            st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(st.session_state["materiales_extra"])
        else:
            st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
                columns=["Materiales", "Unidad", "Cantidad"]
            )

        # === Generar reportes ===
        if st.button("📥 Generar Reportes PDF", key="btn_generar_pdfs"):
            try:
                with st.spinner("⏳ Generando reportes, por favor espere..."):
                    resultados_pdf = procesar_materiales(
                        archivo_estructuras=ruta_estructuras,
                        archivo_materiales=ruta_datos_materiales,
                        estructuras_df=df_expandido,
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

        # === Descarga de reportes ===
        if "pdfs_generados" in st.session_state:
            pdfs = st.session_state["pdfs_generados"]
            st.markdown("### 📥 Descarga de Reportes Generados")
            if isinstance(pdfs, dict):
                if pdfs.get("materiales"):
                    st.download_button("📄 Descargar PDF de Materiales", pdfs["materiales"],
                                       "Resumen_Materiales.pdf", "application/pdf", key="dl_mat")
                if pdfs.get("estructuras_global"):
                    st.download_button("📄 Descargar PDF de Estructuras (Global)", pdfs["estructuras_global"],
                                       "Resumen_Estructuras.pdf", "application/pdf", key="dl_estr_glob")
                if pdfs.get("estructuras_por_punto"):
                    st.download_button("📄 Descargar PDF de Estructuras por Punto", pdfs["estructuras_por_punto"],
                                       "Estructuras_Por_Punto.pdf", "application/pdf", key="dl_estr_punto")
                if pdfs.get("materiales_por_punto"):
                    st.download_button("📄 Descargar PDF de Materiales por Punto", pdfs["materiales_por_punto"],
                                       "Materiales_Por_Punto.pdf", "application/pdf", key="dl_mat_punto")
                if pdfs.get("completo"):
                    st.download_button("📄 Descargar Informe Completo", pdfs["completo"],
                                       "Informe_Completo.pdf", "application/pdf", key="dl_full")


def main():
    # --- Configuración de página y estilos ---
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    aplicar_estilos()
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    # --- Inicializar valores por defecto ---
    defaults = {
        "datos_proyecto": {},
        "df_puntos": pd.DataFrame(columns=COLUMNAS_BASE),
        "materiales_extra": [],
        "calculo_finalizado": False,
        "punto_en_edicion": None,
        "cables_proyecto": {},
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # --- Selección del modo de carga ---
    modo_carga = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"],
        key="modo_carga_radio"
    )

    st.markdown("---")

    # --- Sección de configuración de cables ---
    st.subheader("⚙️ Configuración de Cables del Proyecto")
    cables_registrados = seccion_cables()  # ✅ función devuelve calibres MT, BT, Neutro

    if cables_registrados:
        # Guardar calibres dentro de session_state
        st.session_state["datos_proyecto"]["cables_proyecto"] = cables_registrados
        st.session_state["cables_proyecto"] = cables_registrados
        st.success("✅ Calibres registrados correctamente.")

    st.markdown("---")

    # --- Sección de estructuras del proyecto ---
    df, ruta_estructuras = seccion_entrada_estructuras(modo_carga)

    # --- Sección de materiales adicionales ---
    seccion_adicionar_material()

    # --- Procesamiento final del cálculo ---
    seccion_finalizar_calculo(df)

    # --- Exportación del informe (PDF/Excel) ---
    seccion_exportacion(df, modo_carga, ruta_estructuras, RUTA_DATOS_MATERIALES)


if __name__ == "__main__":
    main()


