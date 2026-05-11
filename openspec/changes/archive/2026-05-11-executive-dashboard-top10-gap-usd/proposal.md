# Propuesta: resumen ejecutivo — gap $ vs ayer + Top 10 productos

**Fecha:** 11/05/2026

## Intención

Completar el panel `/reports/dashboard/resumen-ejecutivo-ventas/` respecto a decisiones de dirección: comparativa **en pesos** frente al día anterior y ranking **Top 10** de artículos con criterio explícito y alineado a ventas netas por renglón.

## Alcance

- Contrato JSON del endpoint `executive-summary`: nuevo campo numérico de gap y lista `top_productos`.
- Servicio `executive_sales_summary.py`: consulta agregada por `IDArt`.
- UI `executive_summary.html` + `executive_summary.js`: KPI «Vs ayer» con % + delta $; bloque responsive Top 10.
- Documentación: delta OpenSpec + actualización `SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md`.

## Fuera de alcance

- Cambiar definición de tickets o serie horaria.
- Ranking alternativo por unidades como predeterminado (queda documentado; se puede ampliar v2).

## Riesgos

- Rendimiento: consulta extra por día; mitigar con índices existentes sobre `stock`/`cuentacliente` (monitoreo en producción).
