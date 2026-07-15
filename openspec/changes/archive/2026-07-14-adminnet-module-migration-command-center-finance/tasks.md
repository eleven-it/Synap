# Tareas — adminnet-module-migration-command-center-finance

**Fase actual:** P0 implementado — pendiente UAT (6.x)

## Fase 1 — Fundación (clasificación caja)

- [x] 1.1 Crear `reports/services/executive_dashboard/caja_classification.py` con `classify_movement()` y `get_payment_method()` (copiar lógica de `query_runner.py`).
- [x] 1.2 Modificar `query_runner.py` para importar/delegar en `caja_classification` sin cambiar comportamiento de informes cash-flow.
- [x] 1.3 Tests unitarios `reports/tests/test_caja_classification.py`: REC→cobranzas, FA→ventas, exclusión tipos internos en helper SQL.

## Fase 2 — Backend métricas

- [x] 2.1 Crear `tesoreria_metrics.py` con `fetch_tesoreria_resumen()`: saldos ini/fin (`caja.Saldo`), flujos, subcategorías, `por_tipo_caja`, `banco_disponible=false`, notas meta.
- [x] 2.2 SQL tesorería: filtro sucursal `cod_sucursal`; excluir `Cierre de Caja` y `Transferencia de Fondos` del neto operativo.
- [x] 2.3 Crear `ventas_cobros_metrics.py` con `fetch_ventas_cobros_resumen()`: `facturado_por_medio` (`resumen_venta_cv` + fallback `cuentacliente`).
- [x] 2.4 Serie `cobrado_caja_por_medio`: agregado `caja` ingresos + `get_payment_method`; buckets y `total` con 2 decimales.
- [x] 2.5 `meta.notas_semanticas` en ambos: facturado ≠ cobrado; sin claves impuestos.

## Fase 3 — API e orquestador

- [x] 3.1 Vistas `ExecutiveDashboardTesoreriaResumenAPIView` y `ExecutiveDashboardVentasCobrosResumenAPIView` en `executive_dashboard_api_views.py` (mixin existente).
- [x] 3.2 Rutas en `reports/api_urls.py`: `tesoreria/resumen/`, `ventas/cobros/resumen/`.
- [x] 3.3 `command_center.py`: `ENDPOINTS_RELATIVOS` + llamadas `_safe_legacy_area` para `tesoreria` y `ventas_cobros`.
- [x] 3.4 Verificar orquestador: 7 áreas operativas; sin `areas.impuestos`; degradación parcial por área.

## Fase 4 — UI Command Center

- [x] 4.1 `command_center.html`: tarjeta **Tesorería (caja)** (saldo ini/fin, variación, ventas/cobranzas/proveedores, nota banco).
- [x] 4.2 `command_center.html`: tarjeta **Ventas por cobro** (dos bloques facturado | cobrado en caja).
- [x] 4.3 `command_center.js`: render KPIs desde `areas.tesoreria` y `areas.ventas_cobros`; formato moneda es-AR.
- [x] 4.4 Cache bust query string en template (`?v=20260519d`).

## Fase 5 — Tests y documentación

- [x] 5.1 Ampliar `test_executive_dashboard_contract.py`: shape `tesoreria/resumen`, `ventas/cobros/resumen`, orquestador con nuevas áreas.
- [x] 5.2 Tests: estructura JSON, `banco_disponible` false, sin `impuestos`.
- [x] 5.3 Ejecutar tests en contenedor (22 OK).
- [x] 5.4 Actualizar `docs/reports/EXECUTIVE_DASHBOARD_API.md` con contratos JSON y rutas P0.

## Fase 6 — Verificación (sdd-verify)

- [x] 6.1 UAT manual: totales tesorería ≈ informe `cash_flow_waterfall` mismo período (`administranet`, 01–19/05/2026) — ver `verify-report.md`.
- [x] 6.2 Checklist specs: escenarios REQ-ED-TES y REQ-ED-COB cubiertos por tests + UAT documentado.

## P1 — Banco, detalle cobros, movimientos caja

- [x] P1.1 `tesoreria/banco/resumen/` sobre `librobanco` + `cuenta_banco`.
- [x] P1.2 `ventas/cobros/detalle/` con fallback caja + medio_cobpag REC.
- [x] P1.3 `tesoreria/movimientos-caja/` paginado (excluye cierre/transferencia).
