# -*- coding: utf-8 -*-
from __future__ import annotations

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz, SalidaEntradas

# =========================================================
# DTO INTERNO
# =========================================================
from entradas.contratos_entradas import EntradaPipeline

# =========================================================
# SERVICIO (LÓGICA REAL)
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

    RESPONSABILIDAD:
        - Validar contrato de entrada (interfaz)
        - Adaptar a DTO interno
        - Ejecutar servicio de dominio
        - Adaptar salida a contrato

    NO:
        - leer archivos
        - normalizar
        - validar estructuras
    """

    # =====================================================
    # 1. VALIDACIÓN DE CONTRATO (INTERFAZ)
    # =====================================================
    if not entrada.ok:
        return SalidaEntradas(
            ok=False,
            errores=entrada.errores,
            warnings=entrada.warnings,
            df_estructuras=None,
            debug={"origen": "interfaz"}
        )

    try:
        # =====================================================
        # 2. ADAPTACIÓN → DTO INTERNO
        # =====================================================
        dto = EntradaPipeline(
            tipo=entrada.tipo_entrada,
            data=entrada.data_entrada,
            tension=tension,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            validar_catalogo=validar_catalogo,
        )

        # =====================================================
        # 3. EJECUCIÓN DEL DOMINIO
        # =====================================================
        resultado = ejecutar_pipeline_entrada(dto)

        # =====================================================
        # 4. VALIDACIÓN DE RESULTADO
        # =====================================================
        if not resultado.ok:
            return SalidaEntradas(
                ok=False,
                errores=resultado.errores,
                warnings=resultado.warnings,
                df_estructuras=resultado.estructuras_df,
                datos_proyecto=entrada.datos_proyecto,
                df_cables=entrada.df_cables,
                df_materiales_extra=entrada.df_materiales_extra,
                debug=resultado.debug,
            )

        # =====================================================
        # 5. ADAPTACIÓN → CONTRATO DE SALIDA
        # =====================================================
        return SalidaEntradas(
            ok=True,
            errores=[],
            warnings=resultado.warnings,
            df_estructuras=resultado.estructuras_df,
            datos_proyecto=entrada.datos_proyecto,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            debug={
                "pipeline": "ok",
                "filas": len(resultado.estructuras_df),
                **resultado.debug,
            },
        )

    except Exception as e:
        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            warnings=[],
            df_estructuras=None,
            datos_proyecto=entrada.datos_proyecto,
            debug={"error": str(e), "etapa": "orquestador_entradas"},
        )
