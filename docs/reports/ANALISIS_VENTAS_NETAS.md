# Análisis Exhaustivo: Reporte Ventas Netas

**Resumen ejecutivo y tests:** [RESUMEN_ANALISIS_VENTAS_NETAS.md](RESUMEN_ANALISIS_VENTAS_NETAS.md) · [TEST_VENTAS_NETAS_RESULTS.md](TEST_VENTAS_NETAS_RESULTS.md)

**Fecha**: 2026-01-23  
**Reporte**: `ventas_netas`  
**Categoría**: Operational  
**Estado**: Legacy (no declarativo)

---

## 1. ESTRUCTURA DEL MODELO

### 1.1 ReportDefinition (Base de Datos)

**Tabla**: `reports_reportdefinition`

**Campos principales**:
- `slug`: `"ventas_netas"` (identificador único)
- `name`: `"Ventas Netas"`
- `description`: Cálculo de ventas netas con importes sin impuestos
- `category`: `"operational"` (requiere `OperationalReportsPermission`)
- `version`: `"1.0.0"` (no declarativo)
- `config`: JSON con métricas, dimensiones, filtros
- `refresh_interval`: `"daily"`
- `is_active`: `True`
- `is_visible`: `True`
- `show_in_catalog`: `True`

**Configuración (config)**:
```json
{
  "metrics": ["ventas_netas", "ventas_brutas", "notas_credito"],
  "dimensions": ["mes", "sucursal", "punto_venta"],
  "tags": ["sales", "net_sales", "operational"],
  "notes": [
    "Fuente: cuentacliente",
    "Cálculo: Ventas (FA,FB,FC,FE,FM) - NC (NCA,NCB,NCC,NCE,NCM) sin impuestos"
  ],
  "filters": {
    "fecha_inicio": {"type": "date", "required": true, "label": "Fecha Inicio"},
    "fecha_fin": {"type": "date", "required": true, "label": "Fecha Fin"},
    "punto_venta": {"type": "multi_select", "required": false, "label": "Punto de Venta"},
    "sucursales": {"type": "multi_select", "required": false, "label": "Sucursales"},
    "mes_actual": {"type": "boolean", "required": false, "label": "Mes en curso", "default": false}
  }
}
```

### 1.2 ReportWidget (Widgets asociados)

**Widget 1**: Gráfico de barras agrupadas
- `name`: "Ventas Netas por Mes y Sucursal"
- `widget_type`: `"d3-bar-grouped"`
- `order`: 1
- `layout`: `{"w": 12, "h": 6}`
- `configuration`:
  ```json
  {
    "x_field": "mes",
    "y_field": "ventas_netas",
    "group_field": "sucursal",
    "unit": "ARS",
    "show_totals": true
  }
  ```

**Widget 2**: Tabla pivot
- `name`: "Tabla Detallada"
- `widget_type`: `"pivot-table"`
- `order`: 2
- `layout`: `{"w": 12, "h": 8}`
- `configuration`:
  ```json
  {
    "rows": ["mes", "sucursal"],
    "columns": ["punto_venta"],
    "values": ["ventas_netas", "ventas_brutas", "notas_credito"],
    "aggregation": "sum"
  }
  ```

---

## 2. VISTAS (Django Views)

### 2.1 DashboardDetailView

**Archivo**: `reports/views.py` (líneas 115-156)

**Responsabilidades**:
1. **Autenticación**: `ReportsLoginRequiredMixin`
2. **Autorización**: Verifica `OperationalReportsPermission` para reportes operacionales
3. **Obtención del reporte**: Filtra por `slug`, `is_active`, `empresa`
4. **Context data**:
   - `report`: Instancia de `ReportDefinition`
   - `widgets`: QuerySet de widgets asociados
   - `dashboard_api_url`: URL para `/api/reports/query/`
   - `workspace_api_url`: URL para workspace
   - `schema_api_url`: URL para schema del reporte
   - `is_declarative`: `False` para ventas_netas (no tiene `version: "declarative-v1"`)
   - `report_config_for_script` + `|json_script` en plantilla: config para JS sin XSS

**Template**: `reports/dashboard_detail.html`

**URL**: `/reports/dashboard/<slug>/` → `/reports/dashboard/ventas_netas/`

---

## 3. API VIEWS (Backend)

### 3.1 ReportQueryAPIView

**Archivo**: `reports/api_views.py` (líneas 79-150+)

**Endpoint**: `POST /api/reports/query/`

