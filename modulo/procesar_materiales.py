# -*- coding: utf-8 -*-
"""
procesar_materiales.py
Módulo para:
1. Leer datos de proyecto y estructuras
2. Procesar materiales con reglas de reemplazo
3. Generar resúmenes (materiales, estructuras, por punto)
4. Exportar Excel y PDF
Funciona desde app.py o en modo consola.
"""

import os
import sys
import pandas as pd
from collections import Counter

# === Módulos propios ===
from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    extraer_estructuras_proyectadas,
    cargar_indice,
    cargar_adicionales,
    cargar_materiales,
)
from modulo.conectores_mt import (
    cargar_conectores_mt,
    aplicar_reemplazos_conectores,
)
from modulo.pdf_utils import (
    generar_pdf_materiales,
    generar_pdf_estructuras,
    generar_pdf_materiales_por_punto,
    generar_pdf_completo,
)
from modulo.excel_utils import exportar_excel


# =====================================================
# Funciones auxiliares
# =====================================================

def limpiar_codigo(codigo):
    """
    Devuelve solo el código base y el tipo de estructura.
    - Si el string trae 'CODIGO – Descripción', devuelve solo CODIGO.
    - Si termina en (X), X es el tipo (ej: (P), (E), (R)).
    - Si no tiene sufijo, se asume tipo = P (proyectada).
    """
    if pd.isna(codigo) or str(codigo).strip() == "":
        return None, None

    codigo = str(codigo).strip()

    # cortar si viene con "–" (guion largo) o "-" con descripción
    if "–" in codigo:
        codigo = codigo.split("–")[0].strip()
    elif " - " in codigo:
        codigo = codigo.split(" - ")[0].strip()

    # manejar sufijos tipo (P), (E), etc.
    if codigo.endswith(")") and "(" in codigo:
        base = codigo[:codigo.rfind("(")].strip()
        tipo = codigo[codigo.rfind("(") + 1 : codigo.rfind(")")].strip().upper()
        return base, tipo

    return codigo, "P"



def expandir_lista_codigos(cadena):
    """
    Maneja entradas con varias estructuras separadas por coma.
    Ej: "A-I-1, A-I-2" → ["A-I-1", "A-I-2"]
    """
    if not cadena:
        return []
    return [parte.strip() for parte in str(cadena).split(",") if parte.strip()]


# =====================================================
# Procesamiento principal
# =====================================================

def procesar_materiales(archivo_estructuras=None, archivo_materiales=None, estructuras_df=None):
    """
    Procesa estructuras y materiales y devuelve resúmenes.
    Retorna:
    - df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto
    """

    # === 1. Datos del proyecto ===
    if archivo_estructuras is not None:
        datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")
    tension = datos_proyecto.get("nivel_de_tension") or datos_proyecto.get("tension")
    calibre_primario = datos_proyecto.get("calibre_primario", "1/0 ASCR")

    if tension:
        tension = str(tension).replace(",", ".").replace("kV", "").strip()

    # === 2. Extraer estructuras proyectadas ===
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)

    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, tipo = limpiar_codigo(parte)
            if codigo and (tipo == "P" or not tipo):
                estructuras_limpias.append(codigo)

    conteo = Counter(estructuras_limpias)

    # === 3. Índice y conectores ===
    df_indice = cargar_indice(archivo_materiales)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    # === 4. Procesar materiales ===
    df_total = pd.DataFrame()
    for estructura, cant in conteo.items():
        try:
            df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
            fila_tension = next(
                i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
            )
            df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)

            df.columns = df.columns.map(lambda x: str(x).strip())
            if "Materiales" not in df.columns or tension not in df.columns:
                continue

            unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
            df_filtrado = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()

            df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
                df_filtrado["Materiales"].tolist(), calibre_primario, tabla_conectores_mt
            )
            df_filtrado["Unidad"] = df_filtrado[unidad_col]
            df_filtrado["Cantidad"] = df_filtrado[tension] * cant
            df_total = pd.concat([df_total, df_filtrado[["Materiales", "Unidad", "Cantidad"]]])
        except Exception as e:
            print(f"⚠️ Error en estructura {estructura}: {e}")

    # === 5. Materiales adicionales ===
    if archivo_estructuras is not None:
        df_adicionales = cargar_adicionales(archivo_estructuras)
        df_total = pd.concat([df_total, df_adicionales[["Materiales", "Unidad", "Cantidad"]]])

    # === 6. Resúmenes ===
    df_resumen = (
        df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_total.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )
    df_indice["Cantidad"] = df_indice["NombreEstructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]

    # === 7. Resumen por punto ===
    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            for parte in expandir_lista_codigos(est):
                codigo, tipo = limpiar_codigo(parte)
                if codigo and (tipo == "P" or not tipo):
                    try:
                        df_temp = cargar_materiales(archivo_materiales, codigo, header=None)
                        fila_tension = next(
                            i for i, row in df_temp.iterrows() if any(str(tension) in str(cell) for cell in row)
                        )
                        df = cargar_materiales(archivo_materiales, codigo, header=fila_tension)

                        df.columns = df.columns.map(lambda x: str(x).strip())
                        unidad_col = df.columns[df.columns.get_loc("Materiales") + 1]
                        dfp = df[df[tension] > 0][["Materiales", unidad_col, tension]].copy()
                        dfp["Unidad"] = dfp[unidad_col]
                        dfp["Cantidad"] = dfp[tension]
                        dfp["Punto"] = punto
                        resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
                    except Exception as e:
                        print(f"⚠️ Error en estructura {codigo}: {e}")

    df_resumen_por_punto = (
        pd.concat(resumen_punto, ignore_index=True)
        .groupby(["Punto", "Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if resumen_punto else pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"])
    )

    return df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto


# =====================================================
# Ejecución directa en consola
# =====================================================

def main():
    BASE_DIR = os.path.dirname(__file__)
    archivo_estructuras = os.path.join(BASE_DIR, "estructura_lista.xlsx")
    archivo_materiales = os.path.join(BASE_DIR, "Estructura_datos.xlsx")

    if not os.path.exists(archivo_estructuras):
        print("❌ No se encontró estructura_lista.xlsx")
        sys.exit()

    df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto = procesar_materiales(
        archivo_estructuras=archivo_estructuras,
        archivo_materiales=archivo_materiales
    )

    # Exportar Excel
    ruta_excel = os.path.join(BASE_DIR, "Resumen_Materiales_y_Estructuras.xlsx")
    exportar_excel(df_estructuras_resumen, df_resumen, None, df_resumen_por_punto, ruta_excel)

    # Exportar PDFs
    ruta_pdf_base = os.path.join(BASE_DIR, "PDFs")
    os.makedirs(ruta_pdf_base, exist_ok=True)

    generar_pdf_materiales(df_resumen, datos_proyecto.get("nombre_proyecto", "Proyecto"), datos_proyecto)
    generar_pdf_estructuras(df_estructuras_resumen, datos_proyecto.get("nombre_proyecto", "Proyecto"))
    generar_pdf_materiales_por_punto(df_resumen_por_punto, datos_proyecto.get("nombre_proyecto", "Proyecto"))
    generar_pdf_completo(df_resumen, df_estructuras_resumen, df_resumen_por_punto, datos_proyecto)

    print("✅ Proceso finalizado: Excel + PDFs generados")


if __name__ == "__main__":
    main()

