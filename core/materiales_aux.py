import pandas as pd

def limpiar_codigo(codigo):
    if pd.isna(codigo) or str(codigo).strip() == "":
        return None, None
    codigo = str(codigo).strip()
    if codigo.isdigit():
        return None, "PUNTO"   # Solo referencia de agrupación
    if codigo.endswith(")") and "(" in codigo:
        base = codigo[:codigo.rfind("(")].strip()
        tipo = codigo[codigo.rfind("(")+1:codigo.rfind(")")].strip().upper()
        return base, tipo
    return codigo, "P"


def expandir_lista_codigos(cadena):
    if not cadena:
        return []
    return [parte.strip() for parte in str(cadena).split(",") if parte.strip()]
