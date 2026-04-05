# -*- coding: utf-8 -*-
"""
modulo/procesar_materiales.py

Wrapper de compatibilidad.
Antes: aquí se calculaba + generaba PDFs (archivo largo).
Ahora:
  1) servicios.calculo_materiales.calcular_materiales -> retorna DFs + datos_proyecto
  2) exportadores.pdf_exportador.generar_pdfs -> genera bytes de PDFs

Así mantenemos el nombre 'procesar_materiales' para no romper imports viejos.
"""

from servicios.calculo_materiales import calcular_materiales
from exportadores.pdf_exportador import generar_pdfs


def procesar_materiales(
    archivo_estructuras=None,
    archivo_materiales=None,
    estructuras_df=None,
    datos_proyecto=None
) -> dict:
    """
    Compatibilidad con el código viejo que aún llama procesar_materiales().
    Devuelve el mismo diccionario de PDFs que devolvía antes:
      {"materiales": bytes, "estructuras_global": bytes, ...}
    """
    resultados = calcular_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=archivo_materiales,
        estructuras_df=estructuras_df,
        datos_proyecto=datos_proyecto
    )
    return generar_pdfs(resultados)
