# core/costos_mano_obra.py

import pandas as pd


def calcular_mo_desde_indice(
    *,
    archivo_materiales: str,   # Estructura_datos.xlsx
    conteo: dict
) -> pd.DataFrame:
    """
    Lee la hoja 'indice' y usa la columna 'Precio'
    como costo unitario de mano de obra.
    """

    df_indice = pd.read_excel(archivo_materiales, sheet_name="indice")
    df_indice.columns = [str(c).strip() for c in df_indice.columns]

    if "Código de Estructura" not in df_indice.columns:
        raise ValueError("No se encontró columna 'Código de Estructura' en hoja indice.")

    if "Precio" not in df_indice.columns:
        raise ValueError("No se encontró columna 'Precio' en hoja indice.")

    precio_map = dict(
        zip(
            df_indice["Código de Estructura"].astype(str).str.strip(),
            pd.to_numeric(df_indice["Precio"], errors="coerce").fillna(0.0)
        )
    )

    desc_map = dict(
        zip(
            df_indice["Código de Estructura"].astype(str).str.strip(),
            df_indice["Descripción"].astype(str)
        )
    )

    filas = []

    for cod, qty in conteo.items():
        qty = int(qty or 0)
        if qty <= 0:
            continue

        cod = str(cod).strip()

        mo_unit = float(precio_map.get(cod, 0.0))
        mo_total = mo_unit * qty

        filas.append({
            "codigodeestructura": cod,
            "Descripcion": desc_map.get(cod, ""),
            "Cantidad": qty,
            "MO Unitario": round(mo_unit, 2),
            "MO Total": round(mo_total, 2),
        })

    out = pd.DataFrame(filas)
    return out.sort_values("codigodeestructura").reset_index(drop=True)
