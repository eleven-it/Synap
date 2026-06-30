# Verification Report

**Change**: armado-unificado-imputacion-1ra  
**Version**: specs delta jun/2026  
**Mode**: Standard (strict_tdd no configurado en openspec/config.yaml)  
**Fecha**: 17/06/2026

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 28 |
| Tasks complete | 25 |
| Tasks incomplete | 3 |

### Tareas incompletas

| Task | Severidad | Notas |
|------|-----------|-------|
| 5.5 Suite en contenedor | **Resuelto en verify** | Ejecutada en esta verificación: 32 tests OK (ver abajo). Recomendado marcar `[x]` en tasks.md. |
| 6.1 `MANUAL_USUARIO_MPR.md` § Armado 1ra/2da e imputación | WARNING | Existe §4.2 C/D con rutas y reglas; **falta** sección operativa dedicada a imputación supervisor (FIFO, confirmación, estados). |
| 6.3 Actualizar SDD estado a implementado tras verify | INFO | Actualizado `state.yaml` → `verify: done` en esta corrida. |

---

## Build & Tests Execution

**Build (syntax)**: ✅ Passed

```bash
python3 -m py_compile mpr/services.py mpr/views.py mpr/request_scope_cache.py
# exit 0
```

**Tests**: ✅ 32 passed / 0 failed / 0 skipped

```bash
docker exec Synap_app python manage.py test \
  mpr.tests.test_armado_unificado_modo \
  mpr.tests.test_armado_unificado_lote_1ra \
  mpr.tests.test_imputacion_armado_1ra \
  mpr.tests.test_estado_acciones_opt_cierre \
  mpr.tests.test_armado_1ra_catalog \
  mpr.tests.test_armado_catalog_api \
  mpr.tests.test_mpr_performance_bulk \
  -v 2
# Ran 32 tests in 0.343s — OK
```

**Notas de ejecución (no bloqueantes):** en `EstadoAccionesOptCierreTest` aparece log `Unknown database 'emp'` al resolver depósito Producción; los tests pasan con mocks parciales.

**Coverage**: ➖ Not available (no umbral configurado en openspec/config.yaml)

---

## Spec Compliance Matrix

### mpr-armado-unificado

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Entrada canónica por menú | Armado 2da sin OPT | `test_armado_surtido_view` / `test_post_modo_1ra_sin_gate_opt` (parcial 1ra) | ⚠️ PARTIAL — POST 1ra sin gate; 2da cubierta en tests surtido legacy |
| Entrada canónica por menú | Redirect legacy OPT armado | `test_armado_unificado_modo > test_armado_opt_redirect_a_1ra` | ✅ COMPLIANT |
| Lote exclusivo por modo | Cambio de modo con carrito ocupado | (none — UI Alpine) | ❌ UNTESTED |
| Armado 1ra con BOM | Pack 1ra sin stock semi (parcial) | `test_armado_unificado_lote_1ra > test_max_packs_limitado_por_componente_escaso` | ⚠️ PARTIAL — max packs, no ejecutar_lote parcial E2E |
| Armado 2da composición libre | Paridad multi-lote 2da | `test_armado_surtido_lote` (demanda/agregado/lote) | ⚠️ PARTIAL — servicios lote; no modal éxitos/fallos en view test |
| Deprecación CTAs en OPT | Detalle OPT sin armado | (none) | ❌ UNTESTED — evidencia estática: `opt_detail` sin CTAs armado; flags `mostrar_tarjeta_armado_surtido=False` |
| Cierre OPT sin armado | Cerrar OPT sin armado previo | `test_estado_acciones_opt_cierre > test_puede_cerrar_sin_armar_si_opp_cero` | ✅ COMPLIANT |

**Compliance armado-unificado**: 2/7 ✅ · 3/7 ⚠️ · 2/7 ❌ UNTESTED

### mpr-imputacion-armado-1ra

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Cola MSTOCK pendientes | MSTOCK 1ra pendiente visible | (none — solo mock vacío en perm test) | ❌ UNTESTED |
| Cola MSTOCK pendientes | MSTOCK 2da excluido | (none) | ❌ UNTESTED |
| Permiso supervisor | Operario sin permiso | `test_imputacion_armado_1ra > test_403_sin_permiso_imputacion` | ✅ COMPLIANT |
| Imputación por movimiento | Imputación parcial a un pedido | (none) | ❌ UNTESTED |
| Imputación por movimiento | Exceder cantidad armada | `test_imputacion_armado_1ra > test_rechaza_exceder_cantidad_armada` | ✅ COMPLIANT |
| Sugerencia FIFO | Confirmar sugerencia FIFO | `test_imputacion_armado_1ra > test_fifo_asigna_pedido_mas_antiguo_primero` | ✅ COMPLIANT |
| Actualización demanda | Pedido cubierto por imputación | (none) | ❌ UNTESTED |

