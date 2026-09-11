# -*- coding: utf-8 -*-
# exportadores/reporte_costos_proyecto.py
from __future__ import annotations

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus.tables import TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


styles = getSampleStyleSheet()


# =========================================================
# FORMATOS
# =========================================================
def _fmt_lps(valor) -> str:
    try:
        return f"L {float(valor):,.2f}"
    except Exception:
        return "L 0.00"


def _fmt_lps_0(valor) -> str:
    try:
        return f"L {float(valor):,.0f}"
    except Exception:
        return "L 0"


def _fmt_pct(valor) -> str:
    try:
        return f"{float(valor):,.2f} %"
    except Exception:
        return "0.00 %"


def _to_float(valor, default=0.0) -> float:
    try:
        if valor is None:
            return default

        if isinstance(valor, str):
            valor = (
                valor.replace("L", "")
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

        return float(valor)

    except Exception:
        return default


# =========================================================
# COLORES
# =========================================================
AZUL = colors.HexColor("#0B3B63")
AZUL_GANTT = colors.HexColor("#1565C0")
GRIS_CLARO = colors.HexColor("#F7F9FB")
GRIS_BORDE = colors.HexColor("#D9E2EC")
TEXTO = colors.HexColor("#263238")
VERDE = colors.HexColor("#1B5E20")
ROJO = colors.HexColor("#8B1E1E")
NARANJA = colors.HexColor("#B26A00")


def _color_utilidad(valor):
    return ROJO if _to_float(valor) < 0 else VERDE


def _color_estado(nivel):
    nivel = str(nivel or "").lower().strip()

    if nivel == "critico":
        return ROJO
    if nivel == "advertencia":
        return NARANJA
    if nivel == "aceptable":
        return AZUL
    if nivel == "bueno":
        return VERDE

    return AZUL


# =========================================================
# ESTILOS
# =========================================================
def _estilos():
    return {
        "titulo": ParagraphStyle(
            "titulo_costos_contratista",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=AZUL,
            spaceAfter=10,
        ),

        "subtitulo": ParagraphStyle(
            "subtitulo_costos_contratista",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=AZUL,
            spaceBefore=4,
            spaceAfter=7,
        ),

        "texto": ParagraphStyle(
            "texto_costos_contratista",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=TEXTO,
        ),

        "kpi_label": ParagraphStyle(
            "kpi_label",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),

        "kpi_valor": ParagraphStyle(
            "kpi_valor",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),

        "evaluacion_titulo": ParagraphStyle(
            "evaluacion_titulo",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.white,
        ),

        "evaluacion_texto": ParagraphStyle(
            "evaluacion_texto",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            textColor=TEXTO,
        ),

        "nota": ParagraphStyle(
            "nota_costos",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#455A64"),
        ),
    }


# =========================================================
# ESTILOS DE TABLAS
# =========================================================
def _estilo_tabla_estandar(
    *,
    header_font=8,
    body_font=7.2,
    align_right_from=1,
):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), header_font),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), body_font),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXTO),

        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.30, GRIS_BORDE),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            GRIS_CLARO,
        ]),

        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ])


# =========================================================
# ACCESOS A LOS DOS MUNDOS
# =========================================================
def _economia_cliente(resultado):
    data = resultado.get("economia_cliente", {})
    return data if isinstance(data, dict) else {}


def _economia_contratista(resultado):
    data = resultado.get("economia_contratista", {})
    return data if isinstance(data, dict) else {}


