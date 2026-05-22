# -*- coding: utf-8 -*-
# costos_precios/precio_estructura.py

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd

from costos_precios.mano_obra_por_punto import obtener_lista_precios


# =========================================================
# CONSTANTES
# =========================================================

FACTOR_PIE_POR_METRO = 3.28084

PRECIOS_CABLE_PIE = {
    "CONDUCTOR MT 1/0 AWG RAVEN": 8.76,
    "CONDUCTOR N 2 AWG SPARROW": 5.64,
    "CONDUCTOR BT WP 3/0 AWG FIG": 55.00,
    "HILO PILOTO HP WP 2 AWG PEACH": 5.23,
    "CONDUCTOR BT WP 266.8 MCM MULBERRY": 81.00,
}


# =========================================================
# LIMPIEZA DE TEXTO
# =========================================================

def limpiar_calibre(txt) -> str:
    """
    Limpia el texto del calibre para construir la descripción del conductor.
    """

    txt = str(txt or "").upper().strip()

    reemplazos = [
        "CABLE DE ALUMINIO",
        "CABLE ALUMINIO",
        "ALUMINIO",
        "FORRADO",
        "ACSR",
        "#",
    ]

    for r in reemplazos:
        txt = txt.replace(r, "")

    txt = txt.replace("  ", " ")

    return txt.strip()


def _normalizar_contratista(contratista: str) -> str:
    return str(contratista or "C1").strip().upper()


def _normalizar_tipo_cable(valor) -> str:
    return str(valor or "").strip().upper()


# =========================================================
# OBTENER DATAFRAME DE CABLES
# =========================================================

def _obtener_df_cables(entrada) -> Optional[pd.DataFrame]:
    """
    Obtiene df_cables desde entrada.
    Si no existe o está vacío, devuelve None.
    """

    df_cables = getattr(entrada, "df_cables", None)

    if (
        df_cables is None
        or not isinstance(df_cables, pd.DataFrame)
        or df_cables.empty
    ):
        return None

    return df_cables.copy()


def _existe_bt_en_cables(df_cables: pd.DataFrame) -> bool:
    """
    Detecta si existe cable BT en el proyecto.

    Regla usada para C2:
    si hay BT, no se cobra N ni HP por separado.
    """

    if not isinstance(df_cables, pd.DataFrame):
        return False

    if "Tipo" not in df_cables.columns:
        return False

    tipos_cable = (
        df_cables["Tipo"]
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )

    return any(t.startswith("BT") for t in tipos_cable)


def _leer_longitud_cable(fila: pd.Series) -> float:
    """
    Lee longitud de cable.

    Prioridad:
    1. Total Cable (m)
    2. Longitud
    3. longitud
    """

    longitud = fila.get(
        "Total Cable (m)",
        fila.get(
            "Longitud",
            fila.get("longitud", 0)
        )
    )

    try:
        return float(longitud or 0)
    except Exception:
        return 0.0


# =========================================================
# REGLAS DE COBRO DE CABLES
# =========================================================

def _debe_ignorar_cable(
    *,
    tipo: str,
    contratista_norm: str,
    existe_bt: bool
) -> bool:
    """
    Define si un cable debe ignorarse según contratista.

    C1:
        Cobra MT, BT, N y HP desagregado.

    C2:
        Si hay BT, no cobra N ni HP por separado.
        Si no hay BT, sí cobra N y HP si aparecen.
    """

    if contratista_norm == "C2" and existe_bt:
        if tipo.startswith("N") or tipo.startswith("HP"):
            return True

    return False


def _obtener_claves_cable(
    *,
    tipo: str,
    calibre: str
) -> Optional[Dict[str, str]]:
    """
    Devuelve descripción y claves internas de material/mano de obra.
    """

    calibre_limpio = limpiar_calibre(calibre)

    if tipo.startswith("MT"):
        calibre_limpio = calibre_limpio.replace("WP", "").strip()

        return {
            "descripcion": f"CONDUCTOR MT {calibre_limpio}",
            "clave_material": "CONDUCTOR MT 1/0 AWG RAVEN",
            "clave_mano_obra": "CONDUCTOR MT 1/0 AWG RAVEN",
        }

    if tipo.startswith("BT"):
        return {
            "descripcion": f"CONDUCTOR BT {calibre_limpio}",
            "clave_material": "CONDUCTOR BT WP 3/0 AWG FIG",
            "clave_mano_obra": "CONDUCTOR BT WP 3/0 AWG FIG",
        }

    if tipo.startswith("N"):
        calibre_limpio = calibre_limpio.replace("WP", "").strip()

        return {
            "descripcion": f"CONDUCTOR N {calibre_limpio}",
            "clave_material": "CONDUCTOR N 2 AWG SPARROW",
            "clave_mano_obra": "CONDUCTOR N 2 AWG SPARROW",
        }

    if tipo.startswith("HP"):
        return {
            "descripcion": f"HILO PILOTO HP {calibre_limpio}",
            "clave_material": "HILO PILOTO HP WP 2 AWG PEACH",
            "clave_mano_obra": "HILO PILOTO HP WP 2 AWG PEACH",
        }

    return None


# =========================================================
# CÁLCULO DE COSTO DE CABLE
# =========================================================

