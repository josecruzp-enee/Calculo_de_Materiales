# interfaz/orquestador_interfaz.py

from interfaz.datos_proyecto import seccion_datos_proyecto
from interfaz.estructuras import seccion_entrada_estructuras
from interfaz.cables import seccion_cables
from interfaz.exportacion import seccion_exportacion

# ⚠️ Este import luego lo moveremos a core real
# por ahora lo dejamos simple para no romper nada
# from core.orquestador import ejecutar_proyecto


def ejecutar_interfaz():
    """
    Orquestador de la UI.
    Controla el flujo completo de la aplicación.
    """

    # ============================
    # 1. DATOS DEL PROYECTO
    # ============================
    datos = seccion_datos_proyecto()

    if not datos:
        return

    # ============================
    # 2. ENTRADA DE ESTRUCTURAS
    # ============================
    df_estructuras, ruta = seccion_entrada_estructuras(datos)

    if df_estructuras is None:
        return

    # ============================
    # 3. CABLES / CONFIGURACIÓN
    # ============================
    config_cables = seccion_cables(df_estructuras)

    # ============================
    # 4. PROCESAMIENTO (TEMPORAL)
    # ============================
    # ⚠️ Aquí estás mezclando UI + lógica actualmente
    # Luego lo moveremos a core.orquestador

    resultado = {
        "datos": datos,
        "estructuras": df_estructuras,
        "ruta": ruta,
        "cables": config_cables,
    }

    # ============================
    # 5. EXPORTACIÓN / PDF
    # ============================
    seccion_exportacion(resultado)
