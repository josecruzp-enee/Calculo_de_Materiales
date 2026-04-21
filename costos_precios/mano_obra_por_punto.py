# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd


# ==========================================================
# CONFIGURACIÓN BASE (BIBLIOTECA DE EJECUCIÓN)
# ==========================================================
COSTOS_BASE = {
    "poste": 2000,
    "primario": 1300,
    "secundario": 800,
    "luminaria": 750,
    "retenida": 2100,
}

FACTOR_FASES = {
    "A-I": 1.0,
    "A-II": 1.3,
    "A-III": 1.6,
}

FACTOR_COMPLEJIDAD = {
    "PASO": 1.0,
    "ANGULO": 1.2,
    "DOBLE": 1.4,
    "REMATE": 1.6,
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
# PRECIO POR ESTRUCTURA
# ==========================================================
def _precio_estructura(estructura: str) -> float:

    if estructura.startswith("PC"):
        return COSTOS_BASE["poste"]

    if estructura.startswith("A-"):

        if estructura.startswith("A-III"):
            f_fase = FACTOR_FASES["A-III"]
        elif estructura.startswith("A-II"):
            f_fase = FACTOR_FASES["A-II"]
        else:
            f_fase = FACTOR_FASES["A-I"]

        if "REM" in estructura:
            f_comp = FACTOR_COMPLEJIDAD["REMATE"]
        elif "DOB" in estructura:
            f_comp = FACTOR_COMPLEJIDAD["DOBLE"]
        else:
            f_comp = FACTOR_COMPLEJIDAD["PASO"]

        return COSTOS_BASE["primario"] * f_fase * f_comp

    if estructura.startswith("B-"):
        return COSTOS_BASE["secundario"]

    if estructura.startswith("LL"):
        return COSTOS_BASE["luminaria"]

    if estructura.startswith("R-"):
        return COSTOS_BASE["retenida"]

    if estructura.startswith("CT"):
        return 500

    if estructura.startswith("CA-32"):
        return 800
        
    if estructura.startswith("CS-2"):
        return 1200
         
    if estructura.startswith("TS"):

        PRECIOS_TRANSFORMADOR = {
            "TS-15KVA": 15000,
            "TS-25KVA": 20000,
            "TS-37.5KVA": 13000,
            "TS-50KVA": 15000,
            "TS-75KVA": 45000,
            "TS-100KVA": 60000,
        }

        if estructura not in PRECIOS_TRANSFORMADOR:
            raise ValueError(f"Transformador sin precio definido: {estructura}")

        return PRECIOS_TRANSFORMADOR[estructura]

    return 0


# ==========================================================
# 🔥 CABLE CONSOLIDADO (NUEVO)
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
            "Punto": None,  # 🔥 CLAVE (ANTES TENÍAS PRESUPUESTO)
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
# FUNCIÓN PRINCIPAL (ACTUALIZADA)
# ==========================================================
def calcular_mano_obra_proyecto(df_estructuras_por_punto: pd.DataFrame, df_cables=None):

    df_detalle = calcular_detalle_mano_obra(df_estructuras_por_punto)

    # 🔥 INTEGRAR CABLE
    df_detalle = _agregar_cable_resumen(df_detalle, df_cables)

    df_totales = calcular_totales_por_punto(df_detalle[df_detalle["Punto"].notna()])

    df_detalle = df_detalle.sort_values(["Punto", "Estructura"])
    df_totales = df_totales.sort_values("Punto")

    return {
        "df_detalle": df_detalle,
        "df_totales": df_totales,
    }
