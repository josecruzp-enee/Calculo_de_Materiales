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
# MANO DE OBRA UNITARIA PARA ESTRUCTURAS
# =========================================================
def _obtener_mano_obra_unitaria(
    estructura: str,
    lista_mano_obra: dict
) -> float:
    """
    Busca la mano de obra unitaria de una estructura.

    Primero intenta match exacto.
    Si no encuentra, intenta match parcial por prefijo.
    """

    estructura = str(estructura).strip().upper()

    if estructura in lista_mano_obra:
        return float(lista_mano_obra[estructura])

    for key in lista_mano_obra:
        key_norm = str(key).strip().upper()

        if estructura.startswith(key_norm):
            return float(lista_mano_obra[key])

    return 0.0


# =========================================================
# COSTOS OPERATIVOS
# =========================================================
def calcular_costos_operativos(
    *,
    costo_material_total: float,
    factor_equipos: float = 0.05,
    factor_logistica: float = 0.15,
):
    """
    Calcula costos operativos distribuidos según el costo de materiales.
    """

    equipos = costo_material_total * factor_equipos
    logistica = costo_material_total * factor_logistica

    return {
        "equipos": round(equipos, 2),
        "logistica": round(logistica, 2),
        "operativo_total": round(equipos + logistica, 2),
    }


# =========================================================
# LIMPIEZA DE TEXTO
# =========================================================
def limpiar_calibre(txt):
    """
    Limpia el texto del calibre para construir la descripción del conductor.
    """

    txt = str(txt).upper().strip()

    txt = txt.replace("CABLE DE ALUMINIO", "")
    txt = txt.replace("FORRADO", "")
    txt = txt.replace("ACSR", "")
    txt = txt.replace("#", "")
    txt = txt.replace("  ", " ")

    return txt.strip()


def _normalizar_contratista(contratista: str) -> str:
    return str(contratista).strip().upper()


def _normalizar_tipo_cable(valor) -> str:
    return str(valor).strip().upper()


