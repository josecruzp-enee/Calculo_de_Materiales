# -*- coding: utf-8 -*-
import pandas as pd


# =========================================================
# CONFIG
# =========================================================
ARCH_COSTOS = "costos_estructuras.xlsx"
ARCH_PUNTOS = "estructura_lista.xlsx"


# =========================================================
# CARGAR COSTOS (AHORA PRECIO UNITARIO)
# =========================================================
def cargar_costos():

    df = pd.read_excel(ARCH_COSTOS)
    df.columns = [str(c).strip() for c in df.columns]

    # 🔥 VALIDACIÓN NUEVA
    if "codigodeestructura" not in df.columns:
        raise ValueError("Falta 'codigodeestructura' en costos")

    if "Precio Unitario" not in df.columns:
        raise ValueError("Falta 'Precio Unitario' en costos")

    dict_precios = dict(
        zip(
            df["codigodeestructura"].astype(str).str.strip(),
            df["Precio Unitario"]
        )
    )

    return dict_precios


# =========================================================
# PROCESAR PUNTOS
# =========================================================
def procesar_puntos():

    dict_precios = cargar_costos()

    df = pd.read_excel(ARCH_PUNTOS)
    df.columns = [str(c).strip() for c in df.columns]

    resultados = []

    for _, row in df.iterrows():

        punto = row.get("Punto")
        estructura = str(row.get("Estructura", "")).strip()
        cantidad = float(row.get("Cantidad", 0) or 0)

        # 🔥 VALIDACIÓN FUERTE
        if estructura not in dict_precios:
            raise ValueError(f"Estructura sin precio: {estructura}")

        precio_unit = float(dict_precios[estructura])
        subtotal = cantidad * precio_unit

        resultados.append({
            "Punto": punto,
            "Estructura": estructura,
            "Cantidad": cantidad,
            "Precio Unitario": round(precio_unit, 2),
            "Subtotal Precio": round(subtotal, 2),
        })

    df_detalle = pd.DataFrame(resultados)

    # =====================================================
    # RESUMEN POR PUNTO (PRECIO)
    # =====================================================
    df_resumen = (
        df_detalle.groupby("Punto")["Subtotal Precio"]
        .sum()
        .reset_index()
        .rename(columns={"Subtotal Precio": "TOTAL_PRECIO_PUNTO"})
    )

    # =====================================================
    # TOTAL PROYECTO
    # =====================================================
    total_proyecto = df_resumen["TOTAL_PRECIO_PUNTO"].sum()

    # =====================================================
    # EXPORTAR
    # =====================================================
    with pd.ExcelWriter("precios_por_punto.xlsx") as writer:
        df_detalle.to_excel(writer, sheet_name="Detalle", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)

    print("\n✅ Precios por punto generados:\n")
    print(df_resumen)
    print(f"\n💰 TOTAL PROYECTO: L {total_proyecto:,.2f}")


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    procesar_puntos()
