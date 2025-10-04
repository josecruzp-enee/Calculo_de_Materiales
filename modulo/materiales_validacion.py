def validar_datos_proyecto(datos_proyecto):
    tension = str(datos_proyecto.get("nivel_de_tension", "")).strip()
    calibre_mt = datos_proyecto.get("calibre_primario", "")

    # 🩹 Si no hay calibre_primario, buscar dentro de cables_proyecto
    if not calibre_mt and "cables_proyecto" in datos_proyecto:
        try:
            calibre_mt = datos_proyecto["cables_proyecto"][0].get("Calibre", "")
        except Exception:
            calibre_mt = ""

    if not tension or not calibre_mt:
        return None, None
    return tension, calibre_mt
