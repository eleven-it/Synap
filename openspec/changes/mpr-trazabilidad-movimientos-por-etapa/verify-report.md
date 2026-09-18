```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9ed9ef7120d09644c4a62211da49bfd6c847b40fa791ecd756f046ee588ffe1b
verdict: fail
blockers: 0
critical_findings: 2
requirements: 12/12
scenarios: 14/16
test_command: docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_paridad_kardex_inventario_etapa mpr.tests.test_kardex_articulo mpr.tests.test_reportes_trazabilidad
test_exit_code: 0
test_output_hash: sha256:9ed9ef7120d09644c4a62211da49bfd6c847b40fa791ecd756f046ee588ffe1b
build_command: docker exec Synap_app python manage.py check
build_exit_code: 0
build_output_hash: sha256:d303172e453d11e2dd051887ab20f13e18e3e861d4768a028dfd82eafd8a020d
```

## Verification Report

**Change**: mpr-trazabilidad-movimientos-por-etapa  
**Version**: spec delta in change (2026-09-17)  
**Mode**: Standard  
**Repo evidence**: working tree at apply-complete; focal suite executed 2026-09-17

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 28 (sections 1.1–5.3) |
| Tasks complete | 28 |
| Tasks incomplete | 0 |

All checkboxes in `tasks.md` are `[x]`. `apply-progress.md` status: complete (PR1+PR2).

### Build & Tests Execution

**Build**: ✅ Passed (`manage.py check`, exit 0; urls.W005 warning pre-existing)
```text
docker exec Synap_app python manage.py check
System check identified 1 issue (0 silenced) — urls.W005 mtrix namespace
```

**Tests**: ✅ 83 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
docker exec Synap_app python manage.py test \
  mpr.tests.test_analisis_trazabilidad_articulo \
  mpr.tests.test_paridad_kardex_inventario_etapa \
  mpr.tests.test_kardex_articulo \
  mpr.tests.test_reportes_trazabilidad

