# -*- coding: utf-8 -*-
"""
materiales_por_punto.py
Cálculo de materiales por punto, respetando cantidad y reemplazo específico de conector en MT.
"""

import pandas as pd

from entradas.excel_legacy import cargar_materiales

from servicios.normalizacion_estructuras import encontrar_col_tension

from core.conectores_mt import reemplazar_solo_yc25a25_mt


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
    ✅ Aplica reemplazo PURO: SOLO YC 25A25 (1/0-1/0) en MT (A/TH/ER/TM),
       y solo si calibre_mt global != 1/0.
    ✅ Encuentra columna por tensión LL numérica.
    ✅ No oculta errores.
    """
    resumen = []
    cache_hojas = {}

    # ✅ Calibre MT global (desde Streamlit/datos_proyecto normalizado)
    calibre_mt_global = (datos_proyecto or {}).get("calibre_mt", "") or ""

    for _, r in tmp_explotado.iterrows():
        punto = str(r.get("Punto", "")).strip()
        codigo = str(r.get("codigodeestructura", "")).strip().upper()
        qty_est = int(r["cantidad"]) if pd.notna(r.get("cantidad")) else 1
        qty_est = max(1, qty_est)

        if not codigo:
            continue

        try:
            # --- Cache de lectura por hoja ---
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
            if "Unidad" not in df.columns:
                df["Unidad"] = ""

            # --- Columna de tensión ---
            col_tension = encontrar_col_tension(df.columns, tension_ll)
            if not col_tension:
                log(
                    f"⚠️ No encontré columna de tensión {tension_ll} en hoja {codigo}. "
                    f"Columnas: {list(df.columns)}"
                )
                continue

            df_work = df.copy()
            df_work[col_tension] = pd.to_numeric(df_work[col_tension], errors="coerce").fillna(0)

            dfp = df_work[df_work[col_tension] > 0][["Materiales", "Unidad", col_tension]].copy()
            if dfp.empty:
                continue

            dfp.rename(columns={col_tension: "Cantidad"}, inplace=True)

            # --- Multiplicar por cantidad en el punto ---
            dfp["Cantidad"] = (
                pd.to_numeric(dfp["Cantidad"], errors="coerce")
                .fillna(0)
                .astype(float)
                * float(qty_est)
            )

            # ✅ Reemplazo PURO (solo YC 25A25 en MT)
            dfp["Materiales"] = reemplazar_solo_yc25a25_mt(
                dfp["Materiales"].astype(str).tolist(),
                codigo,               # estructura
                calibre_mt_global,    # calibre MT global
                tabla_conectores_mt,  # tabla conectores
            )

            dfp["Materiales"] = dfp["Materiales"].astype(str).str.strip()
            dfp["Unidad"] = dfp["Unidad"].astype(str).str.strip()
            dfp["Punto"] = punto

            resumen.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])

        except Exception as e:
            log(f"❌ Error en Punto={punto} Estructura={codigo}: {type(e).__name__}: {e}")

    if not resumen:
        return pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])

    df_out = pd.concat(resumen, ignore_index=True)

    # Agrupar por punto/material (por si hay repetidos)
    df_out = df_out.groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

    return df_out
