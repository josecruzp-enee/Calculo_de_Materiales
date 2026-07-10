# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd


# ==========================================================
# 🔥 PRECIOS CONTRATISTA 1 (ORIGINAL)
# ==========================================================
PRECIOS_FIJOS = {

    "TS-37.5KVA": 13000,
    "TS-50KVA": 15000,
    "TS-15KVA": 10000,

    "CONDUCTOR MT 1/0 AWG RAVEN": 30,
    "CONDUCTOR BT WP 3/0 AWG FIG": 35,
    "HILO PILOTO HP WP 2 AWG PEACH": 28,
    "NEUTRO N 2 AWG SPARROW": 28,

    "R-1": 2100,
    "R-2": 2100,
    "R-3V": 2100,
    "R-4": 2100,
    "R-5T": 2100,
    "R-3C": 1500,

    "PC-30": 2000,
    "PC-40": 2000,
    "PC-35": 2000,
    "PCA-40": 3000,
    "PCA-30": 3000,
    "PM-40": 3000,
    "PM-30": 2000,

    "LL-1-50W": 750,
    "LL-1-100W": 750,
    
    "A-III-4V": 3000,
    "A-III-4": 2800,
    "A-III-1": 2000,
    "A-III-1V": 2200,
    "A-III-5": 3000,
    "A-III-5V": 3200,
    "A-III-6": 3500,
    "A-III-7A": 3200,
    "A-II-1": 1800,
    "A-I-1": 1300,
    "A-I-1V": 1500,
    "A-II-1V": 2000,
    "A-II-4": 2200,
    "A-II-6": 2600,
    "A-II-4A": 2000,
    "A-II-5": 2500,
    "A-I-4": 1600,
    "A-I-4V": 1700,
    "A-I-6": 1800,
    "A-I-5": 1800,

    "B-I-1": 400,
    "B-I-3": 400,
    "B-I-4D": 500,
    "B-I-4": 500,
    "B-I-4B": 500,
    "B-I-6": 600,
    "B-I-5": 600,
    "B-I-7A": 500,
    "B-II-1": 500,
    "B-III-1": 600,
    "B-III-2": 600,
    "B-III-4": 700,
    "B-III-5": 750,
    "B-III-6": 800,
    "B-III-7A": 750,
    "B-III-7": 750,
    "B-III-8": 700,
    "CT-N": 500,
    "CA-32": 800,
    "CS-2": 1200,
    "CS-1": 1200,
}


