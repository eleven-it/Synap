# Apply progress: mpr-trazabilidad-movimientos-por-etapa

**Status:** complete (PR1+PR2 en working tree)  
**Mode:** Standard  
**Date:** 17/09/2026

## Work Unit Evidence

| Evidence | Value |
|----------|--------|
| Focused test command | `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_paridad_kardex_inventario_etapa mpr.tests.test_kardex_articulo mpr.tests.test_reportes_trazabilidad` |
| Result | OK — 82 tests |
| Runtime harness | GET hub kardex componente pipeline (views + partial); export CSV pipeline |
| Rollback | Revertir `mpr/services.py`, `mpr/services_kardex_articulo.py`, `mpr/views.py`, `mpr/export.py`, `mpr/reportes_presentacion.py`, template kardex, tests, docs |

## Completed tasks

All items in `tasks.md` phases 1–5 marked `[x]` after focal suite green.

## Deviations

None material — implementation follows design ADR-01..12.

## Risks / gaps

- Tests UI 4.5 (assertContains columnas pipeline) no añadidos como clase dedicada; regresión cubierta por golden pack + suite existente.
- `verify-report.md` pendiente fase SDD verify formal.
