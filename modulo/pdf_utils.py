# -*- coding: utf-8 -*-
"""
pdf_utils.py
Generación de informes PDF del cálculo de materiales y estructuras
Autor: José Nikol Cruz
"""

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from io import BytesIO
import os
import re
import pandas as pd
from reportlab.lib import colors

# --- Importación de tabla de cables ---
from modulo.configuracion_cables import tabla_cables_pdf

# ======== ESTILOS COMUNES ========
styles = getSampleStyleSheet()
styleN = ParagraphStyle(name="Normal9", parent=styles["Normal"], fontSize=9, leading=11)
styleH = styles["Heading1"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# === Fondo para todas las páginas ===
def fondo_pagina(canvas, doc):
    try:
        canvas.saveState()
        fondo = os.path.join(BASE_DIR, "data", "Imagen Encabezado.jpg")
        ancho, alto = letter
        if os.path.exists(fondo):
            canvas.drawImage(fondo, 0, 0, width=ancho, height=alto, mask="auto")
        canvas.restoreState()
    except Exception as e:
        print(f"⚠️ Error aplicando fondo: {e}")

# === Formateo de materiales ===
def formatear_material(nombre):
    texto = str(nombre).strip().title()
    texto = re.sub(r"\bN[º°]?\s*(\d+)", r"N°\1", texto, flags=re.IGNORECASE)
    texto = texto.replace(" X ", " x ")
    return texto

def hoja_info_proyecto(datos_proyecto, df_estructuras=None, df_mat=None):
    from math import sqrt

    # ===== FUNCIONES INTERNAS =====
    def float_safe(x, d=0.0):
        try:
            return float(x)
        except Exception:
            return d

    def formato_tension(vll):
        """Convierte 34.5 → '19.92 L-N / 34.5 L-L kV' """
        try:
            vll = float(vll)
            vln = round(vll / sqrt(3), 2)
            return f"{vln} L-N / {vll} L-L kV"
        except Exception:
            return str(vll)

    elems = []
    elems.append(Paragraph("<b>Hoja de Información del Proyecto</b>", styleH))
    elems.append(Spacer(1, 12))

    # ------------------------------------
    # ░ CAPTURA DE DATOS BASE
    # ------------------------------------
    descripcion_manual = datos_proyecto.get("descripcion_proyecto", "").strip()

    tension_valor = (
        datos_proyecto.get("nivel_de_tension")
        or datos_proyecto.get("tension")
        or ""
    )
    nivel_tension_fmt = formato_tension(tension_valor)

    cables = datos_proyecto.get("cables_proyecto", []) or []

    # Clasificación de cables
    primarios = [c for c in cables if str(c.get("Tipo", "")).upper() == "MT"]
    secundarios = [c for c in cables if str(c.get("Tipo", "")).upper() in ("BT", "HP", "N")]
    retenidas = [c for c in cables if str(c.get("Tipo", "")).upper() == "RETENIDA"]

    # ------------------------------------
    # ░ CONSTRUCCIÓN DE LISTA NUMERADA
    # ------------------------------------
    lineas = []

    # 1. POSTES
    if df_estructuras is not None and not df_estructuras.empty:
        postes = df_estructuras[
            df_estructuras["codigodeestructura"].str.contains("PC|PT", case=False, na=False)
        ]
        if not postes.empty:
            resumen = {}
            for _, r in postes.iterrows():
                cod = str(r["codigodeestructura"]).strip()
                cant = int(r["Cantidad"])
                resumen[cod] = resumen.get(cod, 0) + cant

            partes = []
            for cod, cant in resumen.items():
                # agregar apóstrofe a postes tipo PC-xx / PT-xx
                sufijo = "′" if cod.upper().startswith(("PC", "PT")) else ""
                partes.append(f"{cant} {cod}{sufijo}")

            total = sum(resumen.values())
            lineas.append(
                f"Hincado de {', '.join(partes)}, para un total de {total} poste(s)."
            )

    # 2. RED PRIMARIA (LP)
    for c in primarios:
        long_m = float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
        fase = str(c.get("Configuración", "")).strip()
        calibre = str(c.get("Calibre", "")).strip()
        if long_m > 0 and calibre:
            lineas.append(
                f"Construcción de {long_m:.0f} m de LP, {nivel_tension_fmt}, {fase}, conductor {calibre}."
            )

    # 3. RED SECUNDARIA (LS)
    for c in secundarios:
        long_m = float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
        fase = str(c.get("Configuración", "")).strip()
        calibre = str(c.get("Calibre", "")).strip()
        if long_m > 0 and calibre:
            lineas.append(
                f"Construcción de {long_m:.0f} m de LS, 120/240 V, {fase}, conductor {calibre}."
            )

    # 4. CABLE DE RETENIDAS (si quieres también se puede describir aquí)
    if retenidas:
        total_ret = 0.0
        calibres_ret = set()
        for c in retenidas:
            total_ret += float_safe(c.get("Total Cable (m)", c.get("Longitud (m)", 0)))
            calibres_ret.add(str(c.get("Calibre", "")).strip())
        if total_ret > 0:
            lineas.append(
                f"Instalación de {total_ret:.0f} m de cable de retenidas ({', '.join(sorted(calibres_ret))})."
            )

    # 5. TRANSFORMADORES
    if df_mat is not None and not df_mat.empty:
        transf = df_mat[df_mat["Materiales"].str.contains("Transformador", case=False, na=False)]
        if not transf.empty:
            total_t = transf["Cantidad"].sum()
            capacidades = ", ".join(sorted(set(
                transf["Materiales"].str.extract(r"(\d+\.?\d*)")[0].dropna().tolist()
            )))
            lineas.append(
                f"Instalación de {int(total_t)} transformador(es) de {capacidades} kVA."
            )

    # 6. LUMINARIAS
    if df_mat is not None and not df_mat.empty:
        lums = df_mat[df_mat["Materiales"].str.contains("Lámpara|Lampara|Alumbrado", case=False, na=False)]
        if not lums.empty:
            total_l = lums["Cantidad"].sum()
            lineas.append(f"Instalación de {int(total_l)} luminaria(s) de alumbrado público.")

    # ------------------------------------
    # ░ DESCRIPCIÓN FINAL → LISTA NUMERADA
    # ------------------------------------
    descripcion_lista = "<br/>".join([f"{i+1}. {l}" for i, l in enumerate(lineas)])

    # Si tienes una descripción manual, la ponemos primero
    bloques = []
    if descripcion_manual:
        bloques.append(descripcion_manual)
    if descripcion_lista:
        bloques.append("<b>Descripción general del Proyecto:</b><br/>" + descripcion_lista)

    descripcion_total = "<br/><br/>".join(bloques) if bloques else ""

    elems.append(
        Paragraph(f"<b>Descripción del Proyecto:</b><br/>{descripcion_total}", styleN)
    )
    elems.append(Spacer(1, 12))

    # ------------------------------------
    # ░ TABLA DE INFORMACIÓN
    # ------------------------------------
    calibre_primario = (
        datos_proyecto.get("calibre_primario")
        or datos_proyecto.get("calibre_mt")
        or ""
    )
    calibre_secundario = datos_proyecto.get("calibre_secundario", "")
    calibre_neutro = datos_proyecto.get("calibre_neutro", "")
    calibre_piloto = datos_proyecto.get("calibre_piloto", "")
    calibre_retenidas = datos_proyecto.get("calibre_retenidas", "")

    data = [
        ["Nombre del Proyecto:", datos_proyecto.get("nombre_proyecto", "")],
        ["Código / Expediente:", datos_proyecto.get("codigo_proyecto", "")],
        ["Nivel de Tensión (kV):", nivel_tension_fmt],
        ["Calibre Primario:", calibre_primario],
        ["Calibre Secundario:", calibre_secundario],
        ["Calibre Neutro:", calibre_neutro],
        ["Calibre Piloto:", calibre_piloto],
        ["Calibre Cable de Retenidas:", calibre_retenidas],
        ["Fecha de Informe:", datos_proyecto.get("fecha_informe", datetime.today().strftime("%Y-%m-%d"))],
        ["Responsable / Diseñador:", datos_proyecto.get("responsable", "N/A")],
        ["Empresa / Área:", datos_proyecto.get("empresa", "N/A")],
    ]

    table = Table(data, colWidths=[180, 300])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
    ]))

    elems.append(table)
    elems.append(Spacer(1, 24))
    elems.append(PageBreak())
    return elems






