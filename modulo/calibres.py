def seleccionar_calibres_formulario(datos_proyecto, calibres):
    """Formulario interactivo para seleccionar calibres comerciales."""

    def combo_comercial(etiqueta, lista_opciones, valor_actual="", clave=None):
        index = lista_opciones.index(valor_actual) if valor_actual in lista_opciones else 0
        return st.selectbox(etiqueta, lista_opciones, index=index, key=clave)

    calibre_primario = combo_comercial(
        "Calibre del Conductor de Media Tensión",
        calibres["primario"],
        datos_proyecto.get("calibre_primario", ""),
        clave="calibre_primario"
    )
    calibre_secundario = combo_comercial(
        "Calibre del Conductor de Baja Tensión",
        calibres["secundario"],
        datos_proyecto.get("calibre_secundario", ""),
        clave="calibre_secundario"
    )
    calibre_neutro = combo_comercial(
        "Calibre del Conductor de Neutro",
        calibres["neutro"],
        datos_proyecto.get("calibre_neutro", ""),
        clave="calibre_neutro"
    )
    calibre_piloto = combo_comercial(
        "Calibre del Conductor de Hilo Piloto",
        calibres["piloto"],
        datos_proyecto.get("calibre_piloto", ""),
        clave="calibre_piloto"
    )
    calibre_retenidas = combo_comercial(
        "Calibre del Cable de Retenida",
        calibres["retenidas"],
        datos_proyecto.get("calibre_retenidas", ""),
        clave="calibre_retenidas"
    )

    return {
        "calibre_primario": calibre_primario,
        "calibre_secundario": calibre_secundario,
        "calibre_neutro": calibre_neutro,
        "calibre_piloto": calibre_piloto,
        "calibre_retenidas": calibre_retenidas
    }
