# Plan de implementación por fases: captura + posting factura compra

**Referencias:** [architecture.md](architecture.md), [test_strategy.md](test_strategy.md), [README.md](README.md) (índice del módulo compras).

---

## Fase 0 — Preparación (ya hecho en parte)

- [x] Auditoría VB6 completa (`auditoria_facturas_compras_*`).
- [x] Especificación producto, dominio, legacy, arquitectura, ADRs, tests.
- [ ] Aprobar decisiones abiertas de [README.md](README.md) (OCR, storage, FM default).

**Entregable:** checklist firmado por producto/técnico.

---

## Fase 1 — Dominio interno (TDD primero)

**Objetivo:** expediente, estados, líneas, documentos en DB Synap sin MySQL legacy.

**Tests primero:** TC-WF-*, TC-CAP-01/02 sin OCR real (mock).

**Implementación:**

- Modelos Django + migraciones internas.
- `ExpedienteService`, máquina de estados.
- API mínima CRUD expediente + transiciones (sin aprobar aún).

**Definición de hecho:** cobertura workflow ≥ umbral; sin imports de `factura_compra_posting`.

---

## Fase 2 — Captura, archivos y OCR pipeline

**Objetivo:** cámara/PDF → almacenamiento → job asíncrono → actualización expediente.

**Tests primero:** TC-OCR-01/02, TC-CAP-* con fixtures archivo.

**Implementación:**

- Storage backend, validación MIME/tamaño.
- Cola Celery/Django-Q + tarea OCR con **adapter mock** en CI.
- PWA shell: upload, lista expedientes, detalle básico.

**Definición de hecho:** E2E manual captura → borrador con resultado OCR simulado.

---

## Fase 3 — Workflow de revisión y edición

**Objetivo:** analista edita cabecera/renglones; validaciones de negocio Synap (no legacy).

**Tests primero:** TC-WF-02, validaciones de campos obligatorios pre-posting.

**Implementación:**

- UI formularios alineados a campos del `LegacyPostingCommand` (mapper documentado).
- Permisos PRD.
- Historial / comentarios internos.

**Definición de hecho:** rechazo y re-edición sin tocar MySQL.

---

## Fase 4 — Posting legacy

**Objetivo:** `LegacyPostingAdapter` + transacción única MySQL (ADR-0002).

**Tests primero:** TC-POST-01–04, TC-VAL-01–02, TC-ERR-10; luego OC/remito/vales/series/contabilidad.

**Implementación:**

- Conexión secundaria MySQL, repositorios SQL parametrizados.
- Módulos por bloque: cabecera, líneas, caja/op, puentes, asiento (feature flags).
- Integración con botón Aprobar: transición `aprobado` solo si posting OK.

**Definición de hecho:** matriz MVP de [test_cases.md](test_cases.md) en verde contra MySQL fixture.

---

## Fase 5 — Hardening

- TC-POST-05 concurrencia.
- TC-VAL-03/04 FM (config).
- Observabilidad, límites rate, hardening archivos.
- Documentación operativa (runbook errores posting).

---

## Fase 6 — Testing integral y rollout

- E2E Playwright opcional.
- Prueba en ambiente pre-producción con schema cliente anonimizado.
- Rollout por empresa/sucursal con feature flag `factura_compra_captura_enabled`.
- Capacitación analistas de compras.

---

## Dependencias entre fases

```text
0 → 1 → 2 → 3 → 4 → 5 → 6
         ↘_______↗   (fase 3 y 4 pueden paralelizarse con dos equipos si el Command está definido por contrato)
```

**Contrato estable entre 3 y 4:** `LegacyPostingCommand` versionado (JSON schema o pydantic en código).

---

## Trazabilidad auditoría

La fase 4 debe cerrar ítems de `especificacion_tecnica_replicacion_factura_compra.json` (`tablas_afectadas`, `orden_persistencia_recomendado`, `validaciones_criticas`).
