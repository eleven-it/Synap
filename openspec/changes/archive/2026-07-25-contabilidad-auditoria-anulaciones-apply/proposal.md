# Propuesta — Apply de anulaciones incompletas (compras/pagos)

**Cambio:** `contabilidad-auditoria-anulaciones-apply`  
**Fecha:** 25/07/2026  
**Change base:** `contabilidad-auditoria-recalculo` (archivado)  
**Fuentes:** `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` §6.8, check `integridad_anulacion_compra_pago` (AUD-LECT-23), `legacy_db/services/cont_recalculo_service.py`

---

## Intent

Extender el **dry-run** y el **apply** del motor `cont_recalculo_service` para **reparar automáticamente** los hallazgos del check `integridad_anulacion_compra_pago`: comprobantes de compra/pago (`FA`, `FC`, `OP`) marcados `Anulado='Si'` cuya anulación en partida doble quedó **incompleta** (falta marcador en `cuentaproveedor`, asiento original sin marcar, o falta contra-asiento). Los casos con contra-asiento existente pero **sin invertir** el original quedan **fuera** del auto-apply (revisión manual).

Complementa REC-18 (regeneración de huérfanos cm>0): los **86 marcadores cm=0** no son huérfanos de asiento sino piezas de anulación; este change trata la **reparación estructural** de anulaciones rotas, no la regeneración de asientos faltantes.

---

## Scope

### In scope

| Entregable | Descripción |
|------------|-------------|
| **Dry-run** | Nueva función `_plan_repair_anulaciones_incompletas` en `cont_recalculo_service.py`; items de plan por problema reparable |
| **Apply** | Paso intermedio en orden seguro: tras regen huérfanos (REC-18), antes de concepto anulación (REC-07 paso 2) |
| **Backup** | Ampliar `TABLAS_BACKUP_PERMITIDAS` con `cuentaproveedor` |
| **Trazabilidad** | Marca `"REGEN auditoria (anulacion incompleta)"` en renglones insertados; `check_id=integridad_anulacion_compra_pago` en log |
| **Registry apply** | Incluir `integridad_anulacion_compra_pago` en `CHECKS_INCLUIDOS` |
| **Tests** | Unitarios dry-run/apply; idempotencia; exclusión `contra_no_invierte_original` |
| **Docs** | Actualizar `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md` |

### Out of scope

- Auto-corrección de `contra_no_invierte_original` (contra mal armado → revisión manual).
- Modificar código VB6 o formularios `Cont_*`.
- Regenerar asientos huérfanos cm>0 (ya cubierto por REC-18).
- Anular comprobantes no marcados `Anulado='Si'` en `cuentaproveedor`.
- Cambios de esquema legacy (solo DML en tablas existentes).

---

## Reglas de negocio (obligatorias)

| Problema (`problemas[]` del check) | Remedio auto-apply |
|-----------------------------------|-------------------|
| `falta_marcador_cuentaproveedor_cm0` | INSERT marcador en `cuentaproveedor` con `CodigoMovimiento=0`, `codigo_movimiento_anul` = cm original, `Detalle="Anulacion - <Tipo> - <Nro>"`, `Anulado='No'` |
| `asiento_original_no_anulado` | UPDATE `cont_asiento` SET `anulado='Si'` en renglones con `codigo_movimiento` = cm original |
| `falta_contra_asiento` | INSERT contra-asiento: `id_concepto_asiento` 4 (FA/FC) u 8 (OP); debe/haber **invertidos** respecto al original; **`codigo_movimiento` nuevo** del contador global; `codigo_movimiento_anul` = cm original; `anulado='No'`; `nro_asiento` nuevo |
| `contra_no_invierte_original` | **EXCLUIDO** del auto-apply (bloqueado; item marcado `excluido` con motivo) |

---

## Orden apply (actualizado)

1. Regeneración huérfanos cm>0 (`comprobante_compra_pago_sin_asiento`, REC-18)  
2. **Reparación anulaciones incompletas** (`integridad_anulacion_compra_pago`, REC-19) — *nuevo*  
3. Concepto anulación incoherente (`concepto_anulacion_incoherente`, REC-07 paso 2)  
4. INSERT filas saldo faltantes (`cuentas_sin_fila_saldo`, REC-07 paso 3)  
5. Recompute saldos (`saldo_*_vs_diario`, REC-07 paso 4)

---

## Capabilities (contrato para sdd-spec)

### New Capabilities

**None**

### Modified Capabilities

| Capability | Delta |
|------------|-------|
| `contabilidad-recalculo-correccion` | ADDED REC-19 — reparación auto-apply de anulaciones incompletas compra/pago |

---

## Approach

1. Reutilizar la detección ya implementada en `integridad_anulacion_compra_pago` (`contabilidad_audit/services/checks/compras_pagos.py`) como fuente de verdad de problemas por `codigo_movimiento`.
2. Portar la lógica de planificación al servicio de corrección (`_plan_repair_anulaciones_incompletas`) generando items `(tabla, accion, clave, valor_anterior, valor_nuevo, check_id)`.
3. Encadenar en `dry_run()` después de `_plan_regeneracion_asientos` y antes de `_plan_concepto_anulacion_incoherente` (o integrar en el orden de items según design).
4. En `apply()`, ejecutar reparaciones por cm original en sub-orden: marcador → marcar original → insertar contra.
5. Tras mutaciones, encadenar reconstrucción de saldos afectados (REC-17) como hoy.

---

## Affected Areas

| Área | Rutas |
|------|-------|
| Motor corrección | `legacy_db/services/cont_recalculo_service.py` |
| Tests | `legacy_db/tests/test_cont_recalculo_dry_run.py`, `legacy_db/tests/test_cont_recalculo_apply.py` |
| Check lectura (sin cambio funcional) | `contabilidad_audit/services/checks/compras_pagos.py` |
| Docs | `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md` |
| Spec delta | `openspec/changes/contabilidad-auditoria-anulaciones-apply/specs/contabilidad-recalculo-correccion/spec.md` |

---

## Risks

| Riesgo | Mitigación |
|--------|------------|
| Contra-asiento mal invertido manualmente | Excluir `contra_no_invierte_original`; no sobrescribir contras existentes |
| Asignación de `codmov` concurrente con VB6 | Locking pesimista en contador global; re-validación fingerprint |
| Fecha del contra-asiento ambigua sin marcador previo | Usar `Fecha` del comprobante original; documentar en design |
| Reparación sobre ejercicio cerrado | Respetar `ejercicios_cerrados` (REC-09) |

---

## Rollback Plan

Backup previo de `cuentaproveedor` y `cont_asiento` vía `*_bkp_<timestamp>`. Reversión por `lote_id` con `rollback_lote` (REC-14). Items de reparación identificables por marca en `desc_renglon_asiento`.

---

## Dependencies

- Change base `contabilidad-auditoria-recalculo` aplicado (F2 dry-run + F3 apply operativos).
- Check `integridad_anulacion_compra_pago` en registry de auditoría.
- REC-18 (regen huérfanos) ya en `CHECKS_INCLUIDOS`.
- Permiso `contabilidad.auditoria.corregir` y `ENVIRONMENT=production` para apply.

---

## Success Criteria

- [ ] Dry-run lista items reparables por cm con problemas `{falta_marcador, asiento_original_no_anulado, falta_contra_asiento}` sin DML.
- [ ] Casos con `contra_no_invierte_original` aparecen como `excluido` con motivo en español.
- [ ] Apply en piloto repara anulaciones incompletas; check `integridad_anulacion_compra_pago` en verde post-apply.
- [ ] Segundo dry-run → plan vacío (idempotencia REC-11).
- [ ] Backup incluye `cuentaproveedor` cuando el plan la afecta.
- [ ] Tests: `docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_apply legacy_db.tests.test_cont_recalculo_dry_run`

---

*Listo para **sdd-design**, **sdd-spec** (delta) y **sdd-tasks**.*
