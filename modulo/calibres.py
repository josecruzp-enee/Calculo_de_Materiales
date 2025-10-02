# -*- coding: utf-8 -*-
"""
Gestión de calibres de conductores para proyecto.
Autor: José Nikol Cruz
"""

import pandas as pd
import os
import streamlit as st


def cargar_calibres_desde_excel(ruta_archivo=None):
    """
    Carga calibres desde 'calibres.xlsx'. Si falla, devuelve valores por defecto.
    """
    if ruta_archivo is None:
        ruta_archivo = os.path.join(os.path.dirname(__file__), "calibres.xlsx")

    # Valores por defecto
    calibres_defecto = {
        "primario": ["2 ASCR", "1/0 ASCR", "2/0 ASCR", "3/0 ASCR", "4/0 ACSR", "266.8 MCM", "477 MCM", "556.5 MCM"],
        "secundario": ["2 WP", "1/0 WP", "2/0 WP", "3/0 WP", "4/0 WP", "266.8 WP"],
        "piloto": ["2 WP"],
        "retenidas": ["1/4 Acerado", "5/8 Acerado", "3/4 Acerado"]
    }

    if not os.path.exists(ruta_archivo):
        return calibres_defecto

    try:
        df = pd.read_excel(ruta_archivo)
    except Exception as e:
        print(f"Error leyendo calibres.xlsx: {e}")
        return calibres_defecto

    # Extraer columnas
    calibres = {
        "primario": df.get("Conductores Primario", pd.Series()).dropna().astype(str).tolist() or calibres_defecto["primario"],
        "secundario": df.get("Conductores Secundarios", pd.Series()).dropna().astype(str).tolist() or calibres_defecto["secundario"],
        "piloto": df.get("Conductores Piloto", pd.Series()).dropna().astype(str).tolist() or calibres_defecto["piloto"],
        "retenidas": df.get("Conductores Retenidas", pd.Series()).dropna().astype(str).tolist() or calibres_defecto["retenidas"],
    }
    return calibres


def seleccionar_calibres_formulario(datos_proyecto, calibres):
    """
    Formulario interactivo para seleccionar o escribir calibres personalizados.
    """
    st.subheader("📝 Selección de Calibres (predeterminados o personalizados)")

    def combo_personalizado(etiqueta, lista_opciones, valor_actual):
        opciones = lista_opciones + ["Otro (personalizado)"]

        # Determinar índice inicial según valor actual
        if valor_actual in lista_opciones:
            index = lista_opciones.index(valor_actual)
        else:
            index = len(opciones) - 1  # "Otro (personalizado)"

        seleccion = st.selectbox(f"{etiqueta}", options=opciones, index=index)

        if seleccion == "Otro (personalizado)":
            # Mostrar advertencia solo si el valor original no estaba en la lista
            if valor_actual not in lista_opciones and valor_actual.strip():
                st.warning(f"⚠️ El valor '{valor_actual}' no coincide con la lista para {etiqueta}. Puedes editarlo o seleccionar uno válido.")
            personalizado = st.text_input(f"Ingrese {etiqueta} personalizado", value=valor_actual)
            return personalizado.strip()
        else:
            return seleccion

    return {
        "calibre_primario": combo_personalizado(
            "Calibre del Conductor de Media Tensión",
            calibres["primario"],
            datos_proyecto.get("calibre_primario", "")
        ),
        "calibre_secundario": combo_personalizado(
            "Calibre del Conductor de Baja Tensión",
            calibres["secundario"],
            datos_proyecto.get("calibre_secundario", "")
        ),
        "calibre_neutro": st.text_input(
            "Calibre del Conductor Neutro",
            value=datos_proyecto.get("calibre_neutro", "")
        ),
        "calibre_piloto": combo_personalizado(
            "Calibre del Conductor de Hilo Piloto",
            calibres["piloto"],
            datos_proyecto.get("calibre_piloto", "")
        ),
        "calibre_retenidas": combo_personalizado(
            "Calibre del Cable de Retenida",
            calibres["retenidas"],
            datos_proyecto.get("calibre_retenidas", "")
        )
    }
