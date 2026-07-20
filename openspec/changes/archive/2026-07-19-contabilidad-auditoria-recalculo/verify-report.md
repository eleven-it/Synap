# Verification Report

**Change:** `contabilidad-auditoria-recalculo`  
**Version:** delta specs F0–F3 + refinamiento REI  
**Mode:** Standard (strict_tdd no configurado en `openspec/config.yaml`)  
**Fecha verificación:** 19/07/2026

---

> **ADDENDUM (cierre post-verify, 19/07/2026).** Los gaps marcados CRITICAL más abajo (REC-07 paso 2 «concepto anulación», REC-07 paso 3 / REC-08 «cuentas_sin_fila_saldo») y el WARNING de test de `rollback_lote` (REC-14) **fueron resueltos antes de archivar**: se implementaron en `legacy_db/services/cont_recalculo_service.py` (orden seguro del apply: regen asientos → paso 2 concepto → paso 3 INSERT filas saldo → paso 4 recompute → REI) con sus tests. Suite final: **40 tests OK** (1 skip integración piloto). El detalle del informe abajo refleja el estado *previo* al cierre de gaps.

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 58 (checkboxes en `tasks.md`) |
| Tasks complete | 58 |
| Tasks incomplete | 0 |

**Nota:** Todos los checkboxes están marcados `[x]`. El pie de `tasks.md` aún dice *«Listo para sdd-apply»* (obsoleto). `state.yaml` mantiene `status: proposed` y `verify: pending` (coherente pre-verify; conviene actualizar tras este informe).

---

## Build & Tests Execution

**Build (compileall):** ✅ Passed  
```
docker exec Synap_app python -m compileall -q contabilidad_audit legacy_db/services/cont_recalculo_service.py
```

**Tests:** ✅ 34 passed / ❌ 0 failed / ⚠️ 1 skipped  
```
docker exec Synap_app python manage.py test contabilidad_audit legacy_db.tests.test_cont_recalculo_dry_run legacy_db.tests.test_cont_recalculo_apply legacy_db.tests.test_cont_recalculo_apply_integracion --keepdb
Found 35 test(s) … OK (skipped=1)
```
- Skip esperado: `legacy_db.tests.test_cont_recalculo_apply_integracion` (requiere `ENVIRONMENT=production` + `SYNAP_PILOTO_CONT=1`; no ejecutado en dev por diseño).

**Coverage:** ➖ Not available (sin umbral configurado en openspec).

---

## Cobertura por grupo de requisitos (estático)

### AUD-LECT (auditoría lectura) — 17 checks, 23 requisitos

| Requisito | Estado | Evidencia |
|-----------|--------|-----------|
| AUD-LECT-01 | ✅ OK | `contabilidad_audit/services/runner.py::ejecutar_corrida` — pool MySQL solo SELECT; test `test_runner.py::test_corrida_sin_dml_legacy` |
| AUD-LECT-02 | ✅ OK | `contabilidad_audit/services/registry.py::CHECKS` — 17 entradas |
| AUD-LECT-03 | ✅ OK | `contabilidad_audit/services/resultados.py` — `AuditResult`, `Diferencia`, `construir_audit_result` |
| AUD-LECT-04 | ✅ OK | `checks/asientos.py::asiento_balanceado` + `_sql.py::clasificar_delta`; test `test_checks.py::test_asiento_balanceado_*` |
| AUD-LECT-05 | ✅ OK | `checks/saldos.py`, `checks/_sql.py`; tests saldo + saldo_pc NULL |
| AUD-LECT-06 | ✅ OK | `checks/saldos.py::cuentas_sin_fila_saldo` |
| AUD-LECT-07 | ✅ OK | `checks/asientos.py::imputacion_a_no_imputable` |
| AUD-LECT-08 | ✅ OK | `checks/conceptos.py::concepto_anulacion_incoherente`; test dedicado |
| AUD-LECT-09 | ✅ OK | `checks/asientos.py::nro_asiento_duplicado` |
| AUD-LECT-10 | ✅ OK | `checks/asientos.py::codigo_movimiento_huerfano` |
| AUD-LECT-11 | ✅ OK | `checks/periodos.py::fecha_fuera_de_periodo`, `periodos_solapados` |
| AUD-LECT-12 | ✅ OK | `checks/cierres.py::cierre_resultado_no_cero` |
| AUD-LECT-13 | ✅ OK | `checks/cierres.py::reparto_cc_incompleto` |
| AUD-LECT-14 | ✅ OK | `checks/rei.py::rei_recalculo` + `services/rei_calculo.py::evaluar_rei_ejercicio`; tests `test_rei.py` (no_computable, H44, fix H02) |
| AUD-LECT-15 | ✅ OK | `checks/conceptos.py::concepto_no_normal` |
| AUD-LECT-16 | ✅ OK | `runner.py` + `views.py::_parse_filtros` |
| AUD-LECT-17 | ✅ OK | Uso transversal `administranet_types` en checks |
| AUD-LECT-18 | ✅ OK | `politicas.py::calcular_config_hash`; tests hash estable/cambiante |
| AUD-LECT-19 | ✅ OK | `views.py` tablero + `services/export.py`; templates canon |
| AUD-LECT-20 | ✅ OK | `views.py` permisos + `runner.py` try/except por check |
| AUD-LECT-21 | ✅ OK | `checks/compras_pagos.py::comprobante_compra_pago_sin_asiento` (cm≠0, sucursal cont); test dedicado |
| AUD-LECT-22 | ✅ OK | `checks/compras_pagos.py::asiento_compra_pago_desbalanceado_saldo_null`; test dedicado |
| AUD-LECT-23 | ✅ OK | `checks/compras_pagos.py::integridad_anulacion_compra_pago` |

