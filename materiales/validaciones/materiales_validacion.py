# -*- coding: utf-8 -*-
# materiales/validaciones/materiales_validacion.py

from __future__ import annotations
from typing import Tuple, Any


def _normalizar_string(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip().upper()


def validar_datos_proyecto(datos_proyecto: dict | None) -> Tuple[str, str]:
    """
    Normaliza y extrae:
    - tensión del sistema
    - calibre del conductor MT

    Retorna siempre valores válidos (nunca None).
    """

    # =========================
    # DEFAULTS
    # =========================
    TENSION_DEFAULT = "13.8"
    CALIBRE_DEFAULT = "1/0 ACSR"

    if not isinstance(datos_proyecto, dict):
        return TENSION_DEFAULT, CALIBRE_DEFAULT

    # =========================
    # 1. TENSIÓN
    # =========================
    tension = (
        datos_proyecto.get("tension")
        or datos_proyecto.get("nivel_de_tension")
        or datos_proyecto.get("tensión")
    )

    tension = _normalizar_string(tension) or TENSION_DEFAULT

    # =========================
    # 2. CALIBRE MT
    # =========================
    calibre_mt = (
        datos_proyecto.get("calibre_mt")
        or datos_proyecto.get("calibre_primario")
        or datos_proyecto.get("conductor_mt")
    )

    calibre_mt = _normalizar_string(calibre_mt)

    # =========================
    # 3. FALLBACK DESDE CABLES
    # =========================
    if not calibre_mt:
        cables = datos_proyecto.get("cables_proyecto")

        try:
            if isinstance(cables, list) and cables:
                calibre_mt = _normalizar_string(cables[0].get("Calibre"))

            elif isinstance(cables, dict):
                calibre_mt = _normalizar_string(
                    cables.get("Calibre") or cables.get("calibre_mt")
                )

        except Exception:
            calibre_mt = ""

    # =========================
    # 4. DEFAULT FINAL
    # =========================
    if not calibre_mt:
        calibre_mt = CALIBRE_DEFAULT

    return tension, calibre_mt
