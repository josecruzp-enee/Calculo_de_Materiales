# -*- coding: utf-8 -*-
"""
debug_materiales.py
Script de depuración completa del proceso de cálculo de materiales.
"""

import os
import pandas as pd
from modulo.procesar_materiales import procesar_materiales

# === Archivos a usar ===
BASE = os.path.dirname(os.path.dirname(__file__))
archivo_estructuras = os.path.join(BASE, "estructura_lista.xlsx")
archivo_materiales = os.path.join(BASE, "Estructura_datos.xlsx")

# === Archivo de log ===
ruta_log = os.path.join(BASE, "debug_log.txt")

def log(msg):
    print(msg)
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

def main():
    # Limpiar log anterior
    if os.path.exists(ruta_log):
        os.remove(ruta_log)

    log("===== 🧭 INICIO DEBUG DE MATERIALES =====")

    try:
        (
            df_resumen,
            df_estructuras_resumen,
            df_estructuras_por_punto,
            df_resumen_por_punto,
            datos_proyecto
        ) = procesar_materiales(
            archivo_estructuras=archivo_estructuras,
            archivo_materiales=archivo_materiales
        )

        log("\n✅ ARCHIVOS CARGADOS CORRECTAMENTE\n")
        log(f"📊 Datos del proyecto: {datos_proyecto}")
        log(f"📊 df_resumen (Materiales): {len(df_resumen)} filas")
        log(f"📊 df_estructuras_resumen: {len(df_estructuras_resumen)} filas")
        log(f"📊 df_estructuras_por_punto: {len(df_estructuras_por_punto)} filas")
        log(f"📊 df_resumen_por_punto: {len(df_resumen_por_punto)} filas\n")

        log(">>> Primeras filas df_resumen:")
        log(df_resumen.head(10).to_string())

        log(">>> Primeras filas df_estructuras_resumen:")
        log(df_estructuras_resumen.head(10).to_string())

        log(">>> Primeras filas df_resumen_por_punto:")
        log(df_resumen_por_punto.head(10).to_string())

    except Exception as e:
        log("❌ ERROR DETECTADO EN EL PROCESO:")
        log(str(e))

    log("\n===== 🧾 FIN DEBUG DE MATERIALES =====")

if __name__ == "__main__":
    main()
