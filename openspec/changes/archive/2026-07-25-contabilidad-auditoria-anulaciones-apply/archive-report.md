# Archive report — contabilidad-auditoria-anulaciones-apply

**Archivado:** 25/07/2026  
**Spec sync:** `openspec/specs/contabilidad-recalculo-correccion/spec.md` (REC-07/08 MODIFIED + REC-19 ADDED)

## Entregado

- Motor REC-19 en `legacy_db/services/cont_recalculo_service.py` (plan + apply + backup `cuentaproveedor`).
- UI: flujo tablero→dry-run→apply, sección anulaciones, lotes + rollback modal Synap.
- Tests: `legacy_db/tests/test_cont_recalculo_anulaciones.py` (+ vistas) en verde.
- Piloto `administranet89`: apply ej.1 lote `L20260725_175235-16b64871` (60 filas); dry-run post idempotente.
- Docs: `AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md`, `AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` §6.8.

## Residual documentado

- 26 diffs globales de integridad: 18 `falta_contra` sin asiento original; 10 marcadores fuera de `ejercicio_seleccionado`.
