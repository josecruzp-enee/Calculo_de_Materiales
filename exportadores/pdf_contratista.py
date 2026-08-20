# -*- coding: utf-8 -*-
from __future__ import annotations

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    PageBreak,
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from io import BytesIO

import pandas as pd
import streamlit as st


from materiales.calculos.calculo_estructuras import (
    calcular_estructuras_por_punto
)

from costos_precios.mano_obra_por_punto import (
    calcular_mano_obra_proyecto
)

from exportadores.pdf_base import fondo_pagina


# ======================================================
# ACTIVAR / DESACTIVAR DESMONTAJES
# ======================================================
#
# True  = mostrar desmontajes
# False = NO mostrar desmontajes
#
# PARA OTRO PROYECTO:
# INCLUIR_DESMONTAJES = False
#
# ======================================================

INCLUIR_DESMONTAJES = True


# ======================================================
# DESMONTAJES GLOBALES DEL PROYECTO
# ======================================================

DESMONTAJES = {

    "A-III-1": {
        "cantidad": 13,
        "precio": 2000,
    },

    "A-III-2": {
        "cantidad": 2,
        "precio": 2500,
    },

    "A-III-4": {
        "cantidad": 1,
        "precio": 3000,
    },

    "A-III-5": {
        "cantidad": 4,
        "precio": 3000,
    },

    "A-III-6": {
        "cantidad": 1,
        "precio": 3500,
    },

    "A-I-4": {
        "cantidad": 3,
        "precio": 1500,
    },

    "A-I-1": {
        "cantidad": 3,
        "precio": 1200,
    },
}


# ======================================================
# DESMONTAJE DE CONDUCTORES
# SIN CONSIDERAR NEUTRO
# ======================================================

DESMONTAJE_LINEA = [

    {
        "descripcion": "Línea primaria 3F",
        "longitud": 417,
        "conductores": 3,
        "precio_m": 40,
    },

    {
        "descripcion": "Línea primaria 2F",
        "longitud": 236,
        "conductores": 2,
        "precio_m": 40,
    },

    {
        "descripcion": "Línea primaria 1F",
        "longitud": 149,
        "conductores": 1,
        "precio_m": 40,
    },
]


# ======================================================
# DESMONTAJES POR PUNTO
# ======================================================
#
# Esto solamente afecta el DETALLE POR PUNTO.
#
# El resumen global se controla arriba con DESMONTAJES.
#
# ======================================================

DESMONTAJES_POR_PUNTO = {

    "P-18": [
        {
            "estructura": "A-III-4",
            "cantidad": 1,
            "precio": 3000,
        },
    ],

    "P-19": [
        {
            "estructura": "A-III-5",
            "cantidad": 1,
            "precio": 3000,
        },
    ],

    "P-20": [
        {
            "estructura": "A-III-2",
            "cantidad": 1,
            "precio": 2500,
        },
    ],

    "P-22": [
        {
            "estructura": "A-III-2",
            "cantidad": 1,
            "precio": 2500,
        },
    ],

    "P-23": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-24": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-25": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-26": [
        {
            "estructura": "A-III-5",
            "cantidad": 1,
            "precio": 3000,
        },
    ],

    "P-27": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-28": [
        {
            "estructura": "A-III-6",
            "cantidad": 1,
            "precio": 3500,
        },
    ],

    "P-29": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-30": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-31": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-32": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
        {
            "estructura": "A-I-4",
            "cantidad": 1,
            "precio": 1500,
        },
    ],

    "P-33": [
        {
            "estructura": "A-III-5",
            "cantidad": 1,
            "precio": 3000,
        },
    ],

    "P-34": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-35": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-36": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-37": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-38": [
        {
            "estructura": "A-III-5",
            "cantidad": 1,
            "precio": 3000,
        },
    ],

    "P-39": [
        {
            "estructura": "A-III-1",
            "cantidad": 1,
            "precio": 2000,
        },
    ],

    "P-50": [
        {
            "estructura": "A-I-4",
            "cantidad": 1,
            "precio": 1500,
        },
    ],

    "P-51": [
        {
            "estructura": "A-I-4",
            "cantidad": 1,
            "precio": 1500,
        },
        {
            "estructura": "A-I-1",
            "cantidad": 1,
            "precio": 1200,
        },
    ],

    "P-52": [
        {
            "estructura": "A-I-1",
            "cantidad": 1,
            "precio": 1200,
        },
    ],

    "P-53": [
        {
            "estructura": "A-I-1",
            "cantidad": 1,
            "precio": 1200,
        },
    ],
}


# ======================================================
# ESTILO TABLA
# ======================================================

