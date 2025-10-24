# -*- coding: utf-8 -*-
"""
conectores_mt.py
Módulo para cargar, buscar y reemplazar conectores de compresión según calibre y tipo de estructura.
Compatible con niveles: Primario (MT), Secundario (BT) y Neutro.
"""

import re
import pandas as pd


# === 1️⃣ Cargar hoja de conectores ===
def cargar_conectores_mt(archivo_materiales):
    """Carga la hoja 'conectores' desde Estructura_datos.xlsx."""
    try:
        df = pd.read_excel(archivo_materiales, sheet_name='conectores')
        df.columns = [c.strip().capitalize() for c in df.columns]

        if 'Descripción' not in df.columns:
            for col in df.columns:
                if "desc" in col.lower():
                    df = df.rename(columns={col: "Descripción"})

        # Normalizar columnas esperadas
        columnas_esperadas = ["Calibre", "Código", "Descripción", "Estructuras aplicables"]
        for col in columnas_esperadas:
            if col not in df.columns:
                df[col] = ""

        return df[columnas_esperadas]

    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])


# === 2️⃣ Determinar calibre según tipo de estructura ===
def determinar_calibre_por_estructura(estructura, datos_proyecto):
    """
    Devuelve el calibre apropiado según el tipo de estructura (MT, BT o Neutro).
    """
    estructura = str(estructura).upper().strip()

    calibre_mt = str(datos_proyecto.get("calibre_mt", "")).upper().strip()
    calibre_bt = str(datos_proyecto.get("calibre_bt", "")).upper().strip()
    calibre_neutro = str(datos_proyecto.get("calibre_neutro", "")).upper().strip()

    # Clasificación por prefijo o coincidencia
    if any(estructura.startswith(pref) for pref in ["A", "TM", "TH", "ER"]):
        return calibre_mt or "1/0 ASCR"
    elif any(estructura.startswith(pref) for pref in ["B", "R"]):
        return calibre_bt or "1/0 WP"
    elif any(pref in estructura for pref in ["CT", "N", "NEUTRO"]):
        return calibre_neutro or "#2 AWG"
    else:
        return calibre_mt or "1/0 ASCR"


# === 3️⃣ Buscar conector adecuado según calibre ===
def buscar_conector_mt(calibre, tabla_conectores: pd.DataFrame):
    """
    Busca un conector simétrico (mismo calibre en ambos extremos).
    Soporta formatos como:
      - 1/0 ASCR → (1/0-1/0)
      - 3/0 ASCR → (3/0-3/0)
      - 266.8 MCM → (266.8-266.8)
    """
    if tabla_conectores.empty or not calibre:
        return None

    calibre_norm = calibre.upper().replace(" ", "")
    calibre_norm = calibre_norm.replace("ASCR", "").replace("AAC", "").replace("MCM", "").strip()

    patron = re.compile(
        rf"\(\s*{re.escape(calibre_norm)}\s*[-–]\s*{re.escape(calibre_norm)}\s*\)", re.IGNORECASE
    )

    for _, fila in tabla_conectores.iterrows():
        desc = str(fila.get("Descripción", "")).upper().replace(" ", "")
        if patron.search(desc):
            return fila["Descripción"]

    return None


# === 4️⃣ Aplicar reemplazo de conectores ===
def aplicar_reemplazos_conectores(lista_materiales, calibre_estructura, tabla_conectores: pd.DataFrame):
    """
    Reemplaza materiales tipo 'CONECTOR DE COMPRESIÓN' por el adecuado según el calibre de esa estructura.
    """
    materiales_modificados = []
    for mat in lista_materiales:
        mat_str = str(mat).upper()
        if "CONECTOR" in mat_str and "COMPRESIÓN" in mat_str:
            nuevo_con = buscar_conector_mt(calibre_estructura, tabla_conectores)
            if nuevo_con:
                materiales_modificados.append(nuevo_con)
                continue
        materiales_modificados.append(mat)
    return materiales_modificados

