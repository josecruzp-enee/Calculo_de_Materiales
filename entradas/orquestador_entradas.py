# -*- coding: utf-8 -*-
from __future__ import annotations

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz, SalidaEntradas

# =========================================================
# SERVICIO DE DOMINIO (AQUÍ VIVE LA LÓGICA REAL)
# =========================================================
from entradas.servicio_entrada import ejecutar_pipeline_entrada


# =========================================================
# ORQUESTADOR PURO
# =========================================================
def ejecutar_entradas(
    entrada: SalidaInterfaz,
    *,
    tension: float,
    validar_catalogo: bool = True,
) -> SalidaEntradas:
    """
    Orquestador del dominio entradas.
    SOLO coordina:
        - recibe contrato
        - llama servicio
        - devuelve contrato
    """

    # =====================================================
    # 1. VALIDAR ENTRADA DE INTERFAZ
    # =====================================================
    if not entrada.ok:
        return SalidaEntradas(
            ok=False,
            errores=entrada.errores,
            warnings=entrada.warnings,
            debug={"origen": "interfaz"}
        )

    try:
        # =====================================================
        # 2. EJECUTAR PIPELINE DE DOMINIO
        # =====================================================
        resultado = ejecutar_pipeline_entrada(
            tipo=entrada.tipo_entrada,
            data=entrada.data_entrada,
            tension=tension,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            validar_catalogo=validar_catalogo,
        )

        # =====================================================
        # 3. ADAPTAR A CONTRATO
        # =====================================================
        return SalidaEntradas(
            ok=True,
            errores=[],
            warnings=[],
            df_estructuras=resultado.estructuras_df,
            datos_proyecto=entrada.datos_proyecto,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            debug={
                "pipeline": "ok",
                "filas": len(resultado.estructuras_df)
            }
        )

    except Exception as e:
        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            warnings=[],
            df_estructuras=None,
            debug={"error": str(e)}
        )
