# -*- coding: utf-8 -*-
"""
modulo/estilos_app.py  (solo header; SIN título/subtítulo)
Estilo visual global para la app Streamlit (ENEE).
- Renderiza SOLO el header institucional fijo (sin H1 ni subtítulo)
- Tokens de color / tipografía
- Modo compacto para reducir espacios
- Helpers: card, end_card, tabs, big_primary_button, json_box
Compatibilidad: Python 3.8+
"""

from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List
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
def _resolver_ruta_imagen(nombre: str) -> Optional[Path]:
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


def _img_to_base64(ruta: Optional[Path]) -> str:
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
    layout_wide: bool = True,
    sidebar_state: str = "expanded",
    page_icon: str = "⚡",
    header_height: int = 46,   # altura del header fijo
    spacer_px: int = 4,        # (queda por si lo usas en tu propio título)
    compact: bool = True,      # reduce paddings/márgenes globales
    show_banner: bool = False  # no se usa por defecto
) -> None:
    """
    Aplica tema global + header institucional (SIN título ni subtítulo).
    Maneja el H1/© desde tu propia vista (ej. interfaz/base.py).
    """

    # Config de página (Streamlit falla si se llama 2 veces; ignoramos)
    try:
        st.set_page_config(
            page_title="Cálculo de materiales · ENEE",
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
        "<style>:root {--enee-header-h:" + str(header_height) + "px; --enee-spacer:" + str(spacer_px) + "px;}</style>",
        unsafe_allow_html=True,
    )

    # ======== CSS GLOBAL (tokens + look) ========
    st.markdown(
        """
        <style>
        :root {
            --enee-primary: #C62828;             /* rojo ENEE */
            --enee-primary-700: #B71C1C;
            --enee-bg: #FFFFFF;
            --enee-surface: #F5F7FB;             /* tarjetas */
            --enee-text: #111827;                /* gris muy oscuro */
            --enee-muted: #6B7280;
            --enee-border: #E5E7EB;
            --enee-success: #10B981;
            --enee-warning: #F59E0B;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background: var(--enee-bg);
            color: var(--enee-text);
            font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial,
                         "Noto Sans", "Liberation Sans", "Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol", sans-serif;
        }

        /* ===== HEADER (solo barra) ===== */
        .enee-header {
            position: fixed; top: 0; left: 0; width: 100%;
            background: linear-gradient(90deg, #ffffff 0%, #FFE5E5 45%, #ffffff 100%);
            border-bottom: 4px solid var(--enee-primary);
            display: flex; align-items: center; gap: 10px;
            padding: 6px 12px;
            z-index: 999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            height: var(--enee-header-h);
        }
        .enee-header img { height: calc(var(--enee-header-h) - 20px); }
        .enee-brand { display:flex; flex-direction:column; }
        .enee-brand strong { font-size: 14px; }
        .enee-brand small { color: var(--enee-muted); font-size: 12.5px; margin-top: -2px; }

        /* ===== CONTENEDOR CENTRAL ===== */
        div.block-container {
            /* pegamos el contenido porque ya no hay título aquí */
            margin-top: calc(var(--enee-header-h) + 6px) !important;
            padding-top: 0.4rem !important;
            padding-bottom: 0.8rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }

        /* ===== CARDS ===== */
        .enee-card {
            background: var(--enee-surface);
            border: 1px solid var(--enee-border);
            border-radius: 14px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(17,24,39,0.04);
            margin-bottom: 14px;
        }
        .enee-card h3 { margin: 0 0 10px 0; font-size: 18px; }

        /* ===== INPUTS ===== */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {
            border-radius: 12px !important;
            border: 1px solid var(--enee-border) !important;
            background: #FAFBFE !important;
        }

        /* ===== TABLAS ===== */
        .stDataFrame, .stTable {
            border-radius: 12px; overflow: hidden; border: 1px solid var(--enee-border);
        }

        /* ===== BOTONES ===== */
        .stButton button {
            background: var(--enee-primary);
            border: 1px solid var(--enee-primary-700);
            color: #fff; font-weight: 600;
            border-radius: 12px; padding: 8px 14px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.04);
        }
        .stButton button:hover { background: var(--enee-primary-700); border-color: var(--enee-primary-700); }

        /* ===== ALERTAS ===== */
        .stAlert { border-radius: 12px; }

        /* ===== SIDEBAR ===== */
        section[data-testid="stSidebar"] > div {
            background: var(--enee-surface);
            border-right: 1px solid var(--enee-border);
        }

        /* ===== COMPACTACIÓN SUAVE ===== */
        h1,h2,h3,h4,h5 { font-weight: 700; }
        .stTextInput, .stSelectbox, .stDateInput { margin-bottom: 0.35rem !important; }
        [data-testid="stDataFrame"] { margin: 0.25rem 0 !important; }
        [data-testid="stVerticalBlock"] { gap: 0.35rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ===== HEADER (solo barra) =====
    header_html = ["<div class='enee-header'>"]
    if logo_b64:
        header_html.append("<img src='data:image/png;base64," + logo_b64 + "' alt='ENEE Logo'/>")
    header_html.append(
        "<div class='enee-brand'>"
        "<strong>Gerencia de Distribución – Empresa Nacional de Energía Eléctrica (ENEE)</strong>"
        "<small>Sistema interno para proyectos de distribución</small>"
        "</div>"
    )
    header_html.append("</div>")
    st.markdown("".join(header_html), unsafe_allow_html=True)

    # (Opcional) Imagen decorativa ancha (no recomendada si buscas compactar)
    if show_banner and encabezado_b64:
        st.markdown(
            "<div style='margin-top:.2rem;'><img alt='Encabezado' src='data:image/jpeg;base64," +
            encabezado_b64 +
            "' style='width:100%;max-height:110px;object-fit:cover;border-radius:8px;'/></div>",
            unsafe_allow_html=True,
        )

    # Footer discreto
    st.markdown(
        """
        <style> footer {visibility:hidden;} </style>
        """,
        unsafe_allow_html=True,
    )

    if compact:
        st.markdown(
            """
            <style>
              .stTextInput, .stSelectbox, .stDateInput, .stNumberInput { margin-bottom: 0.3rem !important; }
              [data-testid="stVerticalBlock"] { gap: 0.28rem !important; }
              [data-testid="stDataFrame"] { margin: 0.2rem 0 !important; }
              .stButton button { padding: 6px 12px; border-radius: 10px; }
            </style>
            """,
            unsafe_allow_html=True,
        )


# ========= HELPERS DE UI =========
@contextmanager
def card(titulo: str, icono: str = "📄"):
    """Contenedor tipo tarjeta con título."""
    st.markdown("<div class='enee-card'><h3>" + icono + " " + titulo + "</h3>", unsafe_allow_html=True)
    try:
        yield st.container()
    finally:
        end_card()


def end_card():
    st.markdown("</div>", unsafe_allow_html=True)


def tabs(labels: List[str]):
    """Atajo a st.tabs para homogeneidad."""
    return st.tabs(labels)


def big_primary_button(texto: str, key: Optional[str] = None, disabled: bool = False) -> bool:
    """Botón principal centrado y ancho completo para acciones clave (PDF/Excel)."""
    cols = st.columns([1, 6, 1])
    with cols[1]:
        return st.button(texto, key=key, use_container_width=True, disabled=disabled)


def json_box(obj, titulo: str = "Resumen"):
    """Muestra JSON formateado dentro de una card bonita."""
    import json as _json
    with card(titulo, "🧾"):
        st.code(_json.dumps(obj, indent=2, ensure_ascii=False), language="json")
        end_card()
