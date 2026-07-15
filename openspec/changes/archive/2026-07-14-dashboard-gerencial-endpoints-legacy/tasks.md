# Tareas — dashboard-gerencial-endpoints-legacy

**Fase actual:** listo para `sdd-apply` (P0)

## P0 — Endpoints resumen

- [x] T1 — `reports/services/executive_dashboard/base.py` + `exceptions.py`
- [x] T2 — `ventas_metrics.py` + tests contrato
- [x] T3 — `GET .../ventas/resumen/` + URL
- [x] T4 — `inventory_metrics.py` + vista resumen
- [x] T5 — `purchase_metrics.py` + vista resumen
- [x] T6 — `manufacturing_metrics.py` + vista resumen
- [x] T7 — `cross_metrics.py` + vista resumen
- [x] T8 — `command_center.py` + `GET .../executive-dashboard/`
- [x] T9 — Tests integración permisos + `docs/reports/EXECUTIVE_DASHBOARD_API.md`

## P1 — Detalle paginado

- [x] T10 — `ventas/pedidos-pendientes/`, `ventas/remitos-no-facturados/`
- [x] T11 — `cruzados/backorder/`, `inventario/existencias/`

## UI Command Center

- [x] T-UI1 — Plantilla `command_center.html` + `command_center.js`
- [x] T-UI2 — `DashboardDetailView` slug `command-center-gerencial`
- [x] T-UI3 — Migración catálogo `0032_add_command_center_gerencial_report`
- [x] T-UI4 — CRM eliminado del orquestador (deprecado)

## P2 — Refactor opcional

- [x] T13 — Refactor opcional: `query_runner` importa `ventas_metrics`
