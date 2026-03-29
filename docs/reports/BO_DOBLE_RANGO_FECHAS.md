# BO - Doble rango de fechas

## Objetivo

Separar el período del reporte `bo-stock-facturacion` en dos rangos:

- `Rango Backorder`: para Backorder y todos sus detalles.
- `Rango Facturación`: para Facturación y Remitos.

## Regla funcional

- `Rango Backorder` aplica a:
  - `BACKORDER TOTAL`
  - `CON STOCK`
  - `CON INGRESO`
  - `SIN STOCK`
  - tabs `Backorder detalle`, `Detalle con stock`, `Detalle con ingreso`, `Detalle sin stock`
- `Rango Facturación` aplica a:
  - `FACTURACIÓN (neto)`
  - `REMITO (no facturados)`
  - `TOTAL FACTURACIÓN + REMITOS`
  - tab `Facturación`
  - tab `Remitos`

## UI (dashboard legacy)

- En `dashboard_detail` para `bo-stock-facturacion` se incluye `filters_period_bo_dual.html`:
  - **Periodo Facturación** (negrita): botones Día / Mes / Año / Personalizado + Fecha desde / Fecha hasta (`periodo_tipo_facturacion`, `fecha_inicio_facturacion`, `fecha_fin_facturacion`). Inputs `type="date"` con altura tipo píldora (`h-9`, `rounded-full`) alineada a los botones.
  - **Periodo Backorder** (negrita): mismo patrón (`periodo_tipo`, `fecha_inicio`, `fecha_fin`).
- `dashboard.js`: `setupBoDualPeriodoTipo`, `syncBoDualSummaryPeriod`, `getFilters` / `applyFilters` / `localStorage` con ambos rangos.

## Implementación técnica

- Frontend envía filtros:
  - `fecha_inicio`, `fecha_fin` (backorder)
  - `fecha_inicio_facturacion`, `fecha_fin_facturacion` (facturación/remitos)
- Backend BO usa:
  - SQL de facturación y remitos con rango facturación
  - SQL de backorder y detalle row-level con rango backorder

## Compatibilidad

Si no se envía `fecha_inicio_facturacion/fecha_fin_facturacion`, el backend usa el rango backorder como fallback.

## Exportación XLSX

La primera hoja del export BO muestra ambos rangos cuando están disponibles en `meta.filters_applied`.
