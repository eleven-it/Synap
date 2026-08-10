# Verification Report

**Change:** `vmm-dto-pie-facturacion`  
**Capability:** `reports-ventas-marcas-mensual`  
**Version:** spec inicial (delta funcional)  
**Mode:** Standard (strict_tdd no activo)  
**Fecha verify:** 10/08/2026  
**Verificador:** sdd-verify

---

## Verdict

**PASS WITH WARNINGS** — Implementación alineada con specs, design y tasks; 88/88 tests verdes en contenedor. Gaps menores: test dedicado filtro marca parcial (ADR-4), escenario integrado proyección/regalías-TC post-pie, y validación E2E MySQL.

---

## Completeness

| Métrica | Valor |
|---------|-------|
| Tasks total | 20 |
| Tasks complete | 20 |
| Tasks incomplete | 0 |

Todas las tareas en `tasks.md` están marcadas `[x]`. Coherencia general verificada contra código y tests.

**Nota:** T6.1 declara test de filtro marca parcial; no se encontró test dedicado con ese nombre o assert explícito (ver WARNINGS).

---

## Build & Tests Execution

**Build:** ➖ No aplica (proyecto Django; sin build/type-check separado configurado)

**Tests:** ✅ 88 passed / ❌ 0 failed / ⚠️ 0 skipped

```bash
docker exec Synap_app python manage.py test --keepdb \
  reports.tests.test_comprobante_descuento_cabecera \
  reports.tests.test_ventas_marcas_mensual \
  reports.tests.test_dabra_consolidado_remitos
```

```
Ran 88 tests in 27.889s
OK
```

**Coverage:** ➖ No disponible en esta ejecución

---

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-VMM-PIE-01 | FA con dto al pie 20 % | `test_ventas_marcas_mensual.py > test_fa_dto_pie_20_facturacion_y_regalias` | ✅ COMPLIANT |
| REQ-VMM-PIE-01 | Signo NC preservado | `test_ventas_marcas_mensual.py > test_nc_mismo_factor_signo_negativo` | ✅ COMPLIANT |
| REQ-VMM-PIE-02 | SubTotal1 cero | `test_comprobante_descuento_cabecera.py > test_subtotal1_cero_factor_uno` | ✅ COMPLIANT |
| REQ-VMM-PIE-02 | Sin dto al pie | `test_comprobante_descuento_cabecera.py > test_sin_pie_factor_uno` + `test_ventas_marcas_mensual.py > test_sin_pie_paridad_factor_uno` | ✅ COMPLIANT |
| REQ-VMM-PIE-03 | Paridad pantalla vs export Detalle | `test_ventas_marcas_mensual.py > test_suma_detalle_coherente_con_kpi` | ✅ COMPLIANT |
| REQ-VMM-PIE-03 | Modo comparar | `test_ventas_marcas_mensual.py > test_modo_comparar_kpis_post_pie` | ✅ COMPLIANT |
| REQ-VMM-PIE-03 | Factor cabecera completo (filtro marca parcial) | (ninguno dedicado) | ⚠️ PARTIAL |
| REQ-VMM-PIE-04 | Regalías sobre base post-pie | `test_ventas_marcas_mensual.py > test_fa_dto_pie_20_facturacion_y_regalias` | ✅ COMPLIANT |
| REQ-VMM-PIE-04 | Regalías/TC post-pie (800, TC 14,5817) | `test_ventas_marcas_mensual.py > KpisLicenciaTest.test_tasa_13_pct_regalias` (genérico, no integrado post-pie) | ⚠️ PARTIAL |
| REQ-VMM-PIE-04 | Proyección $ post-pie (800 → pf 856) | `test_ventas_marcas_mensual.py > ProyeccionTest.test_aplicar_proyeccion_en_matriz` (f=100, no integrado) | ⚠️ PARTIAL |
| REQ-VMM-PIE-05 | Unidades invariantes con dto pie | `test_ventas_marcas_mensual.py > test_unidades_sin_factor_pie_con_dto_20` | ✅ COMPLIANT |
| REQ-VMM-PIE-06 | Regresión DABRA | `test_dabra_consolidado_remitos` (suite completa) | ✅ COMPLIANT |
| REQ-VMM-PIE-06 | Tests factor VMM | `test_comprobante_descuento_cabecera.py` (4 clases) | ✅ COMPLIANT |

**Compliance summary:** 10/13 escenarios ✅ COMPLIANT, 3/13 ⚠️ PARTIAL, 0 ❌ FAILING/UNTESTED

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Evidencia |
|------------|--------|-----------|
| REQ-VMM-PIE-01 post-pie | ✅ Implementado | `sql_signo_imp_post_pie_expr()` en `ventas_marcas_mensual_rules.py`; runner L700 y export L83 usan post-pie |
| REQ-VMM-PIE-02 factor límite | ✅ Implementado | `comprobante_descuento_cabecera.py`: ε=0.0001, SubTotal1=0→1, SubtotalDesc null→SubTotal1 |
| REQ-VMM-PIE-03 coherencia | ✅ Implementado | Misma expr en runner, export detalle; modo comparar con post-pie |
| REQ-VMM-PIE-04 KPIs downstream | ✅ Implementado | `_compute_kpis_licencia` sin cambio de firma; regalías sobre fact post-pie |
| REQ-VMM-PIE-05 unidades | ✅ Implementado | `sql_signo_qty_expr` sin factor; tests unidades invariantes |
| REQ-VMM-PIE-06 helper compartido | ✅ Implementado | Módulo único; DABRA import + re-export en `__all__` |

