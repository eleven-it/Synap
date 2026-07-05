# Proposal: Informe "Clientes sin ventas por vendedor" (migración mayoristapp → reports)

## Intent

Portar a Synap el informe nuevo del PHP `administraNET-ecom` (post‑corte de migración, jun. 2026) que lista **clientes activos sin comprobantes en un período**, agrupados por vendedor, con resumen por vendedor y global para gráficos. Es el primer informe P0 del delta reconciliado en [docs/ecom/DELTA_PHP_2026Q2.md](../../../docs/ecom/DELTA_PHP_2026Q2.md) y sirve de patrón replicable para los demás informes pendientes.

## Scope

### In Scope
- Servicio `reports/services/clientes_sin_ventas.py` con la lógica de `relay-clientes-vendedor.php` (modos `seleccion` y `sin_ventas`), SQL parametrizado sobre MySQL legacy.
- Relay API operativo y gerencial bajo `/api/reports/clientes-sin-ventas/...` (permisos Operational/Managerial), con permisos de sesión (gerencial, supervisor, vendedor_a_cargo, todos_clientes).
- `ReportDefinition` + slug `clientes-sin-ventas-vendedor` accesible en `/reports/dashboard/<slug>/` con UI canónica (`dashboard_detail.html`), filtros de período/vendedor/domicilio y gráfico por vendedor/global.
- Tests unitarios de servicio y relay (parseo de filtros, permisos, forma de respuesta) en `reports/tests/`.
- Actualizar `DELTA_PHP_2026Q2.md` (estado → migrado) y `EcomMigrationCheckpoint`.

### Out of Scope
- Otros informes del delta (utilidad gerencial, cobranzas, etc.) — changes propios posteriores.
- Rediseño del sistema de permisos; se reutiliza `reports/permissions.py`.
- Paridad pixel con la UI PHP (Chart.js/DataTables): se adopta la UI canónica Synap.

## Capabilities

### New Capabilities
- `reports-clientes-sin-ventas`: informe de clientes activos sin comprobantes en un período, por vendedor, con resumen para gráficos y control de acceso operativo/gerencial.

### Modified Capabilities
- None

## Approach

Replicar el patrón ya usado para ventas netas ([reports/ventas_netas_relay_views.py](../../../reports/ventas_netas_relay_views.py) + `reports/services/ventas_netas.py`): servicio con SQL parametrizado vía `core.mysql_pool` (`get_mysql_pool().get_connection(base_empresa)`), vistas relay DRF con permisos, y una `ReportDefinition` para la UI canónica. Normalizar tipos con `core.utils.administranet_types`. Sustituir la concatenación de SQL del PHP por parámetros (`%s`) y listas de IDs validadas a `int`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `reports/services/clientes_sin_ventas.py` | New | Lógica de consulta y resumen |
| `reports/clientes_sin_ventas_relay_views.py` | New | APIViews operativo/gerencial |
| `reports/api_urls.py` | Modified | Registrar rutas relay |
| `reports/migrations/00XX_add_clientes_sin_ventas_report.py` | New | ReportDefinition + checkpoint |
| `reports/tests/test_clientes_sin_ventas_relay.py` | New | Tests |
| `docs/ecom/DELTA_PHP_2026Q2.md` | Modified | Estado del informe |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| SQL inyectable (PHP concatena filtros/fechas) | Med | Parámetros `%s`, IDs a `int`, fechas parseadas |
| Diferencias de permisos sesión Synap vs PHP | Med | Mapear claves sesión (`inf_gerenciales`, `supervisor_venta`, `vendedor_a_cargo`, `todos_clientes`, `usa_id_manual`) con defaults seguros |
| Paridad de conteos con PHP no verificable sin BD real | Med | Tests unitarios de forma + validación operativa en Fase D |

## Rollback Plan

Revertir el commit del change: quitar rutas en `api_urls.py`, eliminar servicio/vistas/tests nuevos y revertir la migración (`migrate reports 00XX_previous`). El `ReportDefinition` se elimina en el `reverse` de la migración. No hay escritura a MySQL legacy (solo lectura), por lo que no hay estado que limpiar.

## Dependencies

- Sesión con `base_empresa` y claves de vendedor/permisos (login Synap).
- Acceso de lectura a tablas legacy `cliente`, `cuentacliente`, `viajantes`, `cliente_domicilio`.

## Success Criteria

- [ ] `/reports/dashboard/clientes-sin-ventas-vendedor/` renderiza con UI canónica y filtros.
- [ ] Relay operativo restringe por vendedor de sesión; gerencial respeta `vendedor_a_cargo`.
- [ ] SQL 100% parametrizado (sin concatenar entrada de usuario).
- [ ] Tests pasan en `docker exec Synap_app` y respuesta expone `datos`, `resumenVendedores`, `resumenGlobal`, `modoTodosVendedores`.
