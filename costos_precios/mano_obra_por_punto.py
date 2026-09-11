# -*- coding: utf-8 -*-
"""
costos_precios/mano_obra_por_punto.py

ROL:
    Motor principal de cálculo de mano de obra por contratista.

QUÉ HACE:
    - Mantiene temporalmente las tarifas de los contratistas C1 y C2.
    - Calcula mano de obra por estructura.
    - Calcula mano de obra asociada al tendido de conductores.
    - Genera detalle de mano de obra.
    - Genera totales por punto.
    - Permite agregar trabajos adicionales manuales cuando sea necesario.

UTILIZADO POR:
    costos_precios.orquestador_costos

PDF CONTRATISTA:
    Alimenta el cálculo de mano de obra, pero NO genera el PDF.

REPORTE COMPLETO:
    Sí. Sus resultados son utilizados por el orquestador de costos.

NO HACE:
    - No genera PDF.
    - No calcula materiales.
    - No calcula ISV.
    - No calcula utilidad.
    - No contiene datos específicos de un proyecto activo.

SALIDA PRINCIPAL:
    {
        "df_detalle": DataFrame,
        "df_totales": DataFrame,
    }

NOTA:
    Los precios permanecen en este archivo temporalmente.
    Posteriormente podrán trasladarse a un catálogo independiente.
"""

from __future__ import annotations

import pandas as pd


# ==========================================================
# PRECIOS CONTRATISTA C1
# ==========================================================

