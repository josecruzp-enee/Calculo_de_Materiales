import pandas as pd
import re
from entradas.excel_legacy import cargar_materiales


def leer_hoja_materiales(archivo, hoja, tension):
    """
    Lee una hoja de estructura y devuelve dataframe limpio con:
    Materiales | Unidad | Cantidad
    """

    try:
        # -------------------------
        # 1. Detectar encabezado
        # -------------------------
        df_temp = cargar_materiales(archivo, hoja, header=None)

        fila_encabezado = None
        for i, row in df_temp.iterrows():
            if row.astype(str).str.contains(r"\bMaterial", case=False, na=False).any():
                fila_encabezado = i
                break

        if fila_encabezado is None:
            return None

        # -------------------------
        # 2. Leer tabla real
        # -------------------------
        df = cargar_materiales(archivo, hoja, header=fila_encabezado)
        df.columns = df.columns.map(str).str.strip()

        if "Materiales" not in df.columns:
            return None

        if "Unidad" not in df.columns:
            df["Unidad"] = ""

        # -------------------------
        # 3. Encontrar columna tensión
        # -------------------------
        col_tension = None
        t_str = str(tension)

        for c in df.columns:
            if t_str in str(c):
                col_tension = c
                break

        if not col_tension:
            return None

        # -------------------------
        # 4. Filtrar
        # -------------------------
        df[col_tension] = pd.to_numeric(df[col_tension], errors="coerce").fillna(0)

        df_out = df[df[col_tension] > 0][["Materiales", "Unidad", col_tension]].copy()
        df_out.rename(columns={col_tension: "Cantidad"}, inplace=True)

        return df_out

    except Exception:
        return None