# === Generar PDF de materiales globales ===
def generar_pdf_materiales(df_mat, nombre_proy, datos_proyecto=None):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [Paragraph(f"<b>Resumen de Materiales - Proyecto: {nombre_proy}</b>", styles["Title"]),
             Spacer(1, 12)]

    df_agrupado = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
    data = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_agrupado.iterrows():
        data.append([Paragraph(formatear_material(row["Materiales"]), styleN),
                     str(row["Unidad"]), f"{row['Cantidad']:.2f}"])

    tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))
    elems.append(tabla)
    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# === Generar estructuras global ===
def generar_pdf_estructuras_global(df_estructuras, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [Paragraph(f"<b>Resumen de Estructuras - Proyecto: {nombre_proy}</b>", styles["Title"]),
             Spacer(1, 12)]
    data = [["Estructura", "Descripción", "Cantidad"]]
    for _, row in df_estructuras.iterrows():
        data.append([
            str(row.get("codigodeestructura", "")),
            str(row.get("Descripcion", "")),
            str(row.get("Cantidad", ""))
        ])
    tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke)
    ]))
    elems.append(tabla)
    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# === Generar estructuras por punto ===
def generar_pdf_estructuras_por_punto(df_por_punto, nombre_proy):
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = [
        Paragraph(f"<b>Estructuras por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    # Ordenar los puntos correctamente (numéricamente)
    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.sub(r'\D', '', str(x)) or 0))

    for p in puntos:
        # 🔹 Evitar duplicar la palabra "Punto" en el encabezado
        num = str(p).replace("Punto", "").strip()

        elems.append(Spacer(1, 6))  # pequeño espacio antes de cada punto
        elems.append(Paragraph(f"<b>Punto {num}</b>", styles["Heading2"]))

        df_p = df_por_punto[df_por_punto["Punto"] == p]
        data = [["Estructura", "Descripción", "Cantidad"]]

        for _, row in df_p.iterrows():
            data.append([
                str(row["codigodeestructura"]),
                str(row["Descripcion"]),
                str(row["Cantidad"])
            ])

        tabla = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
            ("ALIGN", (2,1), (2,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2*inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes



# === Materiales adicionales ===
def agregar_tabla_materiales_adicionales(elems, datos_proyecto):
    df_extra = datos_proyecto.get("materiales_extra")
    if df_extra is None or df_extra.empty:
        return elems
    elems.append(PageBreak())
    elems.append(Paragraph("<b>Materiales Adicionales</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))
    data_extra = [["Material", "Unidad", "Cantidad"]]
    for _, row in df_extra.iterrows():
        data_extra.append([row["Materiales"], row["Unidad"], f"{row['Cantidad']:.2f}"])
    tabla = Table(data_extra, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.orange),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke)
    ]))
    elems.append(tabla)
    return elems

