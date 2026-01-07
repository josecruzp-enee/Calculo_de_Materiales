# -*- coding: utf-8 -*-
"""
procesar_materiales.py
Cálculo de materiales globales y por punto + generación de PDFs.
FIX PRINCIPAL:
- Normaliza la tensión a kV L-L numérica aunque venga como texto ("7.9 LN / 13.8 LL KV")
- Encuentra la columna de tensión en hojas por match directo o numérico
- Ya NO oculta errores en materiales por punto (log explícito)
"""

import re
import pandas as pd

from modulo.entradas import (
    cargar_datos_proyecto,
    cargar_estructuras_proyectadas,
    cargar_indice,
    cargar_materiales,
)

from core.conectores_mt import (
    cargar_conectores_mt,
    determinar_calibre_por_estructura,
    aplicar_reemplazos_conectores,
)

from core.materiales_validacion import validar_datos_proyecto
from core.materiales_estructuras import calcular_materiales_estructura


# ==========================================================
# Helpers generales
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

    cables = datos_proyecto.get("cables_proyecto", [])
    if isinstance(cables, dict) or cables is None:
        cables = []
    datos_proyecto["cables_proyecto"] = cables

    return datos_proyecto


def extraer_tension_ll_kv(x):
    """
    Devuelve la tensión L-L (kV) como float.
    Acepta:
      - 13.8
      - "13.8"
      - "7.9 LN / 13.8 LL KV"
      - "19.9 L-N / 34.5 L-L kV"
    Regla: toma el número mayor (usualmente L-L).
    """
    if x is None:
        return None
    nums = re.findall(r"\d+(?:\.\d+)?", str(x))
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return max(vals) if vals else None


def encontrar_col_tension(cols, tension_ll: float):
    """
    Encuentra la columna de tensión en una hoja de materiales.

    Estrategia:
      1) Match directo por substring (ej: "13.8" dentro del header)
      2) Match numérico: extrae números del header y compara por tolerancia
    """
    if tension_ll is None:
        return None

    # 1) Match directo
    t_str = f"{float(tension_ll)}".rstrip("0").rstrip(".")
    for c in cols:
        if t_str and t_str in str(c):
            return c

    # 2) Match numérico
    for c in cols:
        nums = re.findall(r"\d+(?:\.\d+)?", str(c))
        for n in nums:
            try:
                if abs(float(n) - float(tension_ll)) < 1e-6:
                    return c
            except Exception:
                pass

    return None


# ==========================================================
# Limpieza de DF estructuras (LARGO)
# ==========================================================
def limpiar_df_estructuras(df_estructuras: pd.DataFrame, log) -> pd.DataFrame:
    """
    Espera DF LARGO con columnas mínimas:
      - Punto
      - codigodeestructura
      - cantidad (opcional; si no viene, asume 1)

    ✅ NO elimina duplicados; AGRUPA y SUMA cantidades.
    """
    filas_antes = len(df_estructuras)
    df = df_estructuras.dropna(how="all").copy()

    if "Punto" not in df.columns and "punto" in df.columns:
        df.rename(columns={"punto": "Punto"}, inplace=True)

    for col in ("Punto", "codigodeestructura"):
        if col not in df.columns:
            raise ValueError(
                f"Falta columna requerida: '{col}'. Columnas: {df.columns.tolist()}"
            )

    df["Punto"] = df["Punto"].astype(str).str.strip()
    df["codigodeestructura"] = df["codigodeestructura"].astype(str).str.strip()

    if "cantidad" not in df.columns:
        df["cantidad"] = 1
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)
    df.loc[df["cantidad"] < 1, "cantidad"] = 1

    df = df[df["codigodeestructura"].notna()]
    df = df[df["codigodeestructura"].astype(str).str.strip() != ""]

    df = (
        df.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )

    filas_despues = len(df)
    log(f"🧹 Filas eliminadas: {filas_antes - filas_despues}")
    return df


def _normalizar_codigo_basico(code: str) -> str:
    """
    Normalización básica de código:
      - uppercase
      - strip
      - quita sufijos tipo "(E)" "(P)" "(R)"
      - colapsa espacios (solo para códigos)
      - normaliza TS (quita espacios antes de KVA)
    """
    if code is None:
        return ""
    s = str(code).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()  # quita "(E)" etc al final
    s = re.sub(r"\s+", " ", s).strip()
    s = s.upper()

    # Normalizar transformadores tipo "TS-50 KVA" -> "TS-50KVA"
    s = re.sub(r"\bTS-?\s*(\d+(\.\d+)?)\s*KVA\b", lambda m: f"TS-{m.group(1)}KVA", s)
    s = s.replace(" TS-", "TS-").replace(" KVA", "KVA")
    return s


