# Tasks: Informe cobranzas por vendedor

**Change:** `informe-cobranzas-por-vendedor`
**Estado:** implementado (tests 14/14 OK, migración aplicada)

## Fase 1 — Servicio
- [x] `reports/services/cobranzas_vendedor.py`: `get_cobranzas_vendedor` (SQL parametrizado, modos mes/totalizado)
- [x] Agregados efectivo/dolar/cheque/transferencia/percepcion/total en `Decimal`
- [x] Meses en español + orden cronológico; totales del pie

## Fase 2 — Relay API
- [x] `reports/cobranzas_vendedor_relay_views.py`: operativo (scope propio) + gerencial (todos/filtra)
- [x] Validación 400 sin fechas; 403 operativo sin id_vendedor_usr; parseo de `tipo/modo`

## Fase 3 — Rutas
- [x] `reports/api_urls.py`: `cobranzas-vendedor/relay/` y `.../gerencia/`

## Fase 4 — UI canónica
- [x] Slug `cobranzas-por-vendedor` en `views.py` (`get_template_names` + contexto)
- [x] `reports/templates/reports/dashboard_cobranzas_por_vendedor.html` (filtros, tabla+pie, gráfico)

## Fase 5 — ReportDefinition + checkpoint
- [x] `reports/migrations/0034_add_cobranzas_vendedor_report.py` (+ legacy_section listados + checkpoint)

## Fase 6 — Tests
- [x] `reports/tests/test_cobranzas_vendedor_relay.py` (servicio + relay + permisos) — 14/14

## Fase 7 — Verificación y docs
- [x] `docker exec Synap_app` tests + migrate + smoke
- [x] Actualizar `docs/ecom/DELTA_PHP_2026Q2.md` (Cobranzas por vendedor → Migrado)
- [x] `verify-report.md`