**Flujo**:
1. **Validación**: `ReportQueryRequestSerializer` valida payload
2. **Autorización**: Verifica permisos operacionales/gerenciales
3. **Enriquecimiento**: Agrega `base_empresa` desde sesión a `filters`
4. **Ejecución**: Llama a `QueryRunnerService(user).run(report, payload)`
5. **Respuesta**: Serializa con `ReportQueryResponseSerializer`

**Payload esperado**:
```json
{
  "slug": "ventas_netas",
  "limit": 200,
  "filters": {
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-01-31",
    "punto_venta": [1, 2, 3],
    "sucursales": [10, 20],
    "mes_actual": true
  }
}
```

### 3.2 Filtros API (Punto de Venta, Sucursales)

**Endpoint**: `GET /api/reports/filters/?type=puntos_venta`  
**Endpoint**: `GET /api/reports/filters/?type=sucursales`

Carga opciones dinámicas para los multi-select de filtros.

---

## 4. QUERY RUNNER (Lógica de Negocio)

### 4.1 QueryRunnerService._run_ventas_netas

**Archivo**: `reports/services/query_runner.py` (líneas 312-560)

**Fuente de datos**: Tabla `cuentacliente` (MySQL, base administraNET)

**Lógica**:

1. **Resolución de fechas**: `_resolve_period_dates(filters)`
   - Prioriza `fecha_inicio` / `fecha_fin` recibidas (las mostradas en UI)
   - Solo recalcula si faltan (usando `dia_actual`, `mes_actual`, `año_actual`)

2. **Filtros aplicados**:
   - `cc.Fecha >= fecha_inicio AND cc.Fecha <= fecha_fin`
   - `cc.Anulado = 'No'`
   - `cc.CodigoMovimiento <> 0` (excluye movimientos sin código)
   - `cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')`
   - `cc.id_pv IN (...)` si se seleccionan puntos de venta
   - `cc.CodSucursal IN (...)` si se seleccionan sucursales

3. **Cálculo de métricas**:
   ```sql
   SUM(CASE 
     WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') 
     THEN cc.SubtotalDesc 
     ELSE 0 
   END) AS ventas_brutas,
   
   SUM(CASE 
     WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') 
     THEN cc.SubtotalDesc 
     ELSE 0 
   END) AS notas_credito,
   
   SUM(CASE 
     WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') 
     THEN cc.SubtotalDesc 
     ELSE -cc.SubtotalDesc 
   END) AS ventas_netas
   ```

4. **Agrupación**: `DATE_FORMAT(cc.Fecha, '%Y-%m') AS mes`, `s.nombre AS nombre_sucursal`, `pv.descripcion AS nombre_punto_venta`

5. **JOINs**:
   - `LEFT JOIN sucursales s ON cc.CodSucursal = s.CodSucursal`
   - `LEFT JOIN punto_venta pv ON cc.id_pv = pv.id`

6. **Performance**: `SET SESSION max_execution_time = 90000` + `MAX_EXECUTION_TIME(90000)` hint

7. **Resultado**: `QueryResult` con:
   - `data`: Array de filas (mes, nombre_sucursal, nombre_punto_venta, ventas_brutas, notas_credito, ventas_netas)
   - `totals`: Suma total de cada métrica
   - `notes`: Período, total registros, fuente de datos

---

## 5. TEMPLATES

### 5.1 dashboard_detail.html

**Archivo**: `reports/templates/reports/dashboard_detail.html`

**Estructura para ventas_netas (legacy)**:

#### A. Header
- Título del reporte: `{{ report.name }}`
- Botón "Mostrar filtros" (`data-filters-toggle`)
- Botón "Exportar Excel"

#### B. Summary (KPIs)
- `<div id="report-summary">` con `data-summary-grid`
- Muestra tarjetas para: `ventas_brutas`, `notas_credito`, `ventas_netas`
- Renderizado por `dashboard.js` → `renderSummary()`

#### C. Filtros (ocultos por defecto)
- `<div data-filters-wrapper class="hidden">`
- `<form id="report-filters" data-filters-container class="hidden">`
- **Legacy**: Usa `{% include "reports/includes/filters_period.html" %}` y `{% include "reports/includes/filters_interval.html" %}`
- **Filtros incluidos**:
  - **Período**: Día / Mes / Año / Personalizado (botones + select oculto)
  - **Fecha desde / Fecha hasta**: inputs tipo date
  - **Punto de venta**: multi-select con tags UI
  - **Sucursales**: multi-select con tags UI
  - **Intervalo de actualización**: select (30s, 5m, 10m, 1h, 2h)

