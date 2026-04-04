import pandas as pd


# =========================================================
# CONFIGURACIÓN
# =========================================================
ARCHIVO = "Estructura_datos.xlsx"

CUADRILLA = 1250
FACTOR_TIEMPO = 0.25
FACTOR_EQUIPO = 0.20
FACTOR_UTILIDAD = 0.15


# =========================================================
# CARGAR PRECIOS
# =========================================================
def cargar_precios(xls):

    df_precios = pd.read_excel(xls, sheet_name="Materiales")

    # limpiar nombres de columnas por si hay espacios
    df_precios.columns = [str(c).strip() for c in df_precios.columns]

    dict_precios = dict(
        zip(
            df_precios["CODIGO"].astype(str).str.strip(),
            df_precios["Costo Unitario"]
        )
    )

    return dict_precios


# =========================================================
# CALCULAR MATERIAL POR ESTRUCTURA
# =========================================================
def calcular_material(df, dict_precios):

    total = 0

    for _, row in df.iterrows():

        # código limpio
        codigo = str(row.get("COD. ENEE", "")).strip()

        if not codigo:
            continue

        # cantidad dinámica
        cantidad = 0

        if "34.5" in df.columns:
            cantidad += row.get("34.5", 0)

        if "13.8" in df.columns:
            cantidad += row.get("13.8", 0)

        # precio desde base
        precio = dict_precios.get(codigo, 0)

        total += cantidad * precio

    return total


# =========================================================
# MODELO DE COSTOS
# =========================================================
def calcular_costos(material):

    equipos = material * FACTOR_EQUIPO
    mano_obra = CUADRILLA * FACTOR_TIEMPO
    utilidad = (material + equipos + mano_obra) * FACTOR_UTILIDAD

    total = material + equipos + mano_obra + utilidad

    return equipos, mano_obra, utilidad, total


# =========================================================
# PROCESAMIENTO GENERAL
# =========================================================
def procesar():

    xls = pd.ExcelFile(ARCHIVO)

    dict_precios = cargar_precios(xls)

    resultados = []

    for hoja in xls.sheet_names:

        # hojas que no son estructuras
        if hoja.lower() in ["materiales", "indice", "internos", "conectores"]:
            continue

        df = pd.read_excel(xls, sheet_name=hoja)

        # validar estructura
        if "COD. ENEE" not in df.columns:
            continue

        # calcular material
        material_total = calcular_material(df, dict_precios)

        # calcular costos completos
        equipos, mo, utilidad, total = calcular_costos(material_total)

        resultados.append({
            "Estructura": hoja,
            "Material": round(material_total, 2),
            "Equipos": round(equipos, 2),
            "Mano de Obra": round(mo, 2),
            "Utilidad": round(utilidad, 2),
            "TOTAL": round(total, 2)
        })

    df_final = pd.DataFrame(resultados)

    # ordenar por nombre de estructura
    df_final = df_final.sort_values("Estructura")

    # exportar
    df_final.to_excel("costos_estructuras.xlsx", index=False)

    print("\n✅ Costos generados correctamente:\n")
    print(df_final)


# =========================================================
# EJECUCIÓN
# =========================================================
if __name__ == "__main__":
    procesar()
