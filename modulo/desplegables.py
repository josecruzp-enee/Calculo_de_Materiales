# modulo/desplegables.py
# -*- coding: utf-8 -*-

import os
import pandas as pd
import streamlit as st

# === Rutas ===
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
RUTA_EXCEL = os.path.join(REPO_ROOT, "data", "Estructura_datos.xlsx")

# Campos que espera tu app
CAMPOS = [
    "Poste",
    "Primario",
    "Secundario",
    "Retenidas",
    "Conexiones a tierra",
    "Transformadores",
]


# =========================
# Utilidades
# =========================
def _repite_token(token: str, n: int) -> str:
    """Devuelve 'X + X + ...' n veces, o '' si no hay token o n <= 0."""
    token = (token or "").strip()
    if not token or n <= 0:
        return ""
    return " + ".join([token] * n)


def _contar_tokens(previo: str) -> dict:
    """
    Cuenta repeticiones en una cadena tipo:
      'R-1 + R-1 + A-I-5' -> {'R-1': 2, 'A-I-5': 1}
    Tolerante a separadores ' + ' o ' , ' del historial anterior.
    """
    if not previo:
        return {}
    texto = str(previo).replace(",", " + ")
    piezas = [p.strip() for p in texto.split("+") if p.strip()]
    out = {}
    for p in piezas:
        out[p] = out.get(p, 0) + 1
    return out


# =========================
# Cargar catálogo
# =========================
def cargar_opciones():
    """Lee la hoja 'indice' y organiza opciones por Clasificación."""
    df = pd.read_excel(RUTA_EXCEL, sheet_name="indice")
    df.columns = df.columns.str.strip()

    clas_col = "Clasificación" if "Clasificación" in df.columns else "Clasificacion"
    cod_col = "Código de Estructura" if "Código de Estructura" in df.columns else "Codigo de Estructura"
    desc_col = "Descripción" if "Descripción" in df.columns else "Descripcion"

    opciones = {}
    for clasificacion in df[clas_col].dropna().unique():
        subset = df[df[clas_col] == clasificacion]
        codigos = subset[cod_col].dropna().astype(str).tolist()
        etiquetas = {
            str(row[cod_col]): f"{row[cod_col]} – {row[desc_col]}"
            for _, row in subset.iterrows() if pd.notna(row[cod_col])
        }
        # Guardamos sólo la lista de valores; el format_func se hace al vuelo
        opciones[clasificacion] = {"valores": codigos, "etiquetas": etiquetas}

    # Renombramos claves para que coincidan con CAMPOS
    # (en tu índice, típicamente: Poste / Primaria / Secundaria / Retenidas / Conexiones a tierra / Transformadores)
    m = {
        "Poste": "Poste",
        "Primaria": "Primario",
        "Secundaria": "Secundario",
        "Retenidas": "Retenidas",
        "Conexiones a tierra": "Conexiones a tierra",
        "Transformadores": "Transformadores",
    }
    normalizado = {}
    for k, v in opciones.items():
        normalizado[m.get(k, k)] = v
    return normalizado


# =========================
# UI: Selectbox + Cantidad (permite duplicados)
# =========================
def _selector_con_cantidad(titulo: str, data: dict, key_prefix: str, previo: str) -> str:
    """
    Renderiza:
      - selectbox con TODO el catálogo (no filtra lo ya elegido)
      - number_input de 'Cantidad'
    Si el punto ya tenía datos (previo), se intenta precargar cantidad del primer código encontrado.
    """
    if not data:
        return ""

    # Preparar defaults a partir de lo guardado
    repeticiones_previas = _contar_tokens(previo)
    # Elegimos un default razonable sólo si existe en el catálogo
    default_code = ""
    default_qty = 0
    for code, qty in repeticiones_previas.items():
        if code in data["valores"]:
            default_code = code
            default_qty = qty
            break

    # selectbox
    sel = st.selectbox(
        titulo,
        options=[""] + data["valores"],  # "" permite no elegir nada
        index=(0 if not default_code else (1 + data["valores"].index(default_code))),
        format_func=lambda x: (data["etiquetas"].get(x, x) if x else "Seleccionar estructura"),
        key=f"{key_prefix}_{titulo}_sel",
    )

    # cantidad
    qty = st.number_input(
        f"Cantidad – {titulo}",
        min_value=0,
        step=1,
        value=(default_qty if sel else 0),
        key=f"{key_prefix}_{titulo}_qty",
    )

    # Construir salida
    return _repite_token(sel, qty)


# =========================
# API principal usada por tu interfaz
# =========================
def crear_desplegables(opciones: dict, key_prefix: str = "despl") -> dict:
    """
    Crea selectbox + cantidad por cada categoría:
    - NO elimina opciones ya elegidas (siempre muestra todo el catálogo).
    - Permite repetir una estructura N veces con el control 'Cantidad'.
    - Devuelve un dict con textos del tipo 'X + X + Y' por cada campo.
    """
    st.caption("Selecciona por categoría y define cuántas repeticiones agregarás para este Punto.")

    # Obtener valores previos del punto en edición (si existe)
    df_actual = st.session_state.get("df_puntos", pd.DataFrame())
    punto_actual = st.session_state.get("punto_en_edicion")
    valores_previos = {}
    if not df_actual.empty and punto_actual in df_actual.get("Punto", pd.Series(dtype=str)).values:
        fila = df_actual[df_actual["Punto"] == punto_actual].iloc[0].to_dict()
        valores_previos = {k: v for k, v in fila.items() if k != "Punto"}

    # Layout en 3 filas x 2 columnas
    valores = {}
    pares = [(CAMPOS[i], CAMPOS[i+1]) for i in range(0, len(CAMPOS), 2)]
    for (c1, c2) in pares:
        col_a, col_b = st.columns(2)

        with col_a:
            data1 = opciones.get(c1, {"valores": [], "etiquetas": {}})
            prev1 = valores_previos.get(c1, "")
            valores[c1] = _selector_con_cantidad(c1, data1, key_prefix, prev1)

        with col_b:
            data2 = opciones.get(c2, {"valores": [], "etiquetas": {}})
            prev2 = valores_previos.get(c2, "")
            valores[c2] = _selector_con_cantidad(c2, data2, key_prefix, prev2)

    # Limpieza final por si quedó “Seleccionar estructura”
    for k in list(valores.keys()):
        if "Seleccionar estructura" in (valores[k] or ""):
            valores[k] = ""

    return valores
