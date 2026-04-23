# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd


# ==========================================================
# 🔥 PRECIOS CONTRATISTA 1 (ORIGINAL)
# ==========================================================
PRECIOS_FIJOS = {

    "TS-37.5KVA": 13000,
    "TS-50KVA": 15000,

    "CONDUCTOR MT 1/0 AWG RAVEN": 30,
    "CONDUCTOR BT WP 3/0 AWG FIG": 35,

    "R-1": 2100,
    "R-2": 2100,
    "R-3V": 2100,
    "R-4": 2100,
    "R-5T": 2100,

    "PC-30": 2000,
    "PC-40": 2000,

    "LL-1-50W": 750,

    "A-I-1": 1300,
    "A-I-1V": 1500,
    "A-II-1V": 2000,
    "A-II-4": 2200,
    "A-II-5": 2500,
    "A-I-4": 1600,
    "A-I-4V": 1700,
    "A-I-6": 1800,

    "B-I-1": 400,
    "B-I-4D": 500,
    "B-I-7A": 500,
    "B-III-1": 600,
    "B-III-2": 600,
    "B-III-4": 700,
    "B-III-5": 750,
    "B-III-6": 800,
    "B-III-7A": 750,
    "B-III-7": 750,

    "CT-N": 500,
    "CA-32": 800,
    "CS-2": 1200,
}


# ==========================================================
# 🔥 PRECIOS CONTRATISTA 2
# ==========================================================
PRECIOS_FIJOS_2 = {

    "TS-37.5KVA": 25000,
    "TS-50KVA": 30000,

    "CONDUCTOR MT 1/0 AWG RAVEN": 120,
    "CONDUCTOR BT WP 3/0 AWG FIG": 150,

    "R-1": 2300,
    "R-2": 2300,
    "R-3V": 2300,
    "R-4": 2300,
    "R-5T": 2300,

    "PC-30": 2000,
    "PC-40": 3000,

    "LL-1-50W": 1000,

    "A-I-1": 1300,
    "A-I-1V": 1500,
    "A-II-1V": 2200,
    "A-II-4": 2700,
    "A-II-5": 3200,
    "A-III-1V": 2500,
    "A-III-1V": 2800,
    "A-III-5V": 3500,
    "A-III-4V": 3000,
    "A-I-4": 1600,
    "A-I-4V": 1500,
    "A-I-6": 1800,

    "B-I-1": 400,
    "B-I-4D": 500,
    "B-I-7A": 500,
    "B-III-1": 1200,
    "B-III-2": 600,
    "B-III-4": 1400,
    "B-III-5": 750,
    "B-III-6": 1600,
    "B-III-7A": 750,
    "B-III-7": 750,

    "CT-N": 1500,
    "CA-32": 2500,
    "CS-2": 1200,
}


# ==========================================================
# 🔥 SELECTOR DE LISTA (CAMBIAS AQUÍ)
# ==========================================================
def obtener_lista_precios(nombre="C1"):
    if nombre == "C2":
        return PRECIOS_FIJOS_2
    return PRECIOS_FIJOS


# ==========================================================
# PRECIO POR ESTRUCTURA (NO ROMPE NADA)
# ==========================================================
def _precio_estructura(estructura: str, lista_precios=None) -> float:

    if lista_precios is None:
        lista_precios = PRECIOS_FIJOS

    estructura = str(estructura).upper().strip()

    if estructura in lista_precios:
        return lista_precios[estructura]

    for key in lista_precios:
        if estructura.startswith(key):
            return lista_precios[key]

    return 0


# ==========================================================
# CABLE CONSOLIDADO
# ==========================================================
def _agregar_cable_resumen(df_detalle: pd.DataFrame, df_cables: pd.DataFrame | None):

    if df_cables is None or df_cables.empty:
        return df_detalle

    filas = []

    for _, c in df_cables.iterrows():

        tipo = str(c.get("Tipo", "")).upper()
        descripcion = str(c.get("Descripcion", "")).upper()

        try:
            longitud = float(c.get("Total Cable (m)", 0))
        except:
            continue

        if longitud <= 0:
            continue

        if tipo == "MT":
            precio = 30
            nombre = f"Conductor MT {descripcion}"

        elif tipo == "BT":
            precio = 35
            nombre = f"Fases BT {descripcion}"

        elif tipo == "HP":
            precio = 28
            nombre = f"Hilo Piloto {descripcion}"

        elif tipo == "N":
            precio = 28
            nombre = f"Neutro {descripcion}"

        else:
            continue

        filas.append({
            "Punto": None,
            "Estructura": nombre,
            "Cantidad": longitud,
            "Precio": precio,
            "Subtotal": round(longitud * precio, 2),
        })

    return pd.concat([df_detalle, pd.DataFrame(filas)], ignore_index=True)


# ==========================================================
# DETALLE
# ==========================================================
def calcular_detalle_mano_obra(df_estructuras_por_punto: pd.DataFrame, lista_precios):

    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        return pd.DataFrame(columns=["Punto", "Estructura", "Cantidad", "Precio", "Subtotal"])

    filas = []

    for _, row in df_estructuras_por_punto.iterrows():

        punto = row["Punto"]
        estructura = row["Estructura"]
        cantidad = int(row["Cantidad"])

        precio = _precio_estructura(estructura, lista_precios)
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
# TOTALES
# ==========================================================
def calcular_totales_por_punto(df_detalle: pd.DataFrame):

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
def calcular_mano_obra_proyecto(df_estructuras_por_punto: pd.DataFrame, df_cables=None, contratista="C2"):

    lista_precios = obtener_lista_precios(contratista)

    df_detalle = calcular_detalle_mano_obra(df_estructuras_por_punto, lista_precios)

    df_detalle = _agregar_cable_resumen(df_detalle, df_cables)

    df_totales = calcular_totales_por_punto(df_detalle[df_detalle["Punto"].notna()])

    df_detalle = df_detalle.sort_values(["Punto", "Estructura"])
    df_totales = df_totales.sort_values("Punto")

    return {
        "df_detalle": df_detalle,
        "df_totales": df_totales,
    }