PRECIOS_FIJOS = {
    # Transformadores
    "TS-37.5KVA": 13000,
    "TS-50KVA": 15000,
    "TS-15KVA": 10000,
    "TT-50KVA": 40000,

    # Conductores
    "CONDUCTOR MT 1/0 AWG RAVEN": 30,
    "CONDUCTOR BT WP 3/0 AWG FIG": 35,
    "HILO PILOTO HP WP 2 AWG PEACH": 28,
    "NEUTRO N 2 AWG SPARROW": 28,

    # Retenidas
    "R-1": 2100,
    "R-2": 2100,
    "R-3V": 2100,
    "R-4": 2100,
    "R-5T": 2100,
    "R-3C": 1500,

    # Postes
    "PC-30": 2000,
    "PC-40": 2000,
    "PC-35": 2000,
    "PCA-40": 3000,
    "PCA-30": 3000,
    "PM-40": 3000,
    "PM-30": 2000,

    # Luminarias
    "LL-1-50W": 750,
    "LL-1-100W": 750,

    # Estructuras A
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

    # Estructuras B / complementarias
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
# PRECIOS CONTRATISTA C2
# ==========================================================

PRECIOS_FIJOS_2 = {
    # Transformadores
    "TS-37.5KVA": 25000,
    "TS-50KVA": 30000,
    "TS-100KVA": 40000,

    # Conductores - tarifas globales
    "CONDUCTOR BT GLOBAL": 100,
    "CONDUCTOR MT GLOBAL": 120,
    "CONDUCTOR N GLOBAL": 120,

    # Conductores - referencias específicas
    "CONDUCTOR MT 1/0 AWG RAVEN": 120,
    "CONDUCTOR BT WP 3/0 AWG FIG": 100,
    "CONDUCTOR N 2 AWG SPARROW": 40,
    "HILO PILOTO HP WP 2 AWG PEACH": 40,

    # Retenidas
    "R-1": 2100,
    "R-2": 2300,
    "R-3V": 2300,
    "R-4": 2300,
    "R-5T": 2300,
    "R-3C": 1500,

    # Postes
    "PC-30": 2000,
    "PC-40": 3000,
    "PC-45": 3500,
    "PC-35": 2500,
    "PCA-30": 3500,
    "PCA-40": 4500,

    # Luminarias
    "LL-1-50W": 1000,
    "LL-2-50W": 1500,
    "LL-1-150W": 1000,
    "LL-1-100W": 1000,
    "LL-1-28A50W": 1000,

    # Estructuras A
    "A-I-1": 1300,
    "A-I-1V": 1500,
    "A-I-2": 1600,
    "A-II-6": 1500,
    "A-II-1V": 2200,
    "A-III-1": 2500,
    "A-II-2V": 2500,
    "A-II-4V": 2700,
    "A-II-5V": 3200,
    "A-III-5": 3800,
    "A-III-1V": 2500,
    "ER-III-1": 2500,
    "A-III-2V": 3700,
    "A-III-2": 3000,
    "A-III-5V": 4400,
    "A-III-4V": 3900,
    "A-III-4": 3000,
    "A-III-7": 3000,
    "A-I-4": 1600,
    "A-I-4V": 1500,
    "A-I-6": 1800,
    "A-III-6": 4000,

    # Estructuras B / complementarias
    "G-I-1": 1200,
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

    # Tarifas generales disponibles.
    # NO se agregan automáticamente al proyecto.
    "DESMONTAJE": 35000,
    "REUBICACION": 80000,
}


# ==========================================================
# ADICIONALES MANUALES
# ==========================================================
# Espacio temporal para desmontajes, reubicaciones u otros
# trabajos extraordinarios.
#
# IMPORTANTE:
# Nada de esta lista se agrega si está vacía.
#
# Ejemplo:
#
# ADICIONALES_MANO_OBRA = [
#     {
#         "Punto": "DESMONTAJE",
#         "Estructura": "DESMONTAJE PC-35",
#         "Cantidad": 1,
#         "Precio": 2500,
#     },
# ]
# ==========================================================

ADICIONALES_MANO_OBRA: list[dict] = []


# ==========================================================
# UTILIDADES
# ==========================================================

def _to_float(valor, default: float = 0.0) -> float:
    try:
        numero = pd.to_numeric(valor, errors="coerce")
        return default if pd.isna(numero) else float(numero)
    except (TypeError, ValueError):
        return default


def _limpiar_texto(texto: str) -> str:
    texto = str(texto).upper().strip()

    for termino in ("CABLE DE ALUMINIO", "ACSR", "FORRADO", "#"):
        texto = texto.replace(termino, "")

    return " ".join(texto.split())


def _deduplicar_palabras(texto: str) -> str:
    return " ".join(dict.fromkeys(str(texto).split()))


# ==========================================================
# SELECTOR DE CONTRATISTA
# ==========================================================

def obtener_lista_precios(nombre: str = "C1") -> dict:
    contratista = str(nombre).strip().upper()

    if contratista == "C1":
        return PRECIOS_FIJOS

    if contratista == "C2":
        return PRECIOS_FIJOS_2

    raise ValueError(
        f"Contratista no reconocido: {nombre!r}. "
        "Opciones válidas: C1, C2."
    )


# ==========================================================
# PRECIO POR ESTRUCTURA
# ==========================================================

def _precio_estructura(
    estructura: str,
    lista_precios: dict | None = None,
) -> float:

    lista_precios = lista_precios or PRECIOS_FIJOS
    estructura = str(estructura).upper().strip()

    if estructura in lista_precios:
        return float(lista_precios[estructura])

    # Compatibilidad con códigos que agregan sufijos.
    for codigo, precio in lista_precios.items():
        if estructura.startswith(codigo):
            return float(precio)

    return 0.0


# ==========================================================
# CABLES - UTILIDADES
# ==========================================================

def _longitud_material(cable: pd.Series) -> float:
    longitud = _to_float(cable.get("Total Cable (m)", 0))

    if longitud <= 0:
        longitud = _to_float(cable.get("Longitud", 0))

    return longitud


def _longitud_lineal(cable: pd.Series, longitud_material: float) -> float:
    longitud = _to_float(cable.get("Longitud", 0))

    if longitud > 0:
        return longitud

    conductores = _to_float(cable.get("Conductores", 1), 1.0)

    if conductores <= 0:
        conductores = 1.0

    return longitud_material / conductores


def _fila_mano_obra(
    *,
    estructura: str,
    cantidad: float,
    precio: float,
    punto=None,
) -> dict:

    return {
        "Punto": punto,
        "Estructura": estructura,
        "Cantidad": round(float(cantidad), 2),
        "Precio": round(float(precio), 2),
        "Subtotal": round(float(cantidad) * float(precio), 2),
    }


# ==========================================================
# CABLES - CONTRATISTA C1
# ==========================================================

def _fila_cable_c1(cable: pd.Series, lista_precios: dict) -> dict | None:
    tipo = str(cable.get("Tipo", "")).strip().upper()
    longitud = _longitud_material(cable)

    if longitud <= 0:
        return None

    descripcion = _limpiar_texto(cable.get("Descripcion", ""))
    descripcion = _deduplicar_palabras(descripcion)

    if tipo == "MT":
        nombre = f"CONDUCTOR MT {descripcion.replace('MT', '').strip()}"

    elif tipo == "BT":
        nombre = f"CONDUCTOR BT {descripcion.replace('BT', '').strip()}"

    elif tipo == "HP":
        nombre = f"HILO PILOTO {descripcion}"

    elif tipo == "N":
        nombre = f"NEUTRO {descripcion}"

    else:
        return None

    precio = _precio_estructura(nombre, lista_precios)

    return _fila_mano_obra(
        estructura=nombre,
        cantidad=longitud,
        precio=precio,
    )


# ==========================================================
# CABLES - CONTRATISTA C2
# ==========================================================

def _fila_cable_c2(cable: pd.Series, lista_precios: dict) -> dict | None:
    tipo = str(cable.get("Tipo", "")).strip().upper()
    longitud_material = _longitud_material(cable)

    if longitud_material <= 0:
        return None

    calibre = cable.get("Calibre", cable.get("Descripcion", ""))
    calibre = _limpiar_texto(calibre)

    cantidad = longitud_material

    # ------------------------------------------------------
    # Media tensión
    # ------------------------------------------------------
    if tipo.startswith("MT"):
        calibre_mt = calibre.replace("WP", "").strip()
        nombre = f"CONDUCTOR MT {calibre_mt}"

        precio = lista_precios.get(
            "CONDUCTOR MT GLOBAL",
            lista_precios.get("CONDUCTOR MT 1/0 AWG RAVEN", 0),
        )

    # ------------------------------------------------------
    # Baja tensión
    # ------------------------------------------------------
    elif tipo.startswith("BT"):
        nombre = f"CONDUCTOR BT {calibre}"

        # Para C2, BT se cobra por longitud física del tendido,
        # no por metros-conductor.
        cantidad = _longitud_lineal(cable, longitud_material)

        precio = lista_precios.get(
            "CONDUCTOR BT GLOBAL",
            lista_precios.get("CONDUCTOR BT WP 3/0 AWG FIG", 0),
        )

    # ------------------------------------------------------
    # Neutro
    # ------------------------------------------------------
    elif tipo.startswith("N"):
        calibre_n = calibre.replace("WP", "").strip()
        nombre = f"CONDUCTOR N {calibre_n}"

        precio = lista_precios.get(
            "CONDUCTOR N 2 AWG SPARROW",
            0,
        )

    # ------------------------------------------------------
    # Hilo piloto
    # ------------------------------------------------------
    elif tipo.startswith("HP"):
        nombre = f"HILO PILOTO HP {calibre}"

        precio = lista_precios.get(
            "HILO PILOTO HP WP 2 AWG PEACH",
            0,
        )

    else:
        return None

    return _fila_mano_obra(
        estructura=nombre,
        cantidad=cantidad,
        precio=precio,
    )


# ==========================================================
# CABLES - CONSOLIDACIÓN
# ==========================================================

def _agregar_cable_resumen(
    df_detalle: pd.DataFrame,
    df_cables: pd.DataFrame | None,
    lista_precios: dict | None = None,
    contratista: str = "C1",
) -> pd.DataFrame:

    if df_cables is None or df_cables.empty:
        return df_detalle

    contratista = str(contratista).strip().upper()
    lista_precios = lista_precios or obtener_lista_precios(contratista)

    generador = {
        "C1": _fila_cable_c1,
        "C2": _fila_cable_c2,
    }.get(contratista)

    if generador is None:
        raise ValueError(f"Contratista no reconocido: {contratista!r}")

    filas = []

    for _, cable in df_cables.iterrows():
        fila = generador(cable, lista_precios)

        if fila is not None:
            filas.append(fila)

    if not filas:
        return df_detalle

    return pd.concat(
        [df_detalle, pd.DataFrame(filas)],
        ignore_index=True,
    )


# ==========================================================
# ESTRUCTURAS
# ==========================================================

def calcular_detalle_mano_obra(
    df_estructuras_por_punto: pd.DataFrame,
    lista_precios: dict,
) -> pd.DataFrame:

    columnas = [
        "Punto",
        "Estructura",
        "Cantidad",
        "Precio",
        "Subtotal",
    ]

    if df_estructuras_por_punto is None or df_estructuras_por_punto.empty:
        return pd.DataFrame(columns=columnas)

    filas = []

    for _, row in df_estructuras_por_punto.iterrows():
        punto = row.get("Punto")
        estructura = str(row.get("Estructura", "")).strip()
        cantidad = _to_float(row.get("Cantidad", 0))

        if not estructura or cantidad <= 0:
            continue

        precio = _precio_estructura(
            estructura,
            lista_precios,
        )

        filas.append(
            _fila_mano_obra(
                punto=punto,
                estructura=estructura,
                cantidad=cantidad,
                precio=precio,
            )
        )

    return pd.DataFrame(filas, columns=columnas)


# ==========================================================
# ADICIONALES
# ==========================================================

def _agregar_adicionales(df_detalle: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega trabajos manuales extraordinarios.

    La lista está vacía por defecto, por lo que ningún desmontaje,
    reubicación u otro trabajo se incorpora automáticamente.
    """

    if not ADICIONALES_MANO_OBRA:
        return df_detalle

    filas = []

    for item in ADICIONALES_MANO_OBRA:
        estructura = str(item.get("Estructura", "")).strip()
        punto = item.get("Punto", "ADICIONAL")
        cantidad = _to_float(item.get("Cantidad", 0))
        precio = _to_float(item.get("Precio", 0))

        if not estructura or cantidad <= 0 or precio < 0:
            continue

        filas.append(
            _fila_mano_obra(
                punto=punto,
                estructura=estructura,
                cantidad=cantidad,
                precio=precio,
            )
        )

    if not filas:
        return df_detalle

    return pd.concat(
        [df_detalle, pd.DataFrame(filas)],
        ignore_index=True,
    )


# ==========================================================
# TOTALES POR PUNTO
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

def calcular_mano_obra_proyecto(
    df_estructuras_por_punto: pd.DataFrame,
    df_cables=None,
    contratista: str = "C2",
):
    """
    Calcula la mano de obra completa del proyecto.

    Flujo:
        estructuras
            ↓
        conductores
            ↓
        adicionales manuales
            ↓
        totales por punto

    Mantiene el contrato utilizado actualmente por
    costos_precios.orquestador_costos.
    """

    contratista = str(contratista).strip().upper()
    lista_precios = obtener_lista_precios(contratista)

    # 1. Estructuras
    df_detalle = calcular_detalle_mano_obra(
        df_estructuras_por_punto,
        lista_precios,
    )

    # 2. Conductores
    df_detalle = _agregar_cable_resumen(
        df_detalle,
        df_cables,
        lista_precios,
        contratista,
    )

    # 3. Trabajos extraordinarios
    df_detalle = _agregar_adicionales(df_detalle)

    # 4. Totales
    df_totales = calcular_totales_por_punto(
        df_detalle[df_detalle["Punto"].notna()]
    )

    # 5. Orden
    if not df_detalle.empty:
        df_detalle = (
            df_detalle
            .sort_values(["Punto", "Estructura"], na_position="last")
            .reset_index(drop=True)
        )

    if not df_totales.empty:
        df_totales = (
            df_totales
            .sort_values("Punto")
            .reset_index(drop=True)
        )

    return {
        "df_detalle": df_detalle,
        "df_totales": df_totales,
    }
