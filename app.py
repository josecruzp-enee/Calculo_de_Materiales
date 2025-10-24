# app.py
# -*- coding: utf-8 -*-
import streamlit as st

from interfaz.base import (
    renderizar_encabezado,
    inicializar_estado,
    seleccionar_modo_carga,
    ruta_datos_materiales_por_defecto,
)

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.cables import seccion_cables_proyecto
from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.materiales_extra import seccion_adicionar_material
from interfaz.exportacion import seccion_finalizar_calculo, seccion_exportacion

def main() -> None:
    # 0) Encabezado + estado base
    renderizar_encabezado()
    inicializar_estado()

    # 1) Datos generales
    seccion_datos_proyecto()

    # 2) Cables
    seccion_cables_proyecto()

    # 3) Estructuras
    modo = seleccionar_modo_carga()
    df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)

    # 4) Materiales extra
    seccion_adicionar_material()

    # 5) Finalizar cálculo
    seccion_finalizar_calculo(df_estructuras)

    # 6) Exportación
    seccion_exportacion(
        df=df_estructuras,
        modo_carga=modo,
        ruta_estructuras=ruta_estructuras,
        ruta_datos_materiales=ruta_datos_materiales_por_defecto(),
    )

if __name__ == "__main__":
    main()
