# Cálculo de Materiales

Aplicación web en **Streamlit** para calcular materiales de redes eléctricas, cargar estructuras por distintos métodos, agregar cables/material extra y exportar resultados (incluyendo PDF/Excel y mapa KMZ).

## ¿Cómo funciona?

El flujo principal está dividido en pestañas (barra superior):

1. **Datos**: captura datos generales del proyecto.
2. **Cables**: registra los cables del proyecto.
3. **Modo de Carga**: define cómo ingresar estructuras (listas, PDF, DXF, etc. según módulos habilitados).
4. **Estructuras**: procesa/carga estructuras y las guarda en memoria (`st.session_state`).
5. **Adicionar Material**: permite sumar materiales manualmente.
6. **Finalizar**: ejecuta el cálculo consolidado de materiales.
7. **Exportación**: genera salidas y reportes con los datos calculados.
8. **Mapa / KMZ**: crea o visualiza información geográfica del proyecto.

## Ejecución local

1. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Inicia la app:
   ```bash
   streamlit run app.py
   ```
3. Abre el navegador en la URL que muestra Streamlit (normalmente `http://localhost:8501`).

## Detalles técnicos clave

- El punto de entrada es `app.py`.
- La navegación usa `query params` y `session_state` para cambiar secciones sin perder contexto.
- El archivo base de datos de materiales por defecto se toma de `data/Estructura_datos.xlsx`.
