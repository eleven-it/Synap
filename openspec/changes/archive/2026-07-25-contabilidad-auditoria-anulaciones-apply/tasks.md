# Tasks — Apply de anulaciones incompletas (compras/pagos)

**Change:** `contabilidad-auditoria-anulaciones-apply`  
**Estado:** Completado y archivado 25/07/2026

---

## Fase 1 — Helper de evaluación compartido

- [x] 1.1 `_evaluar_problemas_anulacion_cm` — paridad con check
- [x] 1.2 Paridad en `compras_pagos.py` (criterio `asiento_original_no_anulado`)
- [x] 1.3 Tests unitarios (módulo `test_cont_recalculo_anulaciones`)

## Fase 2 — Planificación dry-run (REC-19)

- [x] 2.1 Constantes CHECK_ANULACION / MARCA / conceptos 4/8
- [x] 2.2 `TABLAS_BACKUP_PERMITIDAS` + `cuentaproveedor`
- [x] 2.3 Check en `CHECKS_INCLUIDOS`
- [x] 2.4 `_plan_reparacion_anulaciones`
- [x] 2.5 Integración en `dry_run()`
- [x] 2.6 Contadores `anulaciones_reparables` / `anulaciones_bloqueadas`
- [x] 2.7 Tests dry-run / anulaciones

## Fase 3 — Apply transaccional

- [x] 3.1 Orden apply REC-18 → REC-19 → concepto → saldo
- [x] 3.2–3.6 Ejecutores marcador / marcar / contra
- [x] 3.7 Log por mutación
- [x] 3.8 Exclusiones ejercicio cerrado
- [x] 3.9 Tests apply

## Fase 4 — Verificación e integración

- [x] 4.1 Piloto administranet89 dry-run → apply → re-check
- [x] 4.2 Documentación residuales / saldos
- [x] 4.3 Docs AUDITORIA_* actualizados
- [x] 4.4 Suite relevante en verde (`--keepdb`)

## UI (plan piloto)

- [x] Tablero → dry-run → apply
- [x] Sección anulaciones en dry-run
- [x] Lotes + rollback modal Synap
