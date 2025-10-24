# modulo/ui_secciones.py
# -*- coding: utf-8 -*-
"""
Secciones de UI y utilidades de la app:
- Estado y encabezado (UI base)
- Datos de proyecto
- Cables
- Entrada de estructuras (Excel / Pegar / Listas)
- Materiales adicionales
- Finalizar cálculo
- Exportación (normalización, conteos, PDFs)
"""

import os
import re
import time
import pandas as pd
import streamlit as st

# IO / utils / UI ya existentes en tu proyecto:
from modulo.io.utils import guardar_archivo_temporal, pegar_texto_a_df
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados
from modulo.io.entradas import cargar_estructuras_proyectadas, cargar_catalogo_materiales
from modulo.configuracion_cables import seccion_cables
from modulo.estilos_app import aplicar_estilos
from modulo.procesar_materiales import procesar_materiales  # núcleo

# =========================
# Constantes (conservadas)
# =========================
COLUMNAS_BASE = [
    "Punto", "Poste", "Primario", "Secundario",
    "Retenidas", "Conexiones a tierra", "Transformadores"
]

def ruta_datos_materiales_por_defecto() -> str:
    """
    Devuelve la ruta al Excel de datos de materiales.
    Se calcula relativa al repo para no depender de app.py.
    """
    # Este archivo vive en .../modulo/ui_secciones.py  → subimos a raíz del repo
    repo_root = os.path.dirname(os.path.dirname(__file__))
    ruta = os.path.join(repo_root, "modulo", "Estructura_datos.xlsx")
    return ruta


# =========================
# Utilidades de estado/UI
# =========================
def inicializar_estado() -> None:
    """Inicializa claves esperadas en st.session_state sin sobrescribir valores existentes."""
    valores_por_defecto = {
        "datos_proyecto": {},
        "df_puntos": pd.DataFrame(columns=COLUMNAS_BASE),
        "materiales_extra": [],
        "calculo_finalizado": False,
        "punto_en_edicion": None,
        "cables_proyecto": {},
        "keys_desplegables": {},
        "pdfs_generados": None,
        "reiniciar_desplegables": False,
    }
    for clave, valor in valores_por_defecto.items():
        st.session_state.setdefault(clave, valor)

def renderizar_encabezado() -> None:
    """Configura la página y aplica estilos."""
    st.set_page_config(page_title="Cálculo de Materiales", layout="wide")
    aplicar_estilos()
    st.title("⚡ Cálculo de Materiales para Proyecto de Distribución")

def resetear_desplegables() -> None:
    """Fuerza nuevas keys para widgets de desplegables (evita estado pegado)."""
    claves = ["sel_poste", "sel_primario", "sel_secundario",
              "sel_retenidas", "sel_tierra", "sel_transformador"]
    for key in claves:
        st.session_state.pop(key, None)
    st.session_state["keys_desplegables"] = {k: f"{k}_{int(time.time()*1000)}" for k in claves}

def seleccionar_modo_carga() -> str:
    """Muestra el selector de modo de carga y retorna la opción elegida."""
    modo = st.radio(
        "Selecciona modo de carga:",
        ["Desde archivo Excel", "Pegar tabla", "Listas desplegables"],
        key="modo_carga_radio"
    )
    st.markdown("---")
    return modo


# =========================
# Sección 1: Datos del proyecto
# =========================
def seccion_datos_proyecto() -> None:
    """Muestra formulario y resumen de datos generales del proyecto."""
    formulario_datos_proyecto()
    mostrar_datos_formateados()


# =========================
# Sección 2: Cables
# =========================
def seccion_cables_proyecto() -> None:
    """Renderiza la sección de configuración de cables y sincroniza estado."""
    st.subheader("⚙️ Configuración de Cables del Proyecto")
    cables_registrados = seccion_cables()  # puede retornar lista de dicts o DataFrame
    if cables_registrados:
        st.session_state["datos_proyecto"]["cables_proyecto"] = cables_registrados
        st.session_state["cables_proyecto"] = cables_registrados
        st.success("✅ Calibres registrados correctamente.")
    st.markdown("---")


