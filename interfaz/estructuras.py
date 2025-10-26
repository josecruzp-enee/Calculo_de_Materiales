# interfaz/estructuras.py
# -*- coding: utf-8 -*-

"""
Sección de entrada de estructuras con 3 modos:
1) Editar  -> Selección de poste / primario / secundario
2) Sumar   -> Retenidas / Conexión a tierra / Transformador
3) Guardar -> Persiste el punto y limpia todo

Comportamiento clave:
- Al pasar de EDITAR -> SUMAR: se limpian los campos de EDITAR
- Al pasar de SUMAR  -> GUARDAR: se limpian los campos de SUMAR al guardar
- Tras GUARDAR: se limpian TODOS y se vuelve a modo EDITAR

Cómo usar desde app.py (modo "clásico" de este proyecto):
    df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)

Cómo usar como UI completa (tu versión original):
    from interfaz.estructuras import seccion_entrada_estructuras
    seccion_entrada_estructuras(
        opciones_poste=[...],
        opciones_primario=[...],
        opciones_secundario=[...],
        opciones_retenidas=[...],
        opciones_tierra=[...],
        opciones_transformadores=[...],
        on_guardar=mi_callback_opcional
    )
"""

from typing import Callable, List, Optional, Dict, Any, Tuple
import streamlit as st
import pandas as pd
import os

# ---------------------------
# Utilidades de estado/limpieza
# ---------------------------

_PLACEHOLDER_DEFAULT = "— Selecciona —"

_EDIT_KEYS = ["poste", "primario", "secundario"]
_SUM_KEYS  = ["retenidas", "ctierra", "transformador"]


def _with_placeholder(opciones: List[str], placeholder: str) -> List[str]:
    """Asegura que la lista tenga un placeholder en la primera posición."""
    if not opciones:
        return [placeholder]
    lower_set = {o.strip().lower() for o in opciones}
    if placeholder.strip().lower() in lower_set:
        ops = [o for o in opciones if o.strip().lower() != placeholder.strip().lower()]
        return [placeholder] + ops
    if "-" in opciones and opciones[0].strip() == "-":
        return opciones
    return [placeholder] + opciones


def _init_state(placeholder: str):
    if "modo" not in st.session_state:
        st.session_state["modo"] = "editar"
    st.session_state["_placeholder"] = placeholder
    if "puntos" not in st.session_state:
        st.session_state["puntos"] = []


def _limpiar(keys: List[str]):
    """Limpia un grupo de keys al placeholder."""
    ph = st.session_state.get("_placeholder", _PLACEHOLDER_DEFAULT)
    for k in keys:
        st.session_state[k] = ph


def _limpiar_editar():
    _limpiar(_EDIT_KEYS)


def _limpiar_sumar():
    _limpiar(_SUM_KEYS)


def _limpiar_todo():
    _limpiar_editar()
    _limpiar_sumar()


# --------------------------------------------------------
# CARGADOR tipo (df, ruta) para compatibilidad con app.py
# --------------------------------------------------------

