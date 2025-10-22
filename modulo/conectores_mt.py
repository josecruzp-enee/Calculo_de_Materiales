# -*- coding: utf-8 -*-
import re
import pandas as pd

def cargar_conectores_mt(archivo_materiales):
    """Carga la hoja 'conectores' desde Estructura_datos.xlsx."""
    try:
        df = pd.read_excel(archivo_materiales, sheet_name='conectores')
        df.columns = [c.strip().capitalize() for c in df.columns]
        if 'Descripción' not in df.columns:
            for col in df.columns:
                if "desc" in col.lower():
                    df = df.rename(columns={col: "Descripción"})
        return df[["Calibre", "Código", "Descripción", "Estructuras aplicables"]]
    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Código", "Descripción", "Estructuras aplicables"])


def buscar_conector_mt(calibre, tabla_conectores: pd.DataFrame):
    """
    Busca conector simétrico (mismo calibre en ambos extremos).
    Ejemplo: (3/0-3/0), (1/0-1/0), (2-2)
    """
    if tabla_conectores.empty:
        return None

    calibre_norm = calibre.strip().upper()
    calibre_base = calibre_norm.replace(" ", "").replace("ASCR", "").replace("AAC", "").strip()

    # 🔍 Buscar coincidencia exacta tipo (3/0-3/0)
    patron = re.compile(rf"\(\s*{re.escape(calibre_base)}\s*-\s*{re.escape(calibre_base)}\s*\)", re.IGNORECASE)

    for _, fila in tabla_conectores.iterrows():
        desc = str(fila.get("Descripción", "")).upper().replace(" ", "")
        if patron.search(desc):
            return fila["Descripción"]

    return None


def aplicar_reemplazos_conectores(lista_materiales, calibre_primario, tabla_conectores: pd.DataFrame):
    """
    Reemplaza materiales tipo 'CONECTOR DE COMPRESIÓN' por el adecuado según calibre.
    """
    materiales_modificados = []
    for mat in lista_materiales:
        mat_str = str(mat).upper()
        if "CONECTOR" in mat_str and "COMPRESIÓN" in mat_str:
            nuevo_con = buscar_conector_mt(calibre_primario, tabla_conectores)
            if nuevo_con:
                materiales_modificados.append(nuevo_con)
                continue
        materiales_modificados.append(mat)
    return materiales_modificados