# =========================================================
# KPI PRINCIPALES — CONTRATISTA
# =========================================================
def _bloque_kpis(elementos, resultado):
    st = _estilos()

    ingreso = resultado.get(
        "ingreso_contratista",
        resultado.get("precio_venta", 0),
    )
    costo = resultado.get(
        "costo_real_contratista",
        resultado.get("costo_total_real", 0),
    )
    utilidad = resultado.get(
        "utilidad_contratista",
        resultado.get("utilidad", 0),
    )
    margen = resultado.get(
        "margen_contratista_pct",
        resultado.get("margen_pct", 0),
    )

    color_resultado = _color_utilidad(utilidad)

    data = [[
        [
            Paragraph("INGRESO CONTRATISTA", st["kpi_label"]),
            Paragraph(_fmt_lps_0(ingreso), st["kpi_valor"]),
        ],
        [
            Paragraph("COSTO REAL EJECUCIÓN", st["kpi_label"]),
            Paragraph(_fmt_lps_0(costo), st["kpi_valor"]),
        ],
        [
            Paragraph("UTILIDAD", st["kpi_label"]),
            Paragraph(_fmt_lps_0(utilidad), st["kpi_valor"]),
        ],
        [
            Paragraph("MARGEN REAL", st["kpi_label"]),
            Paragraph(f"{_to_float(margen):,.1f} %", st["kpi_valor"]),
        ],
    ]]

    tabla = Table(
        data,
        colWidths=[132, 132, 132, 132],
        rowHeights=[64],
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), AZUL),
        ("BACKGROUND", (2, 0), (3, 0), color_resultado),
        ("BOX", (0, 0), (-1, -1), 0.8, AZUL),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 14))


# =========================================================
# ECONOMÍA GLOBAL — CLIENTE
# =========================================================
def _bloque_economia_cliente(elementos, resultado):
    st = _estilos()
    cliente = _economia_cliente(resultado)

    if not cliente:
        return

    materiales = _to_float(cliente.get("materiales_sin_isv", 0))
    isv = _to_float(cliente.get("isv_materiales", 0))
    materiales_con_isv = materiales + isv

    data = [
        ["Concepto", "Monto"],
        ["Materiales sin ISV", _fmt_lps(materiales)],
        ["ISV sobre materiales", _fmt_lps(isv)],
        ["Materiales con ISV", _fmt_lps(materiales_con_isv)],
        ["Ejecución contratada", _fmt_lps(cliente.get("ejecucion_contratada", 0))],
        ["Equipo grúa", _fmt_lps(cliente.get("grua", 0))],
        ["Flete / transporte", _fmt_lps(cliente.get("flete", 0))],
        ["Ingeniería", _fmt_lps(cliente.get("ingenieria", 0))],
        ["Permisos / gestiones", _fmt_lps(cliente.get("permisos_enee", 0))],
        ["Otros", _fmt_lps(cliente.get("otros", 0))],
        ["INVERSIÓN TOTAL DEL CLIENTE", _fmt_lps(cliente.get("inversion_total_cliente", 0))],
    ]

    # Ocultar filas en cero, excepto las esenciales.
    esenciales = {
        "Materiales sin ISV",
        "ISV sobre materiales",
        "Materiales con ISV",
        "Ejecución contratada",
        "INVERSIÓN TOTAL DEL CLIENTE",
    }

    filtrada = [data[0]]
    for fila in data[1:]:
        concepto = fila[0]
        valor_txt = fila[1]
        valor = _to_float(valor_txt)
        if concepto in esenciales or valor > 0:
            filtrada.append(fila)

    elementos.append(
        Paragraph(
            "Economía global del proyecto — cliente",
            st["subtitulo"],
        )
    )

    tabla = Table(
        filtrada,
        colWidths=[335, 180],
        repeatRows=1,
    )
    tabla.setStyle(_estilo_tabla_estandar())

    # Total
    ultima = len(filtrada) - 1
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, ultima), (-1, ultima), "Helvetica-Bold"),
        ("BACKGROUND", (0, ultima), (-1, ultima), colors.HexColor("#E8EEF4")),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 8))

    elementos.append(
        Paragraph(
            "Este bloque representa la inversión global requerida al cliente. "
            "No se utiliza para medir la rentabilidad interna del contratista.",
            st["nota"],
        )
    )
    elementos.append(Spacer(1, 14))


# =========================================================
# DETALLE INTERNO — SOLO CONTRATISTA
# =========================================================
def _es_actividad_contratista(item) -> bool:
    actividad = str(item.get("actividad", "")).strip().lower()

    excluidas = (
        "equipo grúa",
        "flete",
        "ingeniería",
        "gestiones enee",
        "permisos",
    )

    return not any(x in actividad for x in excluidas)


