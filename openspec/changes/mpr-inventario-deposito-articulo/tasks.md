# Tasks: Inventario por depósito y artículo (MPR)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650–950 |
| 800-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR-1 (consulta/UI/docenas) → PR-2 (stock_a_fecha + Excel) |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Consulta hoy + docenas + hub + UI | PR-1 (base tracker) | `docker exec Synap_app python manage.py test mpr.tests.test_inventario_deposito_report` | GET `/mpr/reportes/?grupo=demanda&reporte=inventario_deposito` | Revert `inventario_docenas`, `services_inventario_deposito`, hub slug, partials |
| 2 | stock_a_fecha + Excel + docs | PR-2 (base PR-1) | `docker exec Synap_app python manage.py test stock.tests.test_stock_a_fecha mpr.tests.test_inventario_deposito_report` | GET con `fecha_corte` pasada + `?format=xlsx` | Revert `stock_a_fecha`, export xlsx, docs |

## Phase 0: Spikes (pre-apply)

- [x] 0.1 **S1:** Validar UM pack/pares en muestra real; documentar en `docs/mpr/INVENTARIO_DEPOSITO_ARTICULO.md` §S1
- [x] 0.2 **S2:** Comparar SUM(docenas) vs `Inventarios.xlsx`; delta ≤0,01; documentar §S2
- [x] 0.3 **S3:** Confirmar campo fecha VB6 `Info_Stock.frm` (`stock.Fecha` vs `FechaControl`); bloqueante PR-2

## Phase 1: PR-1 — Docenas y servicio (TDD)

- [x] 1.1 **RED:** `mpr/tests/test_inventario_deposito_report.py` — divisores 12/6/4, pares÷12, docenas float (REQ-INVDEP-04)
- [x] 1.2 **GREEN:** Crear `mpr/inventario_docenas.py` (`divisor_docena_inventario`, `medidas_inventario_excel`)
- [x] 1.3 **RED:** tests TOTAL=SUM(docenas) mix; 2da excluida default; Tercero incluido (REQ-INVDEP-05/06/09)
- [x] 1.4 **GREEN:** Crear `mpr/services_inventario_deposito.py` — query hoy `stock_deposito`, filtros, agrupación Depósito→Marca

## Phase 2: PR-1 — Hub, vista y UI

- [x] 2.1 Modificar `mpr/reportes_hub.py` — slug `inventario_deposito`, partial, columnas CSV (REQ-SHELL-03)
- [x] 2.2 Modificar `mpr/views.py` — rama GET, parse `depositos`/`marcas`/`q`/`incluir_2da`/`fecha_corte` default hoy
- [x] 2.3 Modificar `mpr/reportes_presentacion.py` — `preparar_inventario_deposito_presentacion`
- [x] 2.4 Crear `mpr/templates/mpr/reportes/partials/inventario_deposito.html` — jerarquía, subtotales Marca, TOTAL (REQ-INVDEP-03/11)
- [x] 2.5 Crear `mpr/templates/mpr/reportes/_filtros_inventario_deposito.html` — `fecha_corte` dd/MM/yyyy, toggle 2da; sin alert/confirm
- [x] 2.6 **RED:** tests filtro marca, empty state español, shell ignora Desde/Hasta (REQ-INVDEP-08/12, REQ-SHELL-02)
- [x] 2.7 **GREEN:** wire filtros; verificar regresión `demanda/stock` y `/stock/inventario/` (REQ-INVDEP-01)

## Phase 3: PR-2 — stock_a_fecha (TDD)

- [x] 3.1 **RED:** `stock/tests/test_stock_a_fecha.py` — movimientos fixture, corte inclusive, `Anulado='Si'` excluido
- [x] 3.2 **GREEN:** Crear `stock/services/stock_a_fecha.py` (`saldos_stock_a_fecha` con `DATE(Fecha)<=corte`)
- [x] 3.3 **RED:** test corte histórico en `test_inventario_deposito_report.py` (REQ-INVDEP-07)
- [x] 3.4 **GREEN:** Integrar rama histórica en `services_inventario_deposito.py`; tipos vía `administranet_types`

## Phase 4: PR-2 — Export Excel y documentación

- [x] 4.1 **RED:** test export `format=xlsx` — columnas Stock+Docenas+TOTAL español (REQ-INVDEP-10, REQ-SHELL-10)
- [x] 4.2 **GREEN:** Extender `mpr/export.py` + flag Excel en hub; botón solo si reporte lo declara
- [x] 4.3 Crear `docs/mpr/INVENTARIO_DEPOSITO_ARTICULO.md` — operativo, spikes S1–S3, paridad Excel
- [x] 4.4 UAT paridad muestra vs `Inventarios.xlsx` (REQ-INVDEP-13) — metodología + referencia explore 53861,67; UAT live pendiente

## Phase 5: Verificación final

- [x] 5.1 Suite: `docker exec Synap_app python manage.py test mpr.tests.test_inventario_deposito_report stock.tests.test_stock_a_fecha`
- [x] 5.2 Regresión: tests existentes MPR/stock sin cambios en `reporte_mpr_stock` ni `_celda_stock_deposito`
