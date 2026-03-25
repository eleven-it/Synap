# Definition of Done por fase — compras (captura / workflow / posting)

**Uso:** ningún merge a la rama de integración del módulo sin cumplir el DoD de la fase declarada en el PR/MR.  
**Plan maestro:** [master_execution_plan.md](master_execution_plan.md).

---

## Fase 0 — Preparación

**DoD (todos obligatorios):**

- [ ] [open_decisions_checklist.md](open_decisions_checklist.md) revisado; ítems B2/B3 identificados y con plan o fecha.
- [ ] Ruta documental acordada: especificaciones y plan de ejecución en `docs/compras/` (incluye este conjunto: `master_execution_plan.md`, `uiux_plan.md`, `open_decisions_checklist.md`, `definition_of_done_by_phase.md`, `phase_1_bootstrap_plan.md`).
- [ ] Repositorio: rama base acordada; CI ejecuta al menos lint/tests existentes del monorepo sin regresión.
- [ ] Contrato `LegacyPostingCommand` v1 **referenciado** desde código o issue enlazado a [posting_contract.md](posting_contract.md) (puede ser solo doc hasta Fase 1).
- [ ] UX: kickoff completado según [uiux_plan.md](uiux_plan.md) Fase 0.

**Fuente prioridad:** *decisión nueva de arquitectura/producto* (gobernanza).

---

## Fase 1 — Dominio interno

**DoD:**

- [ ] Apps Django creadas según [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md); migraciones aplicables en entorno dev.
- [ ] Modelos persisten expediente, líneas, documento adjunto (opcional vacío), estado workflow, auditoría interna mínima.
- [ ] Máquina de estados: transiciones inválidas rechazadas con error claro (test).
- [ ] API REST (o equivalente Synap) CRUD + transiciones **sin** llamar MySQL legacy.
- [ ] Tests: cobertura mínima acordada en [test_strategy.md](test_strategy.md) para TC-WF críticos.
- [ ] **No** imports de implementación SQL legacy en app expediente (ADR-0005).
- [ ] Documentación `docs/compras/` actualizada si el modelo diverge de [domain_model.md](domain_model.md).

**Fuente:** *decisión nueva de arquitectura* + PRD.

---

## Fase 2 — Captura + OCR

**DoD:**

- [ ] Subida archivo con validación MIME/tamaño; almacenamiento según decisión D-02 (dev mínimo aceptable).
- [ ] Job asíncrono encolado; estado observable en API (polling o equivalente).
- [ ] OCR: adapter **heuristic** en CI (PDF con texto embebido); **http** opcional para OCR externo; interfaz `OcrAdapter` estable.
- [ ] PWA: shell instalable o documentado «deferred» con justificación en PR si no aplica en este incremento.
- [ ] Tests TC-CAP / TC-OCR según [test_cases.md](test_cases.md) (mínimo acordado).
- [ ] Runbook: qué pasa si worker cae (reintento idempotente a nivel job).

**Fuente:** *decisión nueva de producto* (OCR); auditoría no aplica.

---

## Fase 3 — Workflow revisión

**DoD:**

- [ ] Analista puede editar cabecera y líneas; validaciones servidor alineadas a campos del futuro `LegacyPostingCommand` (tabla de trazabilidad en código o doc).
- [ ] Rechazo con motivo persistido; aprobación llama a **stub** posting o flag fake con respuesta estable (contrato [posting_contract.md](posting_contract.md)).
- [ ] Permisos según [product_requirements.md](product_requirements.md) §10 (o documento permisos Synap que lo sustituya).
- [ ] UI MVP según [uiux_plan.md](uiux_plan.md) §6 o excepción aprobada.
- [ ] **Ninguna** escritura en tablas legacy AdministraNET (ADR-0001).
- [ ] **`LegacyPostingCommand` v1 congelado** al cierre de esta fase: código, validaciones y documentación alineados a [posting_contract.md](posting_contract.md) v1; gobierno según [adrs/0006-congelamiento-legacy-posting-command-v1.md](adrs/0006-congelamiento-legacy-posting-command-v1.md).

**Fuente:** PRD + ADR-0001 + ADR-0005 + ADR-0006.

---

## Fase 4 — Posting legacy

**Test gate obligatorio (regla de equipo):** no se permite ejecutar **SQL real** del adapter contra **MySQL legacy** hasta que estén **en verde** (CI o verificación acordada) todas las suites:

- **UT-CMD-*** ([posting_tests.md](posting_tests.md) §2)
- **UT-ADP-*** ([posting_tests.md](posting_tests.md) §4)
- **Preflight** **UT-PRE-*** ([posting_tests.md](posting_tests.md) §5)

Referencia normativa: [master_execution_plan.md](master_execution_plan.md) §6 y [posting_tests.md](posting_tests.md).

**DoD:**

- [ ] Test gate cumplido **antes** de integrar SQL real contra legacy (ver bloque anterior).
- [ ] `LegacyPostingAdapter` ejecuta transacción única MySQL ADR-0002 para camino **contado mínimo** y **crédito mínimo** en fixture ([posting_tests.md](posting_tests.md) IT-LEG-01/02).
- [ ] Rollback verificado IT-LEG-03; preflight duplicado y período fiscal TC-VAL según matriz MVP [test_cases.md](test_cases.md).
- [ ] Aprobación real: solo `aprobado` + `legacy_codigo_movimiento` si commit OK; idempotencia Synap según contrato.
- [ ] Cada módulo P* trazable a [posting_sql_spec.md](posting_sql_spec.md) o issue explícito de gap.
- [ ] Tipos normalizados AdministraNET en capa escritura ([../general/TIPOS_DATOS_ADMINISTRANET.md](../general/TIPOS_DATOS_ADMINISTRANET.md) / `administranet_types`).
- [ ] Feature flag: posting real solo si activado en settings.

**Fuente:** *confirmado por auditoría* (comportamiento destino) + ADRs.

---

## Fase 5 — Hardening

**DoD:**

- [ ] Test concurrencia codmov o documento de riesgo aceptado + monitorización.
- [ ] Política FM en tests TC-VAL-03/04.
- [ ] Observabilidad: logs estructurados con `expediente_id`, `codigo_movimiento`; métricas básicas.
- [ ] Límites rate upload; checklist seguridad archivos.
- [ ] Runbook errores posting para operaciones.

**Fuente:** *decisión nueva de arquitectura* + riesgos auditoría.

---

## Fase 6 — Rollout

**DoD:**

- [ ] **Primer deploy seguro** completado antes de habilitar posting real en el entorno objetivo: feature flag de posting **desactivado** (o backend `noop`/`fake`); flujo operativo solo hasta **aprobación lógica** sin escritura legacy; **validación con usuarios reales** y registro de feedback; criterio explícito «listo para encender posting» firmado por producto + tech lead. Detalle: [master_execution_plan.md](master_execution_plan.md) §7.
- [ ] Flag por empresa/sucursal en prod; plan rollback comunicado.
- [ ] Prueba en pre-prod con schema representativo.
- [ ] Material capacitación analistas (breve) o sesión grabada.
- [ ] Criterios de éxito medibles primera semana (volumen, tasa error posting) definidos con producto.

**Fuente:** *decisión nueva de producto*.