def _bloque_detalle_actividades(elementos, resultado):
    st = _estilos()

    actividades = resultado.get("detalle_costos_actividades", [])
    actividades = [
        item for item in actividades
        if isinstance(item, dict) and _es_actividad_contratista(item)
    ]

    elementos.append(
        Paragraph(
            "Detalle interno de costos reales de ejecución — contratista",
            st["subtitulo"],
        )
    )

    if not actividades:
        elementos.append(
            Paragraph(
                "No se recibieron actividades internas de ejecución.",
                st["nota"],
            )
        )
        elementos.append(Spacer(1, 10))
        return

    data = [[
        "Actividad",
        "Unidad",
        "Cantidad",
        "P.U.",
        "Total",
        "Criterio",
    ]]

    for item in actividades:
        data.append([
            str(item.get("actividad", "")),
            str(item.get("unidad", "")),
            f"{_to_float(item.get('cantidad', 0)):,.2f}",
            _fmt_lps(item.get("precio_unitario", 0)),
            _fmt_lps(item.get("total", 0)),
            str(item.get("criterio", "")),
        ])

    tabla = Table(
        data,
        colWidths=[132, 42, 55, 65, 75, 166],
        repeatRows=1,
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.8),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 6.3),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXTO),

        ("ALIGN", (2, 1), (4, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.25, GRIS_BORDE),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            GRIS_CLARO,
        ]),

        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 14))


# =========================================================
# PARÁMETROS DE EJECUCIÓN — SOLO CONTRATISTA
# =========================================================
def _bloque_parametros_actividades(elementos, resultado):
    st = _estilos()
    params = resultado.get("parametros_actividades", {})
    tiempos = resultado.get("tiempos", {})
    cron_params = tiempos.get("parametros_cronograma", {}) if isinstance(tiempos, dict) else {}

    if not isinstance(params, dict) or not params:
        return

    elementos.append(
        Paragraph(
            "Parámetros usados para la ejecución del contratista",
            st["subtitulo"],
        )
    )

    data = [
        ["Parámetro", "Valor"],
        ["Costo cuadrilla por día", _fmt_lps(params.get("costo_cuadrilla_dia", 0))],
        ["Costo agujero subcontratado", _fmt_lps(params.get("costo_agujero_unitario", 0)) + " / agujero"],
        ["Horas por jornada de referencia", f"{_to_float(params.get('horas_jornada', 0)):,.2f} h"],
        ["Rendimiento agujeros", f"{_to_float(cron_params.get('rendimiento_agujeros_dia', 0)):,.2f} agujeros/día"],
        ["Horas por poste", f"{_to_float(params.get('horas_por_poste', 0)):,.2f} h"],
        ["Horas por retenida", f"{_to_float(params.get('horas_por_retenida', 0)):,.2f} h"],
        ["Horas por estructura MT", f"{_to_float(params.get('horas_por_estructura_mt', 0)):,.2f} h"],
        ["Horas por estructura BT", f"{_to_float(params.get('horas_por_estructura_bt', 0)):,.2f} h"],
        ["Horas por transformador", f"{_to_float(params.get('horas_por_transformador', 0)):,.2f} h"],
        ["Horas por luminaria", f"{_to_float(params.get('horas_por_luminaria', 0)):,.2f} h"],
        ["Rendimiento tendido MT", f"{_to_float(cron_params.get('rendimiento_mt_dia', 0)):,.0f} m/día"],
        ["Rendimiento tendido BT", f"{_to_float(cron_params.get('rendimiento_bt_dia', 0)):,.0f} m/día"],
    ]

    tabla = Table(
        data,
        colWidths=[290, 180],
        repeatRows=1,
    )
    tabla.setStyle(_estilo_tabla_estandar())

    elementos.append(tabla)
    elementos.append(Spacer(1, 8))

    elementos.append(
        Paragraph(
            "La tarifa diaria de cuadrilla se considera un pago integral por jornada. "
            "Los agujeros se consideran un subcontrato local por unidad y no generan "
            "días adicionales de cuadrilla principal.",
            st["nota"],
        )
    )
    elementos.append(Spacer(1, 14))


