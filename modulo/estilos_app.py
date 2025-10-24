# -*- coding: utf-8 -*-
"""
estilos_app.py
Define los estilos visuales globales de la aplicación Streamlit.
Colores y tipografía inspirados en la línea institucional ENEE.
"""

from pathlib import Path
import base64
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"
DATA_IMG_DIR = REPO_ROOT / "data" / "imagenes"
DATA_DIR = REPO_ROOT / "data"                       
LEGACY_MODULO_DIR = Path(__file__).resolve().parent

NOMBRE_LOGO_BLANCO = "Imagen_ENEE.png"
NOMBRE_LOGO_ROJO   = "Imagen_ENEE_Distribucion.png"
NOMBRE_ENCABEZADO  = "Imagen Encabezado.jpg"        

def _resolver_ruta_imagen(nombre: str) -> Path | None:
    """Busca por prioridad: assets/ → data/imagenes/ → data/ → modulo/ (legado)."""
    for ruta in (
        ASSETS_DIR / nombre,
        DATA_IMG_DIR / nombre,
        DATA_DIR / nombre,                 
        LEGACY_MODULO_DIR / nombre,
    ):
        if ruta.is_file():
            return ruta
    return None


def _img_to_base64(ruta: Path | None) -> str:
    """Convierte imagen a base64; si ruta es None o no existe, retorna cadena vacía."""
    if not ruta or not ruta.is_file():
        return ""
    try:
        with open(ruta, "rb") as img:
            return base64.b64encode(img.read()).decode("utf-8")
    except Exception as e:
        st.warning(f"No se pudo leer la imagen '{ruta}': {e}")
        return ""

def aplicar_estilos(usar_encabezado_rojo: bool = False) -> None:
    """Aplica estilos globales con encabezado institucional ENEE (robusto a rutas)."""
    # Resolver imágenes
    ruta_logo = _resolver_ruta_imagen(NOMBRE_LOGO_ROJO if usar_encabezado_rojo else NOMBRE_LOGO_BLANCO)
    ruta_encabezado = _resolver_ruta_imagen(NOMBRE_ENCABEZADO)

    logo_b64 = _img_to_base64(ruta_logo)
    encabezado_b64 = _img_to_base64(ruta_encabezado)

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

        /* ======== SELECTBOX / INPUTS ======== */
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

    # ====== ENCABEZADO (usa imágenes si están disponibles) ======
    header_html = ["<div class='header'>"]
    if logo_b64:
        header_html.append(f"<img src='data:image/png;base64,{logo_b64}' alt='ENEE Logo'>")
    header_html.append(
        "<div class='titulo'>"
        "<h1>⚡ Sistema de Cálculo de Materiales</h1>"
        "<h4>Gerencia de Distribución – Empresa Nacional de Energía Eléctrica (ENEE)</h4>"
        "</div>"
    )
    header_html.append("</div>")
    st.markdown("".join(header_html), unsafe_allow_html=True)

    # (Opcional) Encabezado/gráfico adicional ancho si existe
    if encabezado_b64:
        st.markdown(
            f"<div style='margin-top: .5rem;'><img alt='Encabezado' "
            f"src='data:image/jpeg;base64,{encabezado_b64}' "
            f"style='width:100%;max-height:140px;object-fit:cover;border-radius:8px;'/></div>",
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

    # ====== Ajuste compacto global ======
    st.markdown("""
    <style>
        .block-container {padding-top: 0.8rem !important; padding-bottom: 0.8rem !important;}
        .stTextInput, .stSelectbox, .stDateInput {margin-bottom: 0.4rem !important;}
        .stButton>button {padding: 0.4rem 0.8rem !important; font-size: 0.9rem !important;}
        h3, h4 {margin-top: 0.5rem !important; margin-bottom: 0.4rem !important;}
    </style>
    """, unsafe_allow_html=True)

    # === Ajuste de estilo compacto visual ===
    st.markdown("""
    <style>
        /* Títulos más pequeños */
        h1, h2, h3 {
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
            font-weight: 600 !important;
        }

        /* Margen general compacto */
        div.block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }

        /* Botones más delgados */
        .stButton>button {
            padding: 0.25rem 0.6rem !important;
            font-size: 0.8rem !important;
            border-radius: 5px !important;
        }

        /* Inputs más cortos */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
            height: 32px !important;
            font-size: 0.9rem !important;
        }

        /* Reducir el espacio entre widgets */
        div[data-testid="stVerticalBlock"] {
            gap: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }

        /* Reducir el espacio en encabezados de secciones */
        h2, h3 {
            font-size: 1.05rem !important;
        }

        /* Reducir márgenes de DataFrames */
        [data-testid="stDataFrame"] {
            margin-top: -0.3rem !important;
            margin-bottom: 0.3rem !important;
        }

        /* Encabezados de tabla más pequeños */
        [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {
            font-size: 0.8rem !important;
            padding: 2px 6px !important;
        }

        /* Bordes más suaves */
        [data-testid="stDataFrame"] table {
            border-radius: 4px !important;
        }

        /* Sección de "Configuración de cables" más compacta */
        div[data-testid="stHorizontalBlock"] {
            gap: 0.8rem !important;
        }

        /* Evitar tanto blanco en secciones */
        section.main > div {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)