**Resumen AUD-LECT:** 23/23 ✅ implementados. ⚠️ 8 checks sin test unitario dedicado (periodos, cierres parcial, integridad_anulacion, imputacion, nro_duplicado, huerfano, concepto_no_normal).

---

### POL (políticas configurables) — 13 requisitos

| Requisito | Estado | Evidencia |
|-----------|--------|-----------|
| POL-01 | ✅ OK | `contabilidad_audit/models.py::PoliticaAuditoriaContable`; migraciones |
| POL-02 | ✅ OK | `politicas.py::resolver_politica`; tests default/override |
| POL-03 | ✅ OK | `_sql.py::filtro_anulados_sql` + design emparejamiento |
| POL-04 | ✅ OK | `_sql.py::clasificar_delta`; test centavo |
| POL-05 | ✅ OK | `models.py::clean` + fallback lectura; tests validación/fallback |
| POL-06 | ✅ OK | Modelo + `_marcar_exclusiones` / gates apply en `cont_recalculo_service.py` |
| POL-07 | ⚠️ PARCIAL | Enum `alcance_recompute` en modelo y `_ejercicios_en_alcance`; **sin advertencia UI de performance** para `historico` ni procesamiento por lotes documentado en UI |
| POL-08 | ✅ OK | `tolerancia_decimal` en checks y dry-run |
| POL-09 | ✅ OK | `calcular_config_hash` v1:sha256; tests |
| POL-10 | ⚠️ PARCIAL | `actualizado_por` / `actualizado_en` en modelo; **sin historial consultable** (spec DEBERÍA) |
| POL-11 | ✅ OK | Política pasada explícita a checks y `cont_recalculo_service` |
| POL-12 | ✅ OK | `views.py` configuración + permisos en `core/constantes_permisos.py` |
| POL-13 | ✅ OK | Template configuración canon; metadatos dd/MM/yyyy |

**Resumen POL:** 11/13 ✅, 2/13 ⚠️ parcial (POL-07 UI, POL-10 historial).

---

### REC (recálculo/corrección) — 18 requisitos