**Compliance imputación**: 3/7 ✅ · 0/7 ⚠️ · 4/7 ❌ UNTESTED

### ui-fuente-verdad-reportes-mpr (delta)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Superficies canon | Canon armado POS `/mpr/armado/` | Redirects + rutas en `urls.py` | ⚠️ PARTIAL — estático; template canónico evolucionado `armado_surtido.html` (existe también `armado.html` para flujo BOM legacy) |
| Superficies canon | Sin CTAs armado en opt_detail | grep template | ⚠️ PARTIAL — estático |

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| `/mpr/armado/` + `modo=1ra\|2da` | ✅ | `ArmadoView` = `ArmadoSurtidoView`, redirects legacy |
| Sin gate OPT en POST armado | ✅ | `test_post_modo_1ra_sin_gate_opt`; `opt_puede_armado_surtido` ya no en flujo POST |
| `MprArmadoLote`, `MprImputacionArmado`, `modo` | ✅ | models + migration `0009` + admin |
| `ejecutar_lote_armado(modo)` | ✅ | delega 1ra/2da |
| BOM read-only 1ra + anti-tamper | ✅ | `validar_composicion_bom_1ra`, tests lote 1ra |
| Imputación FIFO + confirmar | ✅ | `sugerir_imputacion_fifo`, `confirmar_imputacion_armado` |
| Permiso `mpr.imputar_armado_1ra` | ✅ | views + tests 403 |
| `puede_cerrar` sin armado | ✅ | `test_estado_acciones_opt_cierre` |
| Performance P0/P2 (fuera spec SDD original) | ✅ | `listar_ventana_pack` optimizado; cache depositos por request |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Vista única `ArmadoView` | ✅ | Alias sobre `ArmadoSurtidoView` |
| Template `armado.html` unificado | ⚠️ Deviated | Canon POS usa `armado_surtido.html`; `armado.html` queda para flujo BOM/en_abm legacy (`ArmadoLegacyView`) |
| `_ejecutar_armado_1ra_tx` dedicada | ⚠️ Deviated | tasks.md documenta vía validación BOM + `_ejecutar_armado_surtido_tx` (aceptado en tasks) |
| Eliminar gates OPT | ✅ | flags tarjeta armado en opt_detail desactivados |
| Imputación tabla Synap + UPDATE legacy | ✅ | `MprImputacionArmado` + servicios |
| Redirects legacy 6 meses | ✅ | `armado-surtido`, `opt/<id>/armado/` |

---

## Issues Found

### CRITICAL (must fix before archive)

None — funcionalidad core implementada y suite principal verde.

### WARNING (should fix)

1. **Escenarios sin test behavioral**: cola imputación (1ra visible / 2da excluida), imputación parcial restante, actualización `estado_pedido_opt` post-imputación, cambio modo con carrito (Alpine).
2. **Manual usuario 6.1 incompleto**: falta § operativo imputación supervisor (pasos UI, FIFO, confirmación).
3. **Task 5.5** pendiente en tasks.md aunque la suite ya pasó en contenedor — marcar completada.
4. **Design vs template**: documentar en manual que `armado_surtido.html` es la plantilla POS unificada (no renombrar sin migración).

### SUGGESTION (nice to have)

1. Test view `opt_detail` assert ausencia de enlaces `armado-surtido` / `armado_opt`.
2. Test integración `listar_mstock_pendientes_imputacion` filtra `modo != '1ra'`.
3. Open questions design: permiso imputación vs admin MPR; KPI tablero MSTOCK pendientes.

---

## Verdict

**PASS WITH WARNINGS**

Implementación del change **armado-unificado-imputacion-1ra** está **completa en código** para Fases 1–4 y performance asociada; **32/32 tests** de la suite verificada pasan en contenedor. Quedan **huecos de cobertura** en escenarios de imputación/cola y **documentación manual** de imputación antes de archivar sin reservas. Apto para staging con seguimiento de warnings.
