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

        codigo = str(row.get("COD. ENEE", "")).strip()

        if not codigo:
            continue

        cantidad = 0

        if "34.5" in df.columns:
            cantidad += row.get("34.5", 0)

        if "13.8" in df.columns:
            cantidad += row.get("13.8", 0)

        precio = dict_precios.get(codigo, 0)

        # 🔥 VALIDACIÓN
        if precio == 0:
            print(f"⚠️ Material sin precio: {codigo}")

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
# FUNCIÓN PRINCIPAL (REUTILIZABLE)
# =========================================================
def procesar_precios_estructura(ruta_archivo=ARCHIVO, exportar=False):

    xls = pd.ExcelFile(ruta_archivo)

    dict_precios = cargar_precios(xls)

    resultados = []

    for hoja in xls.sheet_names:

        if hoja.lower() in ["materiales", "indice", "internos", "conectores"]:
            continue

        df = pd.read_excel(xls, sheet_name=hoja)

        if "COD. ENEE" not in df.columns:
            continue

        material_total = calcular_material(df, dict_precios)

        equipos, mo, utilidad, total = calcular_costos(material_total)

        resultados.append({
            "Estructura": hoja,
            "Material": round(material_total, 2),
            "Equipos": round(equipos, 2),
            "Mano de Obra": round(mo, 2),
            "Utilidad": round(utilidad, 2),
            "Precio Unitario": round(total, 2)  # 🔥 cambio clave
        })

    df_final = pd.DataFrame(resultados)
    df_final = df_final.sort_values("Estructura")

    if exportar:
        df_final.to_excel("precios_estructuras.xlsx", index=False)

    return df_final


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================
if __name__ == "__main__":

    df = procesar_precios_estructura(exportar=True)

    print("\n✅ Precios de estructuras generados:\n")
    print(df)