# === Generar PDF de Materiales por Punto ===
def generar_pdf_materiales_por_punto(df_por_punto, nombre_proy):
    """Genera un PDF con materiales agrupados por punto."""
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="con_fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []
    elems.append(Paragraph(f"<b>Materiales por Punto - Proyecto: {nombre_proy}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    # Asegurar que los puntos estén ordenados correctamente
    puntos = sorted(df_por_punto["Punto"].unique(), key=lambda x: int(re.search(r'\d+', str(x)).group()))

    for p in puntos:
        elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading2"]))
        df_p = df_por_punto[df_por_punto["Punto"] == p]
        df_agrupado = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()

        data = [["Material", "Unidad", "Cantidad"]]
        for _, row in df_agrupado.iterrows():
            data.append([
                Paragraph(formatear_material(row["Materiales"]), styleN),
                str(row["Unidad"]),
                f"{round(row['Cantidad'], 2):.2f}"
            ])

        tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
        tabla.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.darkgreen),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
        ]))

        elems.append(tabla)
        elems.append(Spacer(1, 0.2*inch))

    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# === PDF completo consolidado ===
def generar_pdf_completo(df_mat, df_estructuras, df_estructuras_por_punto, df_mat_por_punto, datos_proyecto):
    """
    Genera un PDF completo consolidado con:
    - Hoja de información del proyecto
    - Resumen de materiales global (incluye cables)
    - Materiales adicionales
    - Tabla de cables
    - Resumen de estructuras global
    - Estructuras por punto
    - Materiales por punto
    """
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id="fondo", frames=[frame], onPage=fondo_pagina)
    doc.addPageTemplates([template])

    elems = []

    # === Hoja de información del proyecto ===
    elems += hoja_info_proyecto(datos_proyecto, df_estructuras, df_mat)

    # === Resumen global de materiales ===
    elems.append(Paragraph("<b>Resumen de Materiales</b>", styles["Heading2"]))

    df_agr = df_mat.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum() if not df_mat.empty else pd.DataFrame(columns=["Materiales", "Unidad", "Cantidad"])

    # === Agregar los cables del proyecto al resumen de materiales ===
    if "cables_proyecto" in datos_proyecto and datos_proyecto["cables_proyecto"]:
        for cable in datos_proyecto["cables_proyecto"]:
            tipo = cable.get("Tipo", "")
            calibre = cable.get("Calibre", "")
            longitud = cable.get("Total Cable (m)", cable.get("Longitud (m)", 0))
            if longitud and calibre:
                descripcion = f"Cable {tipo} {calibre}"
                df_agr.loc[len(df_agr)] = [descripcion, "m", float(longitud)]

    # === Tabla de resumen de materiales ===
    data = [["Material", "Unidad", "Cantidad"]]
    for _, r in df_agr.iterrows():
        data.append([Paragraph(formatear_material(r["Materiales"]), styleN),
                     r["Unidad"],
                     f"{r['Cantidad']:.2f}"])

    tabla = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))
    elems.append(tabla)
    elems.append(PageBreak())

    # === Materiales adicionales ===
    elems = agregar_tabla_materiales_adicionales(elems, datos_proyecto)

    # === Tabla de cables ===
    from modulo.configuracion_cables import tabla_cables_pdf
    elems.extend(tabla_cables_pdf(datos_proyecto))

    # === Resumen de estructuras global ===
    if not df_estructuras.empty:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>Resumen de Estructuras</b>", styles["Heading2"]))
        data_estruct = [["Estructura", "Descripción", "Cantidad"]]
        for _, row in df_estructuras.iterrows():
            data_estruct.append([
                str(row.get("codigodeestructura", "")),
                str(row.get("Descripcion", "")),
                str(row.get("Cantidad", ""))
            ])
        tabla_estruct = Table(data_estruct, colWidths=[1.5*inch, 4*inch, 1*inch])
        tabla_estruct.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (2,1), (2,-1), "CENTER")
        ]))
        elems.append(tabla_estruct)

    # === Estructuras por punto ===
    if not df_estructuras_por_punto.empty:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>Estructuras por Punto</b>", styles["Heading2"]))
        for p in sorted(df_estructuras_por_punto["Punto"].unique(),
                        key=lambda x: int(re.sub(r'\D', '', str(x)) or 0)):
            elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))
            df_p = df_estructuras_por_punto[df_estructuras_por_punto["Punto"] == p]
            data = [["Estructura", "Descripción", "Cantidad"]]
            for _, row in df_p.iterrows():
                data.append([
                    str(row["codigodeestructura"]),
                    str(row["Descripcion"]),
                    str(row["Cantidad"])
                ])
            tabla_p = Table(data, colWidths=[1.5*inch, 4*inch, 1*inch])
            tabla_p.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
                ("ALIGN", (2,1), (2,-1), "CENTER")
            ]))
            elems.append(tabla_p)
            elems.append(Spacer(1, 0.2*inch))

    # === Materiales por punto ===
    if not df_mat_por_punto.empty:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>Materiales por Punto</b>", styles["Heading2"]))
        puntos = sorted(df_mat_por_punto["Punto"].unique(),
                        key=lambda x: int(re.search(r'\d+', str(x)).group()))
        for p in puntos:
            elems.append(Paragraph(f"<b>Punto {p}</b>", styles["Heading3"]))
            df_p = df_mat_por_punto[df_mat_por_punto["Punto"] == p]
            df_agr_p = df_p.groupby(["Materiales", "Unidad"], as_index=False)["Cantidad"].sum()
            data = [["Material", "Unidad", "Cantidad"]]
            for _, r in df_agr_p.iterrows():
                data.append([
                    Paragraph(formatear_material(r["Materiales"]), styleN),
                    str(r["Unidad"]),
                    f"{r['Cantidad']:.2f}"
                ])
            tabla_m = Table(data, colWidths=[4*inch, 1*inch, 1*inch])
            tabla_m.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.darkgreen),
                ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
                ("ALIGN", (1,1), (-1,-1), "CENTER")
            ]))
            elems.append(tabla_m)
            elems.append(Spacer(1, 0.2*inch))

    # === Construcción final del PDF ===
    doc.build(elems)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes





