```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:8b17ce63eef0f34db064864de98f35d33fd81fdb8eefe1346726417f25d31336
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 16/16
scenarios: 21/21
test_command: docker exec Synap_app python manage.py test mpr.tests.test_inventario_deposito_report stock.tests.test_stock_a_fecha --keepdb
test_exit_code: 0
test_output_hash: sha256:b27f26d4ad713bdc2c80c848bc9305c865e4613048606ce0396f7e14ab63cfee
build_command: docker exec Synap_app python manage.py check
build_exit_code: 0
build_output_hash: sha256:d38619b4e7d4d9ddeee2d37dca781e9fe71ff0d173c9f432e84864c56a6f2eb0
```

## Verification Report

**Change**: mpr-inventario-deposito-articulo  
**Version**: delta specs (mpr-reporte-inventario-deposito + mpr-reportes-shell)  
**Mode**: Strict TDD  
**Artifact store**: hybrid (OpenSpec file + Engram topic)  
**Re-verify**: after verify-remediation batch (+8 tests, suite 34)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 24 |
| Tasks complete | 24 |
| Tasks incomplete | 0 |

All tasks in `tasks.md` are marked `[x]`. Apply-progress confirms PR-1 + PR-2 + verify-remediation complete (24/24).

### Build & Tests Execution

**Build**: ✅ Passed

```text
docker exec Synap_app python manage.py check
System check identified no issues (0 silenced).
Exit code: 0
```

**Tests**: ✅ 34 passed / 0 failed / 0 skipped

```text
docker exec Synap_app python manage.py test mpr.tests.test_inventario_deposito_report stock.tests.test_stock_a_fecha --keepdb
Ran 34 tests in 0.038s
OK
Exit code: 0
```

**Coverage**: ➖ Not run (threshold 0 in `openspec/config.yaml`; no per-file coverage gate configured)

### TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | apply-progress includes PR-2 table + verify-remediation TDD table (8 new tests) |
| All tasks have tests | ✅ | 34 tests across 2 files cover RED/GREEN tasks |
| RED confirmed (tests exist) | ✅ | `mpr/tests/test_inventario_deposito_report.py`, `stock/tests/test_stock_a_fecha.py` exist |
| GREEN confirmed (tests pass) | ✅ | 34/34 pass at verify runtime |
| Triangulation adequate | ✅ | Divisors 12/6/4, grain, hierarchy, corte hoy/histórico, marca filter, dd/MM/yyyy |
| Safety Net for modified files | ➖ | verify-remediation batch tests-only; no production file changes |

**TDD Compliance**: 5/6 checks passed

### Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 34 | 2 | Django `SimpleTestCase` |
| Integration | 0 | 0 | — |
| E2E | 0 | 0 | not available |
| **Total** | **34** | **2** | |

Service/view tests use mocks (`mysql_cursor`, `consultar_inventario_deposito`) — classified as unit layer.

### Changed File Coverage

Coverage analysis skipped — no coverage run executed for changed files (`coverage_threshold: 0`).

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior (no tautologies, ghost loops, or smoke-only tests detected in new or existing tests).

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-INVDEP-01 | Sin regresión reportes existentes | `test_stock_demanda_sin_regresion` | ✅ COMPLIANT |
| REQ-INVDEP-02 | Una fila por depósito-artículo | `InventarioDepositoGranoTest.test_una_fila_por_deposito_articulo` | ✅ COMPLIANT |
| REQ-INVDEP-03 | Marcas separadas | `InventarioDepositoJerarquiaTest.test_marcas_separadas_subtotales_suma_docenas` | ✅ COMPLIANT |
| REQ-INVDEP-04 | Pipeline — pares ÷12 | `test_pipeline_pares_divisor_doce` | ✅ COMPLIANT |
| REQ-INVDEP-04 | Terminado — divisor 6 | `test_terminado_divisor_seis` | ✅ COMPLIANT |
| REQ-INVDEP-04 | Terminado — divisor 4 | `test_terminado_divisor_cuatro` | ✅ COMPLIANT |
| REQ-INVDEP-05 | Mix pipeline y Terminado | `test_total_es_suma_docenas_mix` | ✅ COMPLIANT |
| REQ-INVDEP-06 | Default sin 2da | `test_filtro_2da_excluido_default`, `test_sql_excluye_2da_por_default` | ✅ COMPLIANT |
| REQ-INVDEP-06 | Opt-in 2da | `test_filtro_2da_opt_in`, `test_sql_incluye_2da_cuando_opt_in` | ✅ COMPLIANT |
| REQ-INVDEP-07 | Corte hoy | `test_usa_stock_deposito_cuando_fecha_es_hoy`, `test_corte_hoy_consulta_stock_deposito_no_historico` | ✅ COMPLIANT |
| REQ-INVDEP-07 | Corte histórico | `test_corte_historico_usa_stock_a_fecha`, `stock/tests/test_stock_a_fecha.py` (4 tests) | ✅ COMPLIANT |
| REQ-INVDEP-08 | Filtro marca | `test_filtro_marca_aplica_where_y_recalcula_total` | ✅ COMPLIANT |
| REQ-INVDEP-09 | Tercero incluido | `test_no_filtra_tercero_en_where`, `test_tercero_incluido_en_resultado` | ✅ COMPLIANT |
| REQ-INVDEP-10 | Export con total | `test_export_xlsx_encabezados_y_total`, `test_vista_responde_xlsx` | ✅ COMPLIANT |
| REQ-INVDEP-11 | Fecha visible dd/MM/yyyy | `test_fecha_corte_display_formato_dd_mm_yyyy`, `test_preparar_presentacion_fecha_corte_dd_mm_yyyy` | ✅ COMPLIANT |
| REQ-INVDEP-12 | Sin resultados | `test_empty_state_espanol` | ✅ COMPLIANT |
| REQ-INVDEP-13 | Validación muestra | `InventarioDepositoParidadExcelFixtureTest.test_total_docenas_fixture_ratios_excel_12_6_4` | ⚠️ PARTIAL (automated 12/6/4 fixture; live UAT vs `Inventarios.xlsx` pending) |
| REQ-SHELL-02 | Inventario depósito ignora período shell | `test_shell_periodo_no_afecta_fecha_corte` | ✅ COMPLIANT |
| REQ-SHELL-03 | Navegación a inventario depósito | `test_ruta_inventario_deposito` | ✅ COMPLIANT |
| REQ-SHELL-10 | Export Excel inventario | `test_export_xlsx_encabezados_y_total`, `test_hub_declara_soporte_excel`, `test_vista_responde_xlsx` | ✅ COMPLIANT |
| REQ-SHELL-10 | Reporte solo CSV | `test_hub_declara_soporte_excel` (stock → False) | ✅ COMPLIANT |

