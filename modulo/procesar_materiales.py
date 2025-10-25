# -*- coding: utf-8 -*-
import pandas as pd
from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    cargar_indice,
)
from core.conectores_mt import (
    cargar_conectores_mt,
    determinar_calibre_por_estructura,
    aplicar_reemplazos_conectores,
)
from core.materiales_validacion import validar_datos_proyecto
from core.materiales_estructuras import extraer_conteo_estructuras, calcular_materiales_estructura
from core.materiales_puntos import calcular_materiales_por_punto

try:
    import streamlit as st
    log = st.write
except ImportError:
    log = print


def procesar_materiales(
    archivo_estructuras=None,
    archivo_materiales=None,
    estructuras_df=None,
    datos_proyecto=None
):
    """
    Pipeline principal de procesamiento:
    - Carga/usa datos del proyecto y estructuras (archivo o DataFrame)
    - Valida datos del proyecto (tensión, calibre MT)
    - Limpia estructuras y calcula conteos
    - Carga índice y tabla de conectores
    - Calcula materiales por estructura (multiplicando por cantidad)
    - Reemplaza conectores por estructura según calibre detectado
    - Calcula resúmenes globales, por punto
    - Integra materiales adicionales manuales (session_state["materiales_extra"])
    - Genera 5 PDFs y los devuelve en un dict
    """

    # 0) Entradas
    if archivo_estructuras:
        if not datos_proyecto:
            datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar archivo_estructuras o estructuras_df")

    # 1) Validar datos del proyecto
    tension, calibre_mt = validar_datos_proyecto(datos_proyecto)
    log(f"Tensión: {tension} Calibre MT: {calibre_mt}")

    log("⚙️ DEBUG VALIDAR DATOS PROYECTO")
    log(f"➡️ tension = {tension}")
    log(f"➡️ calibre_mt = {calibre_mt}")
    log(f"➡️ datos_proyecto = {datos_proyecto}")

    # 2) Limpieza y conteo de estructuras
    log("🔍 Limpieza inicial de estructuras...")
    filas_antes = len(df_estructuras)
    df_estructuras = df_estructuras.dropna(how="all")
    if "codigodeestructura" in df_estructuras.columns:
        df_estructuras = df_estructuras[df_estructuras["codigodeestructura"].notna()]
    filas_despues = len(df_estructuras)
    log(f"🧹 Filas eliminadas: {filas_antes - filas_despues}")

    # Uniformidad en nombre "Punto"
    if "Punto" not in df_estructuras.columns and "punto" in df_estructuras.columns:
        df_estructuras.rename(columns={"punto": "Punto"}, inplace=True)

    # Unicidad por Punto + Estructura
    df_estructuras_unicas = df_estructuras.drop_duplicates(subset=["Punto", "codigodeestructura"])

    # Conteo preliminar + estructuras por punto
    conteo, estructuras_por_punto = extraer_conteo_estructuras(df_estructuras_unicas)
    for p in estructuras_por_punto:
        estructuras_por_punto[p] = list(dict.fromkeys(estructuras_por_punto[p]))
    log(f"Conteo estructuras inicial: {conteo}")
    log(f"Estructuras por punto: {estructuras_por_punto}")

    # Recalcular conteo global corregido (por seguridad)
    conteo_global_df = (
        df_estructuras_unicas.groupby("codigodeestructura")
        .size()
        .reset_index(name="Cantidad")
    )
    conteo = dict(zip(conteo_global_df["codigodeestructura"], conteo_global_df["Cantidad"]))
    log("✅ Conteo global corregido considerando todos los puntos:")
    for e, c in conteo.items():
        log(f"   {e}: {c} unidades totales")

    # 3) Cargar índice
    df_indice = cargar_indice(archivo_materiales)
    log("Columnas originales índice: " + str(df_indice.columns.tolist()))
    df_indice.columns = df_indice.columns.str.strip().str.lower()
    if "código de estructura" in df_indice.columns:
        df_indice.rename(columns={"código de estructura": "codigodeestructura"}, inplace=True)
    if "descripcion" in df_indice.columns:
        df_indice.rename(columns={"descripcion": "Descripcion"}, inplace=True)
    log("Columnas normalizadas índice: " + str(df_indice.columns.tolist()))
    log("Primeras filas índice:\n" + str(df_indice.head(10)))

    # 4) Cargar conectores
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    log("🧩 DEBUG ANTES DE CALCULAR MATERIALES:")
    log(f"🧱 Total estructuras detectadas: {len(conteo)}")
    for e, c in conteo.items():
        log(f"{e}: {c} unidades")

    if archivo_materiales:
        excel_temp = pd.ExcelFile(archivo_materiales)
        log(f"📄 Hojas disponibles en Estructura_datos.xlsx: {excel_temp.sheet_names}")

    # 5) Calcular materiales por estructura + Reemplazo de conectores por estructura
    df_lista = []
    for e, c in conteo.items():
        # Calibre adecuado para esa estructura (MT/BT/Neutro)
        calibre_actual = determinar_calibre_por_estructura(e, datos_proyecto)

        df_mat = calcular_materiales_estructura(
            archivo_materiales=archivo_materiales,
            codigo_estructura=e,
            cantidad=c,                    # multiplicación por cantidad detectada
            tension=tension,
            calibre=calibre_actual,        # calibre específico de ESA estructura
            tabla_conectores=tabla_conectores_mt
        )

        # --- Reemplazo de conectores POR ESTRUCTURA con diagnóstico ---
        if not df_mat.empty and "Materiales" in df_mat.columns:
            orig = df_mat["Materiales"].astype(str).tolist()
            repl = aplicar_reemplazos_conectores(
                orig,
                calibre_estructura=calibre_actual,
                tabla_conectores=tabla_conectores_mt,
                codigo_estructura=e,        # filtra por familia (A/TM/TH/ER/B/R/etc.) si aplica
            )
            if orig != repl:
                log(f"🔁 Reemplazos realizados en {e} (calibre {calibre_actual}):")
                for a, b in zip(orig, repl):
                    if a != b and "CONECTOR" in a.upper():
                        log(f"    '{a}'  →  '{b}'")
            else:
                log(f"⚠️ Sin reemplazos efectivos en {e} (calibre {calibre_actual}).")
            df_mat["Materiales"] = repl

        df_lista.append(df_mat)

    df_total = pd.concat(df_lista, ignore_index=True) if df_lista else pd.DataFrame()

    # 6) Resumen global de materiales
    df_resumen = (
        df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        if not df_total.empty
        else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    )
    log("df_resumen (materiales):\n" + str(df_resumen.head(10)))

    # 7) Resumen de estructuras globales
    if "codigodeestructura" not in df_indice.columns:
        df_indice["codigodeestructura"] = None
    df_indice["codigodeestructura"] = df_indice["codigodeestructura"].astype(str).str.strip().str.upper()
    conteo = {str(k).strip().upper(): v for k, v in conteo.items()}
    df_indice["Cantidad"] = df_indice["codigodeestructura"].map(conteo).fillna(0).astype(int)
    df_estructuras_resumen = df_indice[df_indice["Cantidad"] > 0]
    log("df_estructuras_resumen:\n" + str(df_estructuras_resumen.head(10)))

    # 8) Estructuras por punto (Cantidad = 1 por estructura listada en el punto)
    lista_por_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            est_norm = str(est).strip().upper()
            lista_por_punto.append({
                "Punto": punto,
                "codigodeestructura": est_norm,
                "Descripcion": df_indice.loc[
                    df_indice["codigodeestructura"] == est_norm, "Descripcion"
                ].values[0] if est_norm in df_indice["codigodeestructura"].values else "NO ENCONTRADA",
                "Cantidad": 1
            })
    df_estructuras_por_punto = pd.DataFrame(lista_por_punto)
    log("df_estructuras_por_punto:\n" + str(df_estructuras_por_punto.head(10)))

    # 9) Materiales por punto
    df_resumen_por_punto = calcular_materiales_por_punto(
        archivo_materiales, estructuras_por_punto, tension
    )
    log("df_resumen_por_punto:\n" + str(df_resumen_por_punto.head(10)))

    # 🔟 Materiales adicionales (session_state)
    try:
        materiales_extra = st.session_state.get("materiales_extra", [])
        if materiales_extra:
            df_extra = pd.DataFrame(materiales_extra)
            df_resumen = pd.concat([df_resumen, df_extra], ignore_index=True)
            df_resumen = df_resumen.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
            datos_proyecto["materiales_extra"] = df_extra
            log(f"✅ Se integraron {len(df_extra)} materiales adicionales manuales")
        else:
            datos_proyecto["materiales_extra"] = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    except Exception as e:
        log(f"⚠️ No se pudo integrar materiales adicionales: {e}")

    # 11) Generar PDFs
    from modulo.pdf_utils import (
        generar_pdf_materiales,
        generar_pdf_estructuras_global,
        generar_pdf_estructuras_por_punto,
        generar_pdf_materiales_por_punto,
        generar_pdf_completo
    )

    nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto")

    pdf_materiales = generar_pdf_materiales(df_resumen, nombre_proyecto, datos_proyecto)
    pdf_estructuras_global = generar_pdf_estructuras_global(df_estructuras_resumen, nombre_proyecto)
    pdf_estructuras_por_punto = generar_pdf_estructuras_por_punto(df_estructuras_por_punto, nombre_proyecto)
    pdf_materiales_por_punto = generar_pdf_materiales_por_punto(df_resumen_por_punto, nombre_proyecto)
    pdf_informe_completo = generar_pdf_completo(
        df_resumen,
        df_estructuras_resumen,
        df_estructuras_por_punto,
        df_resumen_por_punto,
        datos_proyecto
    )

    # 12) Salida
    return {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_informe_completo,
    }