# =========================================================
# VALIDACIONES DE CABLES
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
    Detecta si en el proyecto existe cable BT.
    Esto se usa para la regla C2:
    si hay BT, no se cobra N ni HP por separado.
    """

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
    Lee la longitud del cable.
    Prioridad:
    1. Total Cable (m)
    2. Longitud
    """

    longitud = fila.get("Total Cable (m)", fila.get("Longitud", 0))

    try:
        longitud = float(longitud or 0)
    except Exception:
        longitud = 0.0

    return longitud


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
    Devuelve la descripción y claves de material/mano de obra
    según el tipo de cable.
    """

    calibre_limpio = limpiar_calibre(calibre).strip()

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
# CÁLCULO DE MATERIAL Y MANO DE OBRA DE CABLES
# =========================================================
def _calcular_material_unitario_cable(
    clave_material: str
) -> float:
    """
    El material del cable está en L/pie.
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
    Devuelve la mano de obra del cable.

    C1:
        Usa la clave específica.

    C2:
        MT usa CONDUCTOR MT GLOBAL.
        BT usa CONDUCTOR BT GLOBAL.
        N usa CONDUCTOR N 2 AWG SPARROW.
        HP usa clave específica.
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

        if tipo.startswith("N"):
            return float(
                lista_mano_obra.get("CONDUCTOR N 2 AWG SPARROW", 0.0)
            )

        if tipo.startswith("HP"):
            return float(
                lista_mano_obra.get(clave_mano_obra, 0.0)
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
    Crea una fila de precio para un cable.
    Mantiene compatibilidad con reportes que esperan:
    Precio Unitario / Precio Total.
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

        # Compatibilidad con reportes anteriores
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
    Procesa una fila de df_cables y devuelve una fila para df_precios.
    Si no aplica, devuelve None.
    """

    tipo = _normalizar_tipo_cable(fila_cable.get("Tipo", ""))
    calibre = str(fila_cable.get("Calibre", "")).strip()

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
# AGREGAR CABLES AL PRESUPUESTO
# =========================================================
def _agregar_cable_a_precios(
    df_precios,
    entrada,
    contratista
):
    """
    Agrega cables al presupuesto.

    Reglas:
    - C1 cobra desagregado: MT, BT, N y HP si existen.
    - C2 cobra globalizado:
        Si hay BT, no cobra N ni HP por separado.
        Si no hay BT, sí cobra N y HP si existen.

    Unidades:
    - Longitud del proyecto: metros.
    - Precio material cable: L/pie.
    - Mano de obra: L/metro.
    """

    df_cables = _obtener_df_cables(entrada)

    if df_cables is None:
        return df_precios

    contratista_norm = _normalizar_contratista(contratista)

    lista_mano_obra = obtener_lista_precios(contratista_norm)

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


# =========================================================
# COSTO UNITARIO DE ESTRUCTURAS
# =========================================================
def _calcular_costo_operativo_unitario(
    *,
    material_total_estructura: float,
    material_total_global: float,
    operativo_total: float,
    cantidad: int
) -> float:
    """
    Distribuye el costo operativo según el peso del material
    de cada estructura.
    """

    if material_total_global <= 0 or cantidad <= 0:
        return 0.0

    peso = material_total_estructura / material_total_global

    return (operativo_total * peso) / cantidad


def _crear_fila_estructura_precio(
    *,
    estructura: str,
    cantidad: int,
    material_unit: float,
    mano_obra_unit: float,
    costo_operativo_unit: float,
    porcentaje_utilidad: float
) -> Dict[str, Any]:
    """
    Crea una fila de precio para una estructura.
    Mantiene compatibilidad con reportes que esperan:
    Precio Unitario / Precio Total.
    """

    total_unitario = (
        material_unit
        + mano_obra_unit
        + costo_operativo_unit
    )

    if porcentaje_utilidad > 0:
        total_unitario = total_unitario * (1 + porcentaje_utilidad)

    total_unitario = round(total_unitario, 2)

    total_proyecto = round(
        total_unitario * cantidad,
        2
    )

    return {
        "Estructura": estructura,
        "Cantidad": cantidad,

        "Material Unitario": round(material_unit, 2),
        "Mano Obra Unitaria": round(mano_obra_unit, 2),
        "Costo Operativo Unitario": round(costo_operativo_unit, 2),

        "Total Unitario": total_unitario,
        "Total Proyecto": total_proyecto,
        "Subtotal": total_proyecto,

        # Compatibilidad con reportes anteriores
        "Costo Unitario": round(material_unit, 2),
        "Costo Operativo": round(costo_operativo_unit, 2),
        "Precio Unitario": total_unitario,
        "Precio Total": total_proyecto,
    }



def _procesar_fila_estructura(
    *,
    fila: pd.Series,
    lista_mano_obra: dict,
    material_total_global: float,
    operativo_total: float,
    porcentaje_utilidad: float
) -> Dict[str, Any]:
    """
    Procesa una fila de df_costos_estructura y devuelve una fila
    para df_precios.
    """

    estructura = str(
        fila["codigodeestructura"]
    ).strip().upper()

    cantidad = max(
        1,
        int(fila["Cantidad"])
    )

    material_unit = float(
        fila["Costo Unitario"]
    )

    material_total_estructura = float(
        fila["Costo Total"]
    )

    costo_operativo_unit = _calcular_costo_operativo_unitario(
        material_total_estructura=material_total_estructura,
        material_total_global=material_total_global,
        operativo_total=operativo_total,
        cantidad=cantidad
    )

    mano_obra_unit = _obtener_mano_obra_unitaria(
        estructura,
        lista_mano_obra
    )

    return _crear_fila_estructura_precio(
        estructura=estructura,
        cantidad=cantidad,
        material_unit=material_unit,
        mano_obra_unit=mano_obra_unit,
        costo_operativo_unit=costo_operativo_unit,
        porcentaje_utilidad=porcentaje_utilidad
    )


def _generar_df_precios_estructuras(
    *,
    df_costos_estructura: pd.DataFrame,
    lista_mano_obra: dict,
    costos_op: Dict[str, float],
    porcentaje_utilidad: float
) -> pd.DataFrame:
    """
    Genera el dataframe base de precios de estructuras.
    """

    material_total_global = float(
        df_costos_estructura["Costo Total"].sum()
    )

    filas = []

    for _, fila in df_costos_estructura.iterrows():

        fila_precio = _procesar_fila_estructura(
            fila=fila,
            lista_mano_obra=lista_mano_obra,
            material_total_global=material_total_global,
            operativo_total=costos_op["operativo_total"],
            porcentaje_utilidad=porcentaje_utilidad
        )

        filas.append(fila_precio)

    df_precios = pd.DataFrame(filas)

    if not df_precios.empty:
        df_precios["Subtotal"] = df_precios["Total Proyecto"]

    return df_precios


# =========================================================
# VALIDACIONES PRINCIPALES
# =========================================================
def _validar_df_costos_estructura(
    df_costos_estructura: pd.DataFrame
) -> Optional[Dict[str, Any]]:
    """
    Valida df_costos_estructura.
    Si está mal, devuelve respuesta de error.
    Si está bien, devuelve None.
    """

    if (
        df_costos_estructura is None
        or df_costos_estructura.empty
    ):
        return {
            "ok": False,
            "errores": ["Sin costos de estructura"],
            "df_precios_estructura": None,
        }

    return None


def _respuesta_ok(
    *,
    df_precios: pd.DataFrame,
    costos_op: Dict[str, float]
) -> Dict[str, Any]:
    return {
        "ok": True,
        "df_precios_estructura": df_precios,
        "costos_operativos": costos_op,
    }


def _respuesta_error(error: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "errores": [str(error)],
        "df_precios_estructura": None,
    }


# =========================================================
# SUMINISTRO E INSTALACIÓN
# =========================================================
def ejecutar_costos(
    entrada,
    contratista="C1",
    porcentaje_utilidad=0.0,
) -> Dict[str, Any]:
    """
    Orquesta el cálculo de costos.

    Flujo:
    1. Valida costos de estructura.
    2. Obtiene lista de mano de obra según contratista.
    3. Calcula costos operativos.
    4. Genera precios de estructuras.
    5. Agrega cables del proyecto.
    6. Devuelve df_precios_estructura.
    """

    try:

        df_costos_estructura = entrada.df_costos_estructura

        error_validacion = _validar_df_costos_estructura(
            df_costos_estructura
        )

        if error_validacion is not None:
            return error_validacion

        lista_mano_obra = obtener_lista_precios(contratista)

        material_total = float(
            df_costos_estructura["Costo Total"].sum()
        )

        costos_op = calcular_costos_operativos(
            costo_material_total=material_total
        )

        df_precios = _generar_df_precios_estructuras(
            df_costos_estructura=df_costos_estructura,
            lista_mano_obra=lista_mano_obra,
            costos_op=costos_op,
            porcentaje_utilidad=porcentaje_utilidad
        )

        df_precios = _agregar_cable_a_precios(
            df_precios,
            entrada,
            contratista
        )

        return _respuesta_ok(
            df_precios=df_precios,
            costos_op=costos_op
        )

    except Exception as e:

        return _respuesta_error(e)