# =========================================================
# RESUMEN FINANCIERO — CONTRATISTA
# =========================================================
def _tabla_distribucion_contratista(resultado):
    contratista = _economia_contratista(resultado)
    costo_total = _to_float(
        contratista.get(
            "costo_real_contratista",
            resultado.get("costo_total_real", 0),
        )
    )

    rubros = [
        ("Cuadrilla", contratista.get("costo_cuadrilla", resultado.get("costo_cuadrilla", 0))),
        ("Agujeros", contratista.get("costo_agujeros", resultado.get("costo_agujeros", 0))),
        ("Herramientas", contratista.get("herramientas", 0)),
        ("Combustible", contratista.get("combustible", 0)),
        ("Movilización", contratista.get("movilizacion", 0)),
        ("Viáticos", contratista.get("viaticos", 0)),
        ("Supervisión", contratista.get("supervision", 0)),
        ("Administración", contratista.get("administracion", 0)),
        ("Grúa propia", contratista.get("grua_propia", 0)),
        ("Flete propio", contratista.get("flete_propio", 0)),
        ("Ingeniería propia", contratista.get("ingenieria_propia", 0)),
        ("Otros", contratista.get("otros", 0)),
        ("Contingencia", contratista.get("contingencia_contratista", resultado.get("contingencia", 0))),
    ]

    data = [["Rubro", "Monto", "%"]]

    for rubro, monto in rubros:
        monto = _to_float(monto)
        if monto <= 0:
            continue

        porcentaje = (monto / costo_total * 100) if costo_total else 0
        data.append([
            rubro,
            _fmt_lps(monto),
            _fmt_pct(porcentaje),
        ])

    tabla = Table(
        data,
        colWidths=[118, 92, 55],
        repeatRows=1,
    )
    tabla.setStyle(_estilo_tabla_estandar(body_font=7.3))

    return tabla


def _tabla_resultado_contratista(resultado):
    contratista = _economia_contratista(resultado)

    subtotal = contratista.get(
        "subtotal_ejecucion",
        resultado.get("subtotal_costos", 0),
    )
    contingencia = contratista.get(
        "contingencia_contratista",
        resultado.get("contingencia", 0),
    )
    costo = contratista.get(
        "costo_real_contratista",
        resultado.get("costo_total_real", 0),
    )
    ingreso = contratista.get(
        "ingreso_contratista",
        resultado.get("precio_venta", 0),
    )
    utilidad = contratista.get(
        "utilidad_contratista",
        resultado.get("utilidad", 0),
    )
    margen = contratista.get(
        "margen_contratista_pct",
        resultado.get("margen_pct", 0),
    )

    data = [
        ["Resultado", "Valor"],
        ["Subtotal ejecución", _fmt_lps(subtotal)],
        ["Contingencia", _fmt_lps(contingencia)],
        ["Costo real ejecución", _fmt_lps(costo)],
        ["Ingreso contratista", _fmt_lps(ingreso)],
        ["Utilidad", _fmt_lps(utilidad)],
        ["Margen real", _fmt_pct(margen)],
    ]

    tabla = Table(
        data,
        colWidths=[142, 112],
        repeatRows=1,
    )

    color_resultado = _color_utilidad(utilidad)

    tabla.setStyle(_estilo_tabla_estandar(body_font=7.3))
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 5), (-1, 6), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 5), (-1, 6), color_resultado),
    ]))

    return tabla


def _bloque_financiero(elementos, resultado):
    st = _estilos()

    elementos.append(
        Paragraph(
            "Resumen financiero interno del contratista",
            st["subtitulo"],
        )
    )

    tabla_izq = _tabla_distribucion_contratista(resultado)
    tabla_der = _tabla_resultado_contratista(resultado)

    fila = Table(
        [[tabla_izq, tabla_der]],
        colWidths=[275, 260],
    )

    fila.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos.append(fila)
    elementos.append(Spacer(1, 14))