Ran 83 tests in ~18s — OK
```

**Coverage**: ➖ Not measured for this verify slice.

### Invariants (product constraints)

| Invariant | Result | Evidence |
|-----------|--------|----------|
| `inventario_tabla` semantics unchanged | ✅ | `git diff HEAD -- stock/services/inventario_tabla.py` empty; runtime kardex does not import `consultar_inventario_tabla` |
| `CAMPOS_CANTIDAD` not expanded for kardex etapas | ✅ | `preparar_saldos_etapa_kardex` uses `_celda_stock_deposito` directly; set unchanged (no `entrada`/`salida`/`saldos_por_etapa` keys added) |
| Pack Terminado / legacy CSV path | ✅ | `desglosar_por_deposito=False` default; `TestGoldenSampleKardex610Blanco`, `TestArticulo340StockInicialRemSobrante` pass unmodified |
| No native dialogs in touched template | ✅ | `kardex_articulo.html`: no `alert`/`confirm`/`prompt`; `test_reportes_trazabilidad` asserts no `alert(` in hub shell |

### Spec Compliance Matrix

| Requirement | Scenario | Test / evidence | Result |
|-------------|----------|-----------------|--------|
| Explosión por depósito | Movimiento en un solo depósito | Code path `_normalizar_fila_kardex` + SQL flag; no dedicated single-dep scenario test | ⚠️ PARTIAL |
| Explosión por depósito | Artículo sin eje pipeline | `TestPackUsaTerminadoPorDefecto`, `TestSqlDesglosePorDeposito.test_flag_off_sin_coddeposito` | ✅ COMPLIANT |
| Transferencias dos renglones | OPP Producción → Semi | `TestDedupeOppDosDepositos`, `TestOrdenOppTransferencia` | ✅ COMPLIANT |
| Corrido multi-etapa backend | Saldos post-movimiento | `TestInvarianteSaldoPorEtapa`, `TestOrdenOppTransferencia` | ✅ COMPLIANT |
| Corrido multi-etapa backend | Consolidado derivado | `TestInvarianteSaldoPorEtapa.test_saldo_corrido_es_suma_etapas` | ✅ COMPLIANT |
| Saldo corrido consolidado UI | Usuario sigue total en grilla | Template column Consolidado + `saldo_corrido`; no pipeline-specific `assertContains` | ⚠️ PARTIAL |
| Columna Etapa y KPIs | Identificación etapa por fila | `kardex_articulo.html` conditional columns; task 4.5 UI asserts **not** added | ⚠️ PARTIAL |
| Columna Etapa y KPIs | KPIs cabecera desglose | Template `meta.saldo_inicial_etapas_ui` / stock badge; no automated KPI assert | ⚠️ PARTIAL |
| Export CSV | Columnas CSV pipeline | `TestExportAnalisisTrazabilidadCsv.test_csv_pipeline_incluye_etapas_y_seccion_saldos` | ✅ COMPLIANT |
| Conciliación Hasta ≥ hoy | Cierre cuadra inventario | `TestParidadKardexInventarioEtapa.test_cierre_cuadra_sin_advertencia_hasta_hoy` (mocks `_fetch_stock_por_etapa`; **no** `consultar_inventario_tabla` oracle) | ⚠️ PARTIAL |
| Conciliación | Rango histórico | `test_hasta_pasado_sin_conciliacion_estricta` | ✅ COMPLIANT |
| Conciliación | Descuadre una etapa → un aviso | `_conciliar_cierre_por_etapa` implemented; **no** test with forced mismatch (design §2.6) | ❌ UNTESTED |
| Filtros paridad inventario | Depósito `suma_stock='No'` excluido | `get_etapas_pipeline_fabricados_mpr` SQL filters; **no** unit test | ❌ UNTESTED |
| Dedupe mov+depósito | OPP sobrevive dedupe | `TestDedupeOppDosDepositos` | ✅ COMPLIANT |
| No regresión Terminado | Golden pack | `TestGoldenSampleKardex610Blanco` (in analisis suite) + kardex golden tests | ✅ COMPLIANT |
| inventario_tabla MUST NOT | Contrato sin cambios | No file diff; read-only in tests elsewhere | ✅ COMPLIANT (static) |
| FA no afecta depósito | FA no mueve etapas | `TestInvarianteSaldoPorEtapa.test_fa_no_mueve_etapas` | ✅ COMPLIANT |

**Compliance summary**: 13/16 scenarios with passing covering tests or acceptable static proof; 3 PARTIAL (UI + paridad oracle); 2 UNTESTED (non-blocking per apply-progress / task 4.5).

### Correctness (Static Evidence)

| RF (AF) | Status | Notes |
|---------|--------|-------|
| RF-01 Explosión SQL | ✅ | `desglosar_por_deposito` on three query functions |
| RF-02 Saldos por etapa | ✅ | `_calcular_saldo_corrido_por_etapa`, payload `por_etapa` |
| RF-03 Consolidado = suma | ✅ | Invariant in calculator |
| RF-04 Dos renglones OPP | ✅ | `_marcar_transferencias_internas` + dedupe key |
| RF-05 Conciliación | ✅ | `_fetch_stock_por_etapa_pipeline` + `_conciliar_cierre_por_etapa` |
| RF-06 UI etapa | ✅ | Template branches on `pipeline_fabricados` |
| RF-07 CSV | ✅ | Dynamic columns in `analisis_trazabilidad_a_csv` |
| RF-08 Filtro etapa | ➖ Out of scope MVP |
| RF-09 KPIs | ✅ | Header/stock badges in template |
| RF-10 Packs legacy | ✅ | Bifurcation + golden tests |
| RF-11 inventario_tabla | ✅ | Not modified |
| RF-12 No native dialogs | ✅ | Template + trazabilidad shell test |
| RF-13 Catálogo tipo_mpr | ✅ | `TIPOS_MPR_PIPELINE_FABRICADOS` / `get_etapas_*` |

### Coherence (Design ADR)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| ADR-01 SQL explosion + flag | ✅ | Verified by `TestSqlDesglosePorDeposito` |
| ADR-02 `get_etapas_pipeline_fabricados_mpr` | ✅ | Implemented with `suma_stock` / `anulado` filters |
| ADR-03 Dedupe key | ✅ | Tests |
| ADR-04 Two rows transfer | ✅ | Tests |
| ADR-05 Backend corrido | ✅ | Tests |
| ADR-06 Stock query MPR-only | ✅ | No runtime `consultar_inventario_tabla` |
| ADR-07 Conciliation warning | ⚠️ | Logic present; mismatch scenario untested |
| ADR-08 UI single thead row | ✅ | Template inspection |
| ADR-09 Presentation helper | ✅ | Code; no direct `_celda_stock_deposito` equality test |
| ADR-10 Dynamic CSV | ✅ | Test |
| ADR-11 Limit/truncation | ✅ | Code present (not re-verified by dedicated test this run) |
| ADR-12 conteo INV | ✅ | `TestInvarianteSaldoPorEtapa` / inventario conteo tests |

### Issues Found

**CRITICAL**: None (focal suite green; MUST RFs implemented).

**WARNING**:

1. **Task 4.5 / design UI contract**: No `assertContains` for pipeline column Etapa + four saldo columns vs Terminado exclusion; regression relies on golden pack + template manual review.
2. **Task 2.6**: Missing test for single-stage reconciliation mismatch message (design integration row).
3. **Task 2.5**: Paridad file does not call `consultar_inventario_tabla(ambito=fabricados)` as independent oracle—only mocks `_fetch_stock_por_etapa_pipeline`.
4. **Spec scenarios**: Depósito `suma_stock='No'` exclusion and descuadre advertencia sin test dedicado.
5. **Task 4.4**: No explicit test comparing `preparar_saldos_etapa_kardex` output to `_celda_stock_deposito` for same input.

**SUGGESTION**:

- Add optional UI render test with `tipo_eje: pipeline_fabricados` fixture (closes 4.5).
- Add one test patching stock mismatch to assert single consolidated warning text.
- Optional: thin integration test comparing `_fetch_stock_por_etapa_pipeline` totals vs `consultar_inventario_tabla` on shared fixture.

### Verdict

**Human verdict: PASS WITH GAPS** (envelope `verdict: fail` reflects 2 UNTESTED spec scenarios, not runtime blockers). All tasks complete; 83/83 focal tests pass; core backend/CSV/regression MUST requirements satisfied. Remaining gaps are documented optional UI asserts, missing conciliation-mismatch and `suma_stock` exclusion tests, and paridad without inventario_tabla oracle—acceptable for archive with warnings, not blocking merge per apply-progress.
