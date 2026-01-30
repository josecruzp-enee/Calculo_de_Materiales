import pandas as pd
import tempfile
import os
from io import BytesIO

def guardar_archivo_temporal(archivo_subido):
    temp_dir = tempfile.mkdtemp()
    ruta_temp = os.path.join(temp_dir, archivo_subido.name)
    with open(ruta_temp, "wb") as f:
        f.write(archivo_subido.getbuffer())
    return ruta_temp

def pegar_texto_a_df(texto, columnas):
    try:
        df = pd.read_csv(BytesIO(texto.encode()), sep=None, engine='python')
        df = df[[col for col in columnas if col in df.columns]]
        return df
    except Exception as e:
        print(f"Error al convertir texto pegado a tabla: {e}")
        return pd.DataFrame(columns=columnas)
