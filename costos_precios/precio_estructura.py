# -*- coding: utf-8 -*-
# costos_precios/precio_estructura.py

from __future__ import annotations

from typing import Dict, Any
import pandas as pd

from costos_precios.mano_obra_por_punto import obtener_lista_precios


# =========================================================
# MANO DE OBRA UNITARIA
# =========================================================
def _obtener_mano_obra_unitaria(
    estructura: str,
    lista_mano_obra: dict
) -> float:

    estructura = str(estructura).strip().upper()

    # =====================================================
    # MATCH EXACTO
    # =====================================================
    if estructura in lista_mano_obra:
        return float(lista_mano_obra[estructura])

    # =====================================================
    # MATCH PARCIAL
    # =====================================================
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

    equipos = costo_material_total * factor_equipos
    logistica = costo_material_total * factor_logistica

    return {
        "equipos": round(equipos, 2),
        "logistica": round(logistica, 2),
        "operativo_total": round(equipos + logistica, 2),
    }


# =========================================================
# LIMPIAR CALIBRE
# =========================================================
def limpiar_calibre(txt):

    txt = str(txt).upper().strip()

    txt = txt.replace("CABLE DE ALUMINIO", "")
    txt = txt.replace("FORRADO", "")
    txt = txt.replace("ACSR", "")
    txt = txt.replace("#", "")
    txt = txt.replace("  ", " ")

    return txt.strip()


