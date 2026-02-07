# -*- coding: utf-8 -*-
"""
exportadores/pdf_utils.py
Fachada de compatibilidad: re-exporta todo para NO romper imports.
Autor: José Nikol Cruz
"""

# Base (estilos, helpers, membrete, calibres)
from exportadores.pdf_base import (
    styles, styleN, styleH, BASE_DIR,
    formatear_material,
    salto_pagina_seguro, extender_flowables, quitar_saltos_finales,
    fondo_pagina,
    _dedupe_keep_order, _calibres_por_tipo,
)

# Reportes simples
from exportadores.pdf_reportes_simples import (
    generar_pdf_materiales,
    generar_pdf_estructuras_global,
    generar_pdf_estructuras_por_punto,
    generar_pdf_materiales_por_punto,
    _tabla_estructuras_por_punto,
)

# Anexos costos
from exportadores.pdf_anexos_costos import (
    tabla_costos_materiales_pdf,
    tabla_costos_estructuras_pdf,
    tabla_costos_por_punto_pdf,
)

# PDF completo
from exportadores.pdf_completo import generar_pdf_completo