def _calcular_material_unitario_cable(clave_material: str) -> float:
    """
    El precio del material de cable está en L/pie.
    Se convierte a L/metro.
    """

    precio_material_pie = float(
        PRECIOS_CABLE_PIE.get(clave_material, 0.0)
    )

    return round(precio_material_pie * FACTOR_PIE_POR_METRO, 2)


def _obtener_mano_obra_cable(
    *,
    tipo: str,
    contratista_norm: str,
    clave_mano_obra: str,
    lista_mano_obra: dict
) -> float:
    """
    Devuelve mano de obra del cable.

    C1:
        Usa clave específica.

    C2:
        MT usa CONDUCTOR MT GLOBAL.
        BT usa CONDUCTOR BT GLOBAL.
        N y HP quedan con clave específica si aplican.
    """

    if contratista_norm == "C2":

        if tipo.startswith("MT"):
            return float(
                lista_mano_obra.get("CONDUCTOR MT GLOBAL", 0.0)
            )

        if tipo.startswith("BT"):
            return float(
                lista_mano_obra.get("CONDUCTOR BT GLOBAL", 0.0)
            )

    return float(
        lista_mano_obra.get(clave_mano_obra, 0.0)
    )


def _crear_fila_cable_precio(
    *,
    descripcion: str,
    longitud: float,
    material_unitario: float,
    mano_obra_unitaria: float
) -> Dict[str, Any]:
    """
    Crea una fila compatible con los reportes de presupuesto.
    """

    total_unitario = round(
        material_unitario + mano_obra_unitaria,
        2
    )

    total_proyecto = round(
        longitud * total_unitario,
        2
    )

    return {
        "Estructura": descripcion,
        "Cantidad": round(longitud, 2),

        "Material Unitario": round(material_unitario, 2),
        "Mano Obra Unitaria": round(mano_obra_unitaria, 2),
        "Costo Operativo Unitario": 0.0,
        "Total Unitario": total_unitario,
        "Total Proyecto": total_proyecto,
        "Subtotal": total_proyecto,

        # Compatibilidad con reportes/cálculos anteriores
        "Costo Unitario": round(material_unitario, 2),
        "Costo Operativo": 0.0,
        "Precio Unitario": total_unitario,
        "Precio Total": total_proyecto,
    }


def _procesar_fila_cable(
    *,
    fila_cable: pd.Series,
    contratista_norm: str,
    existe_bt: bool,
    lista_mano_obra: dict
) -> Optional[Dict[str, Any]]:
    """
    Procesa una fila de df_cables.
    Devuelve una fila para df_precios o None si no aplica.
    """

    tipo = _normalizar_tipo_cable(
        fila_cable.get("Tipo", "")
    )

    calibre = str(
        fila_cable.get("Calibre", "")
    ).strip()

    longitud = _leer_longitud_cable(fila_cable)

    if longitud <= 0:
        return None

    if _debe_ignorar_cable(
        tipo=tipo,
        contratista_norm=contratista_norm,
        existe_bt=existe_bt
    ):
        return None

    claves = _obtener_claves_cable(
        tipo=tipo,
        calibre=calibre
    )

    if claves is None:
        return None

    material_unitario = _calcular_material_unitario_cable(
        claves["clave_material"]
    )

    mano_obra_unitaria = _obtener_mano_obra_cable(
        tipo=tipo,
        contratista_norm=contratista_norm,
        clave_mano_obra=claves["clave_mano_obra"],
        lista_mano_obra=lista_mano_obra
    )

    return _crear_fila_cable_precio(
        descripcion=claves["descripcion"],
        longitud=longitud,
        material_unitario=material_unitario,
        mano_obra_unitaria=mano_obra_unitaria
    )


# =========================================================
# FUNCIÓN USADA POR costos_precios/orquestador_costos.py
# =========================================================

def _agregar_cable_a_precios(
    df_precios,
    entrada,
    contratista=None
) -> pd.DataFrame:
    """
    Agrega cables al DataFrame de precios de estructura.

    Esta función NO orquesta costos.
    Esta función NO calcula costos de estructuras.
    Esta función SOLO agrega las filas de cables al presupuesto.
    """

    if not isinstance(df_precios, pd.DataFrame):
        df_precios = pd.DataFrame()

    df_cables = _obtener_df_cables(entrada)

    if df_cables is None:
        return df_precios

    if contratista is None:
        contratista = getattr(entrada, "contratista", "C1")

    contratista_norm = _normalizar_contratista(contratista)

    lista_mano_obra = obtener_lista_precios(
        contratista_norm
    )

    existe_bt = _existe_bt_en_cables(df_cables)

    filas = []

    for _, fila_cable in df_cables.iterrows():

        fila_precio = _procesar_fila_cable(
            fila_cable=fila_cable,
            contratista_norm=contratista_norm,
            existe_bt=existe_bt,
            lista_mano_obra=lista_mano_obra
        )

        if fila_precio is not None:
            filas.append(fila_precio)

    if not filas:
        return df_precios

    df_cables_precios = pd.DataFrame(filas)

    return pd.concat(
        [df_precios, df_cables_precios],
        ignore_index=True
    )
