# Análisis: "Mostrar en KPI del resumen" en reportes con métricas

## 1. Dónde se define la opción

- **Ubicación**: Report Builder → al editar un campo de tipo **Métrica** (Número calculado / Métrica).
- **UI**: Checkbox **"Mostrar en KPI del resumen"** con la leyenda: *"Si está activado, esta métrica aparecerá como tarjeta KPI en el resumen del reporte"*.
- **Archivos**:
  - **Modo visual** (campos a visualizar): `reports/templates/reports/builder_detail.html` (aprox. líneas 720–732), `x-model="field.show_in_kpi"`.
  - **Modo avanzado** (tabla de métricas): mismo template, columna "Mostrar en KPI" con `x-model="metric.show_in_kpi"` (aprox. 765, 807).

## 2. Dónde se persiste

- El valor se guarda en la **configuración del reporte** en base de datos: `ReportDefinition.config`.
- Estructura: `config.metrics[<nombre_campo>].show_in_kpi` (boolean).
- Por defecto, si no existe la clave se considera **true** (retrocompatibilidad) en el backend.

## 3. Cómo llega al schema (backend)

- **Servicio**: `reports/services/schema_service.py`.
- **Modelo**: `MetricSchema` tiene el campo `show_in_kpi: bool = True` (línea 29).
- Al construir el schema del reporte, para cada métrica se hace:
  ```python
  show_in_kpi = config.get('metrics', {}).get(field_name, {}).get('show_in_kpi', True)
  metrics.append(self._build_metric_schema(..., show_in_kpi))
  ```
- Eso ocurre en varias ramas del builder de schema (líneas 636–638, 651–653, 663–665, 816–818, 831–833, 843–845), de modo que **todas** las métricas del config llevan su `show_in_kpi` al schema que se envía al frontend.

## 4. Comportamiento en el renderizado del reporte

Hay **dos flujos** distintos según el tipo de reporte:

### 4.1 Reportes **declarativos** (`config.version == "declarative-v1"`)

- **Vista**: Dashboard del reporte (`dashboard_detail.html`).
- **Contexto**: `is_declarative = True` (calculado en `views.py` con `config.get("version") == "declarative-v1"`).
- **Flujo**:
  1. Se carga el script que inicializa el flujo declarativo (WidgetEngine, etc.).
  2. Se obtiene el **schema** (API de schema) y se ejecuta la **query** (API de query).
  3. Se llama a **`renderDeclarativeSummary(queryResult, schema)`** (definida en `dashboard_detail.html`, aprox. 3703).
- **Uso de `show_in_kpi`**:
  - Se toman las métricas del schema: `const mainMetrics = schema.metrics || [];`
  - Se filtran las que deben mostrarse en KPI:  
    `const metricsToShow = mainMetrics.filter(metric => metric.show_in_kpi !== false);`
  - Se ordenan (incluyendo orden preferente para ventas_brutas, notas_credito, ventas_netas).
  - Se renderizan **hasta 4 tarjetas KPI** en el resumen usando `metricsToShow` y los valores de `queryResult.totals[metric.name]`.
- **Conclusión**: En reportes declarativos, **"Mostrar en KPI del resumen"** controla correctamente qué métricas aparecen como tarjetas en el resumen.

### 4.2 Reportes **no declarativos** (legacy; sin `version: "declarative-v1"`)

- **Vista**: Mismo template de dashboard, pero `is_declarative = False`.
- **Flujo**:
  1. No se ejecuta el bloque que usa schema + WidgetEngine + `renderDeclarativeSummary`.
  2. El dashboard usa **`dashboard.js`**: `fetchDashboardData` → al recibir la respuesta se llama **`renderSummary(payload.meta || {}, payload.totals || {})`** (aprox. 6993).
- **Función `renderSummary(meta, totals)`** (en `dashboard.js`, aprox. 3977):
  - **No recibe el schema**; solo `meta` y `totals`.
  - Construye las tarjetas a partir de las **claves numéricas de `totals`**, con un orden fijo y exclusiones (`excludedKeys`).
  - No consulta ninguna propiedad `show_in_kpi`.
- **Conclusión**: En reportes legacy, **el checkbox "Mostrar en KPI del resumen" no tiene efecto**: el resumen se arma solo con `totals` y no con el schema.

