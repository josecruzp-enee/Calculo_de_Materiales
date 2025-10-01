# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Cálculo de Materiales", layout="wide")

st.title("⚡ Cálculo de Materiales de Proyecto de Distribución")

# Columnas base de la tabla
columnas = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# --- Opción 1: subir Excel ---
archivo_excel = st.file_uploader("📂 Sube el archivo Excel de estructuras", type=["xlsx", "csv"], key="uploader")

df = None
df_proyecto = None

if archivo_excel:
    if archivo_excel.name.endswith(".xlsx"):
        # Leer todas las hojas
        xls = pd.ExcelFile(archivo_excel)

        # Hoja datos_proyecto (si existe)
        if "datos_proyecto" in xls.sheet_names:
            df_proyecto = pd.read_excel(xls, sheet_name="datos_proyecto")

        # Hoja estructuras (si existe)
        if "estructuras" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="estructuras")
        else:
            st.error("⚠️ El archivo debe tener una hoja llamada 'estructuras'")
    else:
        df = pd.read_csv(archivo_excel)

    st.success("✅ Archivo cargado correctamente")

else:
    # --- Opción 2: tabla editable en vivo ---
    st.info("ℹ️ No subiste archivo, puedes crear/editar la tabla directamente aquí abajo")
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)

    df = st.data_editor(
        st.session_state["df_puntos"],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_tabla"  # 👈 clave única
    )
    st.session_state["df_puntos"] = df

# --- Vista previa datos_proyecto (solo 2 columnas) ---
if df_proyecto is not None:
    st.subheader("📑 Información del Proyecto")
    df_preview = df_proyecto.iloc[:, :2]   # solo 2 primeras columnas
    df_preview.columns = ["Definición", "Dato"]
    st.table(df_preview)

# --- Vista previa de estructuras ---
if df is not None:
    st.subheader("📑 Vista previa de la tabla")
    st.dataframe(df, use_container_width=True, key="preview_estructuras")

    # --- Botones de descarga ---
    st.subheader("📥 Exportar tabla")

    # CSV
    st.download_button(
        "⬇️ Descargar CSV",
        df.to_csv(index=False).encode("utf-8"),
        "estructuras_lista.csv",
        "text/csv",
        key="download_csv"
    )

    # Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Estructuras")
    st.download_button(
        "⬇️ Descargar Excel",
        output.getvalue(),
        "estructuras_lista.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_excel"
    )



