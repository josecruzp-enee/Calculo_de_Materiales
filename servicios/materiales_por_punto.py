# -*- coding: utf-8 -*-
"""
materiales_por_punto.py
Cálculo de materiales por punto, respetando cantidad y reemplazos de conectores.
"""

import pandas as pd

from modulo.entradas import cargar_materiales
from servicios.normalizacion_estructuras import encontrar_col_tension

from core.conectores_mt import (
    determinar_calibre_por_estructura,
    aplicar_reemplazos_conectores,
)


def calcular_materiales_por_punto_con_cantidad(
    archivo_materiales,
    tmp_explotado: pd.DataFrame,
    tension_ll: float,
    tabla_conectores_mt: pd.DataFrame,
    datos_proyecto: dict,
    log=print,
):
    """
    Calcula materiales por punto usando tmp_explotado que YA trae:
      Punto | codigodeestructura | cantidad

    ✅ Multiplica por la cantidad real en el punto.
    ✅ Aplica reemplazo de conectores según calibre de la estructura.
    ✅ Encuentra columna por tensión LL numérica.
    ✅ No oculta errores.
    """
    resumen = []
    cache_hojas = {}

    for _, r in tmp_explotado.iterrows():
        punto = str(r["Punto"]).strip()
        codigo = str(r["codigodeestructura"]).strip().upper()
        qty_est = int(r["cantidad"]) if pd.notna(r["cantidad"]) else 1
        qty_est = max(1, qty_est)
        if not codigo:
            continue

        try:
            if codigo not in cache_hojas:
                df_temp = cargar_materiales(archivo_materiales, codigo, header=None)

                fila_encabezado = None
                for i, row in df_temp.iterrows():
                    if row.astype(str).str.contains("Material", case=False, na=False).any():
                        fila_encabezado = i
                        break

                if fila_encabezado is None:
                    cache_hojas[codigo] = None
                else:
                    df = cargar_materiales(archivo_materiales, codigo, header=fila_encabezado)
                    df.columns = df.columns.map(str).str.strip()
                    cache_hojas[codigo] = df

            df = cache_hojas.get(codigo)
            if df is None or df.empty:
                continue
            if "Materiales" not in df.columns:
                continue

            col_tension = encontrar_col_tension(df.columns, tension_ll)
            if not col_tension:
                log(f"⚠️ No encontré columna de tensión {tension_ll} en hoja {codigo}. Columnas: {list(df.columns)}")
                continue

            df_work = df.copy()
            df_work[col_tension] = pd.to_numeric(df_work[col_tension], errors="coerce").fillna(0)

            dfp = df_work[df_work[col_tension] > 0][["Materiales", "Unidad", col_tension]].copy()
            if dfp.empty:
                continue

            dfp.rename(columns={col_tension: "Cantidad"}, inplace=True)

            # Multiplicar por cantidad en el punto
            dfp["Cantidad"] = pd.to_numeric(dfp["Cantidad"], errors="coerce").fillna(0).astype(float) * float(qty_est)

            # Reemplazo conectores según calibre real de la estructura (igual que global)
            calibre_actual = determinar_calibre_por_estructura(codigo, datos_proyecto)
            dfp["Materiales"] = aplicar_reemplazos_conectores(
                dfp["Materiales"].astype(str).tolist(),
                calibre_estructura=calibre_actual,
                tabla_conectores=tabla_conectores_mt,
            )

            dfp["Unidad"] = dfp["Unidad"].astype(str).str.strip()
            dfp["Punto"] = punto

            resumen.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])

        except Exception as e:
            log(f"❌ Error en Punto={punto} Estructura={codigo}: {type(e).__name__}: {e}")

    if not resumen:
        return pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    df_out = pd.concat(resumen, ignore_index=True)
    df_out = df_out.groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    return df_out
