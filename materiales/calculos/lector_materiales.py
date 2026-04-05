import pandas as pd
import re
from entradas.excel_legacy import cargar_materiales


def leer_hoja_materiales(df, tension):

    try:
        df = df.copy()
        df.columns = df.columns.map(str).str.strip()

        if "Materiales" not in df.columns:
            return None

        if "Unidad" not in df.columns:
            df["Unidad"] = ""

        col_tension = None
        t_str = str(tension)

        for c in df.columns:
            if t_str in str(c):
                col_tension = c
                break

        if not col_tension:
            return None

        df[col_tension] = pd.to_numeric(df[col_tension], errors="coerce").fillna(0)

        df_out = df[df[col_tension] > 0][["Materiales", "Unidad", col_tension]].copy()
        df_out.rename(columns={col_tension: "Cantidad"}, inplace=True)

        return df_out

    except Exception:
        return None
