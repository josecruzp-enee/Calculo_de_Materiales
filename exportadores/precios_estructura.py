# -*- coding: utf-8 -*-
import pandas as pd
import os

# =========================================================
# CONFIGURACIÓN
# =========================================================
BASE_DIR = os.path.dirname(__file__)
ARCHIVO = os.path.join(BASE_DIR, "..", "data", "Estructura_datos.xlsx")

CUADRILLA = 1250
FACTOR_TIEMPO = 0.25
FACTOR_EQUIPO = 0.20
FACTOR_UTILIDAD = 0.15


# =========================================================
# VALIDACIÓN ARCHIVO
# =========================================================
def validar_archivo(ruta):
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No existe el archivo: {ruta}")


# =========================================================
# CARGAR PRECIOS
# =========================================================
def cargar_precios(xls):

    import unicodedata

    def limpiar_texto(s):
        return ''.join(
            c for c in unicodedata.normalize('NFKD', str(s))
            if not unicodedata.combining(c)
        )

    df_precios = pd.read_excel(xls, sheet_name="Materiales")

    # 🔥 NORMALIZAR COLUMNAS (clave)
    df_precios.columns = [
        limpiar_texto(c).strip().upper()
        for c in df_precios.columns
    ]

    # 🔍 DEBUG opcional
    print("Columnas normalizadas:", df_precios.columns)

    # =========================
    # DETECTAR COLUMNAS
    # =========================
    col_codigo = None
    col_precio = None

    for c in df_precios.columns:
        if "CODIGO" in c:
            col_codigo = c
        if "COSTO" in c:
            col_precio = c

    if col_codigo is None:
        raise KeyError(f"No se encontró columna CODIGO: {df_precios.columns}")

    if col_precio is None:
        raise KeyError(f"No se encontró columna COSTO: {df_precios.columns}")

    # =========================
    # CREAR DICCIONARIO
    # =========================
    dict_precios = dict(
        zip(
            df_precios[col_codigo].astype(str).str.strip(),
            df_precios[col_precio]
        )
    )

    return dict_precios
# =========================================================
# CALCULAR MATERIAL POR ESTRUCTURA
# =========================================================
def calcular_material(df, dict_precios):

    total = 0

    for _, row in df.iterrows():

        codigo = str(row.get("COD. ENEE", "")).strip()

        if not codigo:
            continue

        cantidad = 0

        if "34.5" in df.columns:
            cantidad += row.get("34.5", 0)

        if "13.8" in df.columns:
            cantidad += row.get("13.8", 0)

        precio = dict_precios.get(codigo, 0)

        if precio == 0:
            print(f"⚠️ Material sin precio: {codigo}")

        total += cantidad * precio

    return total


# =========================================================
# MODELO DE COSTOS
# =========================================================
def calcular_costos(material):

    equipos = material * FACTOR_EQUIPO
    mano_obra = CUADRILLA * FACTOR_TIEMPO
    utilidad = (material + equipos + mano_obra) * FACTOR_UTILIDAD

    total = material + equipos + mano_obra + utilidad

    return equipos, mano_obra, utilidad, total


# =========================================================
# FUNCIÓN PRINCIPAL (REUTILIZABLE)
# =========================================================
def procesar_precios_estructura(ruta_archivo=None, exportar=False):

    if ruta_archivo is None:
        ruta_archivo = ARCHIVO

    validar_archivo(ruta_archivo)

    xls = pd.ExcelFile(ruta_archivo)
    dict_precios = cargar_precios(xls)

    resultados = []

    for hoja in xls.sheet_names:

        if hoja.lower() in ["materiales", "indice", "internos", "conectores"]:
            continue

        df = pd.read_excel(xls, sheet_name=hoja)

        if "COD. ENEE" not in df.columns:
            continue

        material_total = calcular_material(df, dict_precios)
        equipos, mo, utilidad, total = calcular_costos(material_total)

        resultados.append({
            "Estructura": hoja,
            "Material": round(material_total, 2),
            "Equipos": round(equipos, 2),
            "Mano de Obra": round(mo, 2),
            "Utilidad": round(utilidad, 2),
            "Precio Unitario": round(total, 2)
        })

    df_final = pd.DataFrame(resultados)
    df_final = df_final.sort_values("Estructura")

    if exportar:
        df_final.to_excel("precios_estructuras.xlsx", index=False)

    return df_final


# =========================================================
# GENERAR TABLA PARA PDF (CORREGIDO)
# =========================================================
def generar_tabla_presupuesto(doc, styles, df_estructuras, df_precios):

    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors

    elems = []

    if df_estructuras is None or df_estructuras.empty:
        elems.append(Paragraph("No hay datos de estructuras.", styles["BodyText"]))
        return elems

    # 🔥 MERGE (YA NO LEE EXCEL AQUÍ)
    df = df_estructuras.merge(df_precios, on="Estructura", how="left")

    df["Precio Unitario"] = df["Precio Unitario"].fillna(0)

    data = [
        ["ITEM", "DESCRIPCIÓN", "CANT", "P.U.", "TOTAL"]
    ]

    total_general = 0
    item = 1

    for _, row in df.iterrows():

        pu = row["Precio Unitario"]
        cant = row.get("Cantidad", 1)
        total = pu * cant

        total_general += total

        data.append([
            f"2.{item:02d}",
            f"Suministro e instalación de estructura {row['Estructura']}",
            cant,
            f"L {pu:,.2f}",
            f"L {total:,.2f}"
        ])

        item += 1

    data.append([
        "",
        "TOTAL GENERAL",
        "",
        "",
        f"L {total_general:,.2f}"
    ])

    tabla = Table(
        data,
        colWidths=[
            doc.width * 0.10,
            doc.width * 0.45,
            doc.width * 0.10,
            doc.width * 0.15,
            doc.width * 0.20,
        ]
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        ("GRID", (0,0), (-1,-1), 0.5, colors.black),

        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("ALIGN", (3,1), (-1,-1), "RIGHT"),
        ("ALIGN", (4,1), (-1,-1), "RIGHT"),

        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))

    elems.append(Paragraph("<b>2. COSTO DE ESTRUCTURAS</b>", styles["Heading2"]))
    elems.append(Spacer(1, 8))
    elems.append(tabla)

    return elems


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================
if __name__ == "__main__":

    df_precios = procesar_precios_estructura(exportar=True)

    print("\n✅ Precios de estructuras generados:\n")
    print(df_precios)