def _cargar_estructuras(modo: str = "local") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Devuelve (df_estructuras, ruta_estructuras) para mantener compatibilidad con app.py.
    - modo in {"app","cloud","web"} -> file_uploader
    - cualquier otro -> intenta leer 'estructura_lista.xlsx' en disco
    """
    modo = (modo or "local").strip().lower()

    if modo in {"app", "cloud", "web"}:
        archivo = st.file_uploader("Cargar 'estructura_lista.xlsx'", type=["xlsx"])
        if not archivo:
            # Aún no cargan archivo: devolvemos (None, None) pero sin romper el flujo
            return None, None
        try:
            df = pd.read_excel(archivo)
            nombre = getattr(archivo, "name", "estructura_lista.xlsx")
            return df, nombre
        except Exception as e:
            st.error(f"Error leyendo el Excel cargado: {e}")
            return None, None

    # modo "local" (o similar): leer desde disco
    ruta = "estructura_lista.xlsx"
    try:
        df = pd.read_excel(ruta)
        return df, ruta
    except FileNotFoundError:
        st.error(f"No se encontró el archivo local: {os.path.abspath(ruta)}")
        return None, ruta
    except Exception as e:
        st.error(f"Error leyendo {ruta}: {e}")
        return None, ruta


# ---------------------------
# UI principal (tu versión)
# ---------------------------

def _seccion_ui_entrada_estructuras(
    opciones_poste: List[str],
    opciones_primario: List[str],
    opciones_secundario: List[str],
    opciones_retenidas: List[str],
    opciones_tierra: List[str],
    opciones_transformadores: List[str],
    on_guardar: Optional[Callable[[Dict[str, Any]], None]] = None,
    placeholder: str = _PLACEHOLDER_DEFAULT,
    titulo: str = "Estructuras del Punto"
):
    """
    Renderiza la sección con 3 modos (Editar / Sumar / Guardar) y limpieza automática.
    NO retorna nada (pinta UI y escribe en session_state["puntos"] o llama on_guardar).
    """
    _init_state(placeholder)

    st.markdown(f"### {titulo}")

    # Opciones con placeholder asegurado al inicio
    ops_poste         = _with_placeholder(opciones_poste, placeholder)
    ops_primario      = _with_placeholder(opciones_primario, placeholder)
    ops_secundario    = _with_placeholder(opciones_secundario, placeholder)
    ops_retenidas     = _with_placeholder(opciones_retenidas, placeholder)
    ops_tierra        = _with_placeholder(opciones_tierra, placeholder)
    ops_transformador = _with_placeholder(opciones_transformadores, placeholder)

    # ---------------------------
    # Barra de acciones (3 modos)
    # ---------------------------
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✏️ Editar", use_container_width=True):
            st.session_state["modo"] = "editar"
            _limpiar_sumar()  # al cambiar a editar limpiamos SUMAR

    with c2:
        if st.button("➕ Sumar", use_container_width=True):
            st.session_state["modo"] = "sumar"
            _limpiar_editar()  # al cambiar a sumar limpiamos EDITAR

    with c3:
        if st.button("💾 Guardar punto", use_container_width=True):
            # Armamos el dict del punto con lo que haya hoy en el formulario
            data = {
                "poste":         st.session_state.get("poste", placeholder),
                "primario":      st.session_state.get("primario", placeholder),
                "secundario":    st.session_state.get("secundario", placeholder),
                "retenidas":     st.session_state.get("retenidas", placeholder),
                "ctierra":       st.session_state.get("ctierra", placeholder),
                "transformador": st.session_state.get("transformador", placeholder),
            }

            # Validación mínima (opcional): evitar guardar todo vacío
            if all(v == placeholder for v in data.values()):
                st.warning("No se guardó: completa al menos un campo antes de guardar.")
            else:
                try:
                    if on_guardar is not None:
                        on_guardar(data)
                    else:
                        st.session_state["puntos"].append(data)
                    st.success("✅ Punto guardado correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar el punto: {e}")
                finally:
                    _limpiar_todo()
                    st.session_state["modo"] = "editar"
                    st.rerun()  # asegura que la UI quede vacía

    st.divider()

    # ---------------------------
    # Contenido según modo activo
    # ---------------------------
    modo_ui = st.session_state.get("modo", "editar")

    if modo_ui == "editar":
        st.subheader("Editar características del poste")
        st.selectbox("Poste", ops_poste, key="poste")
        st.selectbox("Conductor primario", ops_primario, key="primario")
        st.selectbox("Conductor secundario", ops_secundario, key="secundario")

    elif modo_ui == "sumar":
        st.subheader("Agregar elementos al poste")
        st.selectbox("Retenidas", ops_retenidas, key="retenidas")
        st.selectbox("Conexión a tierra", ops_tierra, key="ctierra")
        st.selectbox("Transformador", ops_transformador, key="transformador")

    # ---------------------------
    # Vista rápida (opcional)
    # ---------------------------
    with st.expander("Vista rápida del punto actual (no guardado)"):
        st.write({
            "poste":         st.session_state.get("poste", placeholder),
            "primario":      st.session_state.get("primario", placeholder),
            "secundario":    st.session_state.get("secundario", placeholder),
            "retenidas":     st.session_state.get("retenidas", placeholder),
            "ctierra":       st.session_state.get("ctierra", placeholder),
            "transformador": st.session_state.get("transformador", placeholder),
        })

    # Listado de puntos guardados (si no usas callback)
    if on_guardar is None and st.session_state.get("puntos"):
        st.divider()
        st.caption("Puntos guardados en esta sesión:")
        st.table(st.session_state["puntos"])  # este es estructuras.py


# -------------------------------------------------------------------
# DISPATCHER: una sola API que soporta AMBOS USOS sin tocar app.py
# -------------------------------------------------------------------

def seccion_entrada_estructuras(*args, **kwargs):
    """
    Uso 1 (compatibilidad con app.py):
        df_estructuras, ruta_estructuras = seccion_entrada_estructuras(modo)
    Uso 2 (UI original):
        seccion_entrada_estructuras(opciones_poste=[...], ..., on_guardar=..., placeholder=..., titulo=...)

    Regla:
      - Si el primer argumento posicional es un str (p.ej. "app" / "local"), o si viene 'modo' en kwargs,
        actuamos como CARGADOR y devolvemos (df, ruta).
      - Si detectamos kwargs propios de la UI (opciones_poste, etc.), pintamos la UI y devolvemos (None, None)
        para no romper posibles desempaquetados.
    """
    # Detectar patrón "modo"
    if (len(args) == 1 and isinstance(args[0], str)) or ("modo" in kwargs and isinstance(kwargs["modo"], str)):
        modo = args[0] if (len(args) == 1 and isinstance(args[0], str)) else kwargs.get("modo", "local")
        return _cargar_estructuras(modo)

    # Detectar patrón UI (kwargs con opciones)
    ui_keys = {
        "opciones_poste",
        "opciones_primario",
        "opciones_secundario",
        "opciones_retenidas",
        "opciones_tierra",
        "opciones_transformadores",
    }
    if ui_keys & set(kwargs.keys()):
        # Llamar a la UI y retornar tupla neutra para evitar TypeError si el llamador desempaqueta.
        _seccion_ui_entrada_estructuras(**kwargs)
        return None, None

    # Si llega aquí, no sabemos qué quiso el llamador: intentamos cargar por defecto.
    return _cargar_estructuras("local")
