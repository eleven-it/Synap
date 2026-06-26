# Informe: Movimientos detallados de flujo de caja

**Slug:** `cash_flow_detailed_movements`  
**Ruta:** `/reports/dashboard/cash_flow_detailed_movements/`

## Propósito

Lista cada movimiento de caja del período con clasificación de flujo (operativo / inversión / financiamiento), subcategoría, contraparte, medios de pago e importes. Complementa el informe `cash_flow_waterfall` (gráfico cascada) y puede consultarse como informe independiente o como panel embebido en la cascada.

## UI (fuente de verdad)

Alineado a `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` y al patrón de `stock-existencias`:

| Elemento | Ubicación |
|----------|-----------|
| Filtros período + caja | `dashboard_detail.html` + `includes/filters_period.html` |
| Tabla principal | `includes/cash_flow_detailed_movements_panel.html` |
| Lógica cliente | `reports/static/reports/js/cash_flow_detailed_movements.js` |
| Orquestación API / modal carga | `reports/static/reports/js/dashboard.js` |

El informe **no** usa el widget genérico `pivot-table` en pantalla (sigue definido en migración para compatibilidad legacy).

## Funcionalidades de la tabla

- Búsqueda predictiva (mínimo 3 caracteres) sobre contraparte, detalle, comprobante, etc.
- Agrupación multinivel (tags) por fecha, flujo, subcategoría, contraparte, caja, sucursal, etc.
- Paginación local (25 / 50 / 100 / 200 filas o grupos de primer nivel).
- Grupos colapsables con totales de ingreso, egreso e importe neto.
- Exportación Excel desde el hero (mismos filtros que la consulta).

## Backend

- Runner: `reports/services/query_runner.py` → `_run_cash_flow_detailed_movements`
- Tabla origen: movimientos de `caja` con reglas de clasificación de flujo compartidas con el resto de informes de caja.

## Relación con `cash_flow_waterfall`

En la cascada, tras cargar el gráfico, `dashboard.js` invoca `fetchDetailedMovements()` (delegado al módulo dedicado), que pide de nuevo los datos con slug `cash_flow_detailed_movements` y muestra el panel con botón «Ver tabla». En el informe standalone la tabla se muestra directamente al aplicar filtros.

## Cambios de refactor (2026-06-01)

1. Panel extraído a include reutilizable (estilo card reportes, sin placeholder oscuro).
2. JS extraído de `dashboard.js` a `cash_flow_detailed_movements.js`.
3. Slug standalone excluido del bloque widget por defecto; modal de carga y export Excel en hero.
4. Filtro multi-caja habilitado en standalone (`id_caja`).
