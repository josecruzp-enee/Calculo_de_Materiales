def seccion_datos_proyecto():
    st.markdown("### 📘 Datos Generales del Proyecto")

    col1, col2 = st.columns(2)  # 👈 Dividimos en dos columnas

    with col1:
        nombre_proyecto = st.text_input("📄 Nombre del Proyecto", key="nombre_proyecto")
        empresa = st.text_input("🏢 Empresa / Área", value="ENEE", key="empresa")
        tension = st.selectbox("⚡ Nivel de Tensión (kV)", ["13.8", "34.5"], key="nivel_tension")

    with col2:
        codigo_proyecto = st.text_input("🔢 Código / Expediente", key="codigo_proyecto")
        responsable = st.text_input("👷‍♂️ Responsable / Diseñador", key="responsable")
        fecha_informe = st.date_input("📅 Fecha del Informe", key="fecha_informe")

    # Guardar datos
    st.session_state["datos_proyecto"] = {
        "nombre_proyecto": nombre_proyecto,
        "codigo_proyecto": codigo_proyecto,
        "empresa": empresa,
        "responsable": responsable,
        "nivel_de_tension": tension,
        "fecha_informe": str(fecha_informe),
    }

    st.success("✅ Datos del proyecto guardados correctamente.")

