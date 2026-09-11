# -*- coding: utf-8 -*-
"""
costos_precios/precio_estructura.py

Construcción del presupuesto de suministro e instalación.

RESPONSABILIDAD
---------------
Este módulo construye los precios del proyecto a partir de:

1. Costo de materiales por estructura.
2. Mano de obra cotizada por el contratista.
3. Cables del proyecto.
4. Materiales extra.
5. Utilidad comercial opcional.

NO calcula:
- costo real de cuadrillas;
- productividad;
- duración del proyecto;
- costo real de equipos;
- costo real de logística;
- costos indirectos de ejecución;
- margen real del contratista.

Esos conceptos pertenecen al modelo de ejecución/costos operativos.

FLUJO PRINCIPAL
---------------
entrada
    ↓
df_costos_estructura
    ↓
materiales + MO contratista
    ↓
precios de estructuras
    ↓
cables
    ↓
materiales extra
    ↓
df_precios_estructura

FUNCIÓN PÚBLICA PRINCIPAL
-------------------------
ejecutar_costos(...)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from ayuda.debug import debug_guardar
from costos_precios.costos_materiales import _norm_material
from costos_precios.mano_obra_por_punto import obtener_lista_precios

# =========================================================
# COMPATIBILIDAD CON ORQUESTADOR_COSTOS
# =========================================================
def _agregar_cable_a_precios(
    df_precios: pd.DataFrame,
    entrada,
    contratista: str = "C1",
) -> pd.DataFrame:
    """
    Compatibilidad con orquestador_costos.py.
    """
    return _agregar_cables_a_precios(
        df_precios,
        entrada,
        contratista,
    )
# =========================================================
# CONSTANTES
# =========================================================

FACTOR_PIE_POR_METRO = 3.28084


# =========================================================
# UTILIDADES
# =========================================================

def _numero_seguro(valor, default=0.0) -> float:
    """Convierte un valor a float de forma segura."""
    valor = pd.to_numeric(valor, errors="coerce")
    return float(default) if pd.isna(valor) else float(valor)


def _normalizar_contratista(contratista: str) -> str:
    return str(contratista).strip().upper()


def _normalizar_tipo_cable(valor) -> str:
    return str(valor).strip().upper()


def limpiar_calibre(txt) -> str:
    """Limpia el calibre para construir descripciones de conductores."""
    txt = str(txt).upper().strip()

    for termino in (
        "CABLE DE ALUMINIO",
        "FORRADO",
        "ACSR",
        "#",
    ):
        txt = txt.replace(termino, "")

    return " ".join(txt.split())


# =========================================================
# MANO DE OBRA COTIZADA POR CONTRATISTA
# =========================================================

def _obtener_mano_obra_unitaria(
    estructura: str,
    lista_mano_obra: dict,
) -> float:
    """
    Obtiene la tarifa unitaria cotizada por el contratista.

    Primero intenta coincidencia exacta.
    Después intenta coincidencia por prefijo.

    IMPORTANTE:
    Esto representa PRECIO DE MANO DE OBRA DEL CONTRATISTA,
    no costo real de ejecución.
    """
    estructura = str(estructura).strip().upper()

    if estructura in lista_mano_obra:
        return float(lista_mano_obra[estructura])

    for clave, precio in lista_mano_obra.items():
        clave_norm = str(clave).strip().upper()

        if estructura.startswith(clave_norm):
            return float(precio)

    return 0.0


# =========================================================
# CABLES — OBTENCIÓN Y NORMALIZACIÓN
# =========================================================

def _obtener_df_cables(entrada) -> Optional[pd.DataFrame]:
    """Obtiene una copia del DataFrame de cables del proyecto."""
    df_cables = getattr(entrada, "df_cables", None)

    if not isinstance(df_cables, pd.DataFrame) or df_cables.empty:
        return None

    return df_cables.copy()


def _leer_longitud_cable(fila: pd.Series) -> float:
    """Lee la cantidad total de cable en metros-conductor."""
    return _numero_seguro(
        fila.get(
            "Total Cable (m)",
            fila.get("Longitud", 0.0),
        ),
        0.0,
    )


def _calcular_longitud_linea_desde_cable(
    fila_cable: pd.Series,
    longitud_material: float,
) -> float:
    """
    Calcula la longitud lineal del circuito.

    Material:
        metros-conductor.

    Mano de obra:
        metros lineales de tendido.

    Si existe 'Longitud', se utiliza directamente.
    Si no existe, se calcula:

        metros-conductor / número de conductores
    """
    longitud = _numero_seguro(
        fila_cable.get("Longitud", 0.0),
        0.0,
    )

    if longitud > 0:
        return longitud

    conductores = _numero_seguro(
        fila_cable.get("Conductores", 1),
        1.0,
    )

    if conductores <= 0:
        conductores = 1.0

    return float(longitud_material) / conductores


# =========================================================
# CABLES — CLASIFICACIÓN
# =========================================================

def _obtener_claves_cable(
    *,
    tipo: str,
    calibre: str,
) -> Optional[Dict[str, str]]:
    """
    Obtiene descripción y clave de mano de obra según tipo
    de conductor.
    """
    calibre_limpio = limpiar_calibre(calibre)

    if tipo.startswith("MT"):
        calibre_limpio = calibre_limpio.replace("WP", "").strip()

        return {
            "descripcion": f"CONDUCTOR MT {calibre_limpio}",
            "clave_mano_obra": "CONDUCTOR MT 1/0 AWG RAVEN",
        }

    if tipo.startswith("BT"):
        return {
            "descripcion": f"CONDUCTOR BT {calibre_limpio}",
            "clave_mano_obra": "CONDUCTOR BT WP 3/0 AWG FIG",
        }

    if tipo.startswith("N"):
        calibre_limpio = calibre_limpio.replace("WP", "").strip()

        return {
            "descripcion": f"CONDUCTOR N {calibre_limpio}",
            "clave_mano_obra": "CONDUCTOR N 2 AWG SPARROW",
        }

    if tipo.startswith("HP"):
        return {
            "descripcion": f"HILO PILOTO HP {calibre_limpio}",
            "clave_mano_obra": "HILO PILOTO HP WP 2 AWG PEACH",
        }

    return None


# =========================================================
# CABLES — COSTO DE MATERIAL
# =========================================================

def _calcular_material_unitario_cable(
    *,
    calibre: str,
    df_costos_materiales: pd.DataFrame,
) -> float:
    """
    Obtiene el precio del conductor ya evaluado por
    costos_materiales.py.

    El catálogo almacena el conductor en L/pie.
    Aquí únicamente se convierte a L/metro.
    """
    if (
        not isinstance(df_costos_materiales, pd.DataFrame)
        or df_costos_materiales.empty
    ):
        raise ValueError(
            "df_costos_materiales no está disponible "
            "para obtener el precio del cable."
        )

    requeridas = {
        "Materiales",
        "Unidad",
        "Costo Unitario",
    }

    faltantes = requeridas - set(df_costos_materiales.columns)

    if faltantes:
        raise ValueError(
            "df_costos_materiales no contiene las columnas "
            f"requeridas: {sorted(faltantes)}"
        )

    clave_cable = _norm_material(calibre)

    df_busqueda = df_costos_materiales[
        df_costos_materiales["Unidad"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("PIE")
    ].copy()

    df_busqueda["_clave"] = (
        df_busqueda["Materiales"]
        .astype(str)
        .apply(_norm_material)
    )

    coincidencias = df_busqueda[
        df_busqueda["_clave"].eq(clave_cable)
    ]

    if coincidencias.empty:
        raise ValueError(
            "No se encontró el precio evaluado para "
            f"el cable: {calibre}"
        )

    if len(coincidencias) > 1:
        raise ValueError(
            "Se encontraron varios precios evaluados para "
            f"el cable: {calibre}"
        )

    precio_pie = _numero_seguro(
        coincidencias.iloc[0]["Costo Unitario"],
        0.0,
    )

    if precio_pie <= 0:
        raise ValueError(
            f"Costo unitario inválido para cable: {calibre}"
        )

    return round(
        precio_pie * FACTOR_PIE_POR_METRO,
        2,
    )


# =========================================================
# CABLES — MANO DE OBRA
# =========================================================

def _obtener_mano_obra_cable(
    *,
    tipo: str,
    contratista_norm: str,
    clave_mano_obra: str,
    lista_mano_obra: dict,
) -> float:
    """
    Obtiene la tarifa de instalación del conductor.

    C1:
        utiliza las claves específicas.

    C2:
        MT → CONDUCTOR MT GLOBAL
        BT → CONDUCTOR BT GLOBAL
        N  → CONDUCTOR N 2 AWG SPARROW
        HP → clave específica
    """
    if contratista_norm == "C2":
        if tipo.startswith("MT"):
            clave_mano_obra = "CONDUCTOR MT GLOBAL"

        elif tipo.startswith("BT"):
            clave_mano_obra = "CONDUCTOR BT GLOBAL"

        elif tipo.startswith("N"):
            clave_mano_obra = "CONDUCTOR N 2 AWG SPARROW"

    return float(
        lista_mano_obra.get(clave_mano_obra, 0.0)
    )


# =========================================================
# CONTRATO DE FILA DE PRECIO
# =========================================================

def _crear_fila_precio(
    *,
    descripcion: str,
    cantidad: float,
    material_unitario: float,
    mano_obra_unitaria: float,
    cantidad_material: Optional[float] = None,
    cantidad_mano_obra: Optional[float] = None,
    unidad: Optional[str] = None,
    tipo_partida: Optional[str] = None,
    porcentaje_utilidad: float = 0.0,
) -> Dict[str, Any]:
    """
    Crea una fila estándar de df_precios_estructura.

    No agrega costos operativos ficticios.
    """
    cantidad = _numero_seguro(cantidad)
    material_unitario = _numero_seguro(material_unitario)
    mano_obra_unitaria = _numero_seguro(mano_obra_unitaria)

    if cantidad_material is None:
        cantidad_material = cantidad

    if cantidad_mano_obra is None:
        cantidad_mano_obra = cantidad

    cantidad_material = _numero_seguro(cantidad_material)
    cantidad_mano_obra = _numero_seguro(cantidad_mano_obra)

    total_material = cantidad_material * material_unitario
    total_mano_obra = cantidad_mano_obra * mano_obra_unitaria

    subtotal_base = total_material + total_mano_obra

    factor_utilidad = 1.0 + max(
        _numero_seguro(porcentaje_utilidad),
        0.0,
    )

    total_proyecto = subtotal_base * factor_utilidad

    # Precio unitario visual.
    precio_unitario = (
        total_proyecto / cantidad
        if cantidad > 0
        else 0.0
    )

    fila = {
        "Estructura": str(descripcion).strip(),
        "Cantidad": round(cantidad, 2),

        "Material Unitario": round(material_unitario, 2),
        "Mano Obra Unitaria": round(mano_obra_unitaria, 2),

        # Se conserva el contrato de columnas para no romper
        # exportadores existentes, pero ya no se distribuyen
        # costos operativos ficticios.
        "Costo Operativo Unitario": 0.0,

        "Total Unitario": round(precio_unitario, 2),
        "Total Proyecto": round(total_proyecto, 2),
        "Subtotal": round(total_proyecto, 2),

        # Compatibilidad con reportes existentes.
        "Costo Unitario": round(material_unitario, 2),
        "Costo Operativo": 0.0,
        "Precio Unitario": round(precio_unitario, 2),
        "Precio Total": round(total_proyecto, 2),

        # Cantidades separadas.
        "Cantidad Material": round(cantidad_material, 2),
        "Cantidad Mano Obra": round(cantidad_mano_obra, 2),
    }

    if unidad is not None:
        fila["Unidad"] = str(unidad).strip().upper()

    if tipo_partida is not None:
        fila["Tipo Partida"] = tipo_partida

    return fila


# =========================================================
# CABLES — PROCESAMIENTO
# =========================================================

def _procesar_fila_cable(
    *,
    fila_cable: pd.Series,
    contratista_norm: str,
    lista_mano_obra: dict,
    df_costos_materiales: pd.DataFrame,
) -> Optional[Dict[str, Any]]:
    """Convierte una fila de cables en una partida del presupuesto."""
    tipo = _normalizar_tipo_cable(
        fila_cable.get("Tipo", "")
    )

    calibre = str(
        fila_cable.get("Calibre", "")
    ).strip()

    longitud_material = _leer_longitud_cable(
        fila_cable
    )

    if longitud_material <= 0:
        return None

    claves = _obtener_claves_cable(
        tipo=tipo,
        calibre=calibre,
    )

    if claves is None:
        return None

    material_unitario = _calcular_material_unitario_cable(
        calibre=calibre,
        df_costos_materiales=df_costos_materiales,
    )

    mano_obra_unitaria = _obtener_mano_obra_cable(
        tipo=tipo,
        contratista_norm=contratista_norm,
        clave_mano_obra=claves["clave_mano_obra"],
        lista_mano_obra=lista_mano_obra,
    )

    descripcion = claves["descripcion"]

    # Por defecto:
    # material y MO usan la cantidad recibida.
    cantidad_visual = float(longitud_material)
    cantidad_material = float(longitud_material)
    cantidad_mano_obra = float(longitud_material)
    material_unit_visual = float(material_unitario)

    # -----------------------------------------------------
    # BT
    # -----------------------------------------------------
    # Material originalmente viene como metros-conductor,
    # pero el presupuesto se presenta por metro lineal.
    #
    # Ejemplo:
    # 320 m-conductor = 160 m lineales × 2 conductores
    #
    # Se presenta:
    # Cantidad = 160 m
    # Material unitario = precio/m × 2
    # MO = una sola instalación por metro lineal
    # -----------------------------------------------------
    if tipo.startswith("BT"):
        longitud_lineal = _calcular_longitud_linea_desde_cable(
            fila_cable,
            longitud_material,
        )

        conductores = _numero_seguro(
            fila_cable.get("Conductores", 0),
            0.0,
        )

        if conductores <= 0 and longitud_lineal > 0:
            conductores = (
                longitud_material / longitud_lineal
            )

        if conductores <= 0:
            conductores = 1.0

        cantidad_visual = longitud_lineal
        cantidad_material = longitud_lineal
        cantidad_mano_obra = longitud_lineal

        material_unit_visual = (
            material_unitario * conductores
        )

        numero_conductores = int(round(conductores))
        texto_fases = (
            "FASE"
            if numero_conductores == 1
            else "FASES"
        )

        descripcion = (
            f"{descripcion} "
            f"(1 x {numero_conductores} {texto_fases})"
        )

        debug_guardar(
            "CABLE_BT_PRECIO",
            {
                "calibre": calibre,
                "longitud_lineal": longitud_lineal,
                "metros_conductor": longitud_material,
                "conductores": conductores,
                "precio_metro_conductor": material_unitario,
                "precio_material_visual": material_unit_visual,
                "mano_obra_unitaria": mano_obra_unitaria,
                "descripcion": descripcion,
            },
        )

    return _crear_fila_precio(
        descripcion=descripcion,
        cantidad=cantidad_visual,
        material_unitario=material_unit_visual,
        mano_obra_unitaria=mano_obra_unitaria,
        cantidad_material=cantidad_material,
        cantidad_mano_obra=cantidad_mano_obra,
        tipo_partida="CABLE",
    )


# =========================================================
# CABLES — CONSOLIDACIÓN
# =========================================================

def _consolidar_cables(
    df_cables_precios: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida partidas repetidas de cables."""
    if df_cables_precios.empty:
        return df_cables_precios

    numericas = [
        "Cantidad",
        "Cantidad Material",
        "Cantidad Mano Obra",
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
    ]

    for col in numericas:
        if col not in df_cables_precios.columns:
            df_cables_precios[col] = 0.0

        df_cables_precios[col] = pd.to_numeric(
            df_cables_precios[col],
            errors="coerce",
        ).fillna(0.0)

    agrupado = (
        df_cables_precios
        .groupby(
            [
                "Estructura",
                "Material Unitario",
                "Mano Obra Unitaria",
            ],
            as_index=False,
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
            "Tipo Partida": "first",
        })
    )

    return agrupado


