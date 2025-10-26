# ====== PARCHE DE COMPATIBILIDAD (PEGAR AL FINAL DE estructuras.py) ======
from typing import Tuple, Optional, Dict, Any
import os
import pandas as pd
import streamlit as st

# 1) Renombra tu función UI original si aún no está renombrada
try:
    _seccion_ui_entrada_estructuras  # ya existe
except NameError:
    _seccion_ui_entrada_estructuras = seccion_entrada_estructuras  # alias a tu UI

# 2) Cargador tolerante que devuelve (df, ruta) según 'modo'
def _cargar_estructuras(modo: str = "local") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    modo = (modo or "local").strip().lower()

    # Reusar si ya se eligió en esta sesión
    ruta_sesion = st.session_state.get("ruta_estructuras")
    if ruta_sesion and os.path.isfile(ruta_sesion):
        try:
            return pd.read_excel(ruta_sesion), ruta_sesion
        except Exception as e:
            st.error(f"Error leyendo {ruta_sesion}: {e}")

    # Candidatas locales y por variable de entorno
    ruta_env = os.environ.get("ESTRUCTURAS_PATH")
    candidatas = []
    if ruta_env:
        candidatas.append(ruta_env)
    candidatas += [
        "estructura_lista.xlsx",
        os.path.join(os.getcwd(), "estructura_lista.xlsx"),
        os.path.join(os.path.dirname(__file__), "..", "estructura_lista.xlsx"),
        os.path.join(os.path.dirname(__file__), "estructura_lista.xlsx"),
    ]

    def _leer_primera_existente(paths):
        for p in paths:
            p_abs = os.path.abspath(p)
            if os.path.isfile(p_abs):
                try:
                    df = pd.read_excel(p_abs)
                    st.session_state["ruta_estructuras"] = p_abs
                    return df, p_abs
                except Exception as e:
                    st.error(f"Error leyendo {p_abs}: {e}")
        return None, None

    # Modos que obligan a uploader (útil en Cloud)
    if modo in {"app", "cloud", "web"}:
        archivo = st.file_uploader("Cargar 'estructura_lista.xlsx'", type=["xlsx"])
        if not archivo:
            # Intenta también local por si estás desarrollando en tu PC
            df, ruta = _leer_primera_existente(candidatas)
            if df is not None:
                return df, ruta
            with st.expander("No se encontró archivo local. Opciones para continuar"):
                st.write(
                    "• Sube el archivo con el botón arriba.\n"
                    "• O define la variable de entorno `ESTRUCTURAS_PATH`.\n"
                    "• O coloca `estructura_lista.xlsx` en la raíz del proyecto."
                )
            return None, None
        try:
            df = pd.read_excel(archivo)
            nombre = getattr(archivo, "name", "estructura_lista.xlsx")
            st.session_state["ruta_estructuras"] = nombre
            return df, nombre
        except Exception as e:
            st.error(f"Error leyendo el Excel cargado: {e}")
            return None, None

    # Modo "local": intenta rutas; si falla, cae a uploader
    df, ruta = _leer_primera_existente(candidatas)
    if df is not None:
        return df, ruta

    st.info("No se encontró un archivo local de estructuras. Sube uno para continuar.")
    archivo = st.file_uploader("Cargar 'estructura_lista.xlsx'", type=["xlsx"], key="uploader_local_fallback")
    if archivo:
        try:
            df = pd.read_excel(archivo)
            nombre = getattr(archivo, "name", "estructura_lista.xlsx")
            st.session_state["ruta_estructuras"] = nombre
            return df, nombre
        except Exception as e:
            st.error(f"Error leyendo el Excel cargado: {e}")
            return None, None

    with st.expander("Detalles de búsqueda de archivo"):
        st.write("Se intentaron estas rutas:")
        for p in candidatas:
            st.write(f"• {os.path.abspath(p)}")
    return None, None

# 3) Dispatcher que soporta AMBOS USOS sin tocar app.py
def seccion_entrada_estructuras(*args, **kwargs):
    """
    Uso 1 (como en app.py):
        df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)
    Uso 2 (UI):
        seccion_entrada_estructuras(opciones_poste=[...], ..., opciones_transformadores=[...], on_guardar=...)
    """
    # ¿Nos llamaron con un único argumento 'modo' o con kw 'modo'?
    if (len(args) == 1 and isinstance(args[0], str)) or ("modo" in kwargs and isinstance(kwargs.get("modo"), str)):
        modo = args[0] if (len(args) == 1 and isinstance(args[0], str)) else kwargs.get("modo", "local")
        return _cargar_estructuras(modo)

    # ¿Nos llamaron con kwargs propios de la UI?
    ui_keys = {
        "opciones_poste",
        "opciones_primario",
        "opciones_secundario",
        "opciones_retenidas",
        "opciones_tierra",
        "opciones_transformadores",
        "on_guardar",
        "placeholder",
        "titulo",
    }
    if ui_keys & set(kwargs.keys()):
        _seccion_ui_entrada_estructuras(**kwargs)
        # Para no romper si el llamador desempaqueta en dos variables:
        return None, None

    # Si es ambiguo, cae por defecto al cargador local (compatibilidad)
    return _cargar_estructuras("local")
# ====== FIN PARCHE ======

