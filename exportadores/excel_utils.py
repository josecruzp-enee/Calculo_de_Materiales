import pandas as pd

def exportar_excel(
    df_estructuras_resumen,
    df_resumen,
    df_adicionales,
    df_resumen_por_punto,
    ruta_excel
):
    """
    Exporta un archivo Excel con varias hojas:
    1. Estructuras_Proyecto
    2. Materiales
    3. Materiales_Adicionados
    4. Materiales_por_Punto
    """
    with pd.ExcelWriter(ruta_excel, engine="openpyxl", mode="w") as writer:
        # 1. Estructuras del proyecto
        if df_estructuras_resumen is not None and not df_estructuras_resumen.empty:
            df_estructuras_resumen.to_excel(writer, sheet_name="Estructuras_Proyecto", index=False)
        else:
            pd.DataFrame(columns=["NombreEstructura", "Descripcion", "Cantidad"]).to_excel(
                writer, sheet_name="Estructuras_Proyecto", index=False
            )

        # 2. Materiales generales
        if df_resumen is not None and not df_resumen.empty:
            df_resumen.to_excel(writer, sheet_name="Materiales", index=False)
        else:
            pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]).to_excel(
                writer, sheet_name="Materiales", index=False
            )

        # 3. Materiales adicionados
        if df_adicionales is not None and not df_adicionales.empty:
            df_adicionales.to_excel(writer, sheet_name="Materiales_Adicionados", index=False)
        else:
            pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"]).to_excel(
                writer, sheet_name="Materiales_Adicionados", index=False
            )

        # 4. Materiales por punto
        if df_resumen_por_punto is not None and not df_resumen_por_punto.empty:
            df_resumen_por_punto.to_excel(writer, sheet_name="Materiales_por_Punto", index=False)
        else:
            pd.DataFrame(columns=["Punto", "Materiales", "Unidad", "Cantidad"]).to_excel(
                writer, sheet_name="Materiales_por_Punto", index=False
            )

    print(f"✅ Archivo Excel exportado en: {ruta_excel}")
