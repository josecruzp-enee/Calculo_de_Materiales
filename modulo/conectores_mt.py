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
        return df[['Calibre', 'Descripción']]
    except Exception as e:
        print(f"⚠️ No se pudo cargar hoja 'conectores': {e}")
        return pd.DataFrame(columns=["Calibre", "Descripción"])

def buscar_conector_mt(calibre, tabla_conectores: pd.DataFrame):
    calibre_num = ''.join(ch for ch in calibre if (ch.isdigit() or ch == '.'))
    patron = fr"\(\s*{re.escape(calibre_num)}\s*-\s*{re.escape(calibre_num)}\s*\)"
    df_filtrado = tabla_conectores[
        (tabla_conectores['Calibre'].astype(str).str.strip().str.upper() == calibre.strip().upper()) &
        (tabla_conectores['Descripción'].astype(str).str.contains(patron, case=False, regex=True))
    ]
    if not df_filtrado.empty:
        return df_filtrado.iloc[0]['Descripción'].strip()
    return None

def aplicar_reemplazos_conectores(lista_materiales, calibre_primario, tabla_conectores: pd.DataFrame):
    materiales_modificados = []
    for mat in lista_materiales:
        mat_str = str(mat).upper()
        if "CONECTOR" in mat_str and "COMPRESIÓN" in mat_str:
            nuevo_con = buscar_conector_mt(calibre_primario, tabla_conectores)
            if nuevo_con:
                materiales_modificados.append(nuevo_con)
                continue
        materiales_modificados.append(mat_str)
    return materiales_modificados
