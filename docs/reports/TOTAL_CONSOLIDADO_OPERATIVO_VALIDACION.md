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
- `_get_pedidos_pendientes_total(..., filtrar_por_fecha=True)` → total pedidos pendientes de entrega. En `total_consolidado_operativo` se llama con `filtrar_por_fecha=False` (no se aplica rango de fechas; es saldo total pendiente de entrega).

`_run_sales_summary` y `_run_total_consolidado_operativo` usan estos helpers.  
`sales_summary` además aplica ahora filtros opcionales sucursales/punto_venta (antes no los aplicaba).

## 1) Nuevo reporte legacy

- **Slug:** `total-consolidado-operativo`
- **Tipo:** Legacy (no declarativo).
- **Filtros:** fecha_inicio, fecha_fin (requeridos); sucursales, punto_venta (opcionales).
- **Migración:** `0030_add_total_consolidado_operativo.py` crea el `ReportDefinition` y un widget `d3-cards`.

## 2) KPI layout (UI)

- Cuatro KPIs en una sola columna (orden):
  1. VENTAS NETAS (filtrado por período).
  2. REMITOS NO FACTURADOS (filtrado por período).
  3. PEDIDOS EN ARMADO (sin filtro por período: saldo total de PED en estado En preparación/Preparado).
  4. TOTAL CONSOLIDADO (VN + Remitos + Pedidos pendientes; este último sin fecha).
- Formato moneda ARS (mismo que el resto del sistema).

## 3) Backend

- **Routing:** `report.slug == "total-consolidado-operativo"` → `_run_total_consolidado_operativo(report, payload)`.
- **Pedidos en armado (KPI):** se obtiene con `_get_pedidos_pendientes_total(..., filtrar_por_fecha=False)`; no se aplica el rango de fechas del reporte (saldo total de PED En preparación/Preparado).
- **Respuesta:** `QueryResult` con `data` = lista de 4 objetos `{ label, value }`, `totals` con las 4 claves, `notes` (período, nota de pedidos sin filtro fecha, y filtros aplicados).

## 4) Frontend

- **dashboard.js:** Si `reportSlug === "total-consolidado-operativo"`:
  - Resumen: grid 1 columna, orden de claves fijo (ventas_netas, remitos_no_facturados, pedidos_pendientes, total_consolidado), etiqueta "PEDIDOS EN ARMADO".
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
   Ventas netas y Remitos no facturados en total-consolidado-operativo usan el mismo período (y sucursales/PV) que los reportes ventas-netas y remitos-no-facturados. El indicador **Pedidos en armado** en total-consolidado-operativo no usa el rango de fechas (es saldo total), por lo que no coincidirá con un reporte de pedidos-pendientes filtrado por período. TOTAL CONSOLIDADO = VN(período) + Remitos(período) + Pedidos en armado (saldo total).

2. **Workspace:**  
   - Añadir dos instancias de Total Consolidado Operativo con filtros distintos (p. ej. períodos o sucursales diferentes).  
   - Comprobar que cada instancia muestra valores distintos y que al recargar se mantienen (filtros por `item_key` en `localStorage`).  
   - Probar "Duplicar" y que la nueva instancia herede filtros y pueda modificarlos de forma independiente.
