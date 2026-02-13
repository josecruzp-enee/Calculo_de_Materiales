# Plan de refactor: separar lógica de negocio de UI (Streamlit)

## Objetivo

Separar responsabilidades en capas para que:
- `interfaz/` solo renderice y orqueste interacción con Streamlit.
- `core/` contenga reglas de negocio puras (transformaciones/cálculo).
- `io/` centralice lectura/escritura de archivos y parseo de entradas.
- `exportadores/` reciba datos ya calculados y solo genere salidas (PDF/Excel/KMZ).

---

## Estructura propuesta

```text
core/
  estructuras/
    normalizacion.py
    transformaciones.py
  calculo/
    materiales.py
    costos.py
    cables.py
  validacion/
    datos_proyecto.py

io/
  readers/
    excel_reader.py
    pdf_reader.py
    dxf_reader.py
    texto_reader.py
  writers/
    temp_writer.py
  gateways/
    entradas_gateway.py

exportadores/
  pdf/
  excel/
  kmz/

interfaz/
  pages/
    datos.py
    cables.py
    estructuras.py
    finalizar.py
    exportacion.py
    mapa.py
  state/
    session_store.py
  app_shell.py
```

> Nota: No requiere mover todo de una vez. Se puede hacer incrementalmente con wrappers para compatibilidad.

---

## Qué funciones mover (candidatas concretas)

### 1) De `interfaz/` hacia `core/` (lógica de negocio pura)

**Origen: `interfaz/estructuras_comunes.py`**
- `normalizar_columnas`
- `norm_code_value`
- `split_cell_items`
- `es_proyectada`
- `parse_item`
- `expand_wide_to_long`

**Destino sugerido:**
- `core/estructuras/normalizacion.py`
- `core/estructuras/transformaciones.py`

**Razón:** son transformaciones de datos sin dependencia real de Streamlit.

---

### 2) De `interfaz/mapa_kml.py` hacia `exportadores/kmz/`

**Mover a capa exportador KMZ:**
- `_resumen_por_punto`
- `_html_descripcion`
- `_ordenar_puntos_series`
- `_crear_kmz`

**Dejar en UI (`interfaz/`) solo:**
- carga de CSV con `st.file_uploader`
- validaciones visuales/mensajes
- botón de descarga

**Destino sugerido:**
- `exportadores/kmz/generador_kmz.py`

**Razón:** la construcción del KMZ es lógica de salida reutilizable fuera de Streamlit.

---

### 3) Consolidar entradas en `io/`

Actualmente `entradas/` ya hace parte de esto; la propuesta es renombrar y ordenar:
- `entradas/entradas_excel.py` -> `io/readers/excel_reader.py`
- `entradas/entradas_pdf.py` -> `io/readers/pdf_reader.py`
- `entradas/entradas_dxf.py` -> `io/readers/dxf_reader.py`
- `entradas/io_temp.py` -> `io/writers/temp_writer.py`
- `entradas/entradas.py` -> `io/gateways/entradas_gateway.py`

**Razón:** hoy conviven responsabilidades de parsing y orquestación; conviene un gateway explícito por modo.

---

### 4) Mantener y limpiar `core/` de cálculo

Los módulos actuales de `core/` ya están bien encaminados (materiales, costos, cables). Acción sugerida:
- estandarizar contratos de entrada/salida DataFrame (nombres de columnas canónicos).
- evitar duplicidad entre `precios_materiales.py` y `costos_materiales.py` (hay funciones similares de carga de precios).

---

## Contratos de datos recomendados

Definir y congelar contratos (con tests) para evitar regresiones:

- **Estructuras largo:** `Punto`, `codigodeestructura`, `cantidad`
- **Cables:** `Tipo`, `Configuración`, `Calibre`, `Longitud (m)`
- **Materiales extra:** `Materiales`, `Unidad`, `Cantidad`

Crear helpers de validación en `core/validacion/` para que UI solo muestre errores y no implemente reglas.

---

## Pasos seguros (incrementales)

1. **Congelar comportamiento actual**
   - agregar tests de regresión para:
     - conversión ancho->largo de estructuras
     - generación KMZ con dataset mínimo
     - pipeline de cálculo principal

2. **Extraer lógica pura sin cambiar imports públicos**
   - crear nuevos módulos en `core/` y `exportadores/kmz/`.
   - en archivos de `interfaz/`, dejar wrappers que llamen al nuevo módulo.

3. **Separar entrada de datos**
   - introducir `io/gateways/entradas_gateway.py` como puerta única.
   - adaptar `interfaz/estructuras.py` para consumir el gateway y no leer archivos directo.

4. **Reducir `session_state` a DTOs claros**
   - normalizar claves y lifecycle (`df_estructuras`, `datos_proyecto`, etc.).
   - centralizar defaults en `interfaz/state/session_store.py`.

5. **Limpiar duplicidad y deuda técnica**
   - retirar funciones legacy no usadas.
   - consolidar carga de precios/costos en un solo servicio.

6. **Eliminar wrappers temporales**
   - cuando tests estén estables, actualizar imports finales y borrar puentes.

---

## Riesgos y mitigación

- **Riesgo:** ruptura por nombres de columnas.
  - **Mitigación:** validadores canónicos + tests de contratos.

- **Riesgo:** cambios de estado en Streamlit (`session_state`).
  - **Mitigación:** capa `session_store` con API mínima (`get/set/reset`).

- **Riesgo:** exportadores dependientes de formatos internos.
  - **Mitigación:** pasar objetos/DF ya normalizados y versionar contrato de entrada.

---

## Entregables sugeridos por PR

- **PR 1 (bajo riesgo):** extraer `expand_wide_to_long` y helpers a `core/estructuras/*` con wrappers.
- **PR 2:** mover generador KMZ a `exportadores/kmz/generador_kmz.py`.
- **PR 3:** crear `io/gateways/entradas_gateway.py` y adaptar UI.
- **PR 4:** consolidar validaciones + limpieza de duplicidades en costos/precios.

Este orden reduce riesgo, mantiene la app funcional y permite rollback por etapas.