# =========================================================
# AGREGAR CABLES
# =========================================================
# =========================================================
# AGREGAR CABLES
# =========================================================
def _agregar_cable_a_precios(
    df_precios,
    entrada,
    contratista="C1"
):
    """
    Agrega cables al presupuesto.

    Reglas:
    - C1 cobra desagregado:
        MT, BT, N y HP si existen en df_cables.

    - C2 cobra globalizado:
        Si hay BT, no cobra N ni HP por separado.
        Si NO hay BT, sí cobra N y HP si existen.

    Unidades:
    - Longitud del proyecto: metros.
    - Precio de material de cable: L/pie.
    - Mano de obra: L/metro.
    - Conversión: L/pie * 3.28084 = L/metro.
    """

    df_cables = getattr(entrada, "df_cables", None)

    if (
        df_cables is None
        or not isinstance(df_cables, pd.DataFrame)
        or df_cables.empty
    ):
        return df_precios

    lista_mano_obra = obtener_lista_precios(contratista)

    contratista_norm = str(contratista).strip().upper()

    # =====================================================
    # DETECTAR SI EXISTE BT EN EL PROYECTO
    # =====================================================
    tipos_cable = (
        df_cables["Tipo"]
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )

    existe_bt = any(t.startswith("BT") for t in tipos_cable)

    # =====================================================
    # PRECIOS MATERIAL EN L/PIE
    # =====================================================
    PRECIOS_CABLE_PIE = {
        "CONDUCTOR MT 1/0 AWG RAVEN": 8.76,
        "CONDUCTOR N 2 AWG SPARROW": 5.64,
        "CONDUCTOR BT WP 3/0 AWG FIG": 55.00,
        "HILO PILOTO HP WP 2 AWG PEACH": 5.23,
        "CONDUCTOR BT WP 266.8 MCM MULBERRY": 81.00,
    }

    FACTOR_PIE_POR_METRO = 3.28084

    filas = []

    for _, c in df_cables.iterrows():

        tipo = str(c.get("Tipo", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        longitud = c.get("Total Cable (m)", c.get("Longitud", 0))

        try:
            longitud = float(longitud or 0)
        except Exception:
            continue

        if longitud <= 0:
            continue

        calibre_limpio = limpiar_calibre(calibre).strip()

        descripcion = None
        clave_material = None
        clave_mano_obra = None

        # =================================================
        # MEDIA TENSIÓN
        # =================================================
        if tipo.startswith("MT"):

            calibre_limpio = calibre_limpio.replace("WP", "").strip()

            descripcion = f"CONDUCTOR MT {calibre_limpio}"

            clave_material = "CONDUCTOR MT 1/0 AWG RAVEN"
            clave_mano_obra = "CONDUCTOR MT 1/0 AWG RAVEN"

        # =================================================
        # BAJA TENSIÓN
        # =================================================
        elif tipo.startswith("BT"):

            descripcion = f"CONDUCTOR BT {calibre_limpio}"

            clave_material = "CONDUCTOR BT WP 3/0 AWG FIG"
            clave_mano_obra = "CONDUCTOR BT WP 3/0 AWG FIG"

        # =================================================
        # NEUTRO
        # =================================================
        elif tipo.startswith("N"):

            # C2:
            # Si hay BT, el neutro se considera incluido en BT.
            if contratista_norm == "C2" and existe_bt:
                continue

            calibre_limpio = calibre_limpio.replace("WP", "").strip()

            descripcion = f"CONDUCTOR N {calibre_limpio}"

            clave_material = "CONDUCTOR N 2 AWG SPARROW"
            clave_mano_obra = "CONDUCTOR N 2 AWG SPARROW"

        # =================================================
        # HILO PILOTO
        # =================================================
        elif tipo.startswith("HP"):

            # C2:
            # Si hay BT, el HP se considera incluido en BT.
            if contratista_norm == "C2" and existe_bt:
                continue

            descripcion = f"HILO PILOTO HP {calibre_limpio}"

            clave_material = "HILO PILOTO HP WP 2 AWG PEACH"
            clave_mano_obra = "HILO PILOTO HP WP 2 AWG PEACH"

        else:
            continue

        # =================================================
        # MATERIAL UNITARIO
        # Material viene en L/pie.
        # Convertir a L/metro.
        # =================================================
        precio_material_pie = float(
            PRECIOS_CABLE_PIE.get(clave_material, 0.0)
        )

        material_unitario_metro = round(
            precio_material_pie * FACTOR_PIE_POR_METRO,
            2
        )

        # =================================================
        # MANO DE OBRA UNITARIA
        # Mano de obra viene en L/metro.
        # =================================================
        mano_obra_unitaria = float(
            lista_mano_obra.get(clave_mano_obra, 0.0)
        )

        # =================================================
        # TOTAL UNITARIO
        # =================================================
        total_unitario = round(
            material_unitario_metro + mano_obra_unitaria,
            2
        )

        total_proyecto = round(
            longitud * total_unitario,
            2
        )

        filas.append({
            "Estructura": descripcion,
            "Cantidad": round(longitud, 2),

            "Material Unitario": material_unitario_metro,
            "Mano Obra Unitaria": round(mano_obra_unitaria, 2),

            "Costo Operativo Unitario": 0.0,

            "Total Unitario": total_unitario,
            "Total Proyecto": total_proyecto,
            "Subtotal": total_proyecto,
        })

    if not filas:
        return df_precios

    df_cables_precios = pd.DataFrame(filas)

    return pd.concat(
        [df_precios, df_cables_precios],
        ignore_index=True
    )

# =========================================================
# SUMINISTRO E INSTALACIÓN
# =========================================================
def ejecutar_costos(
    entrada,
    contratista="C1",
    porcentaje_utilidad=0.0,
) -> Dict[str, Any]:

    try:

        # =================================================
        # COSTOS MATERIALES
        # =================================================
        df_costos_estructura = entrada.df_costos_estructura

        if (
            df_costos_estructura is None
            or df_costos_estructura.empty
        ):
            return {
                "ok": False,
                "errores": ["Sin costos de estructura"],
                "df_precios_estructura": None,
            }

        # =================================================
        # LISTA CONTRATISTA
        # =================================================
        lista_mano_obra = obtener_lista_precios(contratista)

        # =================================================
        # COSTOS OPERATIVOS
        # =================================================
        material_total = float(
            df_costos_estructura["Costo Total"].sum()
        )

        costos_op = calcular_costos_operativos(
            costo_material_total=material_total
        )

        filas = []

        # =================================================
        # LOOP PRINCIPAL
        # =================================================
        for _, r in df_costos_estructura.iterrows():

            estructura = str(
                r["codigodeestructura"]
            ).strip().upper()

            cantidad = max(
                1,
                int(r["Cantidad"])
            )

            material_unit = float(
                r["Costo Unitario"]
            )

            material_total_estructura = float(
                r["Costo Total"]
            )

            # =============================================
            # PESO OPERATIVO
            # =============================================
            peso = 0

            if material_total > 0:
                peso = (
                    material_total_estructura
                    / material_total
                )

            costo_operativo_unit = (
                costos_op["operativo_total"]
                * peso
            ) / cantidad

            # =============================================
            # MANO OBRA
            # =============================================
            mano_obra_unit = _obtener_mano_obra_unitaria(
                estructura,
                lista_mano_obra
            )

            # =============================================
            # TOTAL UNITARIO
            # =============================================
            total_unitario = (
                material_unit
                + mano_obra_unit
                + costo_operativo_unit
            )

            # =============================================
            # UTILIDAD OPCIONAL
            # =============================================
            if porcentaje_utilidad > 0:

                total_unitario = (
                    total_unitario
                    * (1 + porcentaje_utilidad)
                )

            total_unitario = round(
                total_unitario,
                2
            )

            # =============================================
            # TOTAL PROYECTO
            # =============================================
            total_proyecto = round(
                total_unitario * cantidad,
                2
            )

            filas.append({

                "Estructura": estructura,

                "Cantidad": cantidad,

                # =========================================
                # COSTOS
                # =========================================
                "Material Unitario": round(
                    material_unit,
                    2
                ),

                "Mano Obra Unitaria": round(
                    mano_obra_unit,
                    2
                ),

                "Costo Operativo Unitario": round(
                    costo_operativo_unit,
                    2
                ),

                # =========================================
                # TOTALES
                # =========================================
                "Total Unitario": total_unitario,

                "Total Proyecto": total_proyecto,
            })

        # =================================================
        # DATAFRAME
        # =================================================
        df_precios = pd.DataFrame(filas)

        # =================================================
        # SUBTOTAL
        # =================================================
        if not df_precios.empty:

            df_precios["Subtotal"] = (
                df_precios["Total Proyecto"]
            )

        # =================================================
        # CABLES
        # =================================================
        df_precios = _agregar_cable_a_precios(
            df_precios,
            entrada,
            contratista
        )

        # =================================================
        # OUTPUT
        # =================================================
        return {
            "ok": True,
            "df_precios_estructura": df_precios,

            "costos_operativos": costos_op,
        }

    except Exception as e:

        return {
            "ok": False,
            "errores": [str(e)],
            "df_precios_estructura": None,
        }
