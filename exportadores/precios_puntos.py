import pandas as pd


# =========================================================
# CONFIG
# =========================================================
ARCH_COSTOS = "costos_estructuras.xlsx"
ARCH_PUNTOS = "estructura_lista.xlsx"


# =========================================================
# CARGAR COSTOS
# =========================================================
def cargar_costos():

    df = pd.read_excel(ARCH_COSTOS)

    df.columns = [str(c).strip() for c in df.columns]

    dict_costos = dict(
        zip(
            df["Estructura"].astype(str).str.strip(),
            df["TOTAL"]
        )
    )

    return dict_costos


# =========================================================
# PROCESAR PUNTOS
# =========================================================
def procesar_puntos():

    dict_costos = cargar_costos()

    df = pd.read_excel(ARCH_PUNTOS)

    df.columns = [str(c).strip() for c in df.columns]

    resultados = []

    for _, row in df.iterrows():

        punto = row["Punto"]
        estructura = str(row["Estructura"]).strip()
        cantidad = row["Cantidad"]

        precio = dict_costos.get(estructura, 0)

        subtotal = cantidad * precio

        resultados.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad,
            "Precio Unitario": precio,
            "Subtotal": subtotal
        })

    df_detalle = pd.DataFrame(resultados)

    # =====================================================
    # TOTAL POR PUNTO
    # =====================================================
    df_resumen = df_detalle.groupby("Punto")["Subtotal"].sum().reset_index()
    df_resumen.rename(columns={"Subtotal": "TOTAL_PUNTO"}, inplace=True)

    # =====================================================
    # EXPORTAR
    # =====================================================
    with pd.ExcelWriter("costos_puntos.xlsx") as writer:
        df_detalle.to_excel(writer, sheet_name="Detalle", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)

    print("\n✅ Costos por punto generados:\n")
    print(df_resumen)


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    procesar_puntos()
