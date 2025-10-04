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
    """Borra valores de selectbox para que vuelvan a 'Seleccionar estructura'."""
    for key in ["sel_poste", "sel_primario", "sel_secundario",
                "sel_retenidas", "sel_tierra", "sel_transformador"]:
        if key in st.session_state:
            del st.session_state[key]


# ========================
# Datos del proyecto
# ========================
def seccion_datos_proyecto():
    formulario_datos_proyecto()
    mostrar_datos_formateados()


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
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"])
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
    texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200)
    if texto_pegado:
        df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
        st.success(f"✅ Tabla cargada con {len(df)} filas")
        return df
    return pd.DataFrame(columns=COLUMNAS_BASE)


def listas_desplegables():
    from modulo.desplegables import cargar_opciones, crear_desplegables
    opciones = cargar_opciones()

    st.subheader("4. 🏗️ Estructuras del Proyecto")

    df_actual = st.session_state["df_puntos"]
    puntos_existentes = df_actual["Punto"].unique().tolist()

    # Crear nuevo punto
    if st.button("🆕 Crear nuevo Punto"):
        nuevo_num = len(puntos_existentes) + 1
        st.session_state["punto_en_edicion"] = f"Punto {nuevo_num}"
        st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")
        resetear_desplegables()

    # Seleccionar un punto existente
    if puntos_existentes:
        seleccionado = st.selectbox("📍 Selecciona un Punto existente:", puntos_existentes, index=0)
        if st.button("✏️ Editar Punto seleccionado"):
            st.session_state["punto_en_edicion"] = seleccionado
            resetear_desplegables()

    # Si hay punto en edición
    if "punto_en_edicion" in st.session_state:
        punto = st.session_state["punto_en_edicion"]
        st.markdown(f"### ✏️ Editando {punto}")
        seleccion = crear_desplegables(opciones)
        seleccion["Punto"] = punto

        if st.button("💾 Guardar Punto"):
            if punto in df_actual["Punto"].values:
                # Ya existe → combinar estructuras nuevas con las anteriores
                fila_existente = df_actual[df_actual["Punto"] == punto].iloc[0].to_dict()
                for col in ["Poste", "Primario", "Secundario",
                            "Retenidas", "Conexiones a tierra", "Transformadores"]:
                    anterior = str(fila_existente.get(col, "")).strip()
                    nuevo = str(seleccion.get(col, "")).strip()
                    if anterior and nuevo and anterior != nuevo:
                        seleccion[col] = anterior + " + " + nuevo
                    elif anterior and not nuevo:
                        seleccion[col] = anterior
                    # si no había nada antes, se queda lo nuevo

                # Eliminar fila vieja
                df_actual = df_actual[df_actual["Punto"] != punto]

            # Agregar fila actualizada
            df_actual = pd.concat([df_actual, pd.DataFrame([seleccion])], ignore_index=True)

            # 👉 Ordenar puntos
            df_actual["orden"] = df_actual["Punto"].str.extract(r'(\d+)').astype(int)
            df_actual = df_actual.sort_values("orden").drop(columns="orden")
            st.session_state["df_puntos"] = df_actual.reset_index(drop=True)

            st.success(f"✅ {punto} actualizado correctamente")
            resetear_desplegables()
            st.session_state.pop("punto_en_edicion")
            st.rerun()

    df = st.session_state["df_puntos"]

    # Vista previa
    if not df.empty:
        st.markdown("#### 📑 Vista de estructuras / materiales")
        st.dataframe(df, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Limpiar todo"):
                st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)
                st.session_state.pop("punto_en_edicion", None)
                resetear_desplegables()
                st.success("✅ Se limpiaron todas las estructuras/materiales")
        with col2:
            punto_borrar = st.selectbox("❌ Seleccionar Punto a borrar", df["Punto"].unique())
            if st.button("Borrar Punto"):
                st.session_state["df_puntos"] = df[df["Punto"] != punto_borrar].reset_index(drop=True)
                st.success(f"✅ Se eliminó {punto_borrar}")

    return df

# ========================
# Adicionar materiales manualmente
# ========================
def seccion_adicionar_material():
    st.subheader("5. 🧰 Adicionar Material")
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
                placeholder="Ejemplo: BOMBILLO PARA LÁMPARA – C/U"
            )

        # --- Cantidad (entera) ---
        with col2:
            cantidad = st.number_input("🔢 Cantidad", min_value=1, step=1, value=1)

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
            width="stretch"  # reemplaza use_container_width
        )


# ========================
# Finalizar cálculo
# ========================
def seccion_finalizar_calculo(df):
    if not df.empty:
        st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
        if st.button("✅ Finalizar Cálculo"):
            try:
                st.session_state["calculo_finalizado"] = True
                st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")
            except Exception as e:
                st.error(f"❌ Error al finalizar cálculo: {e}")


# ========================
# Exportación
# ========================
def seccion_exportacion(df, modo_carga, ruta_estructuras, ruta_datos_materiales):
    if not df.empty and st.session_state.get("calculo_finalizado", False):
        st.subheader("6. 📂 Exportación de Reportes")

        if st.button("📥 Generar Reportes PDF"):
            st.session_state["pdfs_generados"] = generar_pdfs(modo_carga, ruta_estructuras, df, ruta_datos_materiales)

        if "pdfs_generados" in st.session_state:
            pdfs = st.session_state["pdfs_generados"]

            st.download_button("📄 Descargar PDF de Materiales", pdfs["materiales"], "Resumen_Materiales.pdf", "application/pdf")
            st.download_button("📄 Descargar PDF de Estructuras (Global)", pdfs["estructuras_global"], "Resumen_Estructuras.pdf", "application/pdf")
            st.download_button("📄 Descargar PDF de Estructuras por Punto", pdfs["estructuras_por_punto"], "Estructuras_Por_Punto.pdf", "application/pdf")
            st.download_button("📄 Descargar PDF de Materiales por Punto", pdfs["materiales_por_punto"], "Materiales_Por_Punto.pdf", "application/pdf")
            st.download_button("📄 Descargar Informe Completo", pdfs["completo"], "Informe_Completo.pdf", "application/pdf")


# ========================
# MAIN
# ========================
def main():
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

    modo_carga = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"]
    )

    # ======================
    # Inicialización del estado
    # ======================
    if "datos_proyecto" not in st.session_state:
        st.session_state["datos_proyecto"] = {}
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=COLUMNAS_BASE)

    # ======================
    # 1️⃣ Sección de datos del proyecto
    # ======================
    seccion_datos_proyecto()

    # ======================
    # 2️⃣ Selección de calibres
    # ======================
    st.header("🧵 Selección de Calibres de Conductores")
    calibres = cargar_calibres_desde_excel()
    calibres_seleccionados = seleccionar_calibres_formulario(
        st.session_state["datos_proyecto"], calibres
    )
    st.session_state["datos_proyecto"].update(calibres_seleccionados)

    # ======================
    # 3️⃣ Configuración de red (1F, 2F, 3F)
    # ======================
    configuracion = seleccionar_configuracion_red()
    st.session_state["datos_proyecto"].update(configuracion)

    # ======================
    # 4️⃣ Carga de estructuras
    # ======================
    df, ruta_estructuras = seccion_entrada_estructuras(modo_carga)

    # ======================
    # 5️⃣ Adición manual de materiales
    # ======================
    seccion_adicionar_material()

    # ======================
    # 6️⃣ Cálculo final y exportación
    # ======================
    seccion_finalizar_calculo(df)
    seccion_exportacion(df, modo_carga, ruta_estructuras, RUTA_DATOS_MATERIALES)


if __name__ == "__main__":
    main()







