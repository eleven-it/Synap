# Proposal: Margen ejecutivo — paridad rentabilidad AdministraNET

**Cambio:** `margen-ejecutivo-costo-display-bulto`

## Intent

El panel ejecutivo debe reportar margen bruto **comparable al informe de rentabilidad AdministraNET** (Crystal `ventas_vista_rentabilidad_*.rpt`, vistas `venta_rentabilidad_resumen`).

Análisis VB6 confirmó: costo agregado = **`SUM(PrecioCostoxR)`** con signo; **sin** escala Display/Bulto ni post-proceso intermedio.

Un intento intermedio (normalizar costo por empaque) desalineaba el panel y generaba márgenes espurios en empresas con embalaje (ej. angelita).

**Objetivo final:** suma firmada de `PrecioCostoxR` por renglón, misma convención FA/NC que venta neta del panel.

## Capabilities

### Modified Capabilities
- `reports-ejecutivo-ventas`: REQ-EXEC-MARG-01, REQ-EXEC-MARG-05 — criterio `precio_costoxr_linea`.

## Approach

Costo línea = `COALESCE(stock.PrecioCostoxR, 0)` con signo FA/NC. Venta sin cambios (`PrecioNetoxR`).

## Success Criteria

- Tests verdes; `meta.margen_costo_criterio` = `precio_costoxr_linea`.
- Panel alineado con informe Crystal rentabilidad en piloto.
- Sin cambio en `ventas_netas_dia`.
