# -*- coding: utf-8 -*-
"""
mapa_funciones.py
Genera un resumen automático de las funciones y dependencias del proyecto.
Autor: José Nikol Cruz
"""

import os
import re
from datetime import datetime

BASE_DIR = "modulo"  # carpeta base donde están tus scripts
SALIDA = "MAPA_FUNCIONES.txt"

def extraer_funciones_y_imports(ruta):
    """Extrae nombres de funciones y módulos importados de un archivo .py"""
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()

    funciones = re.findall(r"def\s+([a-zA-Z_]\w*)", contenido)
    imports = re.findall(r"from\s+([\w\.]+)\s+import", contenido)
    imports += re.findall(r"import\s+([\w\.]+)", contenido)
    return funciones, sorted(set(imports))

def generar_mapa():
    resumen = []
    resumen.append(f"MAPA AUTOMÁTICO DEL PROYECTO\nGenerado: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
    resumen.append("=".ljust(60, "=") + "\n")

    for root, _, files in os.walk(BASE_DIR):
        for archivo in files:
            if archivo.endswith(".py"):
                ruta = os.path.join(root, archivo)
                funciones, imports = extraer_funciones_y_imports(ruta)
                resumen.append(f"\n📄 {archivo}")
                resumen.append("-" * 60)
                if imports:
                    resumen.append(f"🔗 Importa: {', '.join(imports)}")
                if funciones:
                    resumen.append(f"⚙️  Funciones ({len(funciones)}): {', '.join(funciones)}")
                else:
                    resumen.append("⚙️  (sin funciones definidas)")
                resumen.append("")

    with open(SALIDA, "w", encoding="utf-8") as salida:
        salida.write("\n".join(resumen))
    print(f"✅ Archivo generado: {SALIDA}")

if __name__ == "__main__":
    generar_mapa()
