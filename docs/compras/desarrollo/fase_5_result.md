# Resultado Fase 5 — Hardening (entregado incremental)

**Referencias:** DoD Fase 5, [master_execution_plan.md](compras/master_execution_plan.md).

---

## 1. Concurrencia `codmov`

- **Diseño:** bloqueo `FOR UPDATE` en secuencia de posting antes de inserts (validado en UT-ADP con adapter de grabación).
- **Retry:** política recomendada — reintentos acotados en conflicto de bloqueo + jitter; documentar en runbook operativo al activar SQL real.
- **Tests dedicados:** ampliar con simulación de dos hilos cuando exista adapter MySQL de test.

---

## 2. Observabilidad

- **Logs estructurados:** `factura_compra_posting/structured_log.py` + uso en `aprobar_expediente_con_stub` (`evento`, `expediente_id`, `codigo_movimiento`).
- **Métricas:** pendiente integración Prometheus/OpenTelemetry según estándar Synap; campos sugeridos: `posting_ok_total`, `posting_fail_total`, `posting_duration_ms`.

---

## 3. Seguridad

- **Rate limit subida documentos:** `ComprasDocumentUploadThrottle` — scope `compras_document_upload`, `120/min` configurable en `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`.
- **Validación archivos:** ya en Fase 2 (MIME/tamaño); revisión antivirus en capa gateway si aplica en prod.

---

## 4. Errores y política FM

- Clasificación sugerida: `PostingValidationError.code` (negocio) vs excepciones técnicas del driver MySQL.
- Política FM duplicados: `PreflightLegacyPostingService.duplicate_includes_fm` alineado a ADR-0004 (UT-PRE-04).

---

## 5. Runbooks

### Errores posting (resumen)

1. Expediente en `error_posting`: revisar logs JSON `factura_compra_posting`.
2. Reintento: endpoint futuro o transición `reintentar_posting` (permiso `reintentar_posting`) cuando esté cableado al adapter real.
3. Si legacy inconsistente: rollback ya ejecutado en adapter — no reenviar mismo `idempotency_key` sin incrementar `posting_attempt`.

### Rollback manual

- Desactivar `FACTURA_COMPRA_LEGACY_SQL_ENABLED` y `FACTURA_COMPRA_POSTING_BACKEND=noop`/`fake` según entorno.
- Corregir datos en Synap (estado expediente) con procedimiento interno acordado; **no** tocar MySQL legacy sin DBA.

---

## 6. Tests

- Concurrencia / red: pendientes de harness MySQL; las suites actuales no sustituyen pruebas de carga.

**DoD Fase 5:** completar métricas y tests de concurrencia cuando el adapter real esté activo.