#### D. Dashboard Root
- `<div id="dashboard-root" data-report-slug="ventas_netas">`
- **Elemento específico**: `<p id="ventas-netas-summary-period">` (muestra período seleccionado)
- Contenedor para widgets (gráfico + tabla)

#### E. Scripts
- **Inline** (solo declarativo): NO se ejecuta para ventas_netas
- **dashboard.js**: Manejo de filtros, fetch, renderizado
- **widget_engine.js**: NO se carga (solo declarativo)
- **d3.min.js**: Para gráficos

### 5.2 filters_period.html (Include)

**Archivo**: `reports/templates/reports/includes/filters_period.html`

**Contenido**:
- `<div id="period-filters-container">` (raíz con id para setupPeriodoTipo)
- Botones de período: `.periodo-tipo-btn` con `data-periodo="dia_actual|mes_actual|año_actual|personalizado"`
- Select oculto: `<select id="periodo_tipo">`
- Inputs de fecha: `<input id="fecha_inicio">`, `<input id="fecha_fin">`
- **Script inline** (IIFE):
  - Adjunta handlers de click a botones
  - Actualiza fechas según período seleccionado
  - Actualiza estado visual (botón activo)
  - Dispara `change` en select para que `setupPeriodoTipo` (dashboard.js) recargue datos

---

## 6. JAVASCRIPT (Frontend)

### 6.1 dashboard.js

**Archivo**: `reports/static/reports/js/dashboard.js`

#### Funciones clave para ventas_netas:

**A. Inicialización**:
```javascript
if (dashboardRoot && !isWorkspaceMode) {
  loadFilterOptions().then(() => {
    setupPeriodoTipo();
    setupRefreshIntervalButtons();
    fetchDashboardData();
  });
}
```

**B. `loadFilterOptions()`** (líneas 5375-5495):
- Carga opciones de `puntos_venta` y `sucursales` desde API `/filters/`
- Inicializa componentes de tags (`initializeTagsFilter`)
- Aplica filtros guardados desde `localStorage`

**C. `setupPeriodoTipo()`** (líneas 5628-5830):
- Adjunta handlers a `.periodo-tipo-btn` y `#periodo_tipo`
- Define `setPeriodo(tipo)`: actualiza fechas, labels, guarda filtros, recarga datos
- Define `updateButtonStates(selectedValue)`: actualiza clases CSS
- Escucha `change` en select y clicks en botones
- Marca contenedor con `data-periodo-setup="true"` (idempotencia)

**D. `setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin)`** (líneas 6347-6382):
- **Helper** que prioriza fechas de inputs cuando ambas existen
- Solo recalcula si falta alguna
- Asegura que las fechas enviadas al backend coincidan con las mostradas

**E. `getFilters()`** (líneas 6390-6420):
- Para `ventas_netas`: construye objeto `filters` con:
  - `fecha_inicio`, `fecha_fin` (usando `setPeriodDatesFromForm`)
  - `punto_venta` (array de ids seleccionados)
  - `sucursales` (array de ids seleccionados)
  - `refresh_interval`
  - Flags: `dia_actual`, `mes_actual`, `año_actual` según período

**F. `fetchDashboardData()`** (líneas 6688-6780):
- Obtiene filtros con `getFilters()`
- POST a `/api/reports/query/` con `{ slug, limit: 200, filters }`
- Timeout: 120s (`AbortController`)
- Guard: `fetchDashboardDataInFlight` (previene duplicados)
- Guarda filtros en `localStorage` tras éxito
- Renderiza summary (KPIs) y widgets

**G. `renderSummary(data)`** (líneas 3360-4000+):
- Extrae `totals` de la respuesta
- Orden específico para ventas_netas: `ventas_brutas`, `notas_credito`, `ventas_netas`
- Crea tarjetas con formato de moneda
- Destaca `ventas_netas` con color más llamativo (sky-600)
- Muestra "Última actualización" con timestamp

**H. `saveFilters()` / `loadFilters()` / `applyFilters()`**:
- **Storage key**: `report_filters_ventas_netas`
- Guarda: periodo_tipo, fecha_inicio, fecha_fin, punto_venta, sucursales, refresh_interval
- Carga al inicializar y aplica a los controles

**«Ver tabla»:** `dashboard.js` es `type="module"`. El click de `[data-toggle-table]` lo cablea `attachTableToggle` **en el mismo módulo** (llama a `renderTable` con el dataset en caché). No usar el `attachTableToggle` de `cash_flow_detailed_movements.js` (script clásico, no visible al módulo). Sin esa función el gráfico pinta y el botón no muestra la tabla.