| Requisito | Estado | Evidencia |
|-----------|--------|-----------|
| REC-01 | ✅ OK | `dry_run()` SELECT-only; `apply()` exige plan; tests dry-run sin DML |
| REC-02 | ✅ OK | `_es_entorno_produccion()` + permiso; `test_apply_bloqueado_fuera_de_produccion` |
| REC-03 | ✅ OK | `_crear_backups` → `*_bkp_<timestamp>`; abort si falla |
| REC-04 | ✅ OK | Transacción única autocommit off; rollback en error |
| REC-05 | ✅ OK | `data_fingerprint` pre-tx + intra-tx; `FOR UPDATE` en `_bloquear_filas_objetivo` |
| REC-06 | ✅ OK | DDL `contabilidad_audit/sql/` + `catalog.py::run_contabilidad_audit_correccion_log_mysql`; INSERT log en apply |
| REC-07 | ⚠️ PARCIAL | `_orden_apply_items`: asientos → saldos ejercicio → saldos periodo. **Faltan pasos spec 2–3**: no hay plan/apply para `concepto_anulacion_incoherente` (UPDATE) ni `cuentas_sin_fila_saldo` como check_id dedicado (INSERT saldo vía REC-17 cubre parcialmente filas faltantes) |
| REC-08 | ⚠️ PARCIAL | Auto-apply: regen compras/pagos + rebuild saldos + REI aprobado. Excluidos en `CHECKS_EXCLUIDOS_AUTO_APPLY`. **Sin auto-corrección concepto anulación** |
| REC-09 | ✅ OK | `_marcar_exclusiones`, `confirmar_reapertura`, `reapertura_flag` en log |
| REC-10 | ✅ OK | `_ejercicios_en_alcance` según política |
| REC-11 | ✅ OK | Plan vacío → estado aplicado; fingerprint estable; regen no duplica |
| REC-12 | ✅ OK | Escritura vía `administranet_types` en apply |
| REC-13 | ✅ OK | `_calcular_impacto` + export dry-run en views |
| REC-14 | ⚠️ PARCIAL | `rollback_lote()` implementado (`cont_recalculo_service.py`); **sin test dedicado** (solo import en suite) |
| REC-15 | ✅ OK | Guards TTL + config_hash + data_fingerprint; tests invalidación |
| REC-16 | ✅ OK | Exclusión saldo_pc NULL; plan vacío; defaults política |
| REC-17 | ✅ OK | `_plan_reconstruccion_saldos`, `_movimientos_diario` (incluye anulados), modelo sin arrastre; test fingerprint/idempotencia |
| REC-18 | ✅ OK | `_plan_regeneracion_asientos`, reuse codmov, redondeo, encadenamiento saldos; tests regen + apply bloqueado dev |

**Resumen REC:** 14/18 ✅, 4/18 ⚠️ parcial (REC-07, REC-08, REC-14 tests, coherencia task 3.6).

---

## Spec Compliance Matrix (muestra representativa)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| AUD-LECT-01 | Corrida sin escritura | `test_runner.py > test_corrida_sin_dml_legacy` | ✅ COMPLIANT |
| AUD-LECT-14 | Índices faltantes no_computable | `test_rei.py > test_rei_recalculo_no_computable_sin_delta_espurio` | ✅ COMPLIANT |
| AUD-LECT-14 | Desalineación H44 | `test_rei.py > test_rei_recalculo_desalineacion_config_h44` | ✅ COMPLIANT |
| AUD-LECT-21 | Comprobante sin asiento | `test_checks.py > test_comprobante_sin_asiento` | ✅ COMPLIANT |
| POL-09 | Hash estable | `test_politicas.py > test_config_hash_estable` | ✅ COMPLIANT |
| REC-01 | Dry-run sin DML | `test_cont_recalculo_dry_run.py > test_dry_run_no_ejecuta_dml_legacy` | ✅ COMPLIANT |
| REC-02 | Apply bloqueado dev | `test_cont_recalculo_apply.py > test_apply_bloqueado_fuera_de_produccion` | ✅ COMPLIANT |
| REC-15 | Política invalida plan | `test_cont_recalculo_dry_run.py > test_cambio_politica_cambia_config_hash` | ✅ COMPLIANT |
| REC-17 | Reconstrucción idempotente | `test_cont_recalculo_apply.py > test_reconstruccion_saldos_fingerprint_estable_sin_cambios` | ✅ COMPLIANT |
| REC-18 | Regen sin duplicar | `test_cont_recalculo_apply.py > test_regeneracion_no_duplica_si_asiento_existe` | ✅ COMPLIANT |
| REC-11 | Piloto post-apply saldo verde | `test_cont_recalculo_apply_integracion.py > test_apply_y_saldo_ejercicio_vs_diario_verde` | ⚠️ SKIPPED (entorno piloto) |
| REC-07 | UPDATE concepto anulación | (none found) | ❌ UNTESTED |
| REC-14 | Rollback por lote | (none found) | ❌ UNTESTED |
| AUD-LECT-23 | Integridad anulación compra/pago | (none found) | ❌ UNTESTED |