def estilo_tabla():

    return [

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#1F3A5F"),
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white,
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold",
        ),

        (
            "ALIGN",
            (0, 0),
            (-1, 0),
            "CENTER",
        ),

        (
            "ALIGN",
            (1, 1),
            (-1, -1),
            "RIGHT",
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey,
        ),
    ]


# ======================================================
# TABLA GENERAL C1
# ======================================================

def tabla_presupuesto_general(df_detalle):

    df = (
        df_detalle
        .groupby(
            "Estructura",
            as_index=False
        )
        .agg({
            "Cantidad": "sum",
            "Precio": "first",
            "Subtotal": "sum",
        })
    )

    data = [
        [
            "DESCRIPCIÓN",
            "P.U.",
            "CANT",
            "TOTAL",
        ]
    ]

    total_general = float(
        df_detalle["Subtotal"].sum()
    )

    for _, r in df.iterrows():

        data.append([
            f"Instalación de {r['Estructura']}",
            f"L {r['Precio']:,.2f}",
            int(r["Cantidad"]),
            f"L {r['Subtotal']:,.2f}",
        ])

    if st.session_state.get(
        "incluir_logistica",
        True
    ):

        horas = st.session_state.get(
            "horas_grua",
            12
        )

        precio = st.session_state.get(
            "precio_hora_grua",
            1700
        )

        flete = st.session_state.get(
            "costo_flete",
            25000
        )

        viajes = st.session_state.get(
            "viajes_flete",
            1
        )

        ingenieria = st.session_state.get(
            "ingenieria",
            25000
        )

        total_grua = horas * precio
        total_flete = flete * viajes

        data.append([
            "Equipo Grúa",
            f"L {precio:,.2f}",
            horas,
            f"L {total_grua:,.2f}",
        ])

        data.append([
            "Flete",
            f"L {flete:,.2f}",
            viajes,
            f"L {total_flete:,.2f}",
        ])

        data.append([
            "Ingeniería",
            "",
            1,
            f"L {ingenieria:,.2f}",
        ])

        total_general += (
            total_grua
            + total_flete
            + ingenieria
        )

    data.append([
        "",
        "",
        "TOTAL GENERAL",
        f"L {total_general:,.2f}",
    ])

    tabla = Table(
        data,
        colWidths=[
            320,
            80,
            60,
            90,
        ]
    )

    tabla.setStyle(
        estilo_tabla()
    )

    return tabla


# ======================================================
# TABLA BASE C2
# ======================================================

def tabla_presupuesto(df_detalle):

    # ==================================================
    # EXCLUIR DESMONTAJES GENERADOS POR OTROS MÓDULOS
    # ==================================================

    df_base = df_detalle[
        ~df_detalle["Estructura"]
        .astype(str)
        .str.upper()
        .str.startswith("DESMONTAJE")
    ].copy()

    df = (
        df_base
        .groupby(
            "Estructura",
            as_index=False
        )
        .agg({
            "Cantidad": "sum",
            "Precio": "first",
            "Subtotal": "sum",
        })
    )

    data = [
        [
            "DESCRIPCIÓN",
            "P.U.",
            "CANT",
            "TOTAL",
        ]
    ]

    total = 0.0

    for _, r in df.iterrows():

        data.append([
            f"Instalación de {r['Estructura']}",
            f"L {r['Precio']:,.2f}",
            int(r["Cantidad"]),
            f"L {r['Subtotal']:,.2f}",
        ])

        total += float(
            r["Subtotal"]
        )

    data.append([
        "",
        "",
        "TOTAL",
        f"L {total:,.2f}",
    ])

    tabla = Table(
        data,
        colWidths=[
            320,
            80,
            60,
            90,
        ]
    )

    tabla.setStyle(
        estilo_tabla()
    )

    return tabla


# ======================================================
# TABLA GLOBAL DE DESMONTAJES
# ======================================================

def tabla_desmontajes():

    data = [
        [
            "DESCRIPCIÓN",
            "P.U.",
            "CANT",
            "TOTAL",
        ]
    ]

    total_general = 0.0

    # ==================================================
    # ESTRUCTURAS
    # ==================================================

    for estructura, datos in DESMONTAJES.items():

        cantidad = float(
            datos["cantidad"]
        )

        precio = float(
            datos["precio"]
        )

        subtotal = (
            cantidad
            * precio
        )

        data.append([
            f"Desmontaje de {estructura}",
            f"L {precio:,.2f}",
            int(cantidad),
            f"L {subtotal:,.2f}",
        ])

        total_general += subtotal

    # ==================================================
    # CONDUCTORES
    # SIN NEUTRO
    # ==================================================

    for tramo in DESMONTAJE_LINEA:

        longitud = float(
            tramo["longitud"]
        )

        conductores = float(
            tramo["conductores"]
        )

        precio_m = float(
            tramo["precio_m"]
        )

        metros_conductor = (
            longitud
            * conductores
        )

        subtotal = (
            metros_conductor
            * precio_m
        )

        data.append([
            f"Desmontaje de {tramo['descripcion']}",
            f"L {precio_m:,.2f}/m",
            f"{int(metros_conductor)} m",
            f"L {subtotal:,.2f}",
        ])

        total_general += subtotal

    data.append([
        "",
        "",
        "TOTAL",
        f"L {total_general:,.2f}",
    ])

    tabla = Table(
        data,
        colWidths=[
            320,
            80,
            60,
            90,
        ]
    )

    tabla.setStyle(
        estilo_tabla()
    )

    return tabla