**Compliance summary**: 21/21 scenarios covered (20 COMPLIANT + 1 PARTIAL REQ-INVDEP-13 live UAT pending)

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| REQ-INVDEP-02 | ✅ Implemented + tested | `(id_deposito, id_articulo)` grain asserted in `test_una_fila_por_deposito_articulo` |
| REQ-INVDEP-03 | ✅ Implemented + tested | `agrupar_jerarquia_deposito_marca` subtotals per marca |
| REQ-INVDEP-04/05/06/09 | ✅ Implemented + tested | `mpr/inventario_docenas.py`, `services_inventario_deposito.py` |
| REQ-INVDEP-07 corte hoy | ✅ Implemented + tested | `_usa_stock_deposito()` + `stock_deposito` path when `fecha_corte=today` |
| REQ-INVDEP-07 histórico | ✅ Implemented + tested | `stock/services/stock_a_fecha.py`, `DATE(Fecha)<=corte` |
| REQ-INVDEP-08 | ✅ Implemented + tested | SQL `CodigoMarca IN` + total recalc in strengthened test |
| REQ-INVDEP-10/11 | ✅ Implemented + tested | xlsx export + `fecha_corte_display` dd/MM/yyyy |
| REQ-INVDEP-13 | ⚠️ Partial | Automated fixture validates SUM(docenas) mix 12/6/4; live UAT vs cliente `Inventarios.xlsx` documented pending in task 4.4 / docs |
| REQ-SHELL-* | ✅ Implemented + tested | Hub slug, Excel flag, shell period bypass |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Slug `inventario_deposito` (no extend stock) | ✅ Yes | Hub + view branch; regression test on `demanda/stock` |
| Docenas 12/6/4 via `inventario_docenas.py` | ✅ Yes | Not using `_celda_stock_deposito` |
| 2da OFF default | ✅ Yes | SQL filter + parse default |
| Tercero included | ✅ Yes | No `tipo_art_fab` exclusion in WHERE |
| stock_a_fecha in `stock/services/` | ✅ Yes | Shared module created |
| PR split auto-chain | ✅ Yes | PR-1 + PR-2 + verify-remediation evidence |
| Excel export PR-2 | ✅ Yes | `REPORTES_EXPORT_XLSX`, openpyxl helper |
| S3 `stock.Fecha` | ✅ Yes | Documented + SQL uses `Fecha` column |

### Quality Metrics

**Linter**: ➖ Not available  
**Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:
1. REQ-INVDEP-13 — scenario PARTIAL: automated fixture (`test_total_docenas_fixture_ratios_excel_12_6_4`) covers divisor mix 12/6/4 and SUM(docenas); live UAT paridad vs `Inventarios.xlsx` on cliente base remains documented pending (task 4.4). Acceptable for archive with documented follow-up.
2. TDD Cycle Evidence table in apply-progress covers PR-2 + verify-remediation; PR-1 RED/GREEN cycles not tabulated in original apply batch (historical protocol gap, non-blocking).
3. Design spikes S1/S2 numeric paridad validated in docs only; not re-run at verify runtime.

**SUGGESTION**:
1. Schedule live UAT paridad vs `Inventarios.xlsx` when cliente base available (closes REQ-INVDEP-13 fully).
2. Consider one integration test hitting real template render for hierarchy headers (optional; unit coverage adequate).

### Verdict

**PASS WITH WARNINGS**

All 24 tasks complete and 34/34 tests green. Prior verify FAIL blockers (REQ-INVDEP-02, -03, -07 corte hoy, -08, -11) closed by 8 new covering tests. REQ-INVDEP-13 remains PARTIAL pending live Excel UAT; automated fixture provides scenario coverage per project guidance. Ready for `sdd-archive`.
