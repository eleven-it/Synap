# Total Consolidado Operativo — Validación e implementación

## 0) Validación previa (query_runner.py)

**Existente:** Ya existía lógica equivalente en `_run_sales_summary()`:
- Ventas Netas (cuentacliente, FA/FB/FC/FE/FM menos NCA/NCB/…)
- Remitos no facturados (comp_ped, REM, Pendiente)
- Pedidos pendientes (comp_ped, PED, En preparación/Preparado)
- Total consolidado = suma de los tres

**Decisión:** No duplicar. Se extrajeron helpers reutilizables:

- `_parse_sucursales_pv(filters)` → normaliza sucursales y punto_venta desde filters.
- `_get_ventas_netas_total(cursor, fecha_inicio, fecha_fin, sucursales, puntos_venta)` → total ventas netas con filtros opcionales.
- `_get_remitos_no_facturados_total(...)` → total remitos no facturados.
- `_get_pedidos_pendientes_total(...)` → total pedidos pendientes de entrega.

`_run_sales_summary` y `_run_total_consolidado_operativo` usan estos helpers.  
`sales_summary` además aplica ahora filtros opcionales sucursales/punto_venta (antes no los aplicaba).

## 1) Nuevo reporte legacy

- **Slug:** `total-consolidado-operativo`
- **Tipo:** Legacy (no declarativo).
- **Filtros:** fecha_inicio, fecha_fin (requeridos); sucursales, punto_venta (opcionales).
- **Migración:** `0030_add_total_consolidado_operativo.py` crea el `ReportDefinition` y un widget `d3-cards`.

## 2) KPI layout (UI)

- Cuatro KPIs en una sola columna (orden):
  1. VENTAS NETAS  
  2. REMITOS NO FACTURADOS  
  3. PEDIDOS PENDIENTES DE ENTREGA  
  4. TOTAL CONSOLIDADO  
- Formato moneda ARS (mismo que el resto del sistema).

## 3) Backend

- **Routing:** `report.slug == "total-consolidado-operativo"` → `_run_total_consolidado_operativo(report, payload)`.
- **Respuesta:** `QueryResult` con `data` = lista de 4 objetos `{ label, value }`, `totals` con las 4 claves, `notes` (período y filtros aplicados).

## 4) Frontend

- **dashboard.js:** Si `reportSlug === "total-consolidado-operativo"`:
  - Resumen: grid 1 columna, orden de claves fijo (ventas_netas, remitos_no_facturados, pedidos_pendientes, total_consolidado), etiqueta "PEDIDOS PENDIENTES DE ENTREGA".
  - Widget (workspace): si `data` es lista de `{ label, value }`, se renderizan 4 cards verticales desde `data`.

## 5) Workspace — múltiples instancias

- **item_key:** `"<slug>"` (legacy) o `"<slug>::<instance_id>"` (duplicados).
- **Backend (api_views.py):**
  - GET: cada slot incluye `item_key`, `slug`, `instance_id`, `display_name`.
  - POST: `allow_duplicate: true` → se genera `instance_id` y se añade `slug::instance_id`.
  - DELETE: body `item_key` (o `slug` por compatibilidad).
  - PATCH: body `items` (u `order`) = lista de `item_key` en el orden deseado.
- **Frontend:**
  - Filtros por instancia: `localStorage` clave `report_filters_<item_key>`.
  - Botón "Duplicar" en slots de reportes con `allowDuplicateSlugs` (p. ej. total-consolidado-operativo): POST con `allow_duplicate: true`, copia de filtros del item original al nuevo `item_key`, recarga del workspace.
  - Catálogo: para `total-consolidado-operativo` se envía `allow_duplicate: true` y el botón no se deshabilita al agregar (se pueden crear varias instancias).

## 6) Validación final sugerida

1. **Consistencia con reportes individuales:**  
   Mismos filtros (fechas, sucursales, punto_venta) en ventas-netas, remitos-no-facturados, pedidos-pendientes y total-consolidado-operativo → la suma de totales de los tres reportes debe coincidir con TOTAL CONSOLIDADO del nuevo reporte.

2. **Workspace:**  
   - Añadir dos instancias de Total Consolidado Operativo con filtros distintos (p. ej. períodos o sucursales diferentes).  
   - Comprobar que cada instancia muestra valores distintos y que al recargar se mantienen (filtros por `item_key` en `localStorage`).  
   - Probar "Duplicar" y que la nueva instancia herede filtros y pueda modificarlos de forma independiente.
