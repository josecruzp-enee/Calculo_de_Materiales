# -*- coding: utf-8 -*-

from __future__ import annotations
import pandas as pd

from materiales.modelos.entrada import EntradaMateriales
from materiales.modelos.salida import ResultadoMateriales

from materiales.calculos.calculo_materiales import calcular_materiales_proyecto
from materiales.validaciones.materiales_validacion import validar_datos_proyecto
from materiales.cables.cables_materiales import materiales_desde_cables


COLUMNAS_STD = ["Materiales", "Unidad", "Cantidad"]


# =========================================================
# HELPERS
# =========================================================
def _df_vacio():
    return pd.DataFrame(columns=COLUMNAS_STD)


def _consolidar(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return _df_vacio()

    return (
        df
        .groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"]
        .sum()
    )


def _validar_df_materiales(df: pd.DataFrame):

    if df is None or df.empty:
        raise ValueError("Materiales vacíos")

    if not set(COLUMNAS_STD).issubset(df.columns):
        raise ValueError("Formato inválido en materiales")

    if df["Materiales"].isna().any():
        raise ValueError("Materiales contiene nulos")

    if df["Unidad"].isna().any():
        raise ValueError("Unidad contiene nulos")

    cantidades = pd.to_numeric(df["Cantidad"], errors="coerce")

    if cantidades.isna().any():
        raise ValueError("Cantidad inválida")

    if (cantidades < 0).any():
        raise ValueError("Cantidad negativa")


# =========================================================
# ORQUESTADOR
# =========================================================
def ejecutar_materiales(
    entrada: EntradaMateriales,
    catalogo: pd.DataFrame | None = None
) -> ResultadoMateriales:

    errores = []
    warnings = []

    # ======================================================
    # 1. VALIDACIÓN DE ENTRADA
    # ======================================================
    if entrada is None:
        return ResultadoMateriales(False, _df_vacio(), ["Entrada es None"], [])

    if entrada.estructuras_df is None or entrada.estructuras_df.empty:
        return ResultadoMateriales(False, _df_vacio(), ["Sin estructuras"], [])

    if entrada.hojas_base is None:
        return ResultadoMateriales(False, _df_vacio(), ["Base de datos no cargada"], [])

    if not entrada.tension:
        return ResultadoMateriales(False, _df_vacio(), ["Tensión inválida"], [])

    try:
        tension = float(entrada.tension)
        if tension <= 0:
            raise ValueError
    except Exception:
        return ResultadoMateriales(False, _df_vacio(), ["Tensión inválida"], [])

    datos = entrada.datos_proyecto or {}

    # ======================================================
    # 2. VALIDACIÓN DE PROYECTO
    # ======================================================
    try:
        _, calibre_mt = validar_datos_proyecto(datos)
    except Exception as e:
        return ResultadoMateriales(False, _df_vacio(), [f"Error en datos proyecto: {e}"], [])

    # ======================================================
    # 3. CÁLCULO PRINCIPAL
    # ======================================================
    try:
        resultados = calcular_materiales_proyecto(
            hojas_base=entrada.hojas_base,
            df_estructuras=entrada.estructuras_df,
            tension=tension
        )

        df_materiales = resultados.get("df_materiales_detalle")

        if not isinstance(df_materiales, pd.DataFrame):
            raise ValueError("Salida inválida del motor")

        _validar_df_materiales(df_materiales)

    except Exception as e:
        return ResultadoMateriales(False, _df_vacio(), [f"Error en cálculo: {e}"], [])

    # ======================================================
    # 4. CABLES
    # ======================================================
    df_cables = _df_vacio()

    if hasattr(entrada, "df_cables") and isinstance(entrada.df_cables, pd.DataFrame):
        try:
            df_tmp = materiales_desde_cables(entrada.df_cables)
            _validar_df_materiales(df_tmp)
            df_cables = df_tmp
        except Exception as e:
            warnings.append(f"Cables ignorados: {e}")

    # ======================================================
    # 5. MATERIALES EXTRA
    # ======================================================
    df_extra = _df_vacio()

    if isinstance(datos.get("materiales_extra"), pd.DataFrame):
        try:
            _validar_df_materiales(datos["materiales_extra"])
            df_extra = datos["materiales_extra"]
        except Exception as e:
            warnings.append(f"Materiales extra ignorados: {e}")

    # ======================================================
    # 6. UNIÓN
    # ======================================================
    df_total = pd.concat(
        [df_materiales, df_cables, df_extra],
        ignore_index=True
    )

    _validar_df_materiales(df_total)

    # ======================================================
    # 7. CONSOLIDACIÓN
    # ======================================================
    df_total = _consolidar(df_total)

    # ======================================================
    # 8. VALIDACIÓN CATÁLOGO
    # ======================================================
    if catalogo is not None and not catalogo.empty:

        catalogo_base = catalogo.copy()
        catalogo_base["Materiales"] = catalogo_base["Materiales"].astype(str).str.upper().str.strip()

        df_total["Materiales"] = df_total["Materiales"].astype(str).str.upper().str.strip()

        catalogo_set = set(catalogo_base["Materiales"])

        no_validos = df_total.loc[~df_total["Materiales"].isin(catalogo_set)]

        if not no_validos.empty:
            errores.extend([
                f"Material no válido: {m}"
                for m in no_validos["Materiales"].unique()
            ])
            return ResultadoMateriales(False, _df_vacio(), errores, warnings)

    # ======================================================
    # 9. COSTOS
    # ======================================================
    if catalogo is not None and "Costo" in catalogo.columns:

        catalogo_tmp = catalogo.copy()
        catalogo_tmp["Materiales"] = catalogo_tmp["Materiales"].astype(str).str.upper().str.strip()

        df_total = df_total.merge(
            catalogo_tmp[["Materiales", "Costo"]],
            on="Materiales",
            how="left"
        )

        if df_total["Costo"].isna().any():
            warnings.append("Algunos materiales no tienen costo definido")

        df_total["Costo"] = pd.to_numeric(df_total["Costo"], errors="coerce")
        df_total["Costo_Total"] = df_total["Cantidad"] * df_total["Costo"]

    # ======================================================
    # 10. SALIDA
    # ======================================================
    return ResultadoMateriales(True, df_total, errores, warnings)