**Compliance summary (escenarios con evidencia runtime):** ~28/32 escenarios críticos COMPLIANT; 1 SKIPPED; 3 UNTESTED en motor corrección / check integridad.

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| F1 solo SELECT / F3 en legacy_db | ✅ Yes | Separación respetada |
| 17 checks registry | ✅ Yes | +1 vs 16 mínimo (integridad_anulacion) |
| config_hash v1:sha256 | ✅ Yes | `politicas.py` |
| 3 guards plan (TTL, config, fingerprint) | ✅ Yes | `dry_run` / `apply` |
| REI caso a caso | ✅ Yes | `AprobacionREI`, vista REI, `apply(modo='rei')` |
| DDL log vía catalog.py | ✅ Yes | Provider registrado |
| Orden apply REC-07 completo | ⚠️ Deviated | Solo regen asientos + recompute saldos (+ REI) |
| design.md «contabilidad_audit NO existe» | ⚠️ Stale | Artefacto de diseño no actualizado post-apply |

---

## Discrepancias specs / design / tasks vs implementación

1. **Task 3.6 [x]** cita orden «paso 2 concepto → paso 3 INSERT saldos → paso 4 recompute»; el motor de corrección **no genera plan** para `concepto_anulacion_incoherente` ni etiqueta `cuentas_sin_fila_saldo` (solo REC-17/18).
2. **REC-07 / REC-08 en spec** exigen auto-apply de concepto anulación y INSERT filas saldo faltantes; implementación limita `CHECKS_INCLUIDOS` a regen + saldos (+ REI aparte).
3. **POL-07** spec pide advertencia UI en alcance `historico`; no encontrada en templates/views.
4. **POL-10** historial de cambios de política: no implementado (solo último `actualizado_*`).
5. **tasks.md** pie «Listo para sdd-apply» contradice fase `apply-complete` en `state.yaml`.
6. **Test integración piloto (3.17)** existe pero skip permanente fuera de piloto — aceptable con documentación.

---

## Issues Found

### CRITICAL (resolver antes de considerar REC spec-complete)

1. **REC-07 / REC-08 / task 3.6:** Motor de corrección no implementa pasos 2–3 del orden seguro (UPDATE concepto anulación, INSERT filas saldo vía check dedicado). Task marcada completa pero spec no cumplida en esa parte.

### WARNING (debería corregirse)

1. **REC-14:** `rollback_lote` sin test unitario/integración mock.
2. **POL-07:** Sin advertencia de performance para `alcance_recompute=historico`.
3. **POL-10:** Sin UI/historial de cambios de política.
4. **Cobertura tests auditoría:** Varios checks (AUD-LECT-10, 11, 12, 13, 15, 23) sin tests dedicados.
5. **Metadatos change:** `state.yaml` `status: proposed`; pie `tasks.md` obsoleto; `design.md` stale.

### SUGGESTION

1. Ejecutar test integración piloto en entorno controlado antes de producción real.
2. Añadir test de invalidación TTL expirado en apply (guard 1/3).

---

## Verdict

**PASS WITH WARNINGS**

Fases 0–3 están implementadas con **35 tests (34 OK, 1 skip esperado)**. Auditoría solo lectura (AUD-LECT), políticas (POL) y el núcleo de corrección (dry-run, guards triples, apply transaccional, regen compras/pagos, rebuild saldos, REI defensivo) están **operativos y alineados**. Quedan gaps **parciales en REC-07/REC-08** (corrección automática de concepto anulación / cuentas_sin_fila) y **tests faltantes** (rollback, varios checks). **Recomendación:** no archivar como «spec REC 100%» hasta resolver REC-07/08 o documentar desvío explícito; **sí** proceder a `sdd-archive` para el **MVP F1 + pipeline F2/F3 acotado** si producto acepta el alcance actual de corrección (regen + saldos + REI).

**Next:** `sdd-archive` con nota de gaps REC-07/08, **o** `sdd-apply` puntual para completar pasos 2–3 del motor de corrección y tests REC-14.