**I. `initializeFiltersToggle()`** (líneas 222-265):
- Adjunta handler al botón "Mostrar filtros"
- Alterna visibilidad de `data-filters-wrapper` y `data-filters-container`
- **Dispara** `reportPeriodFiltersReady` al **abrir** filtros (para legacy)

### 6.2 filters_period.html (Script inline)

**Funcionalidad**:
- Ejecuta al cargar el include (legacy)
- Adjunta handlers de click a `.periodo-tipo-btn`
- Actualiza `#fecha_inicio` y `#fecha_fin` según período
- Actualiza estado visual (botón activo)
- Dispara `change` en `#periodo_tipo` para que dashboard.js recargue

**Ventaja**: Garantiza que los botones funcionen incluso si `setupPeriodoTipo` no se ejecuta o falla.

---

## 7. FLUJO DE DATOS COMPLETO

### 7.1 Carga inicial

```
1. Usuario navega a /reports/dashboard/ventas_netas/
   ↓
2. DashboardDetailView.get_context_data()
   - Obtiene ReportDefinition (slug=ventas_netas)
   - Pasa report, widgets, URLs, is_declarative=False
   ↓
3. Template dashboard_detail.html renderiza:
   - Header con título y botones
   - Summary (vacío, "Cargando...")
   - Filtros (ocultos) con filters_period.html
   - Dashboard root con ventas-netas-summary-period
   ↓
4. Scripts se cargan:
   - d3.min.js (defer)
   - dashboard.js (module, deferred)
   ↓
5. dashboard.js ejecuta:
   - initializeFiltersToggle() → oculta filtros
   - loadFilterOptions() → carga puntos_venta, sucursales, aplica filtros guardados
   - setupPeriodoTipo() → adjunta handlers a botones de período
   - fetchDashboardData() → POST a /api/reports/query/
   ↓
6. Backend (ReportQueryAPIView):
   - Valida payload
   - Agrega base_empresa desde sesión
   - Llama QueryRunnerService.run(report, payload)
   ↓
7. QueryRunnerService.run():
   - Resuelve fechas con _resolve_period_dates()
   - Ejecuta _run_ventas_netas()
   ↓
8. _run_ventas_netas():
   - Conecta a MySQL (administranet89 u otra base)
   - Ejecuta consulta SQL con filtros
   - Agrupa por mes, sucursal, punto_venta
   - Calcula ventas_brutas, notas_credito, ventas_netas
   - Retorna QueryResult con data, totals, notes
   ↓
9. Frontend recibe respuesta:
   - renderSummary() → muestra KPIs (ventas_brutas, notas_credito, ventas_netas)
   - renderWidget() → renderiza gráfico D3 (barras agrupadas)
   - renderWidget() → renderiza tabla pivot
   ↓
10. Usuario ve:
    - 3 KPIs con totales
    - Gráfico de barras por mes y sucursal
    - Tabla detallada con breakdown
```

### 7.2 Cambio de período (ej. usuario selecciona "Mes")

```
1. Usuario abre "Mostrar filtros"
   ↓
2. initializeFiltersToggle() → muestra filtros, dispara reportPeriodFiltersReady
   ↓
3. setupPeriodoTipo() ejecuta (si no lo hizo antes)
   ↓
4. Usuario hace click en botón "Mes"
   ↓
5. Script inline de filters_period.html:
   - Actualiza #periodo_tipo.value = "mes_actual"
   - Actualiza clases CSS (botón activo)
   - Llama updateDates("mes_actual") → setea #fecha_inicio, #fecha_fin
   - Dispara change en #periodo_tipo
   ↓
6. setupPeriodoTipo() handler de change:
   - Ejecuta setPeriodo("mes_actual")
   - Actualiza labels (#ventas-netas-summary-period)
   - Llama saveFilters()
   - Llama fetchDashboardData()
   ↓
7. fetchDashboardData():
   - getFilters() → lee #fecha_inicio, #fecha_fin (ya actualizados)
   - setPeriodDatesFromForm() → usa esos valores (prioridad a inputs)
   - POST a /api/reports/query/ con nuevas fechas
   ↓
8. Backend ejecuta consulta con nuevas fechas
   ↓
9. Frontend actualiza KPIs, gráfico y tabla
```

---

## 8. VALIDACIÓN CONTRA VB6

