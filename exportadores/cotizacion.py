# -*- coding: utf-8 -*-
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
import pandas as pd


# =========================================================
# HELPERS
# =========================================================
def _fmt(valor: float) -> str:
    return f"L {valor:,.2f}"


def _validar_costos(costos: dict) -> pd.DataFrame:

    if not isinstance(costos, dict):
        raise ValueError("costos inválido")

    if not costos.get("ok"):
        raise ValueError("costos no ejecutado correctamente")

    df = costos.get("df_costos_por_punto")

    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("df_costos_por_punto inválido")

    if df.empty:
        raise ValueError("df_costos_por_punto vacío")

    # 🔥 VALIDACIÓN DE CONTRATO
    required_cols = [
        "Punto",
        "Estructura",
        "Cantidad",
        "Precio Unitario",
        "Subtotal Precio",
    ]

    faltantes = [c for c in required_cols if c not in df.columns]
    if faltantes:
        raise ValueError(f"df_costos_por_punto no cumple contrato: {faltantes}")

    return df.copy()


# =========================================================
# RENDER PRESUPUESTO
# =========================================================
def generar_seccion_presupuesto(doc, styles, costos):

    elems = [PageBreak()]

    # =====================================================
    # VALIDACIÓN DOMINIO
    # =====================================================
    df = _validar_costos(costos)

    # =====================================================
    # TÍTULO
    # =====================================================
    elems.append(Paragraph("<b>9. PRESUPUESTO DETALLADO</b>", styles["Heading1"]))
    elems.append(Spacer(1, 10))

    elems.append(Paragraph(
        "A continuación se presenta el presupuesto correspondiente al suministro e instalación "
        "de las estructuras del proyecto.",
        styles["BodyText"]
    ))
    elems.append(Spacer(1, 12))

    # =====================================================
    # NORMALIZACIÓN SEGURA
    # =====================================================
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce")
    df["Precio Unitario"] = pd.to_numeric(df["Precio Unitario"], errors="coerce")
    df["Subtotal Precio"] = pd.to_numeric(df["Subtotal Precio"], errors="coerce")

    if df[["Cantidad", "Precio Unitario", "Subtotal Precio"]].isna().any().any():
        raise ValueError("Datos numéricos inválidos en df_costos_por_punto")

    df = df.sort_values(by=["Punto", "Estructura"]).reset_index(drop=True)

    # =====================================================
    # TABLA
    # =====================================================
    data = [["ITEM", "DESCRIPCIÓN", "CANT", "P.U.", "TOTAL"]]

    total_general = float(df["Subtotal Precio"].sum())
    item = 1

    for _, r in df.iterrows():

        estructura = r["Estructura"]
        cant = int(r["Cantidad"])
        pu = float(r["Precio Unitario"])
        total = float(r["Subtotal Precio"])

        descripcion = f"Suministro e instalación de estructura tipo {estructura}"

        data.append([
            f"9.{item:02d}",
            descripcion,
            f"{cant}",
            _fmt(pu),
            _fmt(total),
        ])

        item += 1

    # TOTAL
    data.append(["", "TOTAL GENERAL", "", "", _fmt(total_general)])

    # =====================================================
    # TABLA
    # =====================================================
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
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        ("ALIGN", (2, 1), (2, -2), "CENTER"),
        ("ALIGN", (3, 1), (4, -2), "RIGHT"),

        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFEFEF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    elems.append(tabla)
    elems.append(Spacer(1, 12))

    # =====================================================
    # NOTA
    # =====================================================
    elems.append(
        Paragraph(
            "<font size=8><i>"
            "Nota: Este presupuesto incluye suministro de materiales, costos operativos y utilidad."
            "</i></font>",
            styles["Normal"]
        )
    )

    return elems