## 5. Caso concreto: reporte Pedidos pendientes

- El reporte **pedidos-pendientes** creado por migración (`0015_add_pending_orders_report.py`) tiene:
  - `config.metrics` como **lista** (`["subtotal_desc"]`), no como diccionario con `show_in_kpi`.
  - Sin `config.version = "declarative-v1"`.
- Por tanto, en su estado por defecto es **legacy** y usa `renderSummary(meta, totals)`:
  - Aunque en el Builder se marque o desmarque "Mostrar en KPI del resumen" para una métrica, ese valor **no se usa** en la vista del reporte si el reporte sigue siendo no declarativo.
- Para que "Mostrar en KPI del resumen" **sí** afecte a Pedidos pendientes hace falta:
  1. Que el reporte pase a ser **declarativo** (`config.version == "declarative-v1"`) y que `config.metrics` sea un diccionario con definiciones por campo (incluyendo `show_in_kpi`), **y**
  2. Que la vista del dashboard use el flujo declarativo (schema + query + `renderDeclarativeSummary`), cosa que ya ocurre cuando `is_declarative` es True.

## 6. Resumen

| Aspecto | Comportamiento |
|--------|-----------------|
| **Dónde se configura** | Builder, en cada campo de tipo Métrica (modo visual y modo avanzado). |
| **Dónde se guarda** | `ReportDefinition.config.metrics[<nombre>].show_in_kpi`. |
| **Dónde se usa** | Solo en el flujo **declarativo** (`renderDeclarativeSummary` en `dashboard_detail.html`). |
| **Cuándo no se usa** | En el flujo **legacy** (`renderSummary(meta, totals)` en `dashboard.js`): el resumen se arma solo con `totals`, sin schema ni `show_in_kpi`. |
| **Pedidos pendientes** | Por defecto es legacy; el checkbox no afecta al resumen hasta que el reporte sea declarativo y la vista use el flujo declarativo. |

## 7. Bug corregido: show_in_kpi no se enviaba al frontend

**Causa**: Aunque el schema en backend (`MetricSchema`) tenía `show_in_kpi` y se leía bien desde `config.metrics[].show_in_kpi`, la respuesta de la API de schema **no incluía** ese campo al serializar las métricas:

1. En `api_views.py`, al armar `schema_dict` para la API de schema (y para el preview), el diccionario de cada métrica solo tenía `name`, `label`, `expression`, `data_type`, `role`, `format` — **faltaba `show_in_kpi`**.
2. En `serializers.py`, `MetricSchemaSerializer` no declaraba el campo `show_in_kpi`, así que aunque se añadiera al dict, el serializer no lo exponía en `serializer.data`.

**Efecto**: En el frontend, `schema.metrics[].show_in_kpi` era siempre `undefined`. El filtro es `metric.show_in_kpi !== false`; como `undefined !== false` es `true`, todas las métricas se mostraban en el resumen aunque en el builder tuvieran "Mostrar en KPI del resumen" desmarcado.

**Corrección**:
- En `api_views.py`: se añade `"show_in_kpi": getattr(m, "show_in_kpi", True)` al diccionario de cada métrica en las dos rutas que construyen el schema (API de schema y preview).
- En `serializers.py`: se añade `show_in_kpi = serializers.BooleanField(required=False, default=True)` a `MetricSchemaSerializer`.

Con esto, el frontend recibe correctamente `show_in_kpi: false` y las métricas con la opción desmarcada dejan de mostrarse en las tarjetas KPI del resumen.

## 8. Referencia de código

- **Checkbox y modelo en builder**: `builder_detail.html` (field.show_in_kpi / metric.show_in_kpi).
- **Schema**: `schema_service.py` — `MetricSchema.show_in_kpi`, `_build_metric_schema(..., show_in_kpi)`, y lecturas de `config.metrics[].show_in_kpi`.
- **Render declarativo**: `dashboard_detail.html` — `renderDeclarativeSummary(queryResult, schema)`, filtro `metric.show_in_kpi !== false`, y render de hasta 4 KPIs.
- **Render legacy**: `dashboard.js` — `renderSummary(meta, totals)`, construcción de tarjetas desde `Object.keys(totals)` sin schema.