# =========================
# Sección 3: Estructuras (cargar/pegar/desplegables)
# =========================
def cargar_desde_excel() -> tuple[pd.DataFrame, str | None]:
    """Carga el archivo de estructuras desde un uploader y retorna (DataFrame, ruta_temporal)."""
    archivo_estructuras = st.file_uploader("Archivo de estructuras", type=["xlsx"], key="upl_estructuras")
    if not archivo_estructuras:
        return pd.DataFrame(columns=COLUMNAS_BASE), None

    ruta_temporal = guardar_archivo_temporal(archivo_estructuras)
    try:
        df = cargar_estructuras_proyectadas(ruta_temporal)
        st.success("✅ Hoja 'estructuras' leída correctamente")
        return df, ruta_temporal
    except Exception as e:
        st.error(f"❌ No se pudo leer la hoja 'estructuras': {e}")
        return pd.DataFrame(columns=COLUMNAS_BASE), None

def pegar_tabla() -> pd.DataFrame:
    """Convierte texto pegado (CSV/tabulado) en DataFrame con columnas base."""
    texto_pegado = st.text_area("Pega aquí tu tabla CSV/tabulado", height=200, key="txt_pegar_tabla")
    if not texto_pegado:
        return pd.DataFrame(columns=COLUMNAS_BASE)
    df = pegar_texto_a_df(texto_pegado, COLUMNAS_BASE)
    st.success(f"✅ Tabla cargada con {len(df)} filas")
    return df

def editar_punto_con_listas_desplegables(df_actual: pd.DataFrame) -> pd.DataFrame:
    """UI para crear/editar un Punto usando listas desplegables. Retorna el DataFrame actualizado."""
    from modulo.desplegables import cargar_opciones, crear_desplegables

    opciones = cargar_opciones()

    if st.session_state.get("reiniciar_desplegables", False):
        st.session_state["reiniciar_desplegables"] = False
        resetear_desplegables()
        try:
            st.rerun()
        except Exception as e:
            st.warning(f"No se pudo recargar automáticamente ({e})")

    puntos_existentes = df_actual["Punto"].unique().tolist()

    if st.button("🆕 Crear nuevo Punto"):
        nuevo_numero = len(puntos_existentes) + 1
        st.session_state["punto_en_edicion"] = f"Punto {nuevo_numero}"
        st.success(f"✏️ {st.session_state['punto_en_edicion']} creado y listo para editar")
        resetear_desplegables()

    if not st.session_state.get("punto_en_edicion"):
        return df_actual

    punto = st.session_state["punto_en_edicion"]
    st.markdown(f"### ✏️ Editando {punto}")

    seleccion = crear_desplegables(opciones)
    seleccion["Punto"] = punto

    st.markdown("<hr style='border:0.5px solid #ddd; margin:0.7rem 0;'>", unsafe_allow_html=True)

    if st.button("💾 Guardar Estructura del Punto", type="primary", key="btn_guardar_estructura"):
        df_actual = combinar_seleccion_de_punto(df_actual, seleccion, punto)
        st.session_state["df_puntos"] = df_actual.reset_index(drop=True)
        st.success(f"✅ {punto} actualizado correctamente")
        resetear_desplegables()
        st.session_state.pop("punto_en_edicion", None)
        st.session_state["reiniciar_desplegables"] = True
        try:
            st.rerun()
        except Exception as e:
            st.warning(f"No se pudo recargar automáticamente ({e})")

    return df_actual

def combinar_seleccion_de_punto(df_actual: pd.DataFrame, seleccion: dict, punto: str) -> pd.DataFrame:
    """Fusiona la selección con el punto existente (si lo hay), conservando y concatenando valores previos."""
    if punto in df_actual["Punto"].values:
        fila_existente = df_actual[df_actual["Punto"] == punto].iloc[0].to_dict()
        columnas = ["Poste", "Primario", "Secundario", "Retenidas", "Conexiones a tierra", "Transformadores"]
        for col in columnas:
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
    return df_actual

def acciones_sobre_tabla_estructuras(df: pd.DataFrame) -> None:
    """Muestra acciones para limpiar todo, editar o borrar puntos en la tabla."""
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

