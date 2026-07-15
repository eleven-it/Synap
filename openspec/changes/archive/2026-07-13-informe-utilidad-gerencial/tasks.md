# Tasks: Informe utilidad gerencial

**Change:** `informe-utilidad-gerencial`
**Estado:** completado

## Fase 1 — Servicio
- [x] `reports/services/utilidad_gerencial.py`: `get_utilidad_gerencial` (SQL parametrizado stock+cuentacliente)
- [x] Sumas con signo por TipoComp (Venta/Neto/Costo/Utilidad); Costo=PrecioCostoxR
- [x] NC/Desc por dimensión (cliente/tipocliente/vendedor/zona) con exclusiones
- [x] Venta Neta, Utilidad, Utilidad % (ratio, Costo=0→0)
- [x] Variante inflación: 2º rango, índice AVG(PrecioCostoxU), venta_esp, resultado

## Fase 2 — Relay API
- [x] `reports/utilidad_gerencial_relay_views.py`: operativo + gerencial + seleccion filtros
- [x] 400 sin fechas; anti-bypass vendedor; parseo filtrarPor/pvSelec/inflación

## Fase 3 — Rutas
- [x] `reports/api_urls.py`: `utilidad-gerencial/relay/` y `.../gerencia/`

## Fase 4 — UI canónica
- [x] Slug + contexto en `views.py`
- [x] `reports/templates/reports/dashboard_utilidad_gerencial.html`

## Fase 5 — ReportDefinition + checkpoint
- [x] `reports/migrations/0035_add_utilidad_gerencial_report.py` (+ legacy_section gerenciales + checkpoint)

## Fase 6 — Tests
- [x] `reports/tests/test_utilidad_gerencial_relay.py` (servicio + relay + permisos + inflación)

## Fase 7 — Verificación y docs
- [x] `docker exec Synap_app` tests + migrate + smoke
- [x] Actualizar `docs/ecom/DELTA_PHP_2026Q2.md`
- [x] `verify-report.md`