# =========================================================
# INDICADORES OPERATIVOS
# =========================================================
def _dias_cuadrilla(resultado) -> int:
    cronograma = resultado.get("cronograma_resumen", [])
    if not isinstance(cronograma, list):
        return 0

    actividades_cuadrilla = {
        "Postes",
        "Retenidas",
        "Estructuras MT",
        "Tendido MT",
        "Transformadores",
        "Estructuras BT",
        "Tendido BT",
        "Luminarias",
        "Otras estructuras",
    }

    return int(sum(
        _to_float(item.get("duracion_dias", 0))
        for item in cronograma
        if str(item.get("actividad", "")) in actividades_cuadrilla
    ))


def _dias_agujeros(resultado) -> int:
    cronograma = resultado.get("cronograma_resumen", [])
    if not isinstance(cronograma, list):
        return 0

    for item in cronograma:
        if str(item.get("actividad", "")) == "Agujeros":
            return int(_to_float(item.get("duracion_dias", 0)))

    return 0


def _bloque_indicadores(elementos, resultado):
    st = _estilos()

    elementos.append(
        Paragraph(
            "Indicadores operativos",
            st["subtitulo"],
        )
    )

    data = [
        ["Indicador", "Valor"],
        ["Estructuras de armado MT/BT", f"{int(resultado.get('total_estructuras', 0)):,}"],
        ["Estructuras MT", f"{int(resultado.get('num_estructuras_mt', 0)):,}"],
        ["Estructuras BT", f"{int(resultado.get('num_estructuras_bt', 0)):,}"],
        ["Postes", f"{int(resultado.get('num_postes', 0)):,}"],
        ["Retenidas", f"{int(resultado.get('num_retenidas', 0)):,}"],
        ["Transformadores", f"{int(resultado.get('num_transformadores', 0)):,}"],
        ["Luminarias", f"{int(resultado.get('num_luminarias', 0)):,}"],
        ["Longitud primario", f"{_to_float(resultado.get('longitud_primario', 0)):,.2f} m"],
        ["Longitud secundario", f"{_to_float(resultado.get('longitud_secundario', 0)):,.2f} m"],
        ["Duración total del proyecto", f"{_to_float(resultado.get('dias_totales', 0)):,.0f} días"],
        ["Días de cuadrilla principal", f"{_dias_cuadrilla(resultado):,} días"],
        ["Días de agujeros subcontratados", f"{_dias_agujeros(resultado):,} días"],
        [
            "Costo global equivalente por estructura",
            _fmt_lps(
                resultado.get(
                    "costo_global_equivalente_por_estructura",
                    resultado.get("costo_por_estructura", 0),
                )
            ),
        ],
        [
            "Costo global equivalente por poste",
            _fmt_lps(
                resultado.get(
                    "costo_global_equivalente_por_poste",
                    resultado.get("costo_por_poste", 0),
                )
            ),
        ],
        ["Utilidad diaria equivalente", _fmt_lps(resultado.get("utilidad_diaria", 0))],
    ]

    tabla = Table(
        data,
        colWidths=[300, 160],
        repeatRows=1,
    )
    tabla.setStyle(_estilo_tabla_estandar(body_font=7.3))

    elementos.append(tabla)
    elementos.append(Spacer(1, 14))


# =========================================================
# CRONOGRAMA
# =========================================================
def _obtener_cronograma(resultado):
    cronograma = resultado.get("cronograma_resumen")

    if isinstance(cronograma, list) and cronograma:
        return cronograma

    dias = int(
        _to_float(
            resultado.get("dias_totales", 1),
            1,
        )
    )

    return [{
        "actividad": "Ejecución del proyecto",
        "duracion_dias": dias,
        "inicio": 1,
        "fin": dias,
    }]