# ==========================================================
# 🔥 PRECIOS CONTRATISTA 2
# ==========================================================
PRECIOS_FIJOS_2 = {

    "TS-37.5KVA": 25000,
    "TS-50KVA": 30000,

    "CONDUCTOR BT GLOBAL": 150,
    "CONDUCTOR MT GLOBAL": 120,
    "CONDUCTOR N GLOBAL": 120,
    
    "CONDUCTOR MT 1/0 AWG RAVEN": 120,
    "CONDUCTOR BT WP 3/0 AWG FIG": 100,
    "CONDUCTOR N 2 AWG SPARROW": 40,
    "HILO PILOTO HP WP 2 AWG PEACH": 40,

    "R-1": 2100,
    "R-2": 2300,
    "R-3V": 2300,
    "R-4": 2300,
    "R-5T": 2300,
    "R-3C": 1500,

    "PC-30": 2000,
    "PC-40": 3000,
    "PC-35": 2500,
    "PCA-30": 3500,
    "PCA-40": 4500,

    "LL-1-50W": 1000,
    "LL-2-50W": 1500,
    "LL-1-150W": 1000,
    "LL-1-100W": 1000,
    "LL-1-28A50W": 1000,
    
    "A-I-1": 1300,
    "A-I-1V": 1500,
    "A-I-2": 1600,
    "A-II-6": 1500,
    "A-II-1V": 2200,
    "A-II-2V": 2500,
    "A-II-4V": 2700,
    "A-II-5V": 3200,
    "A-III-1V": 2500,
    "A-III-2V": 3700,
    "A-III-5V": 4400,
    "A-III-4V": 3900,
    "A-III-7": 3000,
    "A-I-4": 1600,
    "A-I-4V": 1500,
    "A-I-6": 1800,

    "B-I-1": 1200,
    "B-I-7": 1500,
    "B-I-3": 1500,
    "B-I-4D": 1100,
    "B-I-4": 1100,
    "B-I-6": 1300,
    "B-I-4B": 1100,
    "B-I-7A": 500,
    "B-II-1": 1200,
    "B-II-4C": 1500,
    "B-II-4": 1300,
    "B-III-1": 1200,
    "B-III-2": 1200,
    "B-III-4": 1400,
    "B-III-5": 1500,
    "B-III-6": 1600,
    "B-III-7A": 1500,
    "B-III-7": 1400,

    "CT-N": 1500,
    "CA-32": 2500,
    "CS-2": 1200,
    "DESMONTAJE": 35000,
    "REUBICACION": 80000,
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
def _agregar_cable_resumen(
    df_detalle: pd.DataFrame,
    df_cables: pd.DataFrame | None,
    lista_precios=None,
    contratista="C1"
):

    if df_cables is None or df_cables.empty:
        return df_detalle

    filas = []

    # ======================================================
    # C1 → DETALLADO (NO SE MODIFICA)
    # ======================================================
    if contratista == "C1":

        for _, c in df_cables.iterrows():

            tipo = str(c.get("Tipo", "")).upper()
            descripcion = str(c.get("Descripcion", "")).upper()

            try:
                longitud = float(c.get("Total Cable (m)", 0))
            except (TypeError, ValueError):
                continue

            if longitud <= 0:
                continue

            desc = descripcion
            desc = desc.replace("CABLE DE ALUMINIO", "")
            desc = desc.replace("ACSR", "")
            desc = desc.replace("FORRADO", "")
            desc = desc.replace("#", "")
            desc = desc.replace("  ", " ")
            desc = desc.strip()

            palabras = desc.split()
            desc = " ".join(dict.fromkeys(palabras))

            if tipo == "MT":
                desc = desc.replace("MT", "").strip()
                nombre = f"CONDUCTOR MT {desc}"

            elif tipo == "BT":
                desc = desc.replace("BT", "").strip()
                nombre = f"CONDUCTOR BT {desc}"

            elif tipo == "HP":
                nombre = f"HILO PILOTO {desc}"

            elif tipo == "N":
                nombre = f"NEUTRO {desc}"

            else:
                continue

            precio = _precio_estructura(
                nombre,
                lista_precios
            )

            filas.append({
                "Punto": None,
                "Estructura": nombre,
                "Cantidad": longitud,
                "Precio": precio,
                "Subtotal": round(longitud * precio, 2),
            })

    # ======================================================
    # C2 → MISMA LÓGICA DE PRECIO_ESTRUCTURA
    # ======================================================
    elif contratista == "C2":

        for _, c in df_cables.iterrows():

            tipo = str(
                c.get("Tipo", "")
            ).strip().upper()

            # ----------------------------------------------
            # Longitud de material registrada en df_cables
            # ----------------------------------------------
            longitud_material = pd.to_numeric(
                c.get("Total Cable (m)", 0),
                errors="coerce"
            )

            if pd.isna(longitud_material) or longitud_material <= 0:
                longitud_material = pd.to_numeric(
                    c.get("Longitud", 0),
                    errors="coerce"
                )

            if pd.isna(longitud_material) or longitud_material <= 0:
                continue

            longitud_material = float(longitud_material)

            # ----------------------------------------------
            # Limpiar calibre para la descripción
            # ----------------------------------------------
            calibre = str(
                c.get(
                    "Calibre",
                    c.get("Descripcion", "")
                )
            ).upper().strip()

            calibre = calibre.replace(
                "CABLE DE ALUMINIO",
                ""
            )

            calibre = calibre.replace(
                "FORRADO",
                ""
            )

            calibre = calibre.replace(
                "ACSR",
                ""
            )

            calibre = calibre.replace(
                "#",
                ""
            )

            while "  " in calibre:
                calibre = calibre.replace("  ", " ")

            calibre = calibre.strip()

            # Por defecto, la cantidad de mano de obra
            # corresponde a la cantidad registrada.
            cantidad = longitud_material

            # ----------------------------------------------
            # MT
            # ----------------------------------------------
            if tipo.startswith("MT"):

                calibre_mt = calibre.replace(
                    "WP",
                    ""
                ).strip()

                nombre = (
                    f"CONDUCTOR MT {calibre_mt}"
                )

                precio = lista_precios.get(
                    "CONDUCTOR MT GLOBAL",
                    lista_precios.get(
                        "CONDUCTOR MT 1/0 AWG RAVEN",
                        0
                    )
                )

            # ----------------------------------------------
            # BT
            # ----------------------------------------------
            elif tipo.startswith("BT"):

                nombre = (
                    f"CONDUCTOR BT {calibre}"
                )

                # BT se cobra por longitud lineal.
                longitud_lineal = pd.to_numeric(
                    c.get("Longitud", 0),
                    errors="coerce"
                )

                # Si no existe Longitud, se obtiene mediante
                # metros-conductor / número de conductores.
                if pd.isna(longitud_lineal) or longitud_lineal <= 0:

                    conductores = pd.to_numeric(
                        c.get("Conductores", 1),
                        errors="coerce"
                    )

                    if pd.isna(conductores) or conductores <= 0:
                        conductores = 1

                    longitud_lineal = (
                        longitud_material
                        / float(conductores)
                    )

                cantidad = float(longitud_lineal)

                precio = lista_precios.get(
                    "CONDUCTOR BT GLOBAL",
                    lista_precios.get(
                        "CONDUCTOR BT WP 3/0 AWG FIG",
                        0
                    )
                )

            # ----------------------------------------------
            # NEUTRO
            # ----------------------------------------------
            elif tipo.startswith("N"):

                calibre_n = calibre.replace(
                    "WP",
                    ""
                ).strip()

                nombre = (
                    f"CONDUCTOR N {calibre_n}"
                )

                precio = lista_precios.get(
                    "CONDUCTOR N 2 AWG SPARROW",
                    0
                )

            # ----------------------------------------------
            # HILO PILOTO
            # ----------------------------------------------
            elif tipo.startswith("HP"):

                nombre = (
                    f"HILO PILOTO HP {calibre}"
                )

                precio = lista_precios.get(
                    "HILO PILOTO HP WP 2 AWG PEACH",
                    0
                )

            else:
                continue

            filas.append({
                "Punto": None,
                "Estructura": nombre,
                "Cantidad": round(cantidad, 2),
                "Precio": round(float(precio), 2),
                "Subtotal": round(
                    cantidad * float(precio),
                    2
                ),
            })

    if not filas:
        return df_detalle

    return pd.concat(
        [
            df_detalle,
            pd.DataFrame(filas)
        ],
        ignore_index=True
    )



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

    df_detalle = _agregar_cable_resumen(df_detalle, df_cables, lista_precios, contratista)

    df_totales = calcular_totales_por_punto(df_detalle[df_detalle["Punto"].notna()])

    df_detalle = df_detalle.sort_values(["Punto", "Estructura"])
    df_totales = df_totales.sort_values("Punto")

    return {
        "df_detalle": df_detalle,
        "df_totales": df_totales,
    }
