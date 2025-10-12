# -*- coding: utf-8 -*-
"""
estilos_app.py
Define los estilos visuales globales de la aplicación Streamlit.
Colores y tipografía inspirados en la línea institucional ENEE.
"""

import streamlit as st
import os
import base64

def aplicar_estilos(usar_encabezado_rojo=False):
    """Aplica estilos globales con encabezado institucional ENEE."""

    base_dir = os.path.dirname(__file__)
    logo_blanco = os.path.join(base_dir, "Imagen_ENEE.png")
    logo_rojo = os.path.join(base_dir, "Imagen_ENEE_Distribucion.png")

    # Leer y convertir imagen a base64 (para que funcione en Streamlit Cloud)
    def img_to_base64(ruta):
        with open(ruta, "rb") as img:
            return base64.b64encode(img.read()).decode()

    logo_b64 = img_to_base64(logo_rojo if usar_encabezado_rojo else logo_blanco)

    # ======== CSS GLOBAL ========
    st.markdown(
        """
        <style>
        /* ======== CONTENEDOR PRINCIPAL ======== */
        div.block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            margin-top: 110px !important;
        }

        h1, h2, h3, h4, h5 {
            color: #003366;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }

        p, label, span, div {
            font-family: 'Segoe UI', sans-serif;
        }

        hr {
            border: 1px solid #cccccc;
            margin: 0.8rem 0;
        }

        /* ======== BOTONES ======== */
        .stButton>button {
            background-color: #004080 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.45rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            transition: all 0.3s ease-in-out;
        }

        .stButton>button:hover {
            background-color: #0066cc !important;
            transform: scale(1.03);
        }

        /* ======== SELECTBOX ======== */
        .stSelectbox div[data-baseweb="select"],
        .stTextInput input, .stNumberInput input {
            border-radius: 6px !important;
            background-color: #f1f4f8 !important;
        }

        /* ======== TABLAS ======== */
        [data-testid="stDataFrame"] table {
            border: 1px solid #cccccc;
            border-radius: 8px;
            font-size: 0.9rem;
        }

        /* ======== CABECERA ======== */
        .header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #ffffff;
            border-bottom: 3px solid #cc0000;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 0.4rem 1rem;
            z-index: 999;
            box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease-in-out;
        }

        .header img {
            height: 60px;
        }

        .header .titulo h1 {
            font-size: 1.4rem;
            margin: 0;
            color: #003366;
        }

        .header .titulo h4 {
            font-size: 0.9rem;
            margin: 0;
            color: #444444;
        }

        /* ======== FOOTER ======== */
        footer { visibility: hidden; }
        .footer {
            text-align: center;
            font-size: 13px;
            color: #888888;
            margin-top: 40px;
            border-top: 1px solid #cccccc;
            padding-top: 10px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    # ====== ENCABEZADO ======
    st.markdown(
        f"""
        <div class='header'>
            <img src='data:image/png;base64,{logo_b64}' alt='ENEE Logo'>
            <div class='titulo'>
                <h1>⚡ Sistema de Cálculo de Materiales</h1>
                <h4>Gerencia de Distribución – Empresa Nacional de Energía Eléctrica (ENEE)</h4>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ====== FOOTER ======
    st.markdown(
        """
        <div class='footer'>
            © 2025 - Sistema de Cálculo de Materiales | ENEE - Gerencia de Distribución
        </div>
        """,
        unsafe_allow_html=True
    )
