# -*- coding: utf-8 -*-
import re
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
from core.materiales_estructuras import calcular_materiales_estructura
from core.materiales_puntos import calcular_materiales_por_punto


# ==========================================================
# Helpers
# ==========================================================
def get_logger():
    """Devuelve st.write si existe; si no, print."""
    try:
        import streamlit as st  # noqa
        return st.write
    except Exception:
        return print


def normalizar_datos_proyecto(datos_proyecto: dict) -> dict:
    """Asegura estructuras mínimas y tipos esperados."""
    datos_proyecto = datos_proyecto or {}

    # ⚠️ En tu debug venía cables_proyecto = {}
    # En pdf_utils y en tu app suele esperarse lista de dicts
    cables = datos_proyecto.get("cables_proyecto", [])
    if isinstance(cables, dict):
        cables = []  # si venía mal, lo llevamos a lista vacía
    if cables is None:
        cables = []
    datos_proyecto["cables_proyecto"] = cables

    return datos_proyecto


def limpiar_df_estructuras(df_estructuras: pd.DataFrame, log) -> pd.DataFrame:
    """Limpieza básica y homologación de columnas."""
    filas_antes = len(df_estructuras)
    df = df_estructuras.dropna(how="all").copy()

    # Homologar nombre "Punto"
    if "Punto" not in df.columns and "punto" in df.columns:
        df.rename(columns={"punto": "Punto"}, inplace=True)

    # Filtrar filas sin código
    if "codigodeestructura" in df.columns:
        df = df[df["codigodeestructura"].notna()]

    filas_despues = len(df)
    log(f"🧹 Filas eliminadas: {filas_antes - filas_despues}")

    # Validar columnas mínimas
    for col in ("Punto", "codigodeestructura"):
        if col not in df.columns:
            raise ValueError(f"Falta columna requerida: '{col}'. Columnas: {df.columns.tolist()}")

    # Evitar duplicados exactos por (Punto, codigodeestructura) antes de explotar comas
    df = df.drop_duplicates(subset=["Punto", "codigodeestructura"])

    return df


