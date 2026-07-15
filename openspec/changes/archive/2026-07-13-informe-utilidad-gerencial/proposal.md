# Proposal: Informe "Utilidad gerencial" (+ variante inflación) (mayoristapp → reports)

## Intent

Portar a Synap el informe de **rentabilidad / utilidad gerencial** del PHP `administraNET-ecom`
(`informe-utilidad-gerencial.php` e `informe-utilidad-inflacion-gerencial.php`, que consumen
`relay-ventas-netas-gerencia.php` en modo `verInforme=ut` / `uti`). El informe agrupa por
dimensión (cliente, tipo cliente, vendedor, artículo, proveedor, zona, categoría, rubro,
subrubro, marca) y muestra por período **Venta, Descuento, Venta Neta, Costo, Utilidad y
Utilidad %**, con manejo de notas de crédito/devoluciones. La variante con **inflación**
compara dos rangos aplicando un índice.

Tercer informe del delta reconciliado ([docs/ecom/DELTA_PHP_2026Q2.md](../../../docs/ecom/DELTA_PHP_2026Q2.md)),
prioridad P1. Reutiliza el patrón validado en `informe-clientes-sin-ventas-vendedor` /
`informe-cobranzas-por-vendedor` y la base ya migrada en `reports/services/ventas_netas.py`
(que hoy solo emite un total de utilidad, sin el desglose completo).

## Scope

### In Scope
- Servicio de utilidad con desglose completo (Venta / Desc / Venta Neta / Costo / Utilidad /
  Utilidad %) por dimensión y período, con SQL parametrizado sobre `stock` + `cuentacliente`.
- Manejo de notas de crédito/devoluciones y descuentos con paridad al PHP.
- Variante con inflación (factor/índice sobre segundo rango) como modo del mismo servicio.
- Relay API operativo/gerencial con scope por vendedor y anti-bypass.
- `ReportDefinition` slug `utilidad-gerencial` + UI canónica (`/reports/dashboard/<slug>/`).
- Tests unitarios de servicio y relay; DELTA + checkpoint + verify-report.

### Out of Scope
- Exportación PDF/Excel server-side (la UI canónica usa su exportación estándar).
- Paridad visual DataTables/gráficos del PHP.
- Refactor de `QueryRunnerService` (no cambiar firmas públicas ni slugs existentes).

## Capabilities

### New Capabilities
- `reports-utilidad-gerencial`: rentabilidad por dimensión y período (venta, costo, utilidad,
  margen %), con notas de crédito, descuentos y variante inflación, y control operativo/gerencial.

### Modified Capabilities
- `reports-ventas-netas` (posible extensión menor si se decide reutilizar `get_ventas_netas`
  para emitir el desglose; se define en design tras exploración).

## Approach

Pendiente de confirmar en design según hallazgos de la exploración del relay PHP
(`armar_sql_utilidad`, `traer_valor_nc_utilidad`, descuentos, inflación). Dos alternativas:
1. **Servicio dedicado** `reports/services/utilidad_gerencial.py` (recomendado si la lógica de
   costo/NC/% difiere sustancialmente de `ventas_netas`).
2. **Extender** `get_ventas_netas` para emitir columnas Venta/Costo/Utilidad/%.

En ambos casos: SQL parametrizado vía `core.mysql_pool`, montos en `Decimal`, tipos
normalizados con `core.utils.administranet_types`, y dos APIViews DRF (operativo/gerencial).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `reports/services/utilidad_gerencial.py` (o `ventas_netas.py`) | New/Mod | Cálculo utilidad con desglose |
| `reports/utilidad_gerencial_relay_views.py` | New | APIViews operativo/gerencial |
| `reports/api_urls.py` | Modified | Rutas relay |
| `reports/views.py` | Modified | Slug + contexto |
| `reports/templates/reports/dashboard_utilidad_gerencial.html` | New | UI canónica |
| `reports/migrations/0035_add_utilidad_gerencial_report.py` | New | ReportDefinition + checkpoint |
| `reports/tests/test_utilidad_gerencial_relay.py` | New | Tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Números de margen incorrectos (fuente de costo, NC, descuentos) | **High** | Mapeo exacto por exploración; tests de fórmula; validación operativa antes de exponer |
| Costo `PrecioCostoxR` vs `PrecioCosto*Cantidad` (difieren) | High | Confirmar en exploración y usar la fuente del PHP |
| Performance (JOIN stock+cuentacliente+articulo por dimensión) | Med | Solo agregados; índices existentes; sin detalle masivo |
| Divergencia con `ventas_netas` (utilidad simple) | Med | Documentar diferencia; no romper relay actual |

## Rollback Plan

Revertir el commit: quitar servicio/relay/rutas/vistas/tests y revertir migración
(`migrate reports 0034...`). Solo lectura sobre MySQL legacy.

## Dependencies

- Sesión con `base_empresa`, permisos gerenciales/operativos, `id_vendedor_usr`.
- Tablas legacy `stock`, `cuentacliente`, `articulo`, dimensiones (rubro/marca/zona/etc.).
- Exploración `openspec/changes/informe-utilidad-gerencial/exploration.md` (resultado del análisis PHP).

## Success Criteria

- [ ] `/reports/dashboard/utilidad-gerencial/` muestra Venta/Desc/Venta Neta/Costo/Utilidad/Utilidad %.
- [ ] Paridad de fórmula (costo/NC/descuentos/%) validada con tests y muestreo operativo.
- [ ] Operativo restringe al vendedor de sesión; gerencial ve todos o filtra.
- [ ] Variante inflación aplica índice/doble rango correctamente.
- [ ] SQL 100% parametrizado; montos en `Decimal`. Tests verdes en `docker exec Synap_app`.