# ======================================================
# TABLA LOGÍSTICA
# ======================================================

def tabla_logistica():

    if not st.session_state.get(
        "incluir_logistica",
        True
    ):
        return None

    horas = st.session_state.get(
        "horas_grua",
        12
    )

    precio = st.session_state.get(
        "precio_hora_grua",
        1700
    )

    flete = st.session_state.get(
        "costo_flete",
        25000
    )

    viajes = st.session_state.get(
        "viajes_flete",
        1
    )

    ingenieria = st.session_state.get(
        "ingenieria",
        25000
    )

    total_grua = (
        horas
        * precio
    )

    total_flete = (
        flete
        * viajes
    )

    data = [

        [
            "DESCRIPCIÓN",
            "P.U.",
            "CANT",
            "TOTAL",
        ],

        [
            "Equipo Grúa",
            f"L {precio:,.2f}",
            horas,
            f"L {total_grua:,.2f}",
        ],

        [
            "Flete",
            f"L {flete:,.2f}",
            viajes,
            f"L {total_flete:,.2f}",
        ],

        [
            "Ingeniería",
            "",
            1,
            f"L {ingenieria:,.2f}",
        ],
    ]

    tabla = Table(
        data,
        colWidths=[
            320,
            80,
            60,
            90,
        ]
    )

    tabla.setStyle(
        estilo_tabla()
    )

    return tabla


# ======================================================
# ORDEN NUMÉRICO DE PUNTOS
# ======================================================

def _ordenar_punto(punto):

    try:

        texto = (
            str(punto)
            .upper()
            .strip()
            .replace("P-", "")
            .replace("P", "")
        )

        return int(texto)

    except Exception:

        return 999999


# ======================================================
# DETALLE POR PUNTO
# INSTALACIÓN + DESMONTAJE
# ======================================================

def tabla_detalle_por_punto(df_detalle):

    # ==================================================
    # QUITAR POSIBLES DESMONTAJES YA INYECTADOS
    # ==================================================

    df_base = df_detalle[
        ~df_detalle["Estructura"]
        .astype(str)
        .str.upper()
        .str.startswith("DESMONTAJE")
    ].copy()

    data = [
        [
            "Punto",
            "Descripción",
            "P.U.",
            "Cant",
            "Subtotal",
        ]
    ]

    # ==================================================
    # PUNTOS CON INSTALACIÓN
    # ==================================================

    puntos_instalacion = set(
        df_base["Punto"]
        .dropna()
        .astype(str)
        .unique()
    )

    # ==================================================
    # PUNTOS CON DESMONTAJE
    # ==================================================

    if INCLUIR_DESMONTAJES:

        puntos_desmontaje = set(
            DESMONTAJES_POR_PUNTO.keys()
        )

    else:

        puntos_desmontaje = set()

    # ==================================================
    # UNIR TODOS LOS PUNTOS
    # ==================================================

    todos_los_puntos = (
        puntos_instalacion
        | puntos_desmontaje
    )

    todos_los_puntos = sorted(
        todos_los_puntos,
        key=_ordenar_punto,
    )

    # ==================================================
    # RECORRER PUNTOS
    # ==================================================

    for punto in todos_los_puntos:

        data.append([
            punto,
            "",
            "",
            "",
            "",
        ])

        subtotal_punto = 0.0

        # ==================================================
        # INSTALACIONES
        # ==================================================

        grupo = df_base[
            df_base["Punto"]
            .astype(str)
            == str(punto)
        ]

        for _, r in grupo.iterrows():

            cantidad = float(
                r["Cantidad"]
            )

            precio = float(
                r["Precio"]
            )

            subtotal = float(
                r["Subtotal"]
            )

            cantidad_txt = (
                str(int(cantidad))
                if cantidad.is_integer()
                else f"{cantidad:.2f}"
            )

            data.append([
                "",
                f"Instalación de {r['Estructura']}",
                f"L {precio:,.2f}",
                cantidad_txt,
                f"L {subtotal:,.2f}",
            ])

            subtotal_punto += subtotal

        # ==================================================
        # DESMONTAJES
        # ==================================================

        if INCLUIR_DESMONTAJES:

            desmontajes_punto = (
                DESMONTAJES_POR_PUNTO.get(
                    punto,
                    []
                )
            )

        else:

            desmontajes_punto = []

        for item in desmontajes_punto:

            estructura = str(
                item["estructura"]
            )

            cantidad = float(
                item.get(
                    "cantidad",
                    1
                )
            )

            precio = float(
                item.get(
                    "precio",
                    0
                )
            )

            subtotal = (
                cantidad
                * precio
            )

            cantidad_txt = (
                str(int(cantidad))
                if cantidad.is_integer()
                else f"{cantidad:.2f}"
            )

            data.append([
                "",
                f"Desmontaje de {estructura}",
                f"L {precio:,.2f}",
                cantidad_txt,
                f"L {subtotal:,.2f}",
            ])

            subtotal_punto += subtotal

        # ==================================================
        # SUBTOTAL PUNTO
        # ==================================================

        data.append([
            "",
            "",
            "",
            "Subtotal",
            f"L {subtotal_punto:,.2f}",
        ])

    tabla = Table(
        data,
        colWidths=[
            60,
            210,
            70,
            50,
            90,
        ],
        repeatRows=1,
    )

    tabla.setStyle(
        estilo_tabla()
    )

    return tabla


