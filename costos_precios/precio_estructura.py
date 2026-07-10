# -*- coding: utf-8 -*-
# costos_precios/precio_estructura.py

from __future__ import annotations
from ayuda.debug import debug_guardar
from typing import Dict, Any, Optional
import pandas as pd
from costos_precios.costos_materiales import _norm_material
from costos_precios.mano_obra_por_punto import obtener_lista_precios

def _numero_seguro(valor, default=0.0) -> float:
    valor = pd.to_numeric(valor, errors="coerce")

    if pd.isna(valor):
        return default

    return float(valor)


def _int_seguro(valor, default=0) -> int:
    return int(_numero_seguro(valor, default))

# =========================================================
# CONSTANTES
# =========================================================

FACTOR_PIE_POR_METRO = 3.28084


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
    longitud = fila.get("Total Cable (m)", fila.get("Longitud", 0))
    return _numero_seguro(longitud, 0.0)


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
    Regla actualizada:

    Ya NO se ignora automáticamente N ni HP solo porque exista BT.

    El presupuesto debe respetar las filas que vienen en df_cables:
    - MT se cobra si viene.
    - BT se cobra si viene.
    - N se cobra si viene.
    - HP se cobra si viene.

    La lógica de si el neutro o HP existen debe resolverse antes,
    al construir df_cables.
    """

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
    *,
    calibre: str,
    df_costos_materiales: pd.DataFrame
) -> float:
    """
    Lee el costo unitario ya evaluado contra el Excel.

    No recalcula precios.
    No vuelve a leer el catálogo.
    No realiza otro merge.

    El costo almacenado en df_costos_materiales está en L/pie.
    Únicamente se convierte a L/metro para el presupuesto.
    """

    if (
        df_costos_materiales is None
        or not isinstance(df_costos_materiales, pd.DataFrame)
        or df_costos_materiales.empty
    ):
        raise ValueError(
            "df_costos_materiales no está disponible para obtener "
            "el precio del cable."
        )

    columnas_requeridas = {
        "Materiales",
        "Unidad",
        "Costo Unitario",
    }

    faltantes = columnas_requeridas - set(df_costos_materiales.columns)

    if faltantes:
        raise ValueError(
            "df_costos_materiales no contiene las columnas requeridas "
            f"para leer el precio del cable: {sorted(faltantes)}"
        )

    clave_cable = _norm_material(calibre)

    df_busqueda = df_costos_materiales[
        df_costos_materiales["Unidad"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("PIE")
    ].copy()

    df_busqueda["_Clave Cable"] = (
        df_busqueda["Materiales"]
        .astype(str)
        .apply(_norm_material)
    )

    coincidencias = df_busqueda[
        df_busqueda["_Clave Cable"].eq(clave_cable)
    ]

    if coincidencias.empty:
        raise ValueError(
            "No se encontró en df_costos_materiales el precio ya evaluado "
            f"para el cable: {calibre}"
        )

    if len(coincidencias) > 1:
        raise ValueError(
            "Se encontraron varios precios evaluados para el cable: "
            f"{calibre}"
        )

    precio_material_pie = _numero_seguro(
        coincidencias.iloc[0]["Costo Unitario"],
        0.0
    )

    if precio_material_pie <= 0:
        raise ValueError(
            "El costo unitario evaluado del cable es inválido: "
            f"{calibre}"
        )

    return round(
        precio_material_pie * FACTOR_PIE_POR_METRO,
        2
    )


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
    longitud_material: float,
    longitud_mano_obra: float,
    material_unitario: float,
    mano_obra_unitaria: float
) -> Dict[str, Any]:

    total_unitario = round(
        material_unitario + mano_obra_unitaria,
        2
    )

    total_proyecto = round(
        (longitud_material * material_unitario)
        + (longitud_mano_obra * mano_obra_unitaria),
        2
    )

    return {
        "Estructura": descripcion,
        "Cantidad": round(longitud_mano_obra, 2),

        "Material Unitario": round(material_unitario, 2),
        "Mano Obra Unitaria": round(mano_obra_unitaria, 2),
        "Costo Operativo Unitario": 0.0,
        "Total Unitario": total_unitario,
        "Total Proyecto": total_proyecto,
        "Subtotal": total_proyecto,

        "Costo Unitario": round(material_unitario, 2),
        "Costo Operativo": 0.0,
        "Precio Unitario": total_unitario,
        "Precio Total": total_proyecto,

        # Debug útil
        "Cantidad Material": round(longitud_material, 2),
        "Cantidad Mano Obra": round(longitud_mano_obra, 2),
    }
def _calcular_longitud_linea_desde_cable(
    fila_cable: pd.Series,
    longitud_material: float,
) -> float:
    """
    Calcula la distancia lineal para mano de obra.

    Regla:
    - Material se cobra por metro-conductor.
    - Mano de obra se cobra por distancia lineal del circuito.
    - Si existe columna Longitud, esa es la distancia lineal.
    - Si no existe, usa Total Cable (m) dividido entre Conductores.
    """

    longitud_lineal = _numero_seguro(
        fila_cable.get("Longitud", 0.0),
        0.0,
    )

    if longitud_lineal > 0:
        return longitud_lineal

    conductores = _numero_seguro(
        fila_cable.get("Conductores", 1),
        1,
    )

    if conductores <= 0:
        conductores = 1

    return float(longitud_material) / conductores
    
def _procesar_fila_cable(
    *,
    fila_cable: pd.Series,
    contratista_norm: str,
    existe_bt: bool,
    lista_mano_obra: dict,
    longitud_bt_mano_obra: float,
    df_costos_materiales: pd.DataFrame
) -> Optional[Dict[str, Any]]:

    tipo = _normalizar_tipo_cable(
        fila_cable.get("Tipo", "")
    )

    calibre = str(
        fila_cable.get("Calibre", "")
    ).strip()

    longitud_material = _leer_longitud_cable(
        fila_cable
    )

    if pd.isna(longitud_material) or longitud_material <= 0:
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

    # El precio ya evaluado se obtiene desde df_costos_materiales.
    material_unitario = _calcular_material_unitario_cable(
        calibre=calibre,
        df_costos_materiales=df_costos_materiales
    )

    mano_obra_unitaria = _obtener_mano_obra_cable(
        tipo=tipo,
        contratista_norm=contratista_norm,
        clave_mano_obra=claves["clave_mano_obra"],
        lista_mano_obra=lista_mano_obra
    )

    # Cada cable incluido en df_cables se cobra independientemente.
    longitud_mano_obra = float(longitud_material)

    # BT se cobra por la longitud lineal del circuito.
    if tipo.startswith("BT"):
        longitud_mano_obra = _calcular_longitud_linea_desde_cable(
            fila_cable,
            longitud_material
        )

    if pd.isna(longitud_mano_obra) or longitud_mano_obra <= 0:
        longitud_mano_obra = float(longitud_material)

    # Valores normales para MT, N y HP.
    descripcion_presupuesto = claves["descripcion"]
    cantidad_material_presupuesto = float(longitud_material)
    cantidad_mano_obra_presupuesto = float(longitud_mano_obra)
    material_unitario_presupuesto = float(material_unitario)

    # =====================================================
    # PRESENTACIÓN ESPECIAL PARA BT
    # =====================================================
    # Ejemplo:
    #   320 metros-conductor = 160 m lineales × 2 fases
    #
    # Presentación:
    #   Cantidad: 160 m
    #   Material unitario: precio por metro × 2
    #
    # Se conserva:
    #   320 × precio = 160 × (precio × 2)
    # =====================================================

    if tipo.startswith("BT"):

        conductores = _numero_seguro(
            fila_cable.get("Conductores", 0),
            0.0
        )

        if conductores <= 0 and longitud_mano_obra > 0:
            conductores = (
                float(longitud_material)
                / float(longitud_mano_obra)
            )

        if conductores <= 0:
            conductores = 1.0

        cantidad_material_presupuesto = float(
            longitud_mano_obra
        )

        cantidad_mano_obra_presupuesto = float(
            longitud_mano_obra
        )

        material_unitario_presupuesto = (
            float(material_unitario)
            * float(conductores)
        )

        numero_conductores = int(round(conductores))

        texto_fases = (
            "FASE"
            if numero_conductores == 1
            else "FASES"
        )

        # Sin salto de línea forzado.
        descripcion_presupuesto = (
            f'{claves["descripcion"]} '
            f'(1 x {numero_conductores} {texto_fases})'
        )

        debug_guardar(
            "debug_cable_bt_punto_2",
            {
                "tipo": tipo,
                "calibre": calibre,
                "longitud_lineal": float(
                    longitud_mano_obra
                ),
                "metros_conductor_originales": float(
                    longitud_material
                ),
                "conductores": float(
                    conductores
                ),
                "precio_metro_conductor": float(
                    material_unitario
                ),
                "cantidad_visual": float(
                    cantidad_material_presupuesto
                ),
                "material_unitario_visual": float(
                    material_unitario_presupuesto
                ),
                "mano_obra_unitaria": float(
                    mano_obra_unitaria
                ),
                "material_total_anterior": round(
                    float(longitud_material)
                    * float(material_unitario),
                    2
                ),
                "material_total_nuevo": round(
                    float(cantidad_material_presupuesto)
                    * float(material_unitario_presupuesto),
                    2
                ),
                "descripcion_visual": descripcion_presupuesto,
            }
        )

    return _crear_fila_cable_precio(
        descripcion=descripcion_presupuesto,
        longitud_material=cantidad_material_presupuesto,
        longitud_mano_obra=cantidad_mano_obra_presupuesto,
        material_unitario=material_unitario_presupuesto,
        mano_obra_unitaria=mano_obra_unitaria
    )
    return _crear_fila_cable_precio(
        descripcion=descripcion_presupuesto,

        # Para BT ambas cantidades serán 160.
        # Para los demás cables se conserva la lógica anterior.
        longitud_material=cantidad_material_presupuesto,
        longitud_mano_obra=cantidad_mano_obra_presupuesto,

        # Para BT incluye el número de conductores.
        material_unitario=material_unitario_presupuesto,

        # La mano de obra sigue cobrándose una sola vez
        # por metro lineal.
        mano_obra_unitaria=mano_obra_unitaria
    )
    
    return _crear_fila_cable_precio(
        descripcion=claves["descripcion"],
        longitud_material=float(longitud_material),
        longitud_mano_obra=float(longitud_mano_obra),
        material_unitario=material_unitario,
        mano_obra_unitaria=mano_obra_unitaria
    )
# =========================================================
# AGREGAR CABLES AL PRESUPUESTO
# =========================================================
def _agregar_cable_a_precios(
    df_precios,
    entrada,
    contratista=None
):
    df_cables = _obtener_df_cables(
        entrada
    )

    if df_cables is None:
        return df_precios

    if contratista is None:
        contratista = getattr(
            entrada,
            "contratista",
            "C1"
        )

    contratista_norm = _normalizar_contratista(
        contratista
    )

    lista_mano_obra = obtener_lista_precios(
        contratista_norm
    )

    existe_bt = _existe_bt_en_cables(
        df_cables
    )

    df_costos_materiales = _obtener_df_costos_materiales_existente(
        entrada
    )

    longitud_bt_mano_obra = 0.0

    filas = []

    for _, fila_cable in df_cables.iterrows():

        fila_precio = _procesar_fila_cable(
            fila_cable=fila_cable,
            contratista_norm=contratista_norm,
            existe_bt=existe_bt,
            lista_mano_obra=lista_mano_obra,
            longitud_bt_mano_obra=longitud_bt_mano_obra,
            df_costos_materiales=df_costos_materiales
        )

        if fila_precio is not None:
            filas.append(fila_precio)

    if not filas:
        return df_precios

    df_cables_precios = pd.DataFrame(
        filas
    )

    # =====================================================
    # CONSOLIDAR CABLES REPETIDOS
    # Ejemplo:
    # CONDUCTOR N 2 AWG SPARROW puede venir desde MT y BT.
    # Debe mostrarse en un solo renglón.
    #
    # IMPORTANTE:
    # - Cantidad Material se suma aparte.
    # - Cantidad Mano Obra se suma aparte.
    # - Total Proyecto se suma ya calculado.
    # =====================================================
    columnas_requeridas = [
        "Estructura",
        "Material Unitario",
        "Mano Obra Unitaria",
        "Total Unitario",
        "Total Proyecto",
        "Subtotal",
        "Costo Unitario",
        "Costo Operativo",
        "Costo Operativo Unitario",
        "Precio Unitario",
        "Precio Total",
        "Cantidad",
        "Cantidad Material",
        "Cantidad Mano Obra",
    ]

    for col in columnas_requeridas:
        if col not in df_cables_precios.columns:
            df_cables_precios[col] = 0.0

    columnas_numericas = [
        "Material Unitario",
        "Mano Obra Unitaria",
        "Total Unitario",
        "Total Proyecto",
        "Subtotal",
        "Costo Unitario",
        "Costo Operativo",
        "Costo Operativo Unitario",
        "Precio Unitario",
        "Precio Total",
        "Cantidad",
        "Cantidad Material",
        "Cantidad Mano Obra",
    ]

    for col in columnas_numericas:
        df_cables_precios[col] = pd.to_numeric(
            df_cables_precios[col],
            errors="coerce"
        ).fillna(0.0)

    df_cables_precios = (
        df_cables_precios
        .groupby(
            [
                "Estructura",
                "Material Unitario",
                "Mano Obra Unitaria",
            ],
            as_index=False
        )
        .agg({
            "Cantidad": "sum",
            "Cantidad Material": "sum",
            "Cantidad Mano Obra": "sum",

            "Total Proyecto": "sum",
            "Subtotal": "sum",
            "Precio Total": "sum",

            "Total Unitario": "first",
            "Costo Unitario": "first",
            "Costo Operativo": "first",
            "Costo Operativo Unitario": "first",
            "Precio Unitario": "first",
        })
    )

    return pd.concat(
        [
            df_precios,
            df_cables_precios
        ],
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

        # Contrato actual del exportador
        "Material Unitario": round(material_unit, 2),
        "Mano Obra Unitaria": round(mano_obra_unit, 2),
        "Costo Operativo Unitario": round(costo_operativo_unit, 2),
        "Total Unitario": total_unitario,
        "Total Proyecto": total_proyecto,
        "Subtotal": total_proyecto,

        # Compatibilidad con reportes/cálculos anteriores
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
            "df_costos_materiales": pd.DataFrame(),
        }

    return None


def _obtener_df_costos_materiales_existente(entrada) -> pd.DataFrame:
    """
    Conserva df_costos_materiales si ya existe en entrada.

    No calcula materiales.
    No inventa filas.
    No reemplaza el flujo de costos_materiales.py.
    """

    df_costos_materiales = getattr(
        entrada,
        "df_costos_materiales",
        pd.DataFrame()
    )

    if isinstance(df_costos_materiales, pd.DataFrame):
        return df_costos_materiales

    return pd.DataFrame()


def _respuesta_ok(
    *,
    entrada,
    df_precios: pd.DataFrame,
    costos_op: Dict[str, float]
) -> Dict[str, Any]:

    df_costos_materiales = _obtener_df_costos_materiales_existente(
        entrada
    )

    return {
        "ok": True,
        "df_precios_estructura": df_precios,
        "df_costos_materiales": df_costos_materiales,
        "costos_operativos": costos_op,
    }


def _respuesta_error(
    error: Exception,
    entrada=None
) -> Dict[str, Any]:

    if entrada is not None:
        df_costos_materiales = _obtener_df_costos_materiales_existente(
            entrada
        )
    else:
        df_costos_materiales = pd.DataFrame()

    return {
        "ok": False,
        "errores": [str(error)],
        "df_precios_estructura": None,
        "df_costos_materiales": df_costos_materiales,
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
    7. Conserva df_costos_materiales si ya existe.
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
            entrada=entrada,
            df_precios=df_precios,
            costos_op=costos_op
        )

    except Exception as e:

        return _respuesta_error(
            e,
            entrada=entrada
        )
