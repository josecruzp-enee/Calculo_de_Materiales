# app.py
# -*- coding: utf-8 -*-
import streamlit as st

from modulo.interfaz.ui_secciones import (
    renderizar_encabezado,
    inicializar_estado,
    seccion_datos_proyecto,
    seccion_cables_proyecto,
    seleccionar_modo_carga,
    seccion_entrada_estructuras,
    seccion_adicionar_material,
    seccion_finalizar_calculo,
    seccion_exportacion,
    ruta_datos_materiales_por_defecto,
)

def main() -> None:
    # 0) Encabezado + estado base
    renderizar_encabezado()
    inicializar_estado()

    # 1) Datos generales
    seccion_datos_proyecto()

    # 2) Cables
    seccion_cables_proyecto()

    # 3) Estructuras (Excel / Pegar / Listas)
    modo_carga = seleccionar_modo_carga()
    df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo_carga)

    # 4) Materiales adicionales
    seccion_adicionar_material()

    # 5) Finalizar cálculo
    seccion_finalizar_calculo(df_estructuras)

    # 6) Exportación (PDFs/descargas)
    seccion_exportacion(
        df=df_estructuras,
        modo_carga=modo_carga,
        ruta_estructuras=ruta_estructuras,
        ruta_datos_materiales=ruta_datos_materiales_por_defecto(),  # ← ruta automática
    )

if __name__ == "__main__":
    main()

