# core/materiales_estructuras.py
# -*- coding: utf-8 -*-

import re
import pandas as pd
from collections import Counter

from core.materiales_aux import limpiar_codigo, expandir_lista_codigos
from modulo.entradas import extraer_estructuras_proyectadas, cargar_materiales

# ✅ Import correcto (nombre exacto del archivo core/conectores_mt.py)
from core.conectores_mt import reemplazar_solo_yc25a25_mt


# ==========================================================
# Conteo de estructuras (si aún lo usas en algún flujo)
# ==========================================================
def extraer_conteo_estructuras(df_estructuras):
    """
    Extrae el conteo global de estructuras y la lista por punto.
    OJO: Este método NO maneja columna 'cantidad' (modo largo).
    Si tu flujo ya maneja cantidad en el DF, usa tu pipeline nuevo.
    """
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)

    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, _tipo = limpiar_codigo(parte)
            if codigo:
                estructuras_limpias.append(str(codigo).strip().upper())

    valores_invalidos = {"", "SELECCIONAR", "ESTRUCTURA", "PUNTO", "N/A", "NONE", "0", "1", "2", "3"}
    estructuras_filtradas = [e for e in estructuras_limpias if e not in valores_invalidos]

    conteo = Counter(estructuras_filtradas)

    estructuras_por_punto_filtrado = {}
    for punto, lista in estructuras_por_punto.items():
        estructuras_validas = []
        for x in lista:
            s = str(x).strip().upper()
            if s and s not in valores_invalidos:
                estructuras_validas.append(s)
        estructuras_por_punto_filtrado[punto] = estructuras_validas

    return conteo, estructuras_por_punto_filtrado


# ==========================================================
# Helpers
# ==========================================================
def _find_header_row(df_temp: pd.DataFrame) -> int | None:
    """Busca la fila donde empieza la tabla (donde aparece 'Material' / 'Materiales')."""
    for i, row in df_temp.iterrows():
        if row.astype(str).str.contains(r"\bMaterial", case=False, na=False).any():
            return int(i)
    return None


def _pick_tension_column(columns, tension: float) -> str | None:
    """
    Escoge la mejor columna de tensión. Maneja casos tipo:
      '13.8', '13.8 kV', '13.8KV', etc.
    Regla:
      - si existe una columna que contenga el string exacto de tension -> usar esa
      - si no, parsea floats desde el nombre y toma la más cercana
    """
    cols = [str(c).strip() for c in columns]

    # match directo por string
    t_str = str(tension)
    for c in cols:
        if t_str == c:
            return c
    for c in cols:
        if t_str in c:
            return c

    # match por float más cercano
    cand = []
    for c in cols:
        m = re.search(r"(\d+(?:\.\d+)?)", c.replace(",", "."))
        if m:
            try:
                val = float(m.group(1))
                cand.append((abs(val - float(tension)), c))
            except Exception:
                pass

    if not cand:
        return None

    cand.sort(key=lambda x: x[0])
    return cand[0][1]


# ==========================================================
# Materiales por ESTRUCTURA (CORREGIDO)
# ==========================================================
def calcular_materiales_estructura(
    archivo_materiales,
    estructura,
    cant,
    tension,
    calibre_mt,
    tabla_conectores_mt
):
    """
    Lee la hoja 'estructura' en Estructura_datos.xlsx, filtra la columna de tensión
    y devuelve materiales.

    ✅ CORRECCIÓN CLAVE:
    - Los valores de la hoja son unitarios por estructura -> SIEMPRE se multiplica por 'cant'.
      (Esto arregla LL-1 fotoceldas/lámparas y B-II-1 bastidores cuando hay varias unidades)
    """
    try:
        cant = int(cant) if cant is not None else 1
        if cant < 1:
            cant = 1

        # --- Leer hoja completa sin encabezado ---
        df_temp = cargar_materiales(archivo_materiales, estructura, header=None)

        # --- Encontrar fila de encabezado real ---
        fila_encabezado = _find_header_row(df_temp)
        if fila_encabezado is None:
            print(f"⚠️ No se encontró encabezado en hoja {estructura}")
            return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

        # --- Releer con encabezado correcto ---
        df = cargar_materiales(archivo_materiales, estructura, header=fila_encabezado)
        df.columns = df.columns.map(str).str.strip()

        if "Materiales" not in df.columns:
            print(f"⚠️ Hoja {estructura} no contiene columna 'Materiales'")
            return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

        if "Unidad" not in df.columns:
            df["Unidad"] = ""

        # --- Seleccionar columna de tensión ---
        col_tension = _pick_tension_column(df.columns, tension)
        if not col_tension or col_tension not in df.columns:
            print(f"⚠️ No se encontró columna de tensión para {tension} en {estructura}")
            return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

        # --- Filtrar filas válidas (cantidad > 0) ---
        df[col_tension] = pd.to_numeric(df[col_tension], errors="coerce").fillna(0)

        df_filtrado = df[df[col_tension] > 0][["Materiales", "Unidad", col_tension]].copy()
        df_filtrado.rename(columns={col_tension: "Cantidad"}, inplace=True)

        if df_filtrado.empty:
            return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

        # --- Limpieza base ---
        df_filtrado["Materiales"] = df_filtrado["Materiales"].astype(str).str.strip()
        df_filtrado["Unidad"] = df_filtrado["Unidad"].astype(str).str.strip()
        df_filtrado["Cantidad"] = pd.to_numeric(df_filtrado["Cantidad"], errors="coerce").fillna(0).astype(float)

        # ✅ Reemplazo específico: SOLO YC 25A25 en MT
        df_filtrado["Materiales"] = reemplazar_solo_yc25a25_mt(
            df_filtrado["Materiales"].tolist(),
            estructura,
            calibre_mt,
            tabla_conectores_mt
        )

        # ✅ MULTIPLICAR SIEMPRE por cantidad de estructuras
        df_filtrado["Cantidad"] = df_filtrado["Cantidad"] * float(cant)

        # Agrupar por si hay materiales repetidos dentro de la misma hoja
        df_filtrado = df_filtrado.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        return df_filtrado[["Materiales", "Unidad", "Cantidad"]]

    except Exception as e:
        print(f"⚠️ Error leyendo hoja {estructura}: {e}")
        return pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