def explotar_codigos_por_coma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte celdas tipo:
    "B-III-6, B-I-4B" -> 2 filas.
    También limpia TS-50 KVA -> TS-50.
    """
    tmp = df[["Punto", "codigodeestructura"]].copy()
    tmp["Punto"] = tmp["Punto"].astype(str).str.strip()
    tmp["codigodeestructura"] = tmp["codigodeestructura"].astype(str).str.strip()

    # Separar SOLO por coma/;
    tmp["codigodeestructura"] = tmp["codigodeestructura"].str.replace(";", ",", regex=False)
    tmp["codigodeestructura"] = tmp["codigodeestructura"].str.split(",")
    tmp = tmp.explode("codigodeestructura")

    tmp["codigodeestructura"] = tmp["codigodeestructura"].astype(str).str.strip().str.upper()
    tmp = tmp[tmp["codigodeestructura"] != ""]

    # TS-50 KVA -> TS-50 (porque tu Excel tiene TS-50 como hoja/código)
    tmp["codigodeestructura"] = tmp["codigodeestructura"].str.replace(r"\s+KVA\b", "", regex=True).str.strip()
    tmp = tmp[tmp["codigodeestructura"] != "KVA"]

    # Quitar duplicados por (Punto, código) después de explotar
    tmp = tmp.drop_duplicates(subset=["Punto", "codigodeestructura"])

    return tmp


def construir_estructuras_por_punto_y_conteo(df_unicas: pd.DataFrame, log):
    """
    Construye:
    - estructuras_por_punto: dict {Punto: [codigos...]}
    - conteo: dict {codigo: cantidad_total_en_proyecto}
    Desde el DF real (robusto).
    """
    tmp = explotar_codigos_por_coma(df_unicas)

    estructuras_por_punto = (
        tmp.groupby("Punto")["codigodeestructura"]
           .apply(lambda s: list(dict.fromkeys(s.tolist())))
           .to_dict()
    )

    conteo = tmp["codigodeestructura"].value_counts().to_dict()

    log("✅ estructuras_por_punto (desde DF):")
    log(estructuras_por_punto)
    log("✅ conteo global (desde DF):")
    log(conteo)

    return estructuras_por_punto, conteo, tmp


def cargar_indice_normalizado(archivo_materiales, log) -> pd.DataFrame:
    df_indice = cargar_indice(archivo_materiales)

    log("Columnas originales índice: " + str(df_indice.columns.tolist()))
    df_indice = df_indice.copy()
    df_indice.columns = df_indice.columns.str.strip().str.lower()

    if "código de estructura" in df_indice.columns:
        df_indice.rename(columns={"código de estructura": "codigodeestructura"}, inplace=True)
    if "descripcion" in df_indice.columns:
        df_indice.rename(columns={"descripcion": "Descripcion"}, inplace=True)

    # Normalización de código
    if "codigodeestructura" not in df_indice.columns:
        df_indice["codigodeestructura"] = ""
    df_indice["codigodeestructura"] = df_indice["codigodeestructura"].astype(str).str.strip().str.upper()

    if "Descripcion" not in df_indice.columns:
        df_indice["Descripcion"] = ""

    log("Columnas normalizadas índice: " + str(df_indice.columns.tolist()))
    log("Primeras filas índice:\n" + str(df_indice.head(10)))

    return df_indice


def construir_df_estructuras_resumen(df_indice: pd.DataFrame, conteo: dict, log) -> pd.DataFrame:
    conteo_norm = {str(k).strip().upper(): v for k, v in conteo.items()}
    df = df_indice.copy()
    df["Cantidad"] = df["codigodeestructura"].map(conteo_norm).fillna(0).astype(int)
    df_res = df[df["Cantidad"] > 0].copy()
    log("df_estructuras_resumen:\n" + str(df_res.head(20)))
    return df_res


def construir_df_estructuras_por_punto(tmp_explotado: pd.DataFrame, df_indice: pd.DataFrame, log) -> pd.DataFrame:
    """
    Crea DF por punto usando merge con índice (más robusto que loc en bucle).
    """
    df_pp = tmp_explotado.merge(
        df_indice[["codigodeestructura", "Descripcion"]],
        on="codigodeestructura",
        how="left"
    )
    df_pp["Descripcion"] = df_pp["Descripcion"].fillna("NO ENCONTRADA")

    # En caso futuro: si el mismo código puede repetirse en un punto, aquí se contaría
    df_pp["Cantidad"] = 1

    df_pp = df_pp[["Punto", "codigodeestructura", "Descripcion", "Cantidad"]].copy()

    log("df_estructuras_por_punto:\n" + str(df_pp.head(30)))
    return df_pp


def integrar_materiales_extra(df_resumen: pd.DataFrame, datos_proyecto: dict, log):
    """Integra materiales adicionales desde session_state si existe."""
    try:
        import streamlit as st  # noqa
        materiales_extra = st.session_state.get("materiales_extra", [])
    except Exception:
        materiales_extra = []

    if materiales_extra:
        df_extra = pd.DataFrame(materiales_extra)
        df_out = pd.concat([df_resumen, df_extra], ignore_index=True)
        df_out = df_out.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
        datos_proyecto["materiales_extra"] = df_extra
        log(f"✅ Se integraron {len(df_extra)} materiales adicionales manuales")
        return df_out, datos_proyecto

    datos_proyecto["materiales_extra"] = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])
    return df_resumen, datos_proyecto


# ==========================================================
# Función principal
# ==========================================================
def procesar_materiales(
    archivo_estructuras=None,
    archivo_materiales=None,
    estructuras_df=None,
    datos_proyecto=None
):
    """
    Procesa estructuras y materiales, reemplazando conectores por calibre real por ESTRUCTURA,
    y genera los 5 PDFs de salida.
    """
    log = get_logger()

    # === 0) Entrada: archivo vs DataFrame ===
    if archivo_estructuras:
        if not datos_proyecto:
            datos_proyecto = cargar_datos_proyecto(archivo_estructuras)
        df_estructuras = cargar_estructuras_proyectadas(archivo_estructuras)
    elif estructuras_df is not None:
        datos_proyecto = datos_proyecto or {}
        df_estructuras = estructuras_df.copy()
    else:
        raise ValueError("Debe proporcionar 'archivo_estructuras' o 'estructuras_df'.")

    datos_proyecto = normalizar_datos_proyecto(datos_proyecto)

    # === 1) Validación de datos del proyecto (tensión, calibre MT base) ===
    tension, calibre_mt = validar_datos_proyecto(datos_proyecto)
    log(f"Tensión: {tension}   Calibre MT: {calibre_mt}")
    log("⚙️ DEBUG VALIDAR DATOS PROYECTO")
    log(f"➡️ tension = {tension}")
    log(f"➡️ calibre_mt = {calibre_mt}")
    log(f"➡️ datos_proyecto = {datos_proyecto}")

    # === 2) Limpieza robusta de estructuras ===
    log("🔍 Limpieza inicial de estructuras...")
    df_estructuras_unicas = limpiar_df_estructuras(df_estructuras, log)

    # ✅ Construcción robusta: estructuras_por_punto + conteo global desde DF real
    estructuras_por_punto, conteo, tmp_explotado = construir_estructuras_por_punto_y_conteo(df_estructuras_unicas, log)

    # === 3) Índice de estructuras (descripcion + código) ===
    df_indice = cargar_indice_normalizado(archivo_materiales, log)

    # === 4) Conectores (tabla 'conectores') ===
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    log("🧩 DEBUG ANTES DE CALCULAR MATERIALES:")
    log(f"🧱 Total estructuras detectadas: {len(conteo)}")
    for e, c in conteo.items():
        log(f"{e}: {c} unidades")

    if archivo_materiales:
        excel_temp = pd.ExcelFile(archivo_materiales)
        log(f"📄 Hojas disponibles en Estructura_datos.xlsx: {excel_temp.sheet_names}")

    # === 5) Materiales por ESTRUCTURA (con reemplazo de conectores por calibre real) ===
    df_lista = []
    for e, cantidad in conteo.items():
        calibre_actual = determinar_calibre_por_estructura(e, datos_proyecto)

        try:
            df_mat = calcular_materiales_estructura(
                archivo_materiales, e, cantidad, tension, calibre_actual, tabla_conectores_mt
            )
        except TypeError:
            df_mat = calcular_materiales_estructura(
                archivo_materiales, e, cantidad, tension, calibre_actual
            )

        # Reemplazo conectores SOLO en filas de esta estructura
        if df_mat is not None and not df_mat.empty and "Materiales" in df_mat.columns:
            originales = df_mat["Materiales"].astype(str).tolist()
            reemplazados = aplicar_reemplazos_conectores(
                originales,
                calibre_estructura=calibre_actual,
                tabla_conectores=tabla_conectores_mt,
            )

            if originales != reemplazados:
                log(f"🔁 Reemplazos en {e} (calibre {calibre_actual}):")
                for a, b in zip(originales, reemplazados):
                    if a != b and "CONECTOR" in a.upper():
                        log(f"   '{a}'  →  '{b}'")
            else:
                log(f"⚠️ Sin reemplazos efectivos en {e} (calibre {calibre_actual}).")

            df_mat["Materiales"] = reemplazados

        if df_mat is not None and not df_mat.empty:
            df_lista.append(df_mat)

    df_total = pd.concat(df_lista, ignore_index=True) if df_lista else pd.DataFrame()

    # === 6) Resumen global de materiales ===
    if not df_total.empty:
        df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    else:
        df_resumen = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    log("df_resumen (materiales):\n" + str(df_resumen.head(10)))

    # === 7) Resumen de estructuras globales ===
    df_estructuras_resumen = construir_df_estructuras_resumen(df_indice, conteo, log)

    # === 8) Estructuras por punto (robusto) ===
    df_estructuras_por_punto = construir_df_estructuras_por_punto(tmp_explotado, df_indice, log)

    # === 9) Materiales por punto ===
    df_resumen_por_punto = calcular_materiales_por_punto(
        archivo_materiales, estructuras_por_punto, tension
    )
    log("df_resumen_por_punto:\n" + str(df_resumen_por_punto.head(10)))

    # === 10) Materiales adicionales manuales ===
    df_resumen, datos_proyecto = integrar_materiales_extra(df_resumen, datos_proyecto, log)

    # === 11) Generación de PDFs ===
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

    # En tu pdf_utils.py, en generar_pdf_completo() aún podés tener "Punto Punto X"
    # si no hiciste la corrección ahí. Este DF ya viene con "Punto 1", etc.
    pdf_informe_completo = generar_pdf_completo(
        df_resumen,
        df_estructuras_resumen,
        df_estructuras_por_punto,
        df_resumen_por_punto,
        datos_proyecto
    )

    # === 12) Retorno ===
    return {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_informe_completo,
    }
