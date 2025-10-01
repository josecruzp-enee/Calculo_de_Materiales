# -*- coding: utf-8 -*-
"""
principal_materiales.py
Script orquestador para:
1. Leer datos de proyecto y estructuras
2. Procesar materiales con reglas de reemplazo
3. Generar Excel maestro con varias hojas
4. Generar PDFs individuales y un informe completo
"""

import os, sys
import pandas as pd
from collections import Counter

# === Importar módulos propios ===
from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    extraer_estructuras_proyectadas,
    cargar_indice,
    cargar_adicionales,
    cargar_materiales
)
from modulo.conectores_mt import (
    cargar_conectores_mt,
    aplicar_reemplazos_conectores
)
from modulo.pdf_utils import (
    crear_pdf_materiales,
    crear_pdf_estructuras,
    crear_pdf_materiales_por_punto,
    crear_pdf_completo,
)
from modulo.excel_utils import exportar_excel

# =================== RUTAS ===================
BASE_DIR = os.path.dirname(__file__)
archivo_materiales = os.path.join(BASE_DIR, "Estructura_datos.xlsx")
archivo_estructuras = os.path.join(BASE_DIR, "estructuras_lista.xlsx")
ruta_excel = os.path.join(BASE_DIR, "Resumen_Materiales_y_Estructuras.xlsx")
ruta_pdf_base = os.path.join(BASE_DIR, "PDFs")

# =================== LECTURA DE DATOS ===================
# --- Datos del proyecto ---
datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")
codigo_proyecto = datos_proyecto.get("codigo_proyecto", "")
tension = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension")
calibre_primario = datos_proyecto.get("calibre_primario", "1/0 ASCR")

# Normalizar tensión
if tension:
    tension = str(tension).replace(",", ".").replace("kV", "").strip()
if tension not in ["13.8", "34.5"]:
    print(f"⚠️ Error: tensión inválida ({tension})")
    sys.exit()

# --- Estructuras proyectadas ---
df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)
conteo = Counter(estructuras_proyectadas)

# --- Índice y tabla de conectores ---
df_indice = cargar_indice(archivo_materiales)
tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

# =================== PROCESAMIENTO ===================
df_total = pd.DataFrame()

for estructura, cant in conteo.items():
    try:
        df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
        fila_tension = next(
            i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
        )
        df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

        # 🔧 Normalizar cabeceras
        df.columns = df.columns.map(lambda x: str(x).strip())

        if "Materiales" not in df.columns or tension not in df.columns:
            continue

        unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
        df_filtrado = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()

        # ✅ Reemplazo de conectores MT
        df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
            df_filtrado["Materiales"].tolist(),
            calibre_primario,
            tabla_conectores_mt
        )
        
        df_filtrado["Unidad"] = df_filtrado[unidad_col]
        df_filtrado["Cantidad"] = df_filtrado[tension] * cant
        df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
    except Exception as e:
        print(f"⚠️ Error en estructura {estructura}: {e}")

# --- Materiales adicionales ---
df_adicionales = cargar_adicionales(archivo_estructuras)
df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])

# --- Resúmenes ---
df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

resumen_punto=[]
for punto, estructuras in estructuras_por_punto.items():
    print(f"\n➡ Punto {punto}: estructuras detectadas {estructuras}")  # debug
    for est in estructuras:
        try:
            df_temp = cargar_materiales(archivo_materiales, est, header=None)
            fila_tension = next(
                i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
            )
            df = cargar_materiales(archivo_materiales, est, header=fila_tension)

            # 🔧 Normalizar cabeceras
            df.columns = df.columns.map(lambda x: str(x).strip())

            print(f"   ✔ Estructura {est} → {len(df)} filas leídas")  # debug

            unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
            dfp = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()
            dfp["Unidad"] = dfp[unidad_col]
            dfp["Cantidad"] = dfp[tension]
            dfp["Punto"] = punto

            print(f"      ↳ {len(dfp)} materiales válidos")  # debug
            resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
        except Exception as e:
            print(f"   ⚠ Error en estructura {est}: {e}")  # debug

# --- Resumen por punto ---
df_resumen_por_punto = (
    pd.concat(resumen_punto, ignore_index=True)
    .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"]
    .sum()
)

# =================== SALIDA ===================
# --- Excel maestro ---
exportar_excel(df_estructuras_resumen, df_resumen, df_adicionales, df_resumen_por_punto, ruta_excel)

# --- PDFs ---
os.makedirs(ruta_pdf_base, exist_ok=True)
crear_pdf_materiales(df_resumen, os.path.join(ruta_pdf_base, "Resumen_Materiales.pdf"), nombre_proyecto)
crear_pdf_estructuras(df_estructuras_resumen, os.path.join(ruta_pdf_base, "Resumen_Estructuras.pdf"), nombre_proyecto)
crear_pdf_materiales_por_punto(df_resumen_por_punto, os.path.join(ruta_pdf_base, "Materiales_por_Punto.pdf"), nombre_proyecto)
crear_pdf_completo(
    df_resumen,
    df_estructuras_resumen,
    df_resumen_por_punto,
    os.path.join(ruta_pdf_base, "Informe_Completo.pdf"),
    datos_proyecto,
)

print("✅ Proceso finalizado: Excel + PDFs generados")


