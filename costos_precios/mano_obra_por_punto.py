# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd


# ==========================================================
# 🔥 PRECIOS FIJOS REALES (MODELO COMERCIAL)
# ==========================================================
PRECIOS_FIJOS = {

    # TRANSFORMADORES
    "TS-37.5KVA": 13000,
    "TS-50KVA": 15000,

    # CONDUCTORES (referencia directa)
    "CONDUCTOR MT 1/0 AWG RAVEN": 30,
    "CONDUCTOR BT WP 3/0 AWG FIG": 35,

    # RETENIDAS
    "R-1": 2100,
    "R-3V": 2100,
    "R-4": 2100,
    "R-5T": 2100,

    # POSTES
    "PC-30": 2000,
    "PC-40": 2000,

    # LUMINARIAS
    "LL-1-50W": 750,

    # PRIMARIO
    "A-I-1": 1300,
    "A-I-1V": 1500,
    "A-I-4": 1600,
    "A-I-4V": 1700,
    "A-I-6": 1800,

    # SECUNDARIO
    "B-I-4D": 500,
    "B-III-1": 600,
    "B-III-4": 700,
    "B-III-6": 800,

    # OTROS
    "CT-N": 500,
    "CA-32": 800,
    "CS-2": 1200,
}


# ==========================================================
# LIMPIEZA CALIBRE (PARA CABLE)
# ==========================================================
def limpiar_calibre(txt):
    txt = str(txt).upper().strip()
    txt = txt.replace("CABLE DE ALUMINIO", "")
    txt = txt.replace("FORRADO", "")
    txt = txt.replace("ACSR", "")
    txt = txt.replace("#", "")
    txt = txt.replace("  ", " ")
    return txt.strip()


# ==========================================================
# 🔥 NUEVO PRECIO POR ESTRUCTURA (100% FIJO)
# ==========================================================
def _precio_estructura(estructura: str) -> float:

    estructura = str(estructura).upper().strip()

    # ✔ EXACTO
    if estructura in PRECIOS_FIJOS:
        return PRECIOS_FIJOS[estructura]

    # ✔ MATCH FLEXIBLE (ej: A-I-1V, variantes)
    for key in PRECIOS_FIJOS:
        if estructura.startswith(key):
            return PRECIOS_FIJOS[key]

    # ⚠️ NO DEFINIDO
    return 0


# ==========================================================
# 🔥 CABLE CONSOLIDADO (SE MANTIENE)
# ==========================================================
def _agregar_cable_resumen(df_detalle: pd.DataFrame, df_cables: pd.DataFrame | None):

    if df_cables is None or df_cables.empty:
        return df_detalle

    filas = []

    for _, c in df_cables.iterrows():

        tipo = str(c.get("Tipo", "")).upper()
        calibre = limpiar_calibre(c.get("Calibre", ""))

        try:
            longitud = float(c.get("Total Cable (m)", 0))
        except:
            continue

        if longitud <= 0:
            continue

        if tipo.startswith("MT"):
            nombre = f"Conductor MT {calibre}"
            precio = 30

        elif tipo.startswith("BT"):
            nombre = f"Conductor BT {calibre}"
            precio = 35

        else:
            continue

        filas.append({
            "Punto": None,
            "Estructura": nombre,
            "Cantidad": longitud,
            "Precio": precio,
            "Subtotal": round(longitud * precio, 2),
        })

    if not filas:
        return df_detalle

    return pd.concat([df_detalle, pd.DataFrame(filas)], ignore_index=True)


# ==========================================================
# DETALLE POR PUNTO
# ==========================================================
def calcular_detalle_mano_obra(df_estructuras_por_punto: pd.DataFrame) -> pd.DataFrame:

    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        return pd.DataFrame(columns=["Punto", "Estructura", "Cantidad", "Precio", "Subtotal"])

    filas = []

    for _, row in df_estructuras_por_punto.iterrows():

        punto = row["Punto"]
        estructura = row["Estructura"]
        cantidad = int(row["Cantidad"])

        precio = _precio_estructura(estructura)
        subtotal = precio * cantidad

        filas.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad,
            "Precio": round(precio, 2),
            "Subtotal": round(subtotal, 2),
        })

    return pd.DataFrame(filas)


# ==========================================================
# TOTAL POR PUNTO
# ==========================================================
def calcular_totales_por_punto(df_detalle: pd.DataFrame) -> pd.DataFrame:

    if df_detalle is None or df_detalle.empty:
        return pd.DataFrame(columns=["Punto", "TOTAL_PUNTO"])

    return (
        df_detalle
        .groupby("Punto", as_index=False)["Subtotal"]
        .sum()
        .rename(columns={"Subtotal": "TOTAL_PUNTO"})
    )


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================
def calcular_mano_obra_proyecto(df_estructuras_por_punto: pd.DataFrame, df_cables=None):

    df_detalle = calcular_detalle_mano_obra(df_estructuras_por_punto)

    # 🔥 integrar cable
    df_detalle = _agregar_cable_resumen(df_detalle, df_cables)

    df_totales = calcular_totales_por_punto(df_detalle[df_detalle["Punto"].notna()])

    df_detalle = df_detalle.sort_values(["Punto", "Estructura"])
    df_totales = df_totales.sort_values("Punto")

    return {
        "df_detalle": df_detalle,
        "df_totales": df_totales,
    }
