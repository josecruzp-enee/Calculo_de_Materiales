def validar_datos_proyecto(datos_proyecto):
    tension = str(datos_proyecto.get("nivel_de_tension", "")).strip()
    calibre_mt = datos_proyecto.get("calibre_primario", "")
    if not tension or not calibre_mt:
        return None, None
    return tension, calibre_mt
