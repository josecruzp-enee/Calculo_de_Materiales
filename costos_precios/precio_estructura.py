# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


# =========================================================
# BIBLIOTECA DE PRECIOS
# =========================================================
PRECIOS_BIBLIOTECA = {

    # =====================================================
    # 🔵 PRIMARIO MONOFÁSICO (A-I)
    # =====================================================
    "A-I-1": 1500,
    "A-I-1V": 1700,
    "A-I-2": 1600,
    "A-I-2V": 1800,
    "A-I-3": 1700,
    "A-I-4": 1800,
    "A-I-4A": 1600,
    "A-I-4B": 1700,
    "A-I-4C": 1800,
    "A-I-4V": 1800,
    "A-I-5": 1800,
    "A-I-5V": 1900,
    "A-I-6": 2000,
    "A-I-7": 1900,
    "A-I-7V": 2000,
    "A-I-8": 1900,
    "A-I-8V": 2000,

    # =====================================================
    # 🔵 PRIMARIO BIFÁSICO (A-II)
    # =====================================================
    "A-II-1": 3000,
    "A-II-1V": 3200,
    "A-II-2": 3200,
    "A-II-2V": 3400,
    "A-II-3": 3500,
    "A-II-4": 3600,
    "A-II-4V": 3800,
    "A-II-5": 3800,
    "A-II-5V": 4000,
    "A-II-6": 4000,

    # =====================================================
    # 🔵 PRIMARIO TRIFÁSICO (A-III)
    # =====================================================
    "A-III-1": 5000,
    "A-III-2": 5200,
    "A-III-3": 5400,
    "A-III-4": 5600,
    "A-III-5": 5800,
    "A-III-6": 6000,

    # =====================================================
    # 🟢 NEUTRO (B-I)
    # =====================================================
    "B-I-1": 800,
    "B-I-2": 900,
    "B-I-3": 1000,
    "B-I-4": 1100,
    "B-I-4B": 1100,
    "B-I-4C": 1200,
    "B-I-4D": 1200,

    # =====================================================
    # 🟢 SECUNDARIO (B-II)
    # =====================================================
    "B-II-1": 1200,
    "B-II-2": 1300,
    "B-II-3": 1400,
    "B-II-4": 1500,
    "B-II-5": 1600,

    # =====================================================
    # 🟢 SECUNDARIO (B-III)
    # =====================================================
    "B-III-1": 1200,
    "B-III-2": 1300,
    "B-III-3": 1400,
    "B-III-4": 1400,
    "B-III-5": 1500,
    "B-III-6": 1600,

    # =====================================================
    # 🟠 RETENIDAS
    # =====================================================
    "R-1": 1500,
    "R-2": 1800,
    "R-3": 2000,
    "R-3V": 1800,
    "R-4": 2200,
    "R-5": 3000,
    "R-5T": 3500,

    # =====================================================
    # 🟠 ATERRIZAJE
    # =====================================================
    "CT-N": 1500,

    # =====================================================
    # 🟣 SECCIONAMIENTO / PROTECCIÓN
    # =====================================================
    "CS-1": 2500,
    "CS-2": 3500,
    "CA-32": 2500,

    # =====================================================
    # 🟡 LUMINARIAS
    # =====================================================
    "LL-1-50W": 2800,
    "LL-1-100W": 3200,
    "LL-1-150W": 3500,

    # =====================================================
    # 🟤 POSTES
    # =====================================================
    "PC-30": 9000,
    "PC-40": 15000,
    "PC-45": 17000,

    # =====================================================
    # 🔴 TRANSFORMADORES
    # =====================================================
    "TS-25KVA": 70000,
    "TS-37.5KVA": 85000,
    "TS-50KVA": 98000,
}

# =========================================================
# CONTRATO
# =========================================================
@dataclass(slots=True)
class ResultadoPrecioEstructura:
    estructura: str
    precio_unitario: float


