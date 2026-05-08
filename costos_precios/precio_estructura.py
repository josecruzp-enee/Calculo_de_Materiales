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
def _agregar_cable_a_precios(
    df_precios,
    entrada,
    contratista="C1"
):

    df_cables = getattr(entrada, "df_cables", None)

    if (
        df_cables is None
        or not isinstance(df_cables, pd.DataFrame)
        or df_cables.empty
    ):
        return df_precios

    lista_mano_obra = obtener_lista_precios(contratista)

    filas = []

    for _, c in df_cables.iterrows():

        tipo = str(c.get("Tipo", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        longitud = c.get("Total Cable (m)", c.get("Longitud", 0))

        try:
            longitud = float(longitud or 0)
        except:
            continue

        if longitud <= 0:
            continue

        # =================================================
        # IGNORAR
        # =================================================
        if tipo.startswith(("N", "HP")):
            continue

        # =================================================
        # LIMPIAR
        # =================================================
        calibre_limpio = limpiar_calibre(calibre).replace("WP", "").strip()

        # =================================================
        # MT
        # =================================================
        if tipo.startswith("MT"):

            descripcion = f"CONDUCTOR MT {calibre_limpio}"

            mano_obra = lista_mano_obra.get(
                "CONDUCTOR MT 1/0 AWG RAVEN",
                0
            )

        # =================================================
        # BT
        # =================================================
        elif tipo.startswith("BT"):

            descripcion = f"CONDUCTOR BT {calibre_limpio}"

            mano_obra = lista_mano_obra.get(
                "CONDUCTOR BT WP 3/0 AWG FIG",
                0
            )

        else:
            continue

        # =================================================
        # FILA
        # =================================================
        filas.append({
            "Estructura": descripcion,
            "Cantidad": round(longitud, 2),

            "Material Unitario": 0.0,
            "Mano Obra Unitaria": mano_obra,

            "Costo Operativo Unitario": 0.0,

            "Total Unitario": round(mano_obra, 2),

            "Total Proyecto": round(
                longitud * mano_obra,
                2
            ),
        })

    if not filas:
        return df_precios

    return pd.concat(
        [df_precios, pd.DataFrame(filas)],
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
