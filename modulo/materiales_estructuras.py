import pandas as pd
from collections import Counter
from modulo.materiales_aux import limpiar_codigo, expandir_lista_codigos
from modulo.entradas import extraer_estructuras_proyectadas, cargar_materiales
from modulo.conectores_mt import aplicar_reemplazos_conectores

def extraer_conteo_estructuras(df_estructuras):
    """
    Extrae el conteo global de estructuras y la lista por punto.
    Filtra valores vacíos o genéricos como 'SELECCIONAR' o 'ESTRUCTURA'.
    """
    estructuras_proyectadas, estructuras_por_punto = extraer_estructuras_proyectadas(df_estructuras)

    # Lista total (todas las estructuras del proyecto)
    estructuras_limpias = []
    for e in estructuras_proyectadas:
        for parte in expandir_lista_codigos(e):
            codigo, tipo = limpiar_codigo(parte)
            if codigo:
                estructuras_limpias.append(codigo)

    # 🔍 Filtro para eliminar valores no válidos
    valores_invalidos = {"", "SELECCIONAR", "ESTRUCTURA", "PUNTO", "N/A", "NONE", "1", "2", "3"}
    estructuras_filtradas = [e for e in estructuras_limpias if str(e).strip().upper() not in valores_invalidos]

    # Contar estructuras válidas
    conteo = Counter(estructuras_filtradas)

    # 🔍 Limpiar también estructuras_por_punto
    estructuras_por_punto_filtrado = {}
    for punto, lista in estructuras_por_punto.items():
        estructuras_validas = [
            e for e in lista if str(e).strip().upper() not in valores_invalidos
        ]
        estructuras_por_punto_filtrado[punto] = estructuras_validas

    return conteo, estructuras_por_punto_filtrado


def calcular_materiales_estructura(archivo_materiales, estructura, cant, tension, calibre_mt, tabla_conectores_mt):
    """
    Carga los materiales asociados a una estructura desde el archivo de datos.
    """
    try:
        df_temp = cargar_materiales(archivo_materiales, estructura, header=None)

        # Encontrar fila donde se ubica el nivel de tensión
        fila_tension = next(
            i for i, row in df_temp.iterrows()
            if any(str(tension) in str(cell) for cell in row)
        )

        df = cargar_materiales(archivo_materiales, estructura, header=fila_tension)
        df.columns = df.columns.map(str).str.strip()

        if "Materiales" not in df.columns or str(tension) not in df.columns:
            return pd.DataFrame()

        # Filtrar materiales con cantidad positiva
        df_filtrado = df[df[str(tension)] > 0][["Materiales", "Unidad", str(tension)]].copy()

        # Aplicar reemplazos de conectores según calibre MT
        df_filtrado["Materiales"] = aplicar_reemplazos_conectores(
            df_filtrado["Materiales"].tolist(),
            calibre_mt,
            tabla_conectores_mt
        )

        # Calcular cantidades finales
        df_filtrado["Cantidad"] = df_filtrado[str(tension)] * cant
        return df_filtrado[["Materiales", "Unidad", "Cantidad"]]

    except Exception:
        return pd.DataFrame()
