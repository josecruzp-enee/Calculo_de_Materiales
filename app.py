# app.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os

from modulo.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.generar_pdfs import generar_pdfs
from modulo.entradas import cargar_estructuras_proyectadas
from modulo.entradas import cargar_catalogo_materiales
from modulo.configuracion_cables import seccion_cables
from modulo.estilos_app import aplicar_estilos

# Aplicar estilos institucionales ENEE
aplicar_estilos()  # encabezado blanco
# aplicar_estilos(usar_encabezado_rojo=True)  # si querés la franja roja


# 👇 columnas base ajustadas a tu Excel
COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores"
]

# 📌 Ruta fija al Excel base de materiales
BASE_DIR = os.path.dirname(__file__)
RUTA_DATOS_MATERIALES = os.path.join(BASE_DIR, "modulo", "Estructura_datos.xlsx")


# ========================
# Helpers
# ========================
def resetear_desplegables():
    """Resetea los selectbox y fuerza su recreación cambiando sus claves."""
    claves_base = ["sel_poste", "sel_primario", "sel_secundario",
                   "sel_retenidas", "sel_tierra", "sel_transformador"]

    # Eliminar valores previos del estado
    for key in claves_base:
        if key in st.session_state:
            del st.session_state[key]

    # Generar nuevas claves únicas (con timestamp)
    import time
    st.session_state["keys_desplegables"] = {
        key: f"{key}_{int(time.time() * 1000)}" for key in claves_base
    }


# ========================
# Datos del proyecto
# ========================
def seccion_datos_proyecto():
    formulario_datos_proyecto()
    mostrar_datos_formateados()
    # ⚠️ Nota: el nivel de tensión seleccionado en el formulario se usa automáticamente
    # para determinar qué columna (13.8 kV o 34.5 kV) se toma del archivo Estructura_datos.xlsx.


# ========================
# Entrada de estructuras
# ========================
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

    # 🔄 Si la app quedó marcada para reiniciar los desplegables, hacerlo ahora
    if st.session_state.get("reiniciar_desplegables", False):
        st.session_state["reiniciar_desplegables"] = False
        resetear_desplegables()
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

    df_actual = st.session_state["df_puntos"]
    puntos_existentes = df_actual["Punto"].unique().tolist()

    # --- Crear nuevo punto ---
    if st.button("🆕 Crear nuevo Punto"):
        nuevo_num = len(puntos_existentes) + 1
        st.session_state["punto_en_edicion"] = f"Punto {nuevo_num}"
        st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")
        resetear_desplegables()

    # --- Edición del punto actual ---
    if "punto_en_edicion" in st.session_state and st.session_state["punto_en_edicion"]:
        punto = st.session_state["punto_en_edicion"]
        st.markdown(f"### ✏️ Editando {punto}")

        # Mostrar los desplegables en fila horizontal
        seleccion = crear_desplegables(opciones)
        seleccion["Punto"] = punto

        # Separador visual
        st.markdown("<hr style='border:0.5px solid #ddd; margin:0.7rem 0;'>", unsafe_allow_html=True)

        # --- Botón Guardar Estructura del Punto ---
        guardar = st.button("💾 Guardar Estructura del Punto", type="primary", key="btn_guardar_estructura")

        if guardar:
            if punto in df_actual["Punto"].values:
                fila_existente = df_actual[df_actual["Punto"] == punto].iloc[0].to_dict()
                for col in ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores"]:
                    anterior = str(fila_existente.get(col, "")).strip()
                    nuevo = str(seleccion.get(col, "")).strip()
                    if anterior and nuevo and anterior != nuevo:
                        seleccion[col] = anterior + " + " + nuevo
                    elif anterior and not nuevo:
                        seleccion[col] = anterior

                # Eliminar fila vieja
                df_actual = df_actual[df_actual["Punto"] != punto]

            # Agregar fila actualizada
            df_actual = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)

            # Ordenar puntos numéricamente
            df_actual["orden"] = df_actual["Punto"].str.extract(r'(\d+)').astype(int)
            df_actual = df_actual.sort_values("orden").drop(columns="orden")
            st.session_state["df_puntos"] = df_actual.reset_index(drop=True)

            st.success(f"✅ {punto} actualizado correctamente")
            resetear_desplegables()
            st.session_state.pop("punto_en_edicion", None)

            st.session_state["reiniciar_desplegables"] = True
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()
    else:
        punto = None

    # --- Vista previa general ---
    df = st.session_state["df_puntos"]
    if not df.empty:
        st.markdown("#### 📑 Vista de estructuras / materiales")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # === Controles de acción (3 botones en fila) ===
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
                    st.experimental_rerun()

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