def explotar_codigos_por_coma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte celdas tipo:
      "B-III-6, B-I-4B" -> 2 filas.
    Mantiene y distribuye la misma 'cantidad' a cada código separado.

    ✅ Luego agrupa y SUMA por (Punto, código).
    """
    tmp = df[["Punto", "codigodeestructura", "cantidad"]].copy()

    tmp["Punto"] = tmp["Punto"].astype(str).str.strip()
    tmp["cantidad"] = pd.to_numeric(tmp["cantidad"], errors="coerce").fillna(1).astype(int)
    tmp.loc[tmp["cantidad"] < 1, "cantidad"] = 1

    tmp["codigodeestructura"] = tmp["codigodeestructura"].astype(str).str.replace(";", ",", regex=False)
    tmp["codigodeestructura"] = tmp["codigodeestructura"].str.split(",")
    tmp = tmp.explode("codigodeestructura")

    tmp["codigodeestructura"] = tmp["codigodeestructura"].map(_normalizar_codigo_basico)
    tmp = tmp[tmp["codigodeestructura"] != ""]

    tmp = (
        tmp.groupby(["Punto", "codigodeestructura"], as_index=False)["cantidad"]
        .sum()
    )
    return tmp


def construir_estructuras_por_punto_y_conteo(df_unicas: pd.DataFrame, log):
    """
    Construye:
      - estructuras_por_punto: dict {Punto: [códigos repetidos según cantidad]}
      - conteo: dict {codigo: cantidad_total_en_proyecto}
      - tmp: DataFrame explotado con columnas (Punto, codigodeestructura, cantidad)
    """
    tmp = explotar_codigos_por_coma(df_unicas)

    conteo = (
        tmp.groupby("codigodeestructura")["cantidad"]
        .sum()
        .to_dict()
    )

    estructuras_por_punto = {}
    for punto, grp in tmp.groupby("Punto"):
        lista = []
        for _, r in grp.iterrows():
            cod = str(r["codigodeestructura"]).strip().upper()
            c = int(r["cantidad"])
            lista.extend([cod] * max(1, c))
        estructuras_por_punto[str(punto)] = lista

    log("✅ estructuras_por_punto (repitiendo por cantidad):")
    log(estructuras_por_punto)
    log("✅ conteo global (sumando cantidad):")
    log(conteo)

    return estructuras_por_punto, conteo, tmp


# ==========================================================
# Índice normalizado
# ==========================================================
def cargar_indice_normalizado(archivo_materiales, log) -> pd.DataFrame:
    df_indice = cargar_indice(archivo_materiales)

    log("Columnas originales índice: " + str(df_indice.columns.tolist()))
    df_indice = df_indice.copy()
    df_indice.columns = df_indice.columns.str.strip().str.lower()

    if "código de estructura" in df_indice.columns:
        df_indice.rename(columns={"código de estructura": "codigodeestructura"}, inplace=True)
    if "codigo de estructura" in df_indice.columns:
        df_indice.rename(columns={"codigo de estructura": "codigodeestructura"}, inplace=True)

    if "descripcion" in df_indice.columns:
        df_indice.rename(columns={"descripcion": "Descripcion"}, inplace=True)

    if "codigodeestructura" not in df_indice.columns:
        df_indice["codigodeestructura"] = ""
    df_indice["codigodeestructura"] = df_indice["codigodeestructura"].astype(str).map(_normalizar_codigo_basico)

    if "Descripcion" not in df_indice.columns:
        df_indice["Descripcion"] = ""
    else:
        df_indice["Descripcion"] = df_indice["Descripcion"].fillna("").astype(str)

    log("Columnas normalizadas índice: " + str(df_indice.columns.tolist()))
    log("Primeras filas índice:\n" + str(df_indice.head(10)))

    return df_indice


def construir_df_estructuras_resumen(df_indice: pd.DataFrame, conteo: dict, log) -> pd.DataFrame:
    conteo_norm = {str(k).strip().upper(): int(v) for k, v in conteo.items()}
    df = df_indice.copy()
    df["Cantidad"] = df["codigodeestructura"].map(conteo_norm).fillna(0).astype(int)
    df_res = df[df["Cantidad"] > 0].copy()
    log("df_estructuras_resumen:\n" + str(df_res.head(50)))
    return df_res


def construir_df_estructuras_por_punto(tmp_explotado: pd.DataFrame, df_indice: pd.DataFrame, log) -> pd.DataFrame:
    df_pp = tmp_explotado.merge(
        df_indice[["codigodeestructura", "Descripcion"]],
        on="codigodeestructura",
        how="left"
    )
    df_pp["Descripcion"] = df_pp["Descripcion"].fillna("NO ENCONTRADA")
    df_pp.rename(columns={"cantidad": "Cantidad"}, inplace=True)
    df_pp = df_pp[["Punto", "codigodeestructura", "Descripcion", "Cantidad"]].copy()
    log("df_estructuras_por_punto:\n" + str(df_pp.head(50)))
    return df_pp


# ==========================================================
# Materiales POR PUNTO (respeta cantidad + reemplazo conectores)
# ==========================================================
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
    ✅ Encuentra columna por tensión LL numérica (aunque la validación devuelva texto).
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


def integrar_materiales_extra(df_resumen: pd.DataFrame, datos_proyecto: dict, log):
    """
    Integra materiales extra desde session_state.
    ✅ NO normaliza nombres (ya vienen uniformes).
    """
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
    log = get_logger()

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

    tension_raw, calibre_mt = validar_datos_proyecto(datos_proyecto)
    log(f"Tensión (raw): {tension_raw}   Calibre MT: {calibre_mt}")

    # ✅ FIX: convertir a tensión LL numérica SIEMPRE
    tension_ll = (
        extraer_tension_ll_kv(tension_raw)
        or extraer_tension_ll_kv(datos_proyecto.get("nivel_de_tension"))
        or extraer_tension_ll_kv(datos_proyecto.get("tension"))
    )
    if tension_ll is None:
        raise ValueError(f"No pude interpretar la tensión. Recibí: {tension_raw!r}")

    log(f"✅ Tensión normalizada (LL kV): {tension_ll}")

    log("⚙️ DEBUG VALIDAR DATOS PROYECTO")
    log(f"➡️ tension_raw = {tension_raw}")
    log(f"➡️ tension_ll  = {tension_ll}")
    log(f"➡️ calibre_mt  = {calibre_mt}")
    log(f"➡️ datos_proyecto = {datos_proyecto}")

    log("🔍 Limpieza inicial de estructuras...")
    df_estructuras_unicas = limpiar_df_estructuras(df_estructuras, log)

    estructuras_por_punto, conteo, tmp_explotado = construir_estructuras_por_punto_y_conteo(df_estructuras_unicas, log)

    df_indice = cargar_indice_normalizado(archivo_materiales, log)
    tabla_conectores_mt = cargar_conectores_mt(archivo_materiales)

    log("🧩 DEBUG ANTES DE CALCULAR MATERIALES:")
    log(f"🧱 Total estructuras detectadas: {len(conteo)}")
    for e, c in conteo.items():
        log(f"{e}: {c} unidades")

    if archivo_materiales:
        excel_temp = pd.ExcelFile(archivo_materiales)
        log(f"📄 Hojas disponibles en Estructura_datos.xlsx: {excel_temp.sheet_names}")

    # === Materiales globales por estructura ===
    df_lista = []
    for e, cantidad in conteo.items():
        calibre_actual = determinar_calibre_por_estructura(e, datos_proyecto)

        df_mat = calcular_materiales_estructura(
            archivo_materiales, e, cantidad, tension_ll, calibre_actual, tabla_conectores_mt
        )

        if df_mat is not None and not df_mat.empty:
            # ✅ NO normaliza nombres de materiales
            df_mat["Unidad"] = df_mat["Unidad"].astype(str).str.strip()
            df_lista.append(df_mat)

    df_total = pd.concat(df_lista, ignore_index=True) if df_lista else pd.DataFrame()

    if not df_total.empty:
        df_resumen = df_total.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    else:
        df_resumen = pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    log("df_resumen (materiales):\n" + str(df_resumen.head(30)))

    df_estructuras_resumen = construir_df_estructuras_resumen(df_indice, conteo, log)
    df_estructuras_por_punto = construir_df_estructuras_por_punto(tmp_explotado, df_indice, log)

    # === Materiales por punto (respeta cantidad + conectores) ===
    df_resumen_por_punto = calcular_materiales_por_punto_con_cantidad(
        archivo_materiales, tmp_explotado, tension_ll, tabla_conectores_mt, datos_proyecto, log=log
    )
    log("df_resumen_por_punto:\n" + str(df_resumen_por_punto.head(30)))

    # materiales extra (manuales)
    df_resumen, datos_proyecto = integrar_materiales_extra(df_resumen, datos_proyecto, log)

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

    return {
        "materiales": pdf_materiales,
        "estructuras_global": pdf_estructuras_global,
        "estructuras_por_punto": pdf_estructuras_por_punto,
        "materiales_por_punto": pdf_materiales_por_punto,
        "completo": pdf_informe_completo,
    }