def listas_desplegables() -> pd.DataFrame:
    """Sección de estructuras usando listas desplegables; retorna el DataFrame resultante."""
    st.subheader("3. 🏗️ Estructuras del Proyecto")

    df_actual = st.session_state["df_puntos"]
    df_actual = editar_punto_con_listas_desplegables(df_actual)

    df = st.session_state["df_puntos"]
    if df.empty:
        return df

    st.markdown("#### 📑 Vista de estructuras / materiales")
    st.dataframe(df, use_container_width=True, hide_index=True)
    acciones_sobre_tabla_estructuras(df)
    return df

def seccion_entrada_estructuras(modo_carga: str) -> tuple[pd.DataFrame, str | None]:
    """Enruta según el modo de carga: Excel, tabla pegada o listas desplegables."""
    df = pd.DataFrame(columns=COLUMNAS_BASE)
    ruta_estructuras = None

    if modo_carga == "Desde archivo Excel":
        df, ruta_estructuras = cargar_desde_excel()
    elif modo_carga == "Pegar tabla":
        df = pegar_tabla()
    elif modo_carga == "Listas desplegables":
        df = listas_desplegables()

    return df, ruta_estructuras


# =========================
# Sección 4: Material adicional
# =========================
def seccion_adicionar_material() -> None:
    """Permite agregar materiales extra al proyecto (fuera de estructuras)."""
    st.subheader("4. 🧰 Adicionar Material")
    st.markdown("Agrega materiales adicionales al proyecto que no estén asociados a estructuras específicas.")

    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = []

    catalogo_df = cargar_catalogo_materiales(ruta_datos_materiales_por_defecto())
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
        agregar_material_extra(etiqueta_sel, cantidad)

    if st.session_state["materiales_extra"]:
        st.markdown("### 📋 Materiales adicionales añadidos")
        st.dataframe(pd.DataFrame(st.session_state["materiales_extra"]), use_container_width=True, hide_index=True)

def agregar_material_extra(etiqueta_sel: str, cantidad: int) -> None:
    """Agrega un material adicional a session_state a partir de la etiqueta seleccionada."""
    partes = etiqueta_sel.split(" – ")
    material = partes[0].strip()
    unidad = partes[1].strip() if len(partes) > 1 else ""
    st.session_state["materiales_extra"].append({
        "Materiales": material,
        "Unidad": unidad,
        "Cantidad": int(cantidad)
    })
    st.success(f"✅ Material agregado: {material} ({cantidad} {unidad})")


# =========================
# Sección 5: Finalizar cálculo
# =========================
def seccion_finalizar_calculo(df: pd.DataFrame) -> None:
    """Habilita el botón para marcar el cálculo como finalizado."""
    if df.empty:
        return
    st.subheader("5. 🏁 Finalizar Cálculo del Proyecto")
    if st.button("✅ Finalizar Cálculo", key="btn_finalizar_calculo"):
        st.session_state["calculo_finalizado"] = True
        st.success("🎉 Cálculo finalizado con éxito. Ahora puedes exportar los reportes.")


# =========================
# Helpers de exportación
# =========================
def sincronizar_cables_en_datos_proyecto() -> None:
    """Ajusta tensión y calibre MT en datos_proyecto a partir de cables_proyecto."""
    if "cables_proyecto" not in st.session_state:
        return

    st.session_state["datos_proyecto"]["cables_proyecto"] = st.session_state["cables_proyecto"]

    datos_cables = st.session_state["cables_proyecto"]
    if isinstance(datos_cables, list) and len(datos_cables) > 0:
        datos_cables = datos_cables[0]
    elif not isinstance(datos_cables, dict):
        datos_cables = {}

    tension = datos_cables.get("tension") or datos_cables.get("nivel_de_tension") or 13.8
    calibre_mt = (
        datos_cables.get("calibre_mt")
        or datos_cables.get("conductor_mt")
        or datos_cables.get("Calibre")
        or "1/0 ASCR"
    )

    st.session_state["datos_proyecto"]["tension"] = tension
    st.session_state["datos_proyecto"]["calibre_mt"] = calibre_mt
    st.info(f"🔧 Nivel de tensión: {tension} kV  |  Calibre MT: {calibre_mt}")

