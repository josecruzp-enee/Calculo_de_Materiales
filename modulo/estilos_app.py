# -*- coding: utf-8 -*-
"""
estilos_app.py
Define los estilos visuales globales de la aplicación Streamlit.
Colores y tipografía inspirados en la línea institucional ENEE.
"""

import streamlit as st
import os

def aplicar_estilos(usar_encabezado_rojo=False):
    """Aplica estilos CSS globales para toda la app, con encabezado institucional ENEE."""

    # ====== Rutas de los logos ======
    base_dir = os.path.dirname(__file__)
    logo_blanco = os.path.join(base_dir, "Imagen_ENEE.png")
    logo_rojo = os.path.join(base_dir, "Imagen_ENEE_Distribucion.png")

    # ====== CSS GLOBAL ======
    st.markdown(
        """
        <style>
        /* ======== GENERAL ======== */
        div.block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
            margin-top: 100px !important; /* deja espacio para el encabezado */
        }

        h1, h2, h3, h4, h5 {
            color: #003366; /* azul institucional */
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }

        h2, h3 {
            border-bottom: 2px solid #004080;
            padding-bottom: 0.2rem;
        }

        p, label, span, div {
            font-family: 'Segoe UI', sans-serif;
        }

        hr {
            border: 1px solid #cccccc;
            margin-top: 0.8rem;
            margin-bottom: 0.8rem;
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
            transition: 0.3s;
        }

        .stButton>button:hover {
            background-color: #0066cc !important;
            transform: scale(1.03);
        }

        /* ======== FILA DE BOTONES ======== */
        div[data-testid="stHorizontalBlock"] {
            justify-content: center !important;
            gap: 1rem !important;
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

        /* ======== CABECERA BLANCA ======== */
        .header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #ffffff;
            border-bottom: 3px solid #cc0000;
            display: flex;
            align-items: center;
            padding: 0.4rem 1rem;
            z-index: 999;
        }

        .header .logo {
            height: 55px;
            margin-right: 15px;
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

        /* ======== CABECERA ROJA ======== */
        .header-red {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #cc0000;
            text-align: center;
            padding: 0.3rem 0;
            z-index: 999;
        }

        .header-red .logo-red {
            height: 55px;
        }

        /* ======== FOOTER ======== */
        footer { visibility: hidden; }
        .footer {
            text-align: center;
            font-size: 13px;
            color: #888888;
            margin-top: 30px;
            border-top: 1px solid #cccccc;
            padding-top: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ====== CABECERA INSTITUCIONAL ======
    if usar_encabezado_rojo:
        st.markdown(
            f"""
            <div class='header-red'>
                <img src='file://{logo_rojo}' class='logo-red'>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class='header'>
                <img src='file://{logo_blanco}' class='logo'>
                <div class='titulo'>
                    <h1>⚡ Sistema de Cálculo de Materiales</h1>
                    <h4>Gerencia de Distribución – Empresa Nacional de Energía Eléctrica (ENEE)</h4>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ====== FOOTER INSTITUCIONAL ======
    st.markdown(
        """
        <div class='footer'>
            © 2025 - Sistema de Cálculo de Materiales | ENEE - Gerencia de Distribución
        </div>
        """,
        unsafe_allow_html=True
    )
