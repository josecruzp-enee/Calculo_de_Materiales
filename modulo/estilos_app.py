# -*- coding: utf-8 -*-
"""
modulo/estilos_app.py
UI para Streamlit (ENEE) en un solo archivo:
- Cabecera institucional fija y configurable
- Tokens de color / tipografía
- Modo compacto para reducir espacios
- Helpers: card, end_card, tabs, big_primary_button, json_box
"""

from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import base64
import streamlit as st


# ========= RUTAS =========
REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"
DATA_IMG_DIR = REPO_ROOT / "data" / "imagenes"
DATA_DIR = REPO_ROOT / "data"
LEGACY_MODULO_DIR = Path(__file__).resolve().parent

NOMBRE_LOGO_BLANCO = "Imagen_ENEE.png"
NOMBRE_LOGO_ROJO   = "Imagen_ENEE_Distribucion.png"
NOMBRE_ENCABEZADO  = "Imagen Encabezado.jpg"


# ========= UTILIDADES DE IMAGEN =========
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


# ========= INICIALIZACIÓN / TEMA =========
def aplicar_estilos(
    usar_encabezado_rojo: bool = True,
    titulo: str = "Cálculo de Materiales para Proyecto de Distribución",
    subtitulo: str = "© 2025 · Sistema de Cálculo de Materiales | ENEE · Gerencia de Distribución",
    layout_wide: bool = True,
    sidebar_state: str = "expanded",
    page_icon: str = "⚡",
    *,
    header_height: int = 48,   # altura del header fijo
    spacer_px: int = 6,        # espacio entre header y título
    compact: bool = True,      # reduce paddings/márgenes globales
    show_banner: bool = False  # muestra (o no) imagen ancha decorativa
) -> None:
    """Aplica tema global + cabecera institucional (robusto a rutas)."""

    # Config de página (Streamlit falla si se llama 2 veces; ignoramos)
    try:
        st.set_page_config(
            page_title=titulo,
            page_icon=page_icon,
            layout="wide" if layout_wide else "centered",
            initial_sidebar_state=sidebar_state,
        )
    except Exception:
        pass

    # Resolver imágenes
    ruta_logo = _resolver_ruta_imagen(NOMBRE_LOGO_ROJO if usar_encabezado_rojo else NOMBRE_LOGO_BLANCO)
    ruta_encabezado = _resolver_ruta_imagen(NOMBRE_ENCABEZADO)

    logo_b64 = _img_to_base64(ruta_logo)
    encabezado_b64 = _img_to_base64(ruta_encabezado)

    # Variables CSS para controlar alturas/espacios
    st.markdown(
        f"""
        <style>
          :root {{
            --enee-header-h: {header_height}px;
            --enee-spacer: {spacer_px}px;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ======== CSS GLOBAL (tokens + look) ========
    st.markdown(
        f"""
        <style>
        :root {{
            --enee-primary: #C62828;             /* rojo ENEE */
            --enee-primary-700: #B71C1C;
            --enee-bg: #FFFFFF;
            --enee-surface: #F5F7FB;             /* tarjetas */
            --enee-text: #111827;                /* gris muy oscuro */
            --enee-muted: #6B7280;
            --enee-border: #E5E7EB;
            --enee-success: #10B981;
            --enee-warning: #F59E0B;
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background: var(--enee-bg);
            color: var(--enee-text);
            font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", "Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol", sans-serif;
        }}

        /* ===== CABECERA ===== */
        .enee-header {{
            position: fixed; top: 0; left: 0; width: 100%;
            background: {"linear-gradient(90deg, #ffffff 0%, #FFE5E5 45%, #ffffff 100%)" if usar_encabezado_rojo else "linear-gradient(90deg, #ffffff 0%, #ffffff 100%)"};
            border-bottom: 4px solid var(--enee-primary);
            display: flex; align-items: center; gap: 10px;
            padding: 6px 12px;
            z-index: 999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            height: var(--enee-header-h);
        }}
        .enee-header img {{ height: calc(var(--enee-header-h) - 20px); }}
        .enee-brand {{ display:flex; flex-direction:column; }}
        .enee-brand strong {{ font-size: 14px; }}
        .enee-brand small {{ color: var(--enee-muted); font-size: 12.5px; margin-top: -2px; }}

        /* ===== TÍTULO / SUBTÍTULO ===== */
        .enee-pagetitle {{ margin-top: calc(var(--enee-header-h) + var(--enee-spacer)); }}
        .enee-title {{ font-size: 30px; font-weight: 800; margin: 2px 0 0 0; letter-spacing: -0.02em; }}
        .enee-subtitle {{ color: var(--enee-muted); font-size: 12.5px; margin: 2px 0 6px 0; }}

        /* ===== CONTENEDOR CENTRAL ===== */
        div.block-container {{
            padding-top: 0.4rem !important;
            padding-bottom: 0.8rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }}

        /* ===== CARDS ===== */
        .enee-card {{
            background: var(--enee-surface);
            border: 1px solid var(--enee-border);
            border-radius: 14px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(17,24,39,0.04);
            margin-bottom: 14px;
        }}
        .enee-card h3 {{ margin: 0 0 10px 0; font-size: 18px; }}

        /* ===== INPUTS ===== */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {{
            border-radius: 12px !important;
            border: 1px solid var(--enee-border) !important;
            background: #FAFBFE !important;
        }}

        /* ===== TABLAS ===== */
        .stDataFrame, .stTable {{
            border-radius: 12px; overflow: hidden; border: 1px solid var(--enee-border);
        }}

        /* ===== BOTONES ===== */
        .stButton button {{
            background: var(--enee-primary);
            border: 1px solid var(--enee-primary-700);
            color: #fff; font-weight: 600;
            border-radius: 12px; padding: 8px 14px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.04);
        }}
        .stButton button:hover {{ background: var(--enee-primary-700); border-color: var(--enee-primary-700); }}

        /* ===== ALERTAS ===== */
        .stAlert {{ border-radius: 12px; }}

        /* ===== SIDEBAR ===== */
        section[data-testid="stSidebar"] > div {{
            background: var(--enee