# =========================================================
# PRECIO DE ESTRUCTURA
# =========================================================
def calcular_precio_estructura(
    *,
    estructura: str,
    costo_materiales: float,
    costo_operativo: float,
    porcentaje_utilidad: float,
) -> ResultadoPrecioEstructura:

    estructura = str(estructura).strip().upper()

    if estructura in PRECIOS_BIBLIOTECA:
        precio = PRECIOS_BIBLIOTECA[estructura]
    else:
        base = costo_materiales + costo_operativo
        precio = base * (1 + porcentaje_utilidad)

    return ResultadoPrecioEstructura(
        estructura=estructura,
        precio_unitario=round(precio, 2)
    )


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
        "operativo_total": round(equipos + logistica, 2)
    }


# =========================================================
# 🔥 INTERNO: AGREGAR CABLE (AQUÍ VIVE TODO)
# =========================================================
def _agregar_cable_a_precios(df_precios, datos_proyecto):

    if df_precios is None or df_precios.empty:
        return df_precios

    if not datos_proyecto:
        return df_precios

    cables = datos_proyecto.get("cables_proyecto", [])

    if not cables:
        return df_precios

    filas = []

    for c in cables:

        tipo = str(c.get("Tipo", "")).strip().upper()
        calibre = str(c.get("Calibre", "")).strip()

        try:
            longitud = float(c.get("Longitud", 0))
        except:
            continue

        if longitud <= 0:
            continue

        # 🔧 REGLAS
        if tipo in ["MT", "PRIMARIO"]:
            precio = 120
            nombre = "línea primaria"

        elif tipo in ["BT", "SECUNDARIO"]:
            precio = 80
            nombre = "línea secundaria"

        elif tipo == "NEUTRO":
            precio = 60
            nombre = "conductor neutro"

        elif tipo == "PILOTO":
            precio = 40
            nombre = "hilo piloto"

        elif tipo == "RETENIDA":
            precio = 70
            nombre = "cable de retenida"

        else:
            continue

        descripcion = f"Suministro e instalación de {round(longitud,2)} m de {nombre}"
        if calibre:
            descripcion += f" ({calibre})"

        filas.append({
            "Estructura": descripcion,
            "Cantidad": longitud,
            "Costo Unitario": precio,
            "Costo Operativo": 0,
            "Precio Unitario": precio,
            "Precio Total": round(longitud * precio, 2),
        })

    if not filas:
        return df_precios

    df_cable = pd.DataFrame(filas)

    return pd.concat([df_precios, df_cable], ignore_index=True)
# =========================================================
# ORQUESTADOR LOCAL (SE QUEDA AQUÍ TODO)
# =========================================================
def ejecutar_costos(entrada) -> Dict[str, Any]:

    try:

        df_costos_estructura = entrada.df_costos_estructura

        if df_costos_estructura is None or df_costos_estructura.empty:
            return {
                "ok": False,
                "errores": ["Sin costos de estructura"],
                "df_precios_estructura": None
            }

        material_total = df_costos_estructura["Costo Total"].sum()

        costos_op = calcular_costos_operativos(
            costo_material_total=material_total
        )

        filas = []

        for _, r in df_costos_estructura.iterrows():

            estructura = str(r["codigodeestructura"]).strip().upper()
            costo_unit = float(r["Costo Unitario"])
            costo_total = float(r["Costo Total"])
            cantidad = max(1, int(r["Cantidad"]))

            if material_total <= 0:
                continue

            peso = costo_total / material_total

            costo_operativo_unit = (
                costos_op["operativo_total"] * peso
            ) / cantidad

            res = calcular_precio_estructura(
                estructura=estructura,
                costo_materiales=costo_unit,
                costo_operativo=costo_operativo_unit,
                porcentaje_utilidad=0.25,
            )

            filas.append({
                "Estructura": estructura,
                "Cantidad": cantidad,
                "Costo Unitario": costo_unit,
                "Costo Operativo": costo_operativo_unit,
                "Precio Unitario": res.precio_unitario,
                "Precio Total": res.precio_unitario * cantidad,
            })

        df_precios = pd.DataFrame(filas)

        if not df_precios.empty:
            df_precios["Subtotal"] = df_precios["Precio Total"]

        # 🔥 AQUÍ SE AGREGA CABLE (CONTROLADO)
        df_precios = _agregar_cable_a_precios(
            df_precios,
            entrada.datos_proyecto
        )

        return {
            "ok": True,
            "df_precios_estructura": df_precios
        }

    except Exception as e:
        return {
            "ok": False,
            "errores": [str(e)],
            "df_precios_estructura": None
        }
