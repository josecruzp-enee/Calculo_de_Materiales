# core/costos_mano_obra.py

import pandas as pd


def calcular_mo_desde_indice(
    *,
    archivo_materiales: str,
    conteo: dict
) -> pd.DataFrame:

    def _norm(s):
        return str(s).strip().upper()

    df_indice = pd.read_excel(archivo_materiales, sheet_name="indice")
    df_indice.columns = [str(c).strip() for c in df_indice.columns]

    if "Código de Estructura" not in df_indice.columns:
        raise ValueError("Falta 'Código de Estructura' en hoja indice")

    if "Precio" not in df_indice.columns:
        raise ValueError("Falta 'Precio' en hoja indice")

    if "Descripción" not in df_indice.columns:
        df_indice["Descripción"] = ""

    # 🔹 normalizar
    df_indice["cod_norm"] = df_indice["Código de Estructura"].map(_norm)

    precio_map = dict(
        zip(
            df_indice["cod_norm"],
            pd.to_numeric(df_indice["Precio"], errors="coerce").fillna(0.0)
        )
    )

    desc_map = dict(
        zip(
            df_indice["cod_norm"],
            df_indice["Descripción"].astype(str)
        )
    )

    filas = []

    for cod, qty in conteo.items():

        qty = int(qty or 0)
        if qty <= 0:
            continue

        cod_norm = _norm(cod)

        # 🔥 VALIDACIÓN FUERTE
        if cod_norm not in precio_map:
            raise ValueError(f"Estructura sin costo de MO: {cod}")

        mo_unit = float(precio_map[cod_norm])
        mo_total = mo_unit * qty

        filas.append({
            "codigodeestructura": cod_norm,
            "Descripcion": desc_map.get(cod_norm, ""),
            "Cantidad": qty,
            "MO Unitario": round(mo_unit, 2),
            "MO Total": round(mo_total, 2),
        })

    out = pd.DataFrame(filas)

    if out.empty:
        raise ValueError("No se generaron costos de mano de obra")

    return out.sort_values("codigodeestructura").reset_index(drop=True)
