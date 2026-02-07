# -*- coding: utf-8 -*-
"""
exportadores/pdf_estilos.py
Estilos comunes para PDFs (ReportLab)
"""

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

styles = getSampleStyleSheet()

styleN = ParagraphStyle(
    name="Normal9",
    parent=styles["Normal"],
    fontSize=9,
    leading=11
)

styleH = styles["Heading1"]