**Documento**: `docs/reports/VALIDACION_VENTAS_NETAS.md`

**Resumen**:
- ✅ Tabla `cuentacliente` correcta
- ✅ Tipos de comprobante correctos (FA–FM, NCA–NCM)
- ✅ Campo `SubtotalDesc` correcto (sin impuestos)
- ✅ Filtro `Anulado = 'No'` correcto
- ⚠️ `CodigoMovimiento <> 0`: podría excluir movimientos válidos (revisar)
- ⚠️ Excluye ND* y NCT (notas de débito y crédito tipo T)
- ⚠️ No usa `ImporteVenta` como fallback (solo `SubtotalDesc`)

---

## 9. CACHÉ Y PERFORMANCE

### 9.1 Estrategia de caché

**TTL**: Dinámico según antigüedad de datos
- Si `fecha_fin` es reciente (< 7 días): TTL corto (300s)
- Si es antigua (> 30 días): TTL largo (3600s)
- Intermedio: 1800s

**Cache key**: `report_cache_{slug}_{payload_hash}`

**Invalidación**: Por TTL o cambio en filtros (nuevo payload_hash)

### 9.2 Performance SQL

- **Hint**: `MAX_EXECUTION_TIME(90000)` (90s)
- **Session**: `SET SESSION max_execution_time = 90000`
- **Timeout frontend**: 120s (`AbortController`)

---

## 10. PERMISOS Y SEGURIDAD

### 10.1 Permisos requeridos

- **Autenticación**: `ReportsLoginRequiredMixin` (sesión válida)
- **Autorización**: `OperationalReportsPermission` (rol operacional)

### 10.2 Validaciones

- `is_active = True` (reporte activo)
- `empresa` match (global o empresa del usuario)
- CSRF token en POST requests
- SQL parametrizado (previene SQL injection)

---

## 11. ESTADO ACTUAL Y MEJORAS RECIENTES

### 11.1 Cambios aplicados (sesión actual)

1. **Período funcional en legacy**:
   - Añadido `id="period-filters-container"` a `filters_period.html`
   - Script inline en `filters_period.html` para handlers de click
   - Dispatch de `reportPeriodFiltersReady` al abrir filtros (dashboard.js)

2. **Uso de fechas de inputs**:
   - Helper `setPeriodDatesFromForm` en frontend (prioriza inputs)
   - Helper `_resolve_period_dates` en backend (prioriza recibidas)
   - **Garantía**: Las fechas mostradas son las usadas en SQL

3. **Period label visible**:
   - `<p id="ventas-netas-summary-period">` en dashboard-root
   - Actualizado por `setPeriodo()` y `syncPeriodLabel()`

### 11.2 Issues conocidos (documentados)

Ver `VALIDACION_VENTAS_NETAS.md`:
- Encoding de `Estado` en comp_ped (riesgo)
- Exclusión de ND* y NCT (verificar si es intencional)
- `CodigoMovimiento <> 0` (podría excluir movimientos válidos)

---

## 12. TESTING (A ejecutar)

### 12.1 Tests de estructura

- [ ] Verificar que el reporte existe en DB
- [ ] Verificar widgets asociados
- [ ] Verificar configuración (config, metadata)
- [ ] Verificar permisos

### 12.2 Tests de API

- [ ] POST /api/reports/query/ con filtros válidos
- [ ] Validar estructura de respuesta (data, totals, notes)
- [ ] Validar cálculos (ventas_brutas - notas_credito = ventas_netas)
- [ ] Test con punto_venta filtrado
- [ ] Test con sucursales filtradas
- [ ] Test con período día/mes/año

### 12.3 Tests de UI

- [ ] Cargar /reports/dashboard/ventas_netas/
- [ ] Verificar KPIs se muestran
- [ ] Abrir "Mostrar filtros"
- [ ] Cambiar período a "Mes" → verificar fechas actualizadas
- [ ] Cambiar período a "Personalizado" → verificar inputs habilitados
- [ ] Seleccionar punto de venta → verificar recarga
- [ ] Verificar gráfico renderiza
- [ ] Verificar tabla renderiza

### 12.4 Tests de integración

- [ ] Verificar fechas de inputs coinciden con SQL ejecutado
- [ ] Verificar filtros guardados en localStorage
- [ ] Verificar filtros restaurados al recargar página
- [ ] Verificar exportación a Excel

---

## 13. DEPENDENCIAS

### 13.1 Python
- Django (models, views, migrations)
- MySQLdb (conexión a administraNET)
- django-rest-framework (API views, serializers)

