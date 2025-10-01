# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Gestión de Estructuras", layout="wide")
st.title("⚡ Gestión de Estructuras por Punto")

# Columnas base de la tabla de estructuras
columnas = ["Punto", "Poste", "Primario", "Secundario", "Retenida", "Aterrizaje", "Transformador"]

# --- Opción 1: subir Excel ---
archivo_excel = st.file_uploader("📂 Sube el archivo Excel de estructuras", type=["xlsx", "csv"])

if archivo_excel:
    if archivo_excel.name.endswith(".xlsx"):
        # Leer todas las hojas
        xls = pd.ExcelFile(archivo_excel)

        # Mostrar las hojas disponibles
        hoja_seleccionada = st.selectbox("📑 Selecciona la hoja a cargar", xls.sheet_names)

        # Cargar hoja seleccionada
        df = pd.read_excel(archivo_excel, sheet_name=hoja_seleccionada)

        # --- Mostrar según tipo de hoja ---
        if hoja_seleccionada.lower() == "estructuras":
            # Normalizar columnas
            df.columns = df.columns.str.strip().str.title()
            faltantes = set(columnas) - set(df.columns)
            if faltantes:
                st.error(f"❌ La hoja '{hoja_seleccionada}' debe contener las columnas: {', '.join(columnas)}. Faltan: {', '.join(faltantes)}")
                st.stop()
            st.success(f"✅ Hoja '{hoja_seleccionada}' cargada correctamente")
            st.dataframe(df, use_container_width=True)

        elif hoja_seleccionada.lower() == "datos_proyecto":
            st.success("✅ Datos del proyecto detectados")
            st.write("📋 **Ficha del Proyecto**")
            # Mostrar clave/valor
            for col, val in zip(df.iloc[:,0], df.iloc[:,1]):
                st.write(f"**{col}:** {val}")

        else:
            st.success(f"✅ Hoja '{hoja_seleccionada}' cargada correctamente")
            st.dataframe(df, use_container_width=True)

    else:
        # Si es CSV
        df = pd.read_csv(archivo_excel)
        st.success("✅ Archivo CSV cargado correctamente")
        st.dataframe(df, use_container_width=True)

else:
    # --- Opción 2: tabla editable en vivo ---
    st.info("ℹ️ No subiste archivo, puedes crear/editar la tabla directamente aquí abajo")
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)

    df = st.data_editor(
        st.session_state["df_puntos"],
        num_rows="dynamic",
        use_container_width=True,
    )
    st.session_state["df_puntos"] = df

# --- Botones de descarga ---
if archivo_excel or not df.empty:
    st.subheader("📥 Exportar tabla")

    # CSV
    st.download_button(
        "⬇️ Descargar CSV",
        df.to_csv(index=False).encode("utf-8"),
        "estructuras_lista.csv",
        "text/csv"
    )

    # Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
    st.download_button(
        "⬇️ Descargar Excel",
        output.getvalue(),
        "estructuras_lista.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Guardar en sesión para edición en vivo
    st.session_state["df_puntos"] = df.copy()
else:
    st.info("ℹ️ No subiste archivo, puedes crear/editar la tabla directamente aquí abajo")
    if "df_puntos" not in st.session_state:
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)

    if st.button("🧹 Limpiar tabla"):
        st.session_state["df_puntos"] = pd.DataFrame(columns=columnas)
        st.rerun()

# --- Siempre trabajar con la sesión ---
df = st.data_editor(
    st.session_state.get("df_puntos", pd.DataFrame(columns=columnas)),
    num_rows="dynamic",
    use_container_width=True,
)
st.session_state["df_puntos"] = df

# Mostrar vista previa
st.subheader("📑 Vista previa de la tabla")
st.dataframe(df, use_container_width=True)

# --- Botones de descarga ---
st.subheader("📥 Exportar tabla")

# Exportar a CSV
st.download_button(
    "⬇️ Descargar CSV",
    df.to_csv(index=False).encode("utf-8"),
    "estructuras_lista.csv",
    "text/csv"
)

# Exportar a Excel con ajuste automático de columnas
output = BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Estructuras")
    ws = writer.sheets["Estructuras"]
    for col_idx, col in enumerate(df.columns, 1):
        max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
        ws.column_dimensions[get_column_letter(col_idx)].width = max_length

st.download_button(
    "⬇️ Descargar Excel",
    output.getvalue(),
    "estructuras_lista.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

