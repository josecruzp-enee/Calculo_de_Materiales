# -*- coding: utf-8 -*-
"""
configuracion_cables.py
Fachada (compatibilidad): reexporta UI y PDF.
"""

from .cables_ui import seccion_cables
from exportadores.cables_pdf import tabla_cables_pdf


# Si en otros lados importabas helpers, los podés reexportar:
from core.cables_catalogo import (
    get_tipos,
    get_calibres,
    get_calibres_union,
    get_configs_por_tipo,
    get_configs_union,
)

from .cables_logica import descripcion_oficial
