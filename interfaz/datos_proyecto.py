# -*- coding: utf-8 -*-
# interfaz/datos_proyecto.py

import streamlit as st
from modulo.formularios import formulario_datos_proyecto, mostrar_datos_formateados

def seccion_datos_proyecto() -> None:
    """Muestra formulario y resumen de datos generales del proyecto."""
    formulario_datos_proyecto()
    mostrar_datos_formateados()