# ========================
# Adicionar materiales manualmente
# ========================
def seccion_adicionar_material():
    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto que no estén asociados a estructuras específicas.")

    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    # 🔹 Cargar catálogo de materiales desde la hoja "Materiales"
    catalogo_df = cargar_catalogo_materiales(RUTA_DATOS_MATERIALES)

    if catalogo_df.empty:
        st.warning("⚠️ No se pudo cargar el catálogo de materiales.")
        return

    # 🔹 Crear etiqueta "Material – Unidad"
    catalogo_df["Etiqueta"] = catalogo_df.apply(
        lambda x: f"{x['Descripcion']} – {x['Unidad']}" if pd.notna(x["Unidad"]) else x["Descripcion"],
        axis=1
    )
    opciones_materiales = catalogo_df["Etiqueta"].tolist()

    with st.form("form_adicionar_material"):
        col1, col2 = st.columns([3, 1])

        # --- Seleccionar material (con unidad concatenada) ---
        with col1:
            etiqueta_sel = st.selectbox(
                "🔧 Selecciona el Material",
                options=[""] + opciones_materiales,
                index=0,
                placeholder="Ejemplo: BOMBILLO PARA LÁMPARA – C/U",
                key="sel_material_extra"
            )

        # --- Cantidad (entera) ---
        with col2:
            cantidad = st.number_input("🔢 Cantidad", min_value=1, step=1, value=1, key="num_cantidad_extra")

        agregar = st.form_submit_button("➕ Agregar Material")

    if agregar and etiqueta_sel:
        # Separar descripción y unidad
        partes = etiqueta_sel.split(" – ")
        material = partes[0].strip()
        unidad = partes[1].strip() if len(partes) > 1 else ""

        # Guardar en session_state
        st.session_state["materiales_extra"].append({
            "Materiales": material,
            "Unidad": unidad,
            "Cantidad": int(cantidad)
        })
        st.success(f"✅ Material agregado: {material} ({cantidad} {unidad})")

    # --- Mostrar materiales adicionales agregados ---
    if st.session_state["materiales_extra"]:
        st.markdown("### 📋 Materiales adicionales añadidos")
        st.dataframe(
            pd.DataFrame(st.session_state["materiales_extra"]),
            width="stretch"
        )


# ========================
# Finalizar cálculo
# ========================
def seccion_finalizar_calculo(df):
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo", key="btn_finalizar_calculo"):
            try:
                st.session_state["calculo_finalizado"] = True
                st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")
            except Exception as e:
                st.error(f"❌ Error al finalizar cálculo: {e}")


# ========================
# Exportación (única definición)
# ========================
def seccion_exportacion(df, modo_carga, ruta_estructuras, ruta_datos_materiales):
    if not df.empty and st.session_state.get("calculo_finalizado", False):
        st.subheader("6. 📂 Exportación de Reportes")

        # 🧩 Guardar cables dentro de datos_proyecto antes de exportar
        if "cables_proyecto" in st.session_state:
            st.session_state["datos_proyecto"]["cables_proyecto"] = st.session_state["cables_proyecto"]

        if st.button("📥 Generar Reportes PDF", key="btn_generar_pdfs"):
            st.session_state["pdfs_generados"] = generar_pdfs(
                modo_carga, ruta_estructuras, df, ruta_datos_materiales
            )

        if "pdfs_generados" in st.session_state:
            pdfs = st.session_state["pdfs_generados"]
            st.download_button("📄 Descargar PDF de Materiales", pdfs["materiales"],
                               "Resumen_Materiales.pdf", "application/pdf", key="dl_mat")
            st.download_button("📄 Descargar PDF de Estructuras (Global)", pdfs["estructuras_global"],
                               "Resumen_Estructuras.pdf", "application/pdf", key="dl_estr_glob")
            st.download_button("📄 Descargar PDF de Estructuras por Punto", pdfs["estructuras_por_punto"],
                               "Estructuras_Por_Punto.pdf", "application/pdf", key="dl_estr_punto")
            st.download_button("📄 Descargar PDF de Materiales por Punto", pdfs["materiales_por_punto"],
                               "Materiales_Por_Punto.pdf", "application/pdf", key="dl_mat_punto")
            st.download_button("📄 Descargar Informe Completo", pdfs["completo"],
                               "Informe_Completo.pdf", "application/pdf", key="dl_full")


def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    aplicar_estilos()
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    # 🔄 Forzar recarga diferida si quedó pendiente del ciclo anterior
    # (permite refrescar la app tras guardar, borrar o limpiar sin error en Streamlit Cloud)
    if st.session_state.get("force_reload", False):
        st.session_state["force_reload"] = False

        # ✅ Compatibilidad entre versiones de Streamlit
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

    # ======================
    # Inicialización del estado
    # ======================
    defaults = {
        "datos_proyecto": {},
        "df_puntos": pd.DataFrame(columns=COLUMNAS_BASE),
        "materiales_extra": [],
        "calculo_finalizado": False,
        "punto_en_edicion": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # ======================
    # Selección del modo de carga
    # ======================
    modo_carga = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"],
        key="modo_carga_radio"
    )

    # ======================
    # 1️⃣ Sección de datos del proyecto
    # ======================
    seccion_datos_proyecto()

    # ======================
    # 2️⃣ Configuración y Calibres de Conductores
    # ======================
    cables_registrados = seccion_cables()

    # Guardar en los datos del proyecto
    if cables_registrados:
        st.session_state["datos_proyecto"]["cables_proyecto"] = cables_registrados
        st.session_state["cables_proyecto"] = cables_registrados

    # ======================
    # 3️⃣ Carga de estructuras
    # ======================
    df, ruta_estructuras = seccion_entrada_estructuras(modo_carga)

    # ======================
    # 4️⃣ Adición manual de materiales
    # ======================
    seccion_adicionar_material()

    # ======================
    # 5️⃣ Cálculo final y exportación
    # ======================
    seccion_finalizar_calculo(df)
    seccion_exportacion(df, modo_carga, ruta_estructuras, RUTA_DATOS_MATERIALES)


if __name__ == "__main__":
    main()








