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

Cómo usar desde app.py:
from interfaz.estructuras import seccion_entrada_estructuras

seccion_entrada_estructuras(
    opciones_poste=["Madera", "Cemento"],
    opciones_primario=["1/0 ACSR", "3/0 ACSR", "4/0 ACSR"],
    opciones_secundario=["#2 ACSR", "1/0 ACSR"],
    opciones_retenidas=["R-0", "R-1", "R-2"],
    opciones_tierra=["Sin conexión", "Varilla 5/8\" x 8'", "Malla"],
    opciones_transformadores=["Ninguno", "25 kVA", "37.5 kVA", "50 kVA"],
    on_guardar=mi_funcion_guardar  # opcional; si no se pasa, guarda en session_state["puntos"]
)
"""

from typing import Callable, List, Optional, Dict, Any
import streamlit as st


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
    # Si ya existe un placeholder similar, no duplicar
    lower_set = {o.strip().lower() for o in opciones}
    if placeholder.strip().lower() in lower_set:
        # moverlo al inicio si estuviera en otra posición
        ops = [o for o in opciones if o.strip().lower() != placeholder.strip().lower()]
        return [placeholder] + ops
    # Si ya tienen "-" como placeholder, respétalo
    if "-" in opciones and opciones[0].strip() == "-":
        return opciones
    return [placeholder] + opciones


def _init_state(placeholder: str):
    if "modo" not in st.session_state:
        st.session_state["modo"] = "editar"
    # Guardamos el placeholder para limpieza consistente
    st.session_state["_placeholder"] = placeholder
    # Inicializamos contenedor de puntos si no existe
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


# ---------------------------
# UI principal
# ---------------------------

def seccion_entrada_estructuras(
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

    Args:
        opciones_poste: Lista de opciones para el tipo de poste.
        opciones_primario: Opciones para conductor primario.
        opciones_secundario: Opciones para conductor secundario.
        opciones_retenidas: Opciones de retenidas.
        opciones_tierra: Opciones de conexión a tierra.
        opciones_transformadores: Opciones de transformador.
        on_guardar: Callback opcional que recibe un dict con los datos del punto.
                    Si no se provee, se agregará a st.session_state["puntos"].
        placeholder: Texto de placeholder para selects.
        titulo: Título de la sección.
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
                "poste":        st.session_state.get("poste", placeholder),
                "primario":     st.session_state.get("primario", placeholder),
                "secundario":   st.session_state.get("secundario", placeholder),
                "retenidas":    st.session_state.get("retenidas", placeholder),
                "ctierra":      st.session_state.get("ctierra", placeholder),
                "transformador":st.session_state.get("transformador", placeholder),
            }

            # Validación mínima (opcional): evitar guardar todo vacío
            todo_placeholder = all(v == placeholder for v in data.values())
            if todo_placeholder:
                st.warning("No se guardó: completa al menos un campo antes de guardar.")
            else:
                try:
                    if on_guardar is not None:
                        on_guardar(data)
                    else:
                        # Default: guardar en session_state["puntos"]
                        st.session_state["puntos"].append(data)
                    st.success("✅ Punto guardado correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar el punto: {e}")
                finally:
                    # Limpiamos todo y regresamos a modo editar
                    _limpiar_todo()
                    st.session_state["modo"] = "editar"
                    st.rerun()  # asegura que la UI quede vacía

    st.divider()

    # ---------------------------
    # Contenido según modo activo
    # ---------------------------
    modo = st.session_state.get("modo", "editar")

    if modo == "editar":
        st.subheader("Editar características del poste")
        st.selectbox("Poste", ops_poste, key="poste")
        st.selectbox("Conductor primario", ops_primario, key="primario")
        st.selectbox("Conductor secundario", ops_secundario, key="secundario")

    elif modo == "sumar":
        st.subheader("Agregar elementos al poste")
        st.selectbox("Retenidas", ops_retenidas, key="retenidas")
        st.selectbox("Conexión a tierra", ops_tierra, key="ctierra")
        st.selectbox("Transformador", ops_transformador, key="transformador")

    # ---------------------------
    # Vista rápida (opcional)
    # ---------------------------
    with st.expander("Vista rápida del punto actual (no guardado)"):
        st.write({
            "poste":        st.session_state.get("poste", placeholder),
            "primario":     st.session_state.get("primario", placeholder),
            "secundario":   st.session_state.get("secundario", placeholder),
            "retenidas":    st.session_state.get("retenidas", placeholder),
            "ctierra":      st.session_state.get("ctierra", placeholder),
            "transformador":st.session_state.get("transformador", placeholder),
        })

    # Listado de puntos guardados (si no usas callback)
    if on_guardar is None and st.session_state.get("puntos"):
        st.divider()
        st.caption("Puntos guardados en esta sesión:")
        st.table(st.session_state["puntos"])
