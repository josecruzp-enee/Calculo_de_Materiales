def validar_datos_proyecto(datos_proyecto):
    """
    Extrae la tensión y el calibre MT del diccionario datos_proyecto,
    aceptando distintas variantes de nombres de clave.
    """
    if not datos_proyecto:
        return None, None

    # Buscar tensión (con distintos nombres posibles)
    tension = (
        str(
            datos_proyecto.get("tension")
            or datos_proyecto.get("nivel_de_tension")
            or datos_proyecto.get("tensión")
            or "13.8"
        ).strip()
    )

    # Buscar calibre MT (con variantes)
    calibre_mt = (
        datos_proyecto.get("calibre_mt")
        or datos_proyecto.get("calibre_primario")
        or datos_proyecto.get("conductor_mt")
        or None
    )

    # 🩹 Si no hay calibre, buscar dentro de cables_proyecto
    if not calibre_mt and "cables_proyecto" in datos_proyecto:
        try:
            cables = datos_proyecto["cables_proyecto"]
            if isinstance(cables, list) and len(cables) > 0:
                calibre_mt = cables[0].get("Calibre", "")
            elif isinstance(cables, dict):
                calibre_mt = cables.get("Calibre") or cables.get("calibre_mt") or ""
        except Exception:
            calibre_mt = ""

    # Asignar valores por defecto si siguen vacíos
    if not tension:
        tension = "13.8"
    if not calibre_mt:
        calibre_mt = "1/0 ASCR"

    return tension, calibre_mt