def _bloque_cronograma(elementos, resultado):
    st = _estilos()

    elementos.append(
        Paragraph(
            "Cronograma estimado de ejecución",
            st["subtitulo"],
        )
    )

    cronograma = _obtener_cronograma(resultado)

    if not cronograma:
        elementos.append(
            Paragraph(
                "No se dispone de información de cronograma.",
                st["nota"],
            )
        )
        elementos.append(Spacer(1, 14))
        return

    data_resumen = [[
        "Actividad",
        "Cantidad",
        "Rendimiento",
        "Duración",
        "Inicio",
        "Fin",
    ]]

    for item in cronograma:
        actividad = str(item.get("actividad", ""))
        cantidad = _to_float(item.get("cantidad", 0))
        unidad = str(item.get("unidad", "")).strip()
        rendimiento = item.get("rendimiento")
        duracion = int(_to_float(item.get("duracion_dias", 0)))
        inicio = item.get("inicio")
        fin = item.get("fin")

        if unidad == "m":
            cantidad_txt = f"{cantidad:,.0f} m"
        elif unidad:
            cantidad_txt = f"{cantidad:,.0f} {unidad}"
        else:
            cantidad_txt = f"{cantidad:,.0f}"

        if rendimiento is None:
            rendimiento_txt = "—"
        else:
            rendimiento = _to_float(rendimiento)

            if unidad == "m":
                rendimiento_txt = f"{rendimiento:,.1f} m/día"
            elif unidad:
                rendimiento_txt = f"{rendimiento:,.1f} {unidad}/día"
            else:
                rendimiento_txt = f"{rendimiento:,.1f}/día"

        duracion_txt = f"{duracion} día" if duracion == 1 else f"{duracion} días"
        inicio_txt = f"Día {inicio}" if inicio else "—"
        fin_txt = f"Día {fin}" if fin else "—"

        data_resumen.append([
            actividad,
            cantidad_txt,
            rendimiento_txt,
            duracion_txt,
            inicio_txt,
            fin_txt,
        ])

    tabla_resumen = Table(
        data_resumen,
        colWidths=[145, 72, 100, 70, 65, 65],
        repeatRows=1,
    )

    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 6.8),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXTO),

        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.30, GRIS_BORDE),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            GRIS_CLARO,
        ]),

        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 10))

    max_dia = max(
        (int(item.get("fin") or 0) for item in cronograma),
        default=0,
    )

    if max_dia <= 0:
        elementos.append(Spacer(1, 14))
        return

    if max_dia <= 30:
        paso = 1
    elif max_dia <= 60:
        paso = 2
    elif max_dia <= 90:
        paso = 3
    else:
        paso = 5

    periodos = list(range(1, max_dia + 1, paso))
    data_gantt = [["Actividad"] + [str(dia) for dia in periodos]]

    for item in cronograma:
        actividad = str(item.get("actividad", ""))
        data_gantt.append([actividad] + [""] * len(periodos))

    ancho_actividad = 120
    ancho_disponible = 415
    ancho_periodo = min(ancho_disponible / len(periodos), 16) if periodos else 10

    tabla_gantt = Table(
        data_gantt,
        colWidths=[ancho_actividad] + [ancho_periodo] * len(periodos),
        rowHeights=16,
        repeatRows=1,
    )

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 5.5),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 5.8),

        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("GRID", (0, 0), (-1, -1), 0.20, GRIS_BORDE),

        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]

    for fila_idx, item in enumerate(cronograma, start=1):
        inicio = item.get("inicio")
        fin = item.get("fin")

        if not inicio or not fin:
            continue

        inicio = int(inicio)
        fin = int(fin)

        periodo_inicio = (inicio - 1) // paso
        periodo_fin = (fin - 1) // paso

        col_inicio = min(1 + periodo_inicio, len(periodos))
        col_fin = min(1 + periodo_fin, len(periodos))

        style.append(
            (
                "BACKGROUND",
                (col_inicio, fila_idx),
                (col_fin, fila_idx),
                AZUL_GANTT,
            )
        )

    tabla_gantt.setStyle(TableStyle(style))

    elementos.append(Paragraph("Diagrama de ejecución", st["nota"]))
    elementos.append(Spacer(1, 4))
    elementos.append(tabla_gantt)
    elementos.append(Spacer(1, 5))

    if paso == 1:
        escala_txt = "Cada columna representa 1 día."
    else:
        escala_txt = (
            f"Cada columna representa aproximadamente {paso} días. "
            "Los números del encabezado indican el día inicial de cada período."
        )

    texto_nota = (
        f"<b>Duración total estimada:</b> {max_dia} días. "
        f"{escala_txt} "
        f"<b>Días de cuadrilla principal:</b> {_dias_cuadrilla(resultado)}. "
        f"<b>Días de agujeros subcontratados:</b> {_dias_agujeros(resultado)}. "
        "Los rendimientos utilizados corresponden a promedios diarios de ejecución en campo."
    )

    elementos.append(Paragraph(texto_nota, st["nota"]))
    elementos.append(Spacer(1, 14))


