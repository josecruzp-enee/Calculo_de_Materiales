# -*- coding: utf-8 -*-
"""
debug_materiales.py
Depuración del proceso de cálculo de materiales con funciones pequeñas.
- Valida entradas
- Ejecuta procesar_materiales
- Guarda LOG (timestamps)
- Vuelca PDFs/CSVs/JSON según el retorno
"""

import os
import json
from datetime import datetime
import pandas as pd
from modulo.procesar_materiales import procesar_materiales


# =========================
# Configuración y utilidades
# =========================
def obtener_rutas():
    """Devuelve rutas base, salida, entradas y log."""
    base = os.path.dirname(__file__)
    salida = os.path.join(base, "debug_out")
    rutas = {
        "base": base,
        "salida": salida,
        "estructuras": os.path.join(base, "estructura_lista.xlsx"),
        "materiales": os.path.join(base, "modulo", "Estructura_datos.xlsx"),
        "log": os.path.join(salida, "debug_log.txt"),
    }
    return rutas


def ts():
    """Timestamp legible."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def iniciar_log(rutas):
    """Crea la carpeta de salida y reinicia el log."""
    os.makedirs(rutas["salida"], exist_ok=True)
    if os.path.exists(rutas["log"]):
        os.remove(rutas["log"])


def log(rutas, msg):
    """Escribe en consola y en el archivo de log."""
    linea = f"[{ts()}] {msg}"
    print(linea)
    with open(rutas["log"], "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# =========================
# Validaciones y guardados
# =========================
def validar_archivo(rutas, archivo, etiqueta) -> bool:
    ok = os.path.isfile(archivo)
    log(rutas, f"{'✅' if ok else '❌'} {etiqueta}: {archivo}")
    return ok


def guardar_pdf(rutas, nombre, blob: bytes):
    ruta = os.path.join(rutas["salida"], f"{nombre}.pdf")
    with open(ruta, "wb") as f:
        f.write(blob)
    log(rutas, f"📄 PDF guardado: {ruta}")


def guardar_df(rutas, nombre, df: pd.DataFrame, n_preview: int = 10):
    ruta = os.path.join(rutas["salida"], f"{nombre}.csv")
    try:
        df.to_csv(ruta, index=False, encoding="utf-8")
        log(rutas, f"💾 CSV guardado: {ruta} (filas={len(df)})")
        log(rutas, f"🪟 Vista previa {nombre}:\n{df.head(n_preview).to_string(index=False)}")
    except Exception as e:
        log(rutas, f"⚠️ No se pudo guardar {nombre}.csv: {e}")


def guardar_json(rutas, nombre, obj):
    ruta = os.path.join(rutas["salida"], f"{nombre}.json")
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
        log(rutas, f"🧾 JSON guardado: {ruta}")
    except Exception as e:
        log(rutas, f"⚠️ No se pudo guardar {nombre}.json: {e}")


# =========================
# Manejo de resultados
# =========================
def manejar_resultado_tupla(rutas, resultado):
    """Tupla esperada: (df_resumen, df_estr_res, df_estr_punto, df_res_punto, datos_proyecto)."""
    (df_resumen,
     df_estructuras_resumen,
     df_estructuras_por_punto,
     df_resumen_por_punto,
     datos_proyecto) = resultado

    log(rutas, "\n✅ Retorno TUPLA (DataFrames)\n")
    log(rutas, f"📊 df_resumen: {len(df_resumen)} filas")
    log(rutas, f"📊 df_estructuras_resumen: {len(df_estructuras_resumen)} filas")
    log(rutas, f"📊 df_estructuras_por_punto: {len(df_estructuras_por_punto)} filas")
    log(rutas, f"📊 df_resumen_por_punto: {len(df_resumen_por_punto)} filas")

    guardar_df(rutas, "df_resumen", df_resumen)
    guardar_df(rutas, "df_estructuras_resumen", df_estructuras_resumen)
    guardar_df(rutas, "df_estructuras_por_punto", df_estructuras_por_punto)
    guardar_df(rutas, "df_resumen_por_punto", df_resumen_por_punto)
    guardar_json(rutas, "datos_proyecto", datos_proyecto)


def manejar_resultado_dict(rutas, resultado: dict):
    """Dict puede traer PDFs (bytes), DataFrames o estructuras serializables."""
    log(rutas, "\n✅ Retorno DICT (puede contener PDFs/DFs/JSON)\n")
    log(rutas, f"🔑 Claves: {list(resultado.keys())}")

    for nombre, obj in resultado.items():
        if obj is None:
            log(rutas, f"⚠️ {nombre}: None (omitido)")
            continue
        if isinstance(obj, (bytes, bytearray)):
            guardar_pdf(rutas, nombre, obj)
        elif isinstance(obj, pd.DataFrame):
            guardar_df(rutas, nombre, obj)
        else:
            # intentar json; si falla, solo informar
            try:
                guardar_json(rutas, nombre, obj)
            except Exception:
                log(rutas, f"ℹ️ {nombre}: tipo no reconocido ({type(obj).__name__}), omitido.")


# =========================
# Ejecución principal
# =========================
def ejecutar_proceso(rutas):
    """Invoca procesar_materiales y enruta el manejo según el tipo de retorno."""
    log(rutas, "▶️ Ejecutando procesar_materiales(...)")
    res = procesar_materiales(
        archivo_estructuras=rutas["estructuras"],
        archivo_materiales=rutas["materiales"],
        # si tu función soporta debug=True, puedes activarlo:
        # debug=True
    )
    log(rutas, "✅ procesar_materiales terminó sin excepciones")

    if isinstance(res, tuple) and len(res) == 5:
        manejar_resultado_tupla(rutas, res)
    elif isinstance(res, dict):
        manejar_resultado_dict(rutas, res)
    else:
        log(rutas, f"ℹ️ Retorno no estándar: {type(res).__name__}. No se volcó.")


def main():
    rutas = obtener_rutas()
    iniciar_log(rutas)
    log(rutas, "===== 🧭 INICIO DEBUG DE MATERIALES =====")

    ok_estr = validar_archivo(rutas, rutas["estructuras"], "Excel de estructuras")
    ok_mat  = validar_archivo(rutas, rutas["materiales"],  "Excel de materiales")
    if not (ok_estr and ok_mat):
        log(rutas, "❌ Entradas inválidas. Corrige rutas y reintenta.")
        log(rutas, "===== 🧾 FIN DEBUG DE MATERIALES =====")
        return

    try:
        ejecutar_proceso(rutas)
    except Exception as e:
        log(rutas, "❌ ERROR DETECTADO EN EL PROCESO:")
        log(rutas, str(e))

    log(rutas, "===== 🧾 FIN DEBUG DE MATERIALES =====")


if __name__ == "__main__":
    main()