### 13.2 JavaScript
- D3.js (gráficos)
- Fetch API (requests)
- localStorage (persistencia de filtros)

### 13.3 Base de datos
- **PostgreSQL**: Metadatos (ReportDefinition, ReportWidget)
- **MySQL**: Datos transaccionales (cuentacliente, sucursales, punto_venta)

---

## 14. DIAGRAMA DE ARQUITECTURA

```
┌─────────────────────────────────────────────────────────────┐
│                         USUARIO                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    DJANGO VIEW LAYER                        │
│  DashboardDetailView (/reports/dashboard/ventas_netas/)    │
│    - Autenticación (ReportsLoginRequiredMixin)             │
│    - Autorización (OperationalReportsPermission)           │
│    - Context: report, widgets, URLs, is_declarative        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   TEMPLATE LAYER                            │
│  dashboard_detail.html                                      │
│    - Header (título, botones)                              │
│    - Summary (KPIs: ventas_brutas, notas_credito, netas)  │
│    - Filtros (ocultos): filters_period.html + interval     │
│    - Dashboard root (widgets)                              │
│    - Scripts: dashboard.js, d3.min.js                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (JavaScript)                     │
│  dashboard.js                                               │
│    - loadFilterOptions() → carga PV, sucursales            │
│    - setupPeriodoTipo() → handlers de período              │
│    - fetchDashboardData() → POST /api/reports/query/       │
│    - renderSummary() → KPIs                                │
│    - renderWidget() → gráfico D3 + tabla                   │
│                                                             │
│  filters_period.html (inline script)                        │
│    - Handlers de click en botones Día/Mes/Año              │
│    - Actualiza fecha_inicio, fecha_fin                     │
│    - Dispara change en periodo_tipo                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓ POST /api/reports/query/
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                              │
│  ReportQueryAPIView                                         │
│    - Validación (ReportQueryRequestSerializer)             │
│    - Autorización (permisos)                               │
│    - Enriquecimiento (base_empresa desde sesión)           │
│    - Ejecución: QueryRunnerService.run()                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   QUERY RUNNER                              │
│  QueryRunnerService._run_ventas_netas()                     │
│    - _resolve_period_dates() → prioriza fechas recibidas   │
│    - Conecta a MySQL (base administraNET)                  │
│    - Construye SQL con filtros                             │
│    - Ejecuta consulta                                      │
│    - Agrupa por mes, sucursal, punto_venta                 │
│    - Calcula métricas (ventas_brutas, NC, netas)           │
│    - Retorna QueryResult                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   DATA SOURCES                              │
│  MySQL (administranet89)                                    │
│    - cuentacliente (transacciones)                         │
│    - sucursales (maestro)                                  │
│    - punto_venta (maestro)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 15. ARCHIVOS INVOLUCRADOS

### Modelos y Migraciones
- `reports/models.py` → ReportDefinition, ReportWidget
- `reports/migrations/0008_add_ventas_netas_report.py` → Creación inicial

### Views
- `reports/views.py` → DashboardDetailView
- `reports/api_views.py` → ReportQueryAPIView, ReportFiltersAPIView

### Services
- `reports/services/query_runner.py` → QueryRunnerService._run_ventas_netas
- `reports/services/connection_pool.py` → get_mysql_pool
- `reports/services/schema_service.py` → ReportSchemaService (para /schema/ endpoint)
- `reports/services/export_service.py` → ExportService (Excel export)

### Templates
- `reports/templates/reports/dashboard_detail.html` → Layout principal
- `reports/templates/reports/includes/filters_period.html` → Filtros de período
- `reports/templates/reports/includes/filters_interval.html` → Intervalo de actualización

### JavaScript
- `reports/static/reports/js/dashboard.js` → Lógica principal
- `reports/static/reports/vendor/d3.min.js` → Gráficos

### Documentación
- `docs/reports/VALIDACION_VENTAS_NETAS.md` → Validación vs VB6
- `docs/general/CONTEXTO_TABLAS_VB6_INFORMES.md` → Contexto general

---

## 16. PRÓXIMOS PASOS (Testing)

Ejecutar suite de tests funcionales para validar:
1. Estructura de datos (DB, config, widgets)
2. API endpoints (query, filters, schema)
3. Cálculos (ventas_brutas - NC = ventas_netas)
4. Filtros (período, PV, sucursales)
5. UI (carga, interacción, renderizado)
6. Integración (fechas inputs → SQL)