# =========================================================
# EVALUACIÓN EJECUTIVA — CONTRATISTA
# =========================================================
def _bloque_evaluacion(elementos, resultado):
    st = _estilos()

    estado = resultado.get("estado_proyecto")
    mensaje = resultado.get("mensaje_evaluacion")
    nivel = resultado.get("nivel_evaluacion")

    utilidad = resultado.get(
        "utilidad_contratista",
        resultado.get("utilidad", 0),
    )
    margen = resultado.get(
        "margen_contratista_pct",
        resultado.get("margen_pct", 0),
    )

    if not estado:
        utilidad_num = _to_float(utilidad)
        margen_num = _to_float(margen)

        if utilidad_num < 0:
            estado = "NO RENTABLE"
            mensaje = "El costo real de ejecución supera el ingreso contratado."
            nivel = "critico"

        elif margen_num < 10:
            estado = "RENTABILIDAD BAJA"
            mensaje = "La ejecución tiene utilidad positiva, pero el margen es bajo."
            nivel = "advertencia"

        elif margen_num < 20:
            estado = "RENTABLE"
            mensaje = "La ejecución presenta utilidad positiva con margen aceptable."
            nivel = "aceptable"

        else:
            estado = "RENTABLE ALTO"
            mensaje = "La ejecución presenta una rentabilidad favorable."
            nivel = "bueno"

    color = _color_estado(nivel)

    texto = (
        f"{mensaje}<br/><br/>"
        f"<b>Utilidad estimada del contratista:</b> {_fmt_lps(utilidad)}<br/>"
        f"<b>Margen real estimado:</b> {_fmt_pct(margen)}"
    )

    tabla = Table(
        [
            [
                Paragraph(
                    f"Evaluación interna del contratista: {estado}",
                    st["evaluacion_titulo"],
                )
            ],
            [
                Paragraph(
                    texto,
                    st["evaluacion_texto"],
                )
            ],
        ],
        colWidths=[535],
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F6F8")),
        ("BOX", (0, 0), (-1, -1), 0.8, GRIS_BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))


# =========================================================
# BLOQUE COMPLETO
# =========================================================
def construir_bloque_costos(
    elementos,
    styles_param,
    resultado,
    df_materiales_costos=None,
):
    if not resultado:
        return

    # 1. Resumen interno del contratista
    _bloque_kpis(
        elementos,
        resultado,
    )

    # 2. Mundo cliente
    _bloque_economia_cliente(
        elementos,
        resultado,
    )

    # 3. Mundo contratista
    _bloque_detalle_actividades(
        elementos,
        resultado,
    )

    _bloque_parametros_actividades(
        elementos,
        resultado,
    )

    _bloque_financiero(
        elementos,
        resultado,
    )

    # 4. Operación y cronograma
    _bloque_indicadores(
        elementos,
        resultado,
    )

    _bloque_cronograma(
        elementos,
        resultado,
    )

    # 5. Evaluación final
    _bloque_evaluacion(
        elementos,
        resultado,
    )


# =========================================================
# PDF FINAL INDIVIDUAL
# =========================================================
def generar_pdf_costos_proyecto(
    resultado,
    df_materiales_costos=None,
    ruta="costos_proyecto.pdf",
):
    doc = SimpleDocTemplate(
        ruta,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elementos = []
    st = _estilos()

    elementos.append(
        Paragraph(
            "REPORTE DE COSTOS DEL PROYECTO Y RENTABILIDAD DEL CONTRATISTA",
            st["titulo"],
        )
    )

    construir_bloque_costos(
        elementos=elementos,
        styles_param=styles,
        resultado=resultado,
        df_materiales_costos=df_materiales_costos,
    )

    doc.build(elementos)

    return ruta