def _agregar_cables_a_precios(
    df_precios: pd.DataFrame,
    entrada,
    contratista: str,
) -> pd.DataFrame:
    """Agrega las partidas de conductores al presupuesto."""
    df_cables = _obtener_df_cables(entrada)

    if df_cables is None:
        return df_precios

    contratista_norm = _normalizar_contratista(
        contratista
    )

    lista_mano_obra = obtener_lista_precios(
        contratista_norm
    )

    df_costos_materiales = (
        _obtener_df_costos_materiales_existente(
            entrada
        )
    )

    filas = []

    for _, fila_cable in df_cables.iterrows():
        fila = _procesar_fila_cable(
            fila_cable=fila_cable,
            contratista_norm=contratista_norm,
            lista_mano_obra=lista_mano_obra,
            df_costos_materiales=df_costos_materiales,
        )

        if fila is not None:
            filas.append(fila)

    if not filas:
        return df_precios

    df_cables_precios = _consolidar_cables(
        pd.DataFrame(filas)
    )

    return pd.concat(
        [df_precios, df_cables_precios],
        ignore_index=True,
    )


# =========================================================
# MATERIALES EXTRA
# =========================================================

def _obtener_df_materiales_extra(
    entrada,
) -> Optional[pd.DataFrame]:
    """Obtiene materiales extra definidos por el proyecto."""
    df = getattr(
        entrada,
        "df_materiales_extra",
        None,
    )

    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    requeridas = {
        "Materiales",
        "Unidad",
        "Cantidad",
    }

    faltantes = requeridas - set(df.columns)

    if faltantes:
        raise ValueError(
            "df_materiales_extra no contiene las columnas "
            f"requeridas: {sorted(faltantes)}"
        )

    return df.copy()


