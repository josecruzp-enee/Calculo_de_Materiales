from costos.costos_operativos import calcular_costos_operativos
from costos.precios_venta import calcular_precio_venta


def calcular_costos_por_estructura(
    *,
    archivo_materiales: str,
    conteo: Dict[str, int],
    tension_ll: float,
    calibre_mt: str,
    tabla_conectores_mt: pd.DataFrame,
    df_indice: Optional[pd.DataFrame] = None,

    # 🔥 NUEVOS PARÁMETROS
    costo_cuadrilla_dia: float = 1250,
    fraccion_jornada: float = 1/16,
    costo_equipos: float = 0.0,
    costo_logistica: float = 0.0,
    margen_utilidad: float = 0.15,
) -> pd.DataFrame:

    filas = []

    for cod, qty in conteo.items():

        cod = str(cod).strip()

        try:
            qty = int(qty or 0)
        except Exception:
            qty = 0

        if not cod or qty <= 0:
            continue

        # -------------------------------------------------
        # 1) MATERIALES UNITARIOS
        # -------------------------------------------------
        df_mat = calcular_materiales_estructura(
            archivo_materiales,
            cod,
            1,
            tension_ll,
            calibre_mt,
            tabla_conectores_mt,
        )

        if df_mat is None or df_mat.empty:
            costo_material = 0.0
        else:
            df_val = calcular_costos_desde_resumen(
                df_mat[["Materiales", "Unidad", "Cantidad"]],
                archivo_materiales
            )

            costo_material = float(
                pd.to_numeric(df_val["Costo"], errors="coerce")
                .fillna(0.0)
                .sum()
            )

        # -------------------------------------------------
        # 2) COSTOS OPERATIVOS (por estructura)
        # -------------------------------------------------
        costos_op = calcular_costos_operativos(
            costo_cuadrilla_dia=costo_cuadrilla_dia,
            fraccion_jornada=fraccion_jornada,
            costo_equipos=costo_equipos,
            costo_logistica=costo_logistica,
        )

        costo_operativo = costos_op["operativo_total"]

        # -------------------------------------------------
        # 3) COSTO TOTAL
        # -------------------------------------------------
        costo_total = costo_material + costo_operativo

        # -------------------------------------------------
        # 4) PRECIO DE VENTA
        # -------------------------------------------------
        venta = calcular_precio_venta(
            costo_total=costo_total,
            margen_utilidad=margen_utilidad
        )

        precio_unitario = venta["precio_venta"]

        # -------------------------------------------------
        # RESULTADO
        # -------------------------------------------------
        filas.append({
            "codigodeestructura": cod,
            "Cantidad": qty,
            "Costo Material": round(costo_material, 2),
            "Costo Operativo": round(costo_operativo, 2),
            "Costo Unitario": round(costo_total, 2),
            "Precio Unitario": round(precio_unitario, 2),
            "Total": round(precio_unitario * qty, 2),
        })

    if not filas:
        return pd.DataFrame()

    return pd.DataFrame(filas).sort_values("codigodeestructura").reset_index(drop=True)
