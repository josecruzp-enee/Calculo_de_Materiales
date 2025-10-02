import pandas as pd
from collections import Counter
from modulo.materiales_aux import limpiar_codigo, expandir_lista_codigos
from modulo.entradas import extraer_estructuras_proyectadas, cargar_materiales
from modulo.conectores_mt import aplicar_reemplazos_conectores

def extraer_conteo_estructuras(df_estructuras):
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)
    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, tipo = limpiar_codigo(parte)
            if codigo:
                estructuras_limpias.append(codigo)
    conteo = Counter(estructuras_limpias)
    return conteo, estructuras_por_punto


def calcular_materiales_estructura(archivo_materiales, estructura, cant, tension, calibre_mt, tabla_conectores_mt):
    try:
        df_temp = cargar_materiales(archivo_materiales, estructura, header=None)
        fila_tension = next(
            i for i, row in df_temp.iterrows()
            if any(str(tension) in str(cell) for cell in row)
        )
        df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)
        df.columns = df.columns.map(str).str.strip()
        if "Materiales" not in df.columns or str(tension) not in df.columns:
            return pd.DataFrame()
        df_filtrado = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()
        df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
            df_filtrado["Materiales"].tolist(),
            calibre_mt,
            tabla_conectores_mt
        )
        df_filtrado["Cantidad"] = df_filtrado[str(tension)] * cant
        return df_filtrado[["Materiales", "Unidad", "Cantidad"]]
    except Exception:
        return pd.DataFrame()
