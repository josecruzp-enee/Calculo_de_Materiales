# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


# =========================================================
# BIBLIOTECA DE PRECIOS (CONTROL TOTAL)
# =========================================================
PRECIOS_BIBLIOTECA = {

    # =========================
    # PRIMARIO MONOFÁSICO (A-I)
    # =========================
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

    # =========================
    # PRIMARIO BIFÁSICO (A-II)
    # =========================
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

    # =========================
    # PRIMARIO TRIFÁSICO (A-III)
    # =========================
    "A-III-1": 5000,
    "A-III-2": 5200,
    "A-III-3": 5400,
    "A-III-4": 5600,
    "A-III-5": 5800,
    "A-III-6": 6000,

    # =========================
    # NEUTROS (B-I)
    # =========================
    "B-I-1": 800,
    "B-I-2": 900,
    "B-I-3": 1000,
    "B-I-4": 1100,
    "B-I-4D": 1200,
    "B-I-4B": 1100,
    "B-I-4C": 1200,

    # =========================
    # SECUNDARIO (B-II / B-III)
    # =========================
    "B-II-1": 1200,
    "B-II-2": 1300,
    "B-II-3": 1400,
    "B-II-4": 1500,
    "B-II-5": 1600,

    "B-III-1": 1200,
    "B-III-2": 1300,
    "B-III-3": 1400,
    "B-III-4": 1400,
    "B-III-5": 1500,
    "B-III-6": 1600,

    # =========================
    # RETENIDAS
    # =========================
    "R-1": 1500,
    "R-2": 1800,
    "R-3": 2000,
    "R-3V": 1800,
    "R-4": 2200,
    "R-5": 3000,
    "R-5T": 3500,

    # =========================
    # ATERRIZAJE
    # =========================
    "CT-N": 1500,

    # =========================
    # CUCHILLAS / SECCIONAMIENTO
    # =========================
    "CS-1": 2500,
    "CS-2": 3500,
    

    # =========================
    # PROTECCIONES / OTROS
    # =========================
    "CA-32": 2500,

    # =========================
    # LUMINARIAS
    # =========================
    "LL-1-50W": 2800,
    "LL-1-100W": 3200,
    "LL-1-150W": 3500,

    # =========================
    # POSTES
    # =========================
    "PC-30": 9000,
    "PC-40": 15000,
    "PC-45": 17000,

    # =========================
    # TRANSFORMADORES
    # =========================
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
# FUNCIÓN ÚNICA DE PRECIO (🔥 ESTA MANDA TODO)
# =========================================================
def calcular_precio_estructura(
    *,
    estructura: str,
    costo_materiales: float,
    costo_operativo: float,
    porcentaje_utilidad: float,
) -> ResultadoPrecioEstructura:

    estructura_norm = estructura.strip().upper()

    # 🔥 PRIORIDAD: BIBLIOTECA
    if estructura_norm in PRECIOS_BIBLIOTECA:
        precio_unitario = PRECIOS_BIBLIOTECA[estructura_norm]

    else:
        # 🔧 MODELO AUTOMÁTICO (fallback)
        costo_base = costo_materiales + costo_operativo
        precio_unitario = costo_base * (1 + porcentaje_utilidad)

    return ResultadoPrecioEstructura(
        estructura=estructura_norm,
        precio_unitario=round(precio_unitario, 2)
    )


# =========================================================
# FUNCIONES AUXILIARES (SE MANTIENEN)
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
# ORQUESTADOR LOCAL (SI ALGUNA VEZ LO USAS)
# =========================================================
def ejecutar_costos(entrada: EntradaCostos) -> Dict[str, Any]:

    debug: Dict[str, Any] = {}

    try:
        # =====================================================
        # 1. VALIDACIÓN
        # =====================================================
        if not isinstance(entrada.df_materiales, pd.DataFrame):
            raise TypeError("df_materiales inválido")

        if not isinstance(entrada.df_catalogo, pd.DataFrame):
            raise TypeError("df_catalogo inválido")

        # =====================================================
        # 2. CATÁLOGO
        # =====================================================
        df_costos = preparar_catalogo_costos(entrada.df_catalogo)

        if df_costos is None or df_costos.empty:
            raise ValueError("df_costos vacío")

        # =====================================================
        # 3. COSTOS DE MATERIALES
        # =====================================================
        df_materiales_costos = calcular_lista_materiales_con_costos(
            df_materiales=entrada.df_materiales,
            df_catalogo_costos=df_costos
        )

        # =====================================================
        # 4. COSTOS POR ESTRUCTURA
        # =====================================================
        df_costos_estructura = None

        if (
            entrada.df_estructuras is not None and
            entrada.df_materiales_por_estructura is not None
        ):
            df_costos_estructura = calcular_costos_por_estructura(
                df_estructuras=entrada.df_estructuras,
                df_materiales_por_estructura=entrada.df_materiales_por_estructura,
                df_precios_materiales=df_costos
            )

        # =====================================================
        # 5. MANO DE OBRA
        # =====================================================
        df_mano_obra = None

        if df_costos_estructura is not None and entrada.ruta_datos_materiales:
            try:
                df_mano_obra = calcular_mano_obra(
                    df_estructuras=entrada.df_estructuras,
                    archivo_materiales=entrada.ruta_datos_materiales
                )
            except Exception:
                df_mano_obra = None

        # =====================================================
        # 6. PRECIOS POR ESTRUCTURA
        # =====================================================
        df_precios_estructura = None

        if df_costos_estructura is not None:

            material_total = df_costos_estructura["Costo Total"].sum()

            mo_total = (
                df_mano_obra["MO Total"].sum()
                if df_mano_obra is not None else 0.0
            )

            costos_op = calcular_costos_operativos(
                costo_material_total=material_total,
                costo_mano_obra=mo_total
            )

            filas = []

            for _, r in df_costos_estructura.iterrows():

                estructura = str(r["codigodeestructura"]).strip().upper()
                costo_mat_unit = float(r["Costo Unitario"])
                costo_total_estructura = float(r["Costo Total"])
                cantidad = max(1, int(r["Cantidad"]))

                if material_total <= 0:
                    continue

                peso = costo_total_estructura / material_total

                costo_operativo_unit = (
                    costos_op.operativo_total * peso
                ) / cantidad

                res = calcular_precio_estructura(
                    estructura=estructura,
                    costo_materiales=costo_mat_unit,
                    costo_operativo=costo_operativo_unit,
                    porcentaje_utilidad=0.25,
                )

                filas.append({
                    "Estructura": estructura,
                    "Cantidad": cantidad,
                    "Costo Unitario": costo_mat_unit,
                    "Costo Operativo": costo_operativo_unit,
                    "Precio Unitario": res.precio_unitario,
                    "Precio Total": res.precio_unitario * cantidad,
                })

            df_precios_estructura = pd.DataFrame(filas)
            if not df_precios_estructura.empty:
                df_precios_estructura["Subtotal"] = df_precios_estructura["Precio Total"]

            # =====================================================
            # 🔥 CABLE COMPLETO (MT, BT, NEUTRO, PILOTO, RETENIDA)
            # =====================================================
            if entrada.df_cables is not None and not entrada.df_cables.empty:

                filas_cable = []

                for _, r in entrada.df_cables.iterrows():

                    tipo = str(r.get("tipo", "")).strip().upper()

                    try:
                        longitud = float(r.get("longitud", 0))
                    except:
                        continue

                    if tipo in ["MT", "PRIMARIO"]:
                        precio = 120
                        nombre = "LÍNEA PRIMARIA MT"

                    elif tipo in ["BT", "SECUNDARIO"]:
                        precio = 80
                        nombre = "LÍNEA SECUNDARIA BT"

                    elif tipo == "NEUTRO":
                        precio = 60
                        nombre = "CONDUCTOR NEUTRO"

                    elif tipo == "PILOTO":
                        precio = 40
                        nombre = "HILO PILOTO"

                    elif tipo == "RETENIDA":
                        precio = 70
                        nombre = "CABLE DE RETENIDA"

                    else:
                        continue

                    total = longitud * precio

                    filas_cable.append({
                        "Estructura": nombre,
                        "Cantidad": longitud,
                        "Costo Unitario": precio,
                        "Costo Operativo": 0,
                        "Precio Unitario": precio,
                        "Precio Total": total,
                    })

                if filas_cable:
                    df_cable = pd.DataFrame(filas_cable)

                    df_precios_estructura = pd.concat(
                        [df_precios_estructura, df_cable],
                        ignore_index=True
                    )

        # =====================================================
        # 7. MÉTRICAS
        # =====================================================
        total_materiales = float(df_materiales_costos["Costo Total"].sum())

        total_estructura = (
            float(df_costos_estructura["Costo Total"].sum())
            if df_costos_estructura is not None else 0.0
        )

        total_precio = (
            float(df_precios_estructura["Precio Total"].sum())
            if df_precios_estructura is not None else 0.0
        )

        debug["metricas"] = {
            "materiales": total_materiales,
            "estructuras": total_estructura,
            "precio_total": total_precio
        }

        return {
            "ok": True,
            "df_materiales_costos": df_materiales_costos,
            "df_costos_estructura": df_costos_estructura,
            "df_mano_obra": df_mano_obra,
            "df_precios_estructura": df_precios_estructura,
            "debug": debug
        }

    except Exception as e:
        return {
            "ok": False,
            "errores": [str(e)],
            "df_materiales_costos": None,
            "df_costos_estructura": None,
            "df_mano_obra": None,
            "df_precios_estructura": None,
            "debug": {"error": str(e)}
        }
