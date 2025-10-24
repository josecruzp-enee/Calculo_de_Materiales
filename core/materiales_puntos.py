import pandas as pd
from core.materiales_aux import limpiar_codigo, expandir_lista_codigos
from modulo.entradas import cargar_materiales

def calcular_materiales_por_punto(archivo_materiales, estructuras_por_punto, tension):
    resumen_punto = []
    for punto, estructuras in estructuras_por_punto.items():
        for est in estructuras:
            for parte in expandir_lista_codigos(est):
                codigo, tipo = limpiar_codigo(parte)
                if not codigo:
                    continue
                try:
                    df_temp = cargar_materiales(archivo_materiales, codigo, header=None)
                    fila_tension = next(
                        i for i, row in df_temp.iterrows()
                        if any(str(tension) in str(cell) for cell in row)
                    )
                    df = cargar_materiales(archivo_materiales, codigo, header=fila_tension)
                    df.columns = df.columns.map(str).str.strip()
                    if "Materiales" not in df.columns or str(tension) not in df.columns:
                        continue
                    dfp = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()
                    dfp["Cantidad"] = dfp[str(tension)]
                    dfp["Punto"] = punto
                    resumen_punto.append(dfp[["Punto", "Materiales", "Unidad", "Cantidad"]])
                except Exception:
                    pass
    return (
        pd.concat(resumen_punto, ignore_index=True)
          .groupby(["Punto","Materiales","Unidad"], as_index=False)["Cantidad"].sum()
        if resumen_punto else
        pd.DataFrame(columns=["Punto","Materiales","Unidad","Cantidad"])
    )
