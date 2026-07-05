# Proposal: Informe "Cobranzas por vendedor" (migración mayoristapp → reports)

## Intent

Portar a Synap el informe de **cobranzas por vendedor** del PHP `administraNET-ecom` (`listado-cobranzas-vendedor.php` + `informes-json/cobranza_lista_vendedor_resumen.php`, actualizado jun. 2026). Resume por período los cobros de `cuentacliente` (efectivo, dólares, cheques, transferencias, percepciones y total) filtrando por vendedor y rango de fechas. Segundo informe del delta reconciliado ([docs/ecom/DELTA_PHP_2026Q2.md](../../../docs/ecom/DELTA_PHP_2026Q2.md)); reutiliza el patrón validado en `informe-clientes-sin-ventas-vendedor`.

## Scope

### In Scope
- Servicio `reports/services/cobranzas_vendedor.py` con la lógica de `cobranza_lista_vendedor_resumen.php` (SQL parametrizado, agregados por período), modos `mes` y `totalizado`.
- Relay API operativo y gerencial bajo `/api/reports/cobranzas-vendedor/...` (permisos Operational/Managerial), con scope por vendedor de sesión y anti-bypass.
- `ReportDefinition` + slug `cobranzas-por-vendedor` en `/reports/dashboard/<slug>/` con UI canónica (filtros período/vendedor, tabla con totales y gráfico).
- Tests unitarios de servicio y relay; actualización de DELTA + checkpoint.

### Out of Scope
- Informes de cobranzas por cliente o facturas a cobrar (`cobranza_*`), que son otras verticales.
- Exportación PDF/Excel server-side (la UI canónica ofrece su propia exportación estándar).
- Paridad visual con DataTables/Chart.js del PHP.

## Capabilities

### New Capabilities
- `reports-cobranzas-vendedor`: resumen de cobranzas (recibos y ventas contado) por período y vendedor, con desglose por medio de pago y control de acceso operativo/gerencial.

### Modified Capabilities
- None

## Approach

Mismo patrón que `informe-clientes-sin-ventas-vendedor`: servicio con SQL parametrizado vía `core.mysql_pool`, dos APIViews DRF (operativo fuerza `CodViajante` de sesión; gerencial ve todos o filtra), y una `ReportDefinition` con template dedicado (slug en `DashboardDetailView.get_template_names`). Tipos normalizados con `core.utils.administranet_types`; montos en `Decimal`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `reports/services/cobranzas_vendedor.py` | New | Consulta y agregados |
| `reports/cobranzas_vendedor_relay_views.py` | New | APIViews operativo/gerencial |
| `reports/api_urls.py` | Modified | Rutas relay |
| `reports/views.py` | Modified | Slug + contexto |
| `reports/templates/reports/dashboard_cobranzas_por_vendedor.html` | New | UI canónica |
| `reports/migrations/0034_add_cobranzas_vendedor_report.py` | New | ReportDefinition + checkpoint |
| `reports/tests/test_cobranzas_vendedor_relay.py` | New | Tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| SQL inyectable (PHP concatena codViajante/fechas) | Med | Parámetros `%s`, `CodViajante` a `int`, fechas parseadas |
| Montos con float pierden precisión | Med | `Decimal` en agregados y totales |
| Paridad de sumas no verificable sin BD real | Med | Tests de forma + validación operativa Fase D |

## Rollback Plan

Revertir el commit: quitar rutas/servicio/vistas/tests y revertir migración (`migrate reports 0033...`). Solo lectura sobre MySQL legacy; sin estado que limpiar.

## Dependencies

- Sesión con `base_empresa` y `id_vendedor_usr`/permisos.
- Lectura de tabla legacy `cuentacliente` y `viajantes`.

## Success Criteria

- [ ] `/reports/dashboard/cobranzas-por-vendedor/` renderiza con filtros y totales.
- [ ] Operativo restringe al vendedor de sesión; gerencial ve todos o filtra por vendedor.
- [ ] SQL 100% parametrizado; montos en `Decimal`.
- [ ] Tests verdes en `docker exec Synap_app`.
