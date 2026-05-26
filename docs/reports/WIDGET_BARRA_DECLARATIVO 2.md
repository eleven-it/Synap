# Widget Gráfico de Barras (informes declarativos)

## Dónde está el widget

- **Motor de renderizado:** `reports/static/reports/js/widget_engine.js`  
  - Método: `WidgetEngine.renderBarChart(container, widgetSchema)` (aprox. línea 954).
- **Configuración en Builder:** `reports/templates/reports/builder_detail.html`  
  - Pestaña "Widgets", formulario del widget: nombre, tipo "Gráfico de barras", dimensión X (Mes), métricas Y (ventas_netas), **Serie (agrupación opcional)** = Sucursal.

## Template / UI en el Builder

- **Serie (agrupación opcional):**  
  `<select x-model="widget.configuration.series_dimension">` con opciones generadas desde `config.dimensions` (clave = nombre de dimensión, p. ej. `nombre_sucursal`).  
  Texto de ayuda: "Para gráficos apilados o múltiples series".
- **Dimensiones X e Y:**  
  - Dimensión X: `widget.configuration.x_dimension` (ej. `mes`).  
  - Métricas Y: `widget.configuration.y_metrics` (ej. `['ventas_netas']`).
- El schema del reporte (backend) mapea `series_dimension: "sucursal"` o `"Sucursal"` → `nombre_sucursal` cuando existe esa dimensión en el reporte (`reports/services/schema_service.py`, `_convert_report_widgets_to_schema`).  
- Si hay `series_dimension` y el widget es `bar`, se fuerza `options.stacked = True` en el schema.

## Cómo se cargan los datos

1. **Dashboard declarativo** (`dashboard_detail.html` con `is_declarative=true`):  
   - Se llama a `loadDeclarativeDashboard()`:  
     - GET al **schema** (`schema_api_url`).  
     - POST a **query** (`query_api_url`) con `slug` y `filters`.  
   - La respuesta de la query incluye `data` (array de filas).  
   - Se instancia/usa **WidgetEngine** con `queryResult` y el schema; para cada widget de tipo `bar` se llama a `WidgetEngine.renderBarChart(container, widgetSchema)`.

2. **Origen de `data` para Ventas Netas:**  
   - Mismo endpoint de query que el resto de reportes.  
   - Para `slug` `ventas-netas` o `ventas_netas`, el backend usa `QueryRunnerService._run_ventas_netas`, que devuelve filas con: `mes`, `mes_formato`, `id_sucursal`, **`nombre_sucursal`**, `id_punto_venta`, `nro_punto_venta`, `ventas_brutas`, `notas_credito`, `ventas_netas`.

3. **Uso en el gráfico:**  
   - `renderBarChart` usa `this.queryResult.data`, `widgetSchema.x_dimension`, `widgetSchema.y_metrics`, `widgetSchema.series_dimension`.  
   - Si hay `series_dimension`, agrupa por `xDimension` y `seriesDimension` y suma métricas; si además `widgetSchema.options.stacked === true`, dibuja barras apiladas por serie (p. ej. por sucursal).  
   - **Normalización:** Si en el schema viene `series_dimension` como "Sucursal" o "sucursal" y los datos tienen columna `nombre_sucursal`, en `renderBarChart` se usa `nombre_sucursal` como dimensión de serie para que coincida con las columnas del backend.

## Resumen

| Elemento              | Ubicación / Comportamiento |
|-----------------------|----------------------------|
| Renderizado barra     | `widget_engine.js` → `renderBarChart()` |
| UI del widget         | `builder_detail.html` → pestaña Widgets, serie = `series_dimension` |
| Schema (serie → campo)| `schema_service.py` → `series_dimension` "sucursal"/"Sucursal" → `nombre_sucursal`; `stacked: true` si hay serie |
| Datos                 | POST a query API → `QueryRunnerService`; Ventas Netas: `_run_ventas_netas` → filas con `nombre_sucursal` |
| Apilado por sucursal  | `series_dimension` = nombre_sucursal + `options.stacked`; en JS se normaliza "Sucursal" → `nombre_sucursal` |