---

## Coherence (Design / ADRs)

| Decisión | Followed? | Notas |
|----------|-----------|-------|
| ADR-1 Módulo compartido | ✅ Sí | `reports/services/comprobante_descuento_cabecera.py` creado |
| ADR-2 Expr nueva sin mutar vieja | ✅ Sí | `sql_signo_imp_expr()` intacta; VMM usa `sql_signo_imp_post_pie_expr()` |
| ADR-3 Epsilon y casos límite | ✅ Sí | Python y SQL alineados; tests unitarios |
| ADR-4 Filtro marca parcial | ✅ Sí (código + docs) | Documentado en SPEC y MAPEO; test dedicado ausente |
| DABRA re-export | ✅ Sí | `__all__` incluye `factor_descuento_cabecera`, `porcentaje_descuento_cabecera`; cero defs locales duplicadas |
| Licenciatarios pre-pie | ✅ Sí | `ventas_mensuales_licenciatarios_query.py` sigue con `sql_signo_imp_expr()` |
| Export sin `_signo_imp_sql` | ✅ Sí | Función eliminada; solo assert negativo en test |

---

## Grep de regresión (T8.1)

| Check | Resultado |
|-------|-----------|
| VMM runner usa post-pie | ✅ `ventas_marcas_mensual_runner.py:700` → `sql_signo_imp_post_pie_expr()` |
| VMM export usa post-pie | ✅ `ventas_marcas_mensual_export.py:83` → `sql_signo_imp_post_pie_expr()` |
| VMM runner NO usa expr vieja | ✅ Sin `sql_signo_imp_expr()` en runner |
| Licenciatarios pre-pie | ✅ `ventas_mensuales_licenciatarios_query.py:41` → `sql_signo_imp_expr()` |
| `_signo_imp_sql` en producción | ✅ Ausente (solo assert en test) |
| Defs duplicadas factor | ✅ Solo en `comprobante_descuento_cabecera.py` |

---

## Documentación (T7)

| Doc | post-pie / dto pie | Estado |
|-----|-------------------|--------|
| `docs/reports/SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md` | §3.1 motor post-pie, filtro marca parcial ADR-4 | ✅ |
| `docs/reports/MAPEO_PUW_PUM_ADMINISTRANET.md` | §3.1 factor cabecera compartido VMM/DABRA | ✅ |
| `docs/reports/MANUAL_USUARIO_REPORTES.md` | Frase facturación incluye dto al pie | ✅ |

---

## Issues Found

### CRITICAL (must fix before archive)

None

### WARNING (should fix)

1. **Test filtro marca parcial (ADR-4):** T6.1 marcada done pero no hay test que valide factor cabecera completo con subset de marcas (p. ej. FA multi-marca, filtro una marca, assert factor no recalculado por subset).
2. **Escenarios REQ-VMM-PIE-04 integrados:** `regalias_tc` y proyección `pf=856` con base post-pie 800 no tienen test integrado end-to-end (solo unitarios genéricos).
3. **Validación E2E MySQL:** Todos los tests usan mocks; no hay smoke contra MySQL real con FA `PorDesc1` (riesgo residual de paridad SQL vs AdministraNET).
4. **Proposal § Success Criteria:** checkboxes en `proposal.md` siguen `[ ]` pese a implementación completa (inconsistencia documental menor).

### SUGGESTION (nice to have)

1. Añadir assert `regalias_tc ≈ 104/14.5817` en `test_fa_dto_pie_20_facturacion_y_regalias`.
2. Test proyección con `f=800`, `coef=1.07` → `pf=856` en fixture post-pie.

---

## Checklist REQ (resumen ejecutivo)

- [x] REQ-VMM-PIE-01 — Importe post-pie (FA 20 %, NC signo)
- [x] REQ-VMM-PIE-02 — Factor cabecera y casos límite
- [x] REQ-VMM-PIE-03 — Coherencia matriz/comparar/export (parcial: filtro marca sin test)
- [x] REQ-VMM-PIE-04 — Regalías/proyección (parcial: escenarios integrados)
- [x] REQ-VMM-PIE-05 — Unidades sin cambio
- [x] REQ-VMM-PIE-06 — Helper compartido y paridad DABRA

---

## Riesgos residuales

| Riesgo | Severidad | Mitigación actual |
|--------|-----------|-------------------|
| Filtro marca parcial Σ ≠ SubtotalDesc subset | Media | ADR-4 documentado; sin test automatizado |
| Paridad MySQL real vs mock | Media | Suite mock verde; smoke manual pendiente |
| Redondeo Σ líneas × factor | Baja | Mismo criterio DABRA; tolerancia places=2 |

---

## Next recommended

**sdd-archive** — No hay blockers CRITICAL; warnings son mejoras de cobertura, no regresiones funcionales detectadas.