# ======================================================
# GENERADOR PDF
# ======================================================

def generar_pdf_contratista(entrada):

    contratista = st.session_state.get(
        "contratista",
        "C1"
    )

    # ==================================================
    # EXTRAER DATA
    # ==================================================

    if isinstance(
        entrada,
        pd.DataFrame
    ):

        df_estructuras = entrada
        df_cables = None

    else:

        df_estructuras = getattr(
            entrada,
            "df_estructuras",
            None
        )

        df_cables = getattr(
            entrada,
            "df_cables",
            None
        )

    if df_estructuras is None:

        raise ValueError(
            "No hay estructuras"
        )

    # ==================================================
    # CALCULAR PUNTOS
    # ==================================================

    df_puntos = calcular_estructuras_por_punto(
        df_estructuras
    )

    resultado = calcular_mano_obra_proyecto(
        df_puntos,
        df_cables,
        contratista=contratista
    )

    df_detalle = resultado[
        "df_detalle"
    ]

    # ==================================================
    # PDF
    # ==================================================

    buffer = BytesIO()

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(

        buffer,

        topMargin=90,
        bottomMargin=40,
        leftMargin=40,
        rightMargin=40,
    )

    elementos = []

    # ==================================================
    # TABLAS PRINCIPALES
    # ==================================================

    if contratista == "C1":

        elementos.append(
            Paragraph(
                "CUADRO GENERAL DE PRECIOS",
                styles["Title"]
            )
        )

        elementos.append(
            Spacer(
                1,
                12
            )
        )

        elementos.append(
            tabla_presupuesto_general(
                df_detalle
            )
        )

        elementos.append(
            PageBreak()
        )

    else:

        # ==================================================
        # ESTRUCTURAS Y CONDUCTORES
        # ==================================================

        elementos.append(
            Paragraph(
                "ESTRUCTURAS Y CONDUCTORES",
                styles["Title"]
            )
        )

        elementos.append(
            tabla_presupuesto(
                df_detalle
            )
        )

        elementos.append(
            PageBreak()
        )

        # ==================================================
        # LOGÍSTICA
        # ==================================================

        tabla_log = (
            tabla_logistica()
        )

        if tabla_log:

            elementos.append(
                Paragraph(
                    "LOGÍSTICA",
                    styles["Title"]
                )
            )

            elementos.append(
                Spacer(
                    1,
                    12
                )
            )

            elementos.append(
                tabla_log
            )

            elementos.append(
                PageBreak()
            )

    # ==================================================
    # DESMONTAJES
    # ==================================================

    if (
        INCLUIR_DESMONTAJES
        and DESMONTAJES
    ):

        elementos.append(
            Paragraph(
                "DESMONTAJE DE RED",
                styles["Title"]
            )
        )

        elementos.append(
            Spacer(
                1,
                12
            )
        )

        elementos.append(
            tabla_desmontajes()
        )

        elementos.append(
            PageBreak()
        )

    # ==================================================
    # DETALLE POR PUNTO
    # ==================================================

    elementos.append(
        Paragraph(
            "DETALLE DE PRECIOS POR PUNTO",
            styles["Title"]
        )
    )

    elementos.append(
        Spacer(
            1,
            12
        )
    )

    elementos.append(
        tabla_detalle_por_punto(
            df_detalle
        )
    )

    # ==================================================
    # GENERAR
    # ==================================================

    doc.build(
        elementos,
        onFirstPage=fondo_pagina
    )

    pdf = buffer.getvalue()

    buffer.close()

    return pdf
