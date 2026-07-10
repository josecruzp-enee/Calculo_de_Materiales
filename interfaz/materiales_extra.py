# -*- coding: utf-8 -*-
# interfaz/materiales_extra.py

from __future__ import annotations

import pandas as pd
import streamlit as st


COLUMNAS = ["Materiales", "Unidad", "Cantidad"]

UNIDADES_DISPONIBLES = [
    "Unidad",
    "m",
    "m²",
    "m³",
    "kg",
    "lb",
    "galón",
    "litro",
    "rollo",
    "caja",
    "bolsa",
    "juego",
    "lote",
    "hora",
]


# =========================================================
# HELPERS
# =========================================================
def dataframe_vacio() -> pd.DataFrame:
    """
    Crea un DataFrame vacío con la estructura estándar.
    """
    return pd.DataFrame(columns=COLUMNAS)


def normalizar_dataframe(df: pd.DataFrame | None) -> pd.DataFrame:
    """
    Garantiza que el DataFrame tenga las columnas esperadas.

    No consolida materiales.
    Solo normaliza su estructura y tipos básicos.
    """

    if df is None or not isinstance(df, pd.DataFrame):
        return dataframe_vacio()

    df = df.copy()

    for columna in COLUMNAS:
        if columna not in df.columns:
            if columna == "Cantidad":
                df[columna] = 0.0
            else:
                df[columna] = ""

    df = df[COLUMNAS]

    df["Materiales"] = (
        df["Materiales"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["Unidad"] = (
        df["Unidad"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["Cantidad"] = pd.to_numeric(
        df["Cantidad"],
        errors="coerce",
    ).fillna(0.0)

    return df


# =========================================================
# ESTADO
# =========================================================
def inicializar_materiales_extra() -> None:
    """
    Inicializa el estado de materiales adicionales.

    También normaliza datos antiguos que pudieran existir
    en st.session_state.
    """

    if "materiales_extra" not in st.session_state:
        st.session_state["materiales_extra"] = dataframe_vacio()
        return

    st.session_state["materiales_extra"] = normalizar_dataframe(
        st.session_state.get("materiales_extra")
    )


# =========================================================
# OPERACIONES
# =========================================================
def agregar_material(
    nombre: str,
    unidad: str,
    cantidad: float,
) -> bool:
    """
    Agrega un material adicional al estado de Streamlit.

    Retorna:
        True  -> material agregado.
        False -> datos inválidos.
    """

    inicializar_materiales_extra()

    nombre_limpio = str(nombre or "").strip()
    unidad_limpia = str(unidad or "").strip()

    try:
        cantidad_num = float(cantidad)
    except (TypeError, ValueError):
        return False

    if not nombre_limpio:
        return False

    if not unidad_limpia:
        unidad_limpia = "Unidad"

    if cantidad_num <= 0:
        return False

    df_actual = normalizar_dataframe(
        st.session_state.get("materiales_extra")
    )

    nuevo_material = pd.DataFrame(
        [
            {
                "Materiales": nombre_limpio,
                "Unidad": unidad_limpia,
                "Cantidad": cantidad_num,
            }
        ],
        columns=COLUMNAS,
    )

    st.session_state["materiales_extra"] = pd.concat(
        [df_actual, nuevo_material],
        ignore_index=True,
    )

    return True


def consolidar_materiales(
    df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Agrupa materiales repetidos por nombre y unidad.

    Ejemplo:
        Conductor THHN | m | 10
        Conductor THHN | m | 15

    Resultado:
        Conductor THHN | m | 25
    """

    if df is None:
        df = st.session_state.get(
            "materiales_extra",
            dataframe_vacio(),
        )

    df = normalizar_dataframe(df)

    if df.empty:
        return dataframe_vacio()

    df = df[
        (df["Materiales"] != "")
        & (df["Cantidad"] > 0)
    ].copy()

    if df.empty:
        return dataframe_vacio()

    df["Unidad"] = df["Unidad"].replace("", "Unidad")

    consolidado = (
        df.groupby(
            ["Materiales", "Unidad"],
            as_index=False,
            dropna=False,
        )
        .agg({"Cantidad": "sum"})
        .sort_values(
            by=["Materiales", "Unidad"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    return consolidado[COLUMNAS]


def limpiar_materiales() -> None:
    """
    Elimina todos los materiales adicionales.
    """

    st.session_state["materiales_extra"] = dataframe_vacio()


# =========================================================
# CALLBACKS DE INTERFAZ
# =========================================================
def _callback_agregar_material() -> None:
    """
    Callback del formulario de Streamlit.
    """

    nombre = st.session_state.get("material_extra_nombre", "")
    unidad = st.session_state.get("material_extra_unidad", "Unidad")
    cantidad = st.session_state.get("material_extra_cantidad", 1.0)

    agregado = agregar_material(
        nombre=nombre,
        unidad=unidad,
        cantidad=cantidad,
    )

    if agregado:
        st.session_state["material_extra_nombre"] = ""
        st.session_state["material_extra_cantidad"] = 1.0
        st.session_state["material_extra_mensaje"] = (
            "Material adicional agregado correctamente."
        )
        st.session_state["material_extra_error"] = ""
    else:
        st.session_state["material_extra_error"] = (
            "Ingrese un nombre y una cantidad mayor que cero."
        )
        st.session_state["material_extra_mensaje"] = ""


def _callback_limpiar_materiales() -> None:
    """
    Callback para borrar todos los materiales adicionales.
    """

    limpiar_materiales()

    st.session_state["material_extra_mensaje"] = (
        "Se eliminaron los materiales adicionales."
    )
    st.session_state["material_extra_error"] = ""


# =========================================================
# INTERFAZ
# =========================================================
def render_materiales_extra(
    titulo: str = "Materiales adicionales",
    mostrar_descripcion: bool = True,
) -> pd.DataFrame:
    """
    Renderiza la interfaz para administrar materiales extra.

    Permite:
    - Agregar materiales manualmente.
    - Editar cantidades, unidades y nombres.
    - Eliminar filas desde el editor.
    - Consolidar materiales repetidos.
    - Limpiar toda la tabla.

    Retorna:
        DataFrame consolidado de materiales adicionales.
    """

    inicializar_materiales_extra()

    st.markdown(f"### {titulo}")

    if mostrar_descripcion:
        st.caption(
            "Agregue materiales que no fueron incluidos automáticamente "
            "en el cálculo principal. Estos materiales se incorporarán "
            "al listado final del proyecto."
        )

    _mostrar_mensajes()

    with st.form(
        key="form_materiales_extra",
        clear_on_submit=False,
    ):
        col_nombre, col_unidad, col_cantidad = st.columns(
            [3.5, 1.5, 1.5]
        )

        with col_nombre:
            st.text_input(
                "Material",
                key="material_extra_nombre",
                placeholder="Ejemplo: Cinta aislante",
            )

        with col_unidad:
            st.selectbox(
                "Unidad",
                options=UNIDADES_DISPONIBLES,
                key="material_extra_unidad",
            )

        with col_cantidad:
            st.number_input(
                "Cantidad",
                min_value=0.0,
                value=1.0,
                step=1.0,
                key="material_extra_cantidad",
            )

        st.form_submit_button(
            "➕ Agregar material",
            type="primary",
            on_click=_callback_agregar_material,
            use_container_width=True,
        )

    st.markdown("#### Materiales registrados")

    df_actual = normalizar_dataframe(
        st.session_state.get("materiales_extra")
    )

    if df_actual.empty:
        st.info(
            "No se han agregado materiales adicionales."
        )
        return dataframe_vacio()

    df_editado = st.data_editor(
        df_actual,
        key="editor_materiales_extra",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Materiales": st.column_config.TextColumn(
                "Material",
                help="Nombre o descripción del material.",
                required=True,
                width="large",
            ),
            "Unidad": st.column_config.TextColumn(
                "Unidad",
                help="Unidad de medida del material.",
                required=True,
                width="small",
            ),
            "Cantidad": st.column_config.NumberColumn(
                "Cantidad",
                help="Cantidad requerida.",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                required=True,
                width="small",
            ),
        },
    )

    df_editado = normalizar_dataframe(df_editado)

    st.session_state["materiales_extra"] = df_editado

    col_consolidar, col_limpiar = st.columns(2)

    with col_consolidar:
        if st.button(
            "🔄 Consolidar repetidos",
            key="btn_consolidar_materiales_extra",
            use_container_width=True,
        ):
            st.session_state["materiales_extra"] = (
                consolidar_materiales(df_editado)
            )

            st.session_state["material_extra_mensaje"] = (
                "Los materiales repetidos fueron consolidados."
            )

            st.session_state["material_extra_error"] = ""

            st.rerun()

    with col_limpiar:
        st.button(
            "🗑️ Limpiar materiales",
            key="btn_limpiar_materiales_extra",
            on_click=_callback_limpiar_materiales,
            use_container_width=True,
        )

    materiales_finales = consolidar_materiales(
        st.session_state.get("materiales_extra")
    )

    _mostrar_resumen(materiales_finales)

    return materiales_finales


def _mostrar_mensajes() -> None:
    """
    Muestra mensajes generados por las operaciones de la interfaz.
    """

    mensaje = st.session_state.pop(
        "material_extra_mensaje",
        "",
    )

    error = st.session_state.pop(
        "material_extra_error",
        "",
    )

    if mensaje:
        st.success(mensaje)

    if error:
        st.error(error)


def _mostrar_resumen(df: pd.DataFrame) -> None:
    """
    Muestra un pequeño resumen de los materiales adicionales.
    """

    if df is None or df.empty:
        return

    cantidad_registros = len(df)
    cantidad_total = pd.to_numeric(
        df["Cantidad"],
        errors="coerce",
    ).fillna(0).sum()

    st.caption(
        f"Materiales consolidados: **{cantidad_registros}** · "
        f"Suma de cantidades: **{cantidad_total:,.2f}**"
    )


# =========================================================
# EXPORT
# =========================================================
def obtener_materiales_finales() -> pd.DataFrame:
    """
    Devuelve los materiales adicionales consolidados.

    Esta función puede utilizarse desde el orquestador,
    generador de reportes o consolidación general.
    """

    inicializar_materiales_extra()

    df = consolidar_materiales()

    if df is None or df.empty:
        return dataframe_vacio()

    return df.copy()


# =========================================================
# COMPATIBILIDAD
# =========================================================
def render() -> pd.DataFrame:
    """
    Alias para integrar este módulo como una sección estándar
    de la aplicación.
    """

    return render_materiales_extra()
