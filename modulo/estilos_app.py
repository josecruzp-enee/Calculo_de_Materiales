# -*- coding: utf-8 -*-
"""
estilos_app.py
Define los estilos visuales globales de la aplicación Streamlit.
Colores y tipografía inspirados en la línea institucional ENEE.
"""

import streamlit as st

def aplicar_estilos():
    """Aplica estilos CSS globales para toda la app."""
    st.markdown(
        """
        <style>

        /* ======== GENERAL ======== */
        div.block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        h1, h2, h3, h4, h5 {
            color: #003366; /* azul institucional */
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
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
            padding: 0.4rem 0.9rem !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            transition: 0.3s;
        }

        .stButton>button:hover {
            background-color: #0066cc !important;
            color: #ffffff !important;
            transform: scale(1.02);
        }

        /* ======== SELECTBOX ======== */
        .stSelectbox, .stTextInput, .stNumberInput {
            border-radius: 6px !important;
            background-color: #f8f9fa !important;
        }

        /* ======== RADIO BUTTONS ======== */
        div[role="radiogroup"] label {
            font-weight: 600;
        }

        /* ======== TABLAS ======== */
        [data-testid="stDataFrame"] table {
            border: 1px solid #cccccc;
            border-radius: 8px;
            font-size: 0.9rem;
        }

        /* ======== FOOTER ======== */
        footer {
            visibility: hidden;
        }
        .footer {
            text-align: center;
            font-size: 13px;
            color: #888888;
            margin-top: 30px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    # Pie de página institucional
    st.markdown(
        """
        <div class='footer'>
            © 2025 - Sistema de Cálculo de Materiales | ENEE - Gerencia de Distribución
        </div>
        """,
        unsafe_allow_html=True
    )
