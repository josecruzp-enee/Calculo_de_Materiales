def renderizar_estructuras():

    modo = st.session_state.get("modo_carga_seleccionado")

    if not modo:
        st.warning("⚠️ Primero selecciona el modo de carga.")
        return

    df = None
    ruta = None

    # =====================================================
    # MULTI-MODO REAL
    # =====================================================

    try:

        # -------------------------
        # MANUAL (DESPLEGABLES)
        # -------------------------
        if modo == "manual":
            df, ruta = seccion_entrada_estructuras()

        # -------------------------
        # EXCEL
        # -------------------------
        elif modo == "excel":
            from entradas.leer_excel import leer_excel
            df, ruta = leer_excel()

        # -------------------------
        # TABLA PEGADA
        # -------------------------
        elif modo == "tabla":
            from entradas.entradas_tabla import leer_tabla
            df, ruta = leer_tabla()

        # -------------------------
        # PDF
        # -------------------------
        elif modo == "pdf":
            from entradas.entradas_pdf import leer_pdf
            df, ruta = leer_pdf()

        # -------------------------
        # DXF
        # -------------------------
        elif modo == "dxf":
            from entradas.entradas_dxf import leer_dxf
            df, ruta = leer_dxf()

        else:
            st.warning(f"⚠️ Modo no soportado: {modo}")
            return

    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        return

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    if not es_dataframe_valido(df):
        st.info("⚠️ No hay estructuras aún.")
        return

    # =====================================================
    # GUARDAR EN ESTADO
    # =====================================================
    st.session_state["df_estructuras"] = df
    st.session_state["ruta_estructuras_compacto"] = ruta

    st.success(f"✅ Estructuras cargadas desde modo: {modo}")
