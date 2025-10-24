# modulo/ui_datos_proyecto.py
# -*- coding: utf-8 -*-
"""
Sección de datos generales del proyecto (formulario + resumen).
"""

from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados

def seccion_datos_proyecto() -> None:
    """Muestra formulario y resumen de datos generales del proyecto."""
    formulario_datos_proyecto()
    mostrar_datos_formateados()
