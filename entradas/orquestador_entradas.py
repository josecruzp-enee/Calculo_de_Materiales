# -*- coding: utf-8 -*-
from __future__ import annotations

# =========================================================
# CONTRATOS
# =========================================================
from interfaz.contratos import SalidaInterfaz, SalidaEntradas

# =========================================================
# LECTORES
# =========================================================
from entradas.leer_excel import leer_estructuras as leer_excel
from entradas.leer_tabla import leer_tabla
from entradas.leer_pdf import leer_pdf
from entradas.leer_dxf import leer_dxf

# =========================================================
# PROCESAMIENTO
# =========================================================
from entradas.normalizar import normalizar_estructuras
from entradas.validacion import validar_estructuras


# =========================================================
# DISPATCH
# =========================================================
def _leer(tipo: str, data):

    if tipo == "excel":
        return leer_excel(data)

    elif tipo == "tabla":
        return leer_tabla(data)

    elif tipo == "pdf":
        return leer_pdf(data)

    elif tipo == "dxf":
        return leer_dxf(data)

    elif tipo == "manual":
        return data

    else:
        raise ValueError(f"Tipo no soportado: {tipo}")


# =========================================================
# ORQUESTADOR REAL (PIPELINE)
# =========================================================
def ejecutar_entradas(
    entrada: SalidaInterfaz,
    *,
    tension: float,
    validar_catalogo: bool = True,
) -> SalidaEntradas:

    # =====================================================
    # 1. VALIDACIÓN INTERFAZ
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
        # 2. LECTURA
        # =====================================================
        df_raw = _leer(entrada.tipo_entrada, entrada.data_entrada)

        if df_raw is None or getattr(df_raw, "empty", True):
            return SalidaEntradas(
                ok=False,
                errores=["No se pudo leer la entrada"],
                debug={"fase": "lectura"}
            )

        # =====================================================
        # 3. NORMALIZACIÓN
        # =====================================================
        df_norm, errores_norm, warnings_norm = normalizar_estructuras(df_raw)

        if errores_norm:
            return SalidaEntradas(
                ok=False,
                errores=errores_norm,
                warnings=warnings_norm,
                debug={"fase": "normalizacion"}
            )

        # =====================================================
        # 4. VALIDACIÓN
        # =====================================================
        errores_val = validar_estructuras(df_norm)

        if errores_val:
            return SalidaEntradas(
                ok=False,
                errores=errores_val,
                warnings=warnings_norm,
                df_estructuras=df_norm,
                debug={"fase": "validacion"}
            )

        # =====================================================
        # 5. OK
        # =====================================================
        return SalidaEntradas(
            ok=True,
            errores=[],
            warnings=warnings_norm,
            df_estructuras=df_norm,
            datos_proyecto=entrada.datos_proyecto,
            df_cables=entrada.df_cables,
            df_materiales_extra=entrada.df_materiales_extra,
            debug={
                "fase": "ok",
                "filas": len(df_norm),
                "columnas": list(df_norm.columns),
                "tipo": entrada.tipo_entrada,
            }
        )

    except Exception as e:
        return SalidaEntradas(
            ok=False,
            errores=[str(e)],
            debug={
                "fase": "exception",
                "tipo": entrada.tipo_entrada
            }
        )