def limpiar_estructuras_fila(fila: pd.Series, columnas: list[str]) -> list[str]:
    """Limpia y separa los códigos de estructuras en una fila."""
    estructuras = []
    for col in columnas:
        valor = str(fila.get(col, '')).strip()
        if not valor or valor.lower() == 'seleccionar estructura':
            continue
        partes = re.split(r'[+,;]', valor)
        for p in partes:
            p = p.strip().upper()
            p = re.sub(r"[^A-Z0-9\-\.]", "", p)  # elimina símbolos y espacios
            if p and p not in ['SELECCIONAR', 'ESTRUCTURA', 'N/A', 'NONE']:
                estructuras.append(p)
    # eliminar duplicados preservando orden
    return list(dict.fromkeys(estructuras))

def expandir_estructuras_en_filas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza y expande estructuras en filas (columna 'codigodeestructura')."""
    columnas_estructuras = [
        "Poste", "Primario", "Secundario",
        "Retenidas", "Conexiones a tierra", "Transformadores"
    ]
    df_expandido = df.copy()
    df_expandido["Estructura"] = df_expandido.apply(
        lambda fila: limpiar_estructuras_fila(fila, columnas_estructuras),
        axis=1
    )
    df_expandido = df_expandido.explode("Estructura", ignore_index=True)
    df_expandido = df_expandido[
        df_expandido["Estructura"].notna() & (df_expandido["Estructura"].str.strip() != "")
    ]
    df_expandido["Estructura"] = df_expandido["Estructura"].str.strip().str.upper()
    df_expandido.drop_duplicates(subset=["Punto", "Estructura"], inplace=True)
    df_expandido.rename(columns={"Estructura": "codigodeestructura"}, inplace=True)
    return df_expandido

def mostrar_previsualizacion_conteo(df_expandido: pd.DataFrame) -> None:
    """Muestra una tabla con el conteo por Punto y código de estructura."""
    conteo_preview = (
        df_expandido.groupby(["Punto", "codigodeestructura"])
        .size()
        .reset_index(name="Cantidad")
    )
    st.caption("Conteo rápido de estructuras por punto (sin duplicados):")
    st.dataframe(conteo_preview, use_container_width=True, hide_index=True)

def inyectar_materiales_extra_en_datos_proyecto() -> None:
    """Convierte materiales_extra a DataFrame dentro de datos_proyecto para exportación."""
    if st.session_state.get("materiales_extra"):
        st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(st.session_state["materiales_extra"])
    else:
        st.session_state["datos_proyecto"]["materiales_extra"] = pd.DataFrame(
            columns=["Materiales", "Unidad", "Cantidad"]
        )

def generar_reportes_desde_interfaz(
    df_expandido: pd.DataFrame,
    ruta_estructuras: str | None,
    ruta_datos_materiales: str
) -> None:
    """Invoca el núcleo para generar reportes y almacena el resultado en session_state."""
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

def mostrar_botones_descarga_reportes() -> None:
    """Muestra los botones de descarga para los PDFs generados."""
    if "pdfs_generados" not in st.session_state:
        return
    pdfs = st.session_state["pdfs_generados"]
    if not isinstance(pdfs, dict):
        return

    st.markdown("### 📥 Descarga de Reportes Generados")
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


# =========================
# Sección 6: Exportación
# =========================
def seccion_exportacion(
    df: pd.DataFrame,
    modo_carga: str,
    ruta_estructuras: str | None,
    ruta_datos_materiales: str
) -> None:
    """
    Exportación de reportes (PDF/Excel).
    - Corrige estructuras duplicadas.
    - Normaliza nombres con símbolos.
    """
    if df.empty or not st.session_state.get("calculo_finalizado", False):
        return

    st.subheader("6. 📂 Exportación de Reportes")

    sincronizar_cables_en_datos_proyecto()
    df_expandido = expandir_estructuras_en_filas(df)
    mostrar_previsualizacion_conteo(df_expandido)
    inyectar_materiales_extra_en_datos_proyecto()

    generar_reportes_desde_interfaz(df_expandido, ruta_estructuras, ruta_datos_materiales)
    mostrar_botones_descarga_reportes()
