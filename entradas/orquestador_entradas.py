from entradas.lectores.leer_excel import leer_excel_estructuras
from entradas.normalizadores.normalizar_estructuras import normalizar_df_estructuras
from entradas.validadores.validar_estructuras import validar_df_estructuras
from entradas.contratos import EntradaEstructuras


def cargar_desde_excel(ruta: str) -> EntradaEstructuras:
    df = leer_excel_estructuras(ruta)
    df = normalizar_df_estructuras(df)
    validar_df_estructuras(df)

    return EntradaEstructuras(df=df, origen="excel")