def _buscar_precio_material_extra(
    *,
    material: str,
    unidad: str,
    df_costos_materiales: pd.DataFrame,
) -> float:
    """Obtiene el precio ya evaluado de un material extra."""
    if (
        not isinstance(df_costos_materiales, pd.DataFrame)
        or df_costos_materiales.empty
    ):
        raise ValueError(
            "df_costos_materiales no está disponible para "
            f"obtener el precio de: {material}"
        )

    requeridas = {
        "Materiales",
        "Unidad",
        "Costo Unitario",
    }

    faltantes = requeridas - set(df_costos_materiales.columns)

    if faltantes:
        raise ValueError(
            "df_costos_materiales no contiene las columnas "
            f"requeridas: {sorted(faltantes)}"
        )

    clave_material = _norm_material(material)
    clave_unidad = str(unidad).strip().upper()

    df = df_costos_materiales.copy()

    df["_clave_material"] = (
        df["Materiales"]
        .astype(str)
        .apply(_norm_material)
    )

    df["_clave_unidad"] = (
        df["Unidad"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    coincidencias = df[
        df["_clave_material"].eq(clave_material)
        & df["_clave_unidad"].eq(clave_unidad)
    ]

    if coincidencias.empty:
        raise ValueError(
            "No se encontró el precio evaluado del material "
            f"extra: {material} [{unidad}]"
        )

    precios = (
        pd.to_numeric(
            coincidencias["Costo Unitario"],
            errors="coerce",
        )
        .dropna()
        .unique()
    )

    if len(precios) == 0:
        raise ValueError(
            f"Precio inválido para material extra: {material}"
        )

    if len(precios) > 1:
        raise ValueError(
            "Se encontraron varios precios para el material "
            f"extra: {material} [{unidad}]"
        )

    precio = float(precios[0])

    if precio < 0:
        raise ValueError(
            f"Precio negativo para material extra: {material}"
        )

    return precio


def _procesar_material_extra(
    fila: pd.Series,
    df_costos_materiales: pd.DataFrame,
) -> Optional[Dict[str, Any]]:
    """Convierte un material extra en una partida de presupuesto."""
    material = str(
        fila.get("Materiales", "")
    ).strip()

    unidad = str(
        fila.get("Unidad", "")
    ).strip()

    cantidad = _numero_seguro(
        fila.get("Cantidad", 0.0)
    )

    if not material or cantidad <= 0:
        return None

    material_unitario = _buscar_precio_material_extra(
        material=material,
        unidad=unidad,
        df_costos_materiales=df_costos_materiales,
    )

    mano_obra_unitaria = _numero_seguro(
        fila.get("Mano Obra Unitaria", 0.0)
    )

    descripcion = (
        f"SUMINISTRO E INSTALACIÓN DE {material}"
        if mano_obra_unitaria > 0
        else f"SUMINISTRO DE {material}"
    )

    return _crear_fila_precio(
        descripcion=descripcion,
        cantidad=cantidad,
        material_unitario=material_unitario,
        mano_obra_unitaria=mano_obra_unitaria,
        cantidad_material=cantidad,
        cantidad_mano_obra=(
            cantidad
            if mano_obra_unitaria > 0
            else 0.0
        ),
        unidad=unidad,
        tipo_partida="MATERIAL EXTRA",
    )


def _agregar_materiales_extra_a_precios(
    df_precios: pd.DataFrame,
    entrada,
) -> pd.DataFrame:
    """Agrega materiales extra al presupuesto."""
    df_extra = _obtener_df_materiales_extra(
        entrada
    )

    if df_extra is None:
        return df_precios

    df_costos_materiales = (
        _obtener_df_costos_materiales_existente(
            entrada
        )
    )

    filas = []

    for _, fila in df_extra.iterrows():
        partida = _procesar_material_extra(
            fila,
            df_costos_materiales,
        )

        if partida is not None:
            filas.append(partida)

    if not filas:
        return df_precios

    df_extra_precios = pd.DataFrame(filas)

    debug_guardar(
        "MATERIALES_EXTRA_AGREGADOS_A_PRECIOS",
        {
            "cantidad_filas": len(df_extra_precios),
            "total": round(
                df_extra_precios["Total Proyecto"].sum(),
                2,
            ),
        },
    )

    return pd.concat(
        [df_precios, df_extra_precios],
        ignore_index=True,
    )


# =========================================================
# ESTRUCTURAS
# =========================================================

def _crear_fila_estructura(
    *,
    estructura: str,
    cantidad: int,
    material_unitario: float,
    mano_obra_unitaria: float,
    porcentaje_utilidad: float,
) -> Dict[str, Any]:
    """Construye la partida de una estructura."""
    return _crear_fila_precio(
        descripcion=estructura,
        cantidad=cantidad,
        material_unitario=material_unitario,
        mano_obra_unitaria=mano_obra_unitaria,
        cantidad_material=cantidad,
        cantidad_mano_obra=cantidad,
        tipo_partida="ESTRUCTURA",
        porcentaje_utilidad=porcentaje_utilidad,
    )


def _procesar_fila_estructura(
    *,
    fila: pd.Series,
    lista_mano_obra: dict,
    porcentaje_utilidad: float,
) -> Dict[str, Any]:
    """Procesa una estructura del proyecto."""
    estructura = str(
        fila["codigodeestructura"]
    ).strip().upper()

    cantidad = max(
        1,
        int(_numero_seguro(fila["Cantidad"], 1)),
    )

    material_unitario = _numero_seguro(
        fila["Costo Unitario"]
    )

    mano_obra_unitaria = _obtener_mano_obra_unitaria(
        estructura,
        lista_mano_obra,
    )

    return _crear_fila_estructura(
        estructura=estructura,
        cantidad=cantidad,
        material_unitario=material_unitario,
        mano_obra_unitaria=mano_obra_unitaria,
        porcentaje_utilidad=porcentaje_utilidad,
    )


def _generar_df_precios_estructuras(
    *,
    df_costos_estructura: pd.DataFrame,
    lista_mano_obra: dict,
    porcentaje_utilidad: float,
) -> pd.DataFrame:
    """
    Construye el presupuesto base de estructuras.

    Precio =
        material
        + MO cotizada por contratista
        + utilidad opcional

    No distribuye costos operativos.
    """
    filas = []

    for _, fila in df_costos_estructura.iterrows():
        filas.append(
            _procesar_fila_estructura(
                fila=fila,
                lista_mano_obra=lista_mano_obra,
                porcentaje_utilidad=porcentaje_utilidad,
            )
        )

    return pd.DataFrame(filas)


# =========================================================
# VALIDACIONES
# =========================================================

def _validar_df_costos_estructura(
    df_costos_estructura: pd.DataFrame,
) -> Optional[Dict[str, Any]]:
    """Valida la entrada principal del cálculo."""
    if (
        not isinstance(df_costos_estructura, pd.DataFrame)
        or df_costos_estructura.empty
    ):
        return {
            "ok": False,
            "errores": ["Sin costos de estructura"],
            "df_precios_estructura": None,
            "df_costos_materiales": pd.DataFrame(),
        }

    requeridas = {
        "codigodeestructura",
        "Cantidad",
        "Costo Unitario",
    }

    faltantes = requeridas - set(
        df_costos_estructura.columns
    )

    if faltantes:
        return {
            "ok": False,
            "errores": [
                "df_costos_estructura incompleto. "
                f"Faltan: {sorted(faltantes)}"
            ],
            "df_precios_estructura": None,
            "df_costos_materiales": pd.DataFrame(),
        }

    return None


def _obtener_df_costos_materiales_existente(
    entrada,
) -> pd.DataFrame:
    """
    Recupera df_costos_materiales ya calculado.

    Este módulo NO recalcula costos de materiales.
    """
    df = getattr(
        entrada,
        "df_costos_materiales",
        pd.DataFrame(),
    )

    return (
        df
        if isinstance(df, pd.DataFrame)
        else pd.DataFrame()
    )


# =========================================================
# RESPUESTAS
# =========================================================

def _respuesta_ok(
    *,
    entrada,
    df_precios: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Contrato de salida exitoso.

    'costos_operativos' se conserva temporalmente como
    diccionario vacío para compatibilidad con consumidores
    existentes. Ya NO se calculan aquí.
    """
    return {
        "ok": True,
        "df_precios_estructura": df_precios,
        "df_costos_materiales": (
            _obtener_df_costos_materiales_existente(
                entrada
            )
        ),
        "costos_operativos": {},
    }


def _respuesta_error(
    error: Exception,
    entrada=None,
) -> Dict[str, Any]:
    """Contrato de salida cuando ocurre un error."""
    df_costos_materiales = (
        _obtener_df_costos_materiales_existente(entrada)
        if entrada is not None
        else pd.DataFrame()
    )

    return {
        "ok": False,
        "errores": [str(error)],
        "df_precios_estructura": None,
        "df_costos_materiales": df_costos_materiales,
    }


# =========================================================
# FUNCIÓN PÚBLICA PRINCIPAL
# =========================================================

def ejecutar_costos(
    entrada,
    contratista="C1",
    porcentaje_utilidad=0.0,
) -> Dict[str, Any]:
    """
    Construye el presupuesto de suministro e instalación.

    FLUJO
    -----
    1. Valida costos de estructuras.
    2. Obtiene tarifas de MO del contratista.
    3. Genera precios de estructuras.
    4. Agrega cables.
    5. Agrega materiales extra.
    6. Devuelve df_precios_estructura.

    IMPORTANTE
    ----------
    Este módulo NO calcula el costo real de ejecución.

    La comparación futura será:

        INGRESO CONTRATISTA
            = MO cotizada / precio contractual

        COSTO REAL DE EJECUCIÓN
            = cuadrillas
            + equipos
            + logística
            + otros costos reales

        MARGEN
            = ingreso - costo real
    """
    try:
        df_costos_estructura = (
            entrada.df_costos_estructura
        )

        error = _validar_df_costos_estructura(
            df_costos_estructura
        )

        if error is not None:
            return error

        contratista_norm = _normalizar_contratista(
            contratista
        )

        lista_mano_obra = obtener_lista_precios(
            contratista_norm
        )

        # -------------------------------------------------
        # 1. ESTRUCTURAS
        # -------------------------------------------------
        df_precios = _generar_df_precios_estructuras(
            df_costos_estructura=df_costos_estructura,
            lista_mano_obra=lista_mano_obra,
            porcentaje_utilidad=porcentaje_utilidad,
        )

        # -------------------------------------------------
        # 2. CABLES
        # -------------------------------------------------
        df_precios = _agregar_cables_a_precios(
            df_precios,
            entrada,
            contratista_norm,
        )

        # -------------------------------------------------
        # 3. MATERIALES EXTRA
        # -------------------------------------------------
        df_precios = (
            _agregar_materiales_extra_a_precios(
                df_precios,
                entrada,
            )
        )

        debug_guardar(
            "PRECIO_ESTRUCTURA_RESULTADO",
            {
                "contratista": contratista_norm,
                "filas": len(df_precios),
                "total_presupuesto": round(
                    pd.to_numeric(
                        df_precios["Total Proyecto"],
                        errors="coerce",
                    ).fillna(0.0).sum(),
                    2,
                ),
            },
        )

        return _respuesta_ok(
            entrada=entrada,
            df_precios=df_precios,
        )

    except Exception as error:
        debug_guardar(
            "PRECIO_ESTRUCTURA_ERROR",
            {
                "error": str(error),
                "tipo": type(error).__name__,
            },
        )

        return _respuesta_error(
            error,
            entrada=entrada,
        )
