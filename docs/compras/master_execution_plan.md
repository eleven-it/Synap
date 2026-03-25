# Master execution plan — módulo captura / revisión / posting facturas de compra

**Rol:** plan maestro de ejecución y gobernanza técnica (tech lead).  
**No sustituye** el detalle funcional en [README.md](README.md) ni [implementation_plan.md](implementation_plan.md); los **ordena y cierra** con criterios de salida y dependencias.

**Jerarquía de conflicto (obligatoria):**

1. *Confirmado por auditoría* — `docs/compras/auditoria_facturas_compras_*`
2. *Decisión de arquitectura* — `docs/compras/adrs/*`
3. *Decisión de producto* — [product_requirements.md](product_requirements.md)
4. *Arquitectura / plan previo* — [architecture.md](architecture.md), [implementation_plan.md](implementation_plan.md)

**Documentos hermanos:** [uiux_plan.md](uiux_plan.md), [open_decisions_checklist.md](open_decisions_checklist.md), [definition_of_done_by_phase.md](definition_of_done_by_phase.md), [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md).

---

## Respuestas explícitas (preguntas del tech lead)

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿Orden completo punta a punta? | Fase 0 → 1 → 2 → 3 → 4 → 5 → 6 (tabla §2). Paralelismos en §5. |
| 2 | ¿Cuándo entra UI/UX? | Tras **Fase 0** cerrada; trabajo **UX base** en paralelo con **Fase 1**; **UI alta fidelidad** intensiva desde **Fase 2** (detalle + captura). Ver [uiux_plan.md](uiux_plan.md). |
| 3 | ¿Qué UX antes del backend completo? | Flujos y wireframes de lista/borrador/estados; design system; pantallas contra **API mock** o stub sin posting. |
| 4 | ¿Qué se construye sin posting real? | Fases 1–3 completas (dominio, archivos, OCR mock, workflow, permisos) + **adapter posting = `NoOp` o fake** que solo valida comando. *Arquitectura* ADR-0005. |
| 5 | ¿Qué bloquea el posting? | Contrato `LegacyPostingCommand` estable + **MySQL fixture** mínima + decisiones no bloqueantes de [open_decisions_checklist.md](open_decisions_checklist.md) marcadas para posting; **no** bloquea iniciar **código** del paquete posting con stubs (ver [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md)). |
| 6 | ¿Primer MVP interno usable? | **Post–Fase 1:** CRUD expediente + transiciones + lista; sin OCR real ni legacy. Ver §4. |
| 7 | ¿Primer E2E con usuarios? | Tras **Fase 2** (captura + OCR mock o real) + **Fase 3** mínima (revisión): usuario puede subir, ver borrador y editar; **sin** aprobar hacia legacy o con aprobar que termina en «simulado». |
| 8 | ¿Hitos antes de escritura MySQL legacy? | ADR-0001 + **test gate** (UT-CMD-*, UT-ADP-*, preflight UT-PRE-*) en verde; fixture; feature flag; runbook; DoD Fase 4 en [definition_of_done_by_phase.md](definition_of_done_by_phase.md). |

---

## 1. Congelamiento del contrato `LegacyPostingCommand` v1

**Regla explícita (*decisión nueva de arquitectura*):** al **finalizar la Fase 3** (criterio de salida cumplido), **`LegacyPostingCommand` v1 queda congelado** según [adrs/0006-congelamiento-legacy-posting-command-v1.md](adrs/0006-congelamiento-legacy-posting-command-v1.md).

**A partir de ese cierre:**

- Fase 4 implementa el adapter y el SQL real **contra ese contrato**, sin redefinir el shape del comando en silencio.
- **Cambios posteriores** al comando requieren: **versionado v2** (o equivalente explícito), **actualización de tests** afectados y **aprobación técnica** antes de merge.

**Objetivo:** evitar caos de integración cuando arranque el trabajo de posting legacy.

---

## 2. Mapa de fases (orden total)

| Fase | Nombre | Objetivo | Depende de |
|------|--------|----------|------------|
| **0** | Preparación | Decisiones mínimas, repos, entorno, contratos congelados v1 | — |
| **1** | Dominio interno | Expediente, estados, API, sin legacy | Fase 0 |
| **2** | Captura + OCR | Archivos, cola, OCR (mock→real), PWA shell | Fase 1 |
| **3** | Workflow revisión | Edición, permisos, aprobar/rechazar **sin** MySQL o con stub | Fase 1 (Fase 2 en paralelo posible) |
| **4** | Posting legacy | `LegacyPostingAdapter` real, transacción única ADR-0002 | Contrato + fixture + Fase 3 integración botón aprobar |
| **5** | Hardening | Concurrencia, FM, observabilidad, seguridad archivos | Fase 4 |
| **6** | Rollout | Flag, pre-prod, capacitación | Fase 5 |

---

## 3. Objetivo, entregables, riesgos y criterio de salida por fase

### Fase 0 — Preparación

- **Objetivo:** desbloquear implementación sin ambigüedad de gobierno.
- **Entregables:** checklist [open_decisions_checklist.md](open_decisions_checklist.md) actualizado; rama `feature/compras-captura` o equivalente; CI job vacío o lint; referencia a paths `docs/compras/*`.
- **Riesgos:** parálisis por decisiones OCR/storage → mitigar con **defaults temporales** documentados.
- **Salida:** DoD Fase 0 ([definition_of_done_by_phase.md](definition_of_done_by_phase.md)).

### Fase 1 — Dominio interno

- **Objetivo:** persistencia Synap del expediente y máquina de estados.
- **Entregables:** apps + modelos + migraciones + tests TC-WF base; API REST interna.
- **Riesgos:** modelo mal alineado a `LegacyPostingCommand` → mitigar revisando mapper en PR de Fase 1.
- **Salida:** DoD Fase 1.

### Fase 2 — Captura + OCR

- **Objetivo:** ingesta documento y pipeline asíncrono.
- **Entregables:** storage, tarea cola, adapter OCR mock en CI; PWA mínima carga lista.
- **Riesgos:** tamaño archivo, virus, coste OCR.
- **Salida:** DoD Fase 2.

### Fase 3 — Workflow

- **Objetivo:** analista completa datos y cierra ciclo rechazo/aprobación **lógica**.
- **Entregables:** formularios cabecera/líneas, permisos, historial; integración **stub posting** o flag «simular éxito»; **cierre con contrato v1 congelado** (ADR-0006).
- **Riesgos:** scope UI infinito → acotar MVP en [uiux_plan.md](uiux_plan.md).
- **Salida:** DoD Fase 3.

### Fase 4 — Posting legacy

- **Objetivo:** escritura MySQL según auditoría; **no** iniciar sin DoD previos ni sin **test gate** ([definition_of_done_by_phase.md](definition_of_done_by_phase.md) §Fase 4).
- **Entregables:** adapter por módulos P0–P10 [posting_sql_spec.md](posting_sql_spec.md); integración aprobar real.
- **Riesgos:** divergencia numérica, DDL cliente, triggers ocultos (*pendiente*).
- **Salida:** DoD Fase 4.

### Fase 5 — Hardening

- **Objetivo:** producción-ready no funcional.
- **Entregables:** métricas, rate limits, concurrencia codmov, runbook.
- **Salida:** DoD Fase 5.

### Fase 6 — Rollout

- **Objetivo:** adopción controlada.
- **Entregables:** flag por empresa, documentación usuario, feedback; **primer deploy seguro** (ver §7) antes de habilitar posting real en producción.
- **Salida:** DoD Fase 6.

---

## 4. Primer corte ejecutable (MVP interno)

**Inmediatamente después de Fase 1:** aplicación donde un usuario autenticado crea un expediente, agrega líneas «placeholder», cambia estados hasta `en_revision` / `rechazado`, **sin** archivo, **sin** OCR, **sin** MySQL legacy.

**Detalle técnico:** [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md).

---

## 5. Paralelismo permitido y prohibido

| Paralelo permitido | Prohibido |
|--------------------|-----------|
| UX research + wireframes **mientras** Fase 1 backend | Escribir MySQL legacy antes de DoD Fase 4 **y** antes del **test gate** (§6) |
| Fase 2 (captura) y Fase 3 (formularios) con **equipos distintos** si API estable | Alterar el contrato **v1 congelado** (post Fase 3) sin **v2 + tests + aprobación técnica** (ADR-0006) |
| Implementar **stubs** posting + tests según [posting_tests.md](posting_tests.md) durante Fase 1–3 | Mezclar SQL legacy en vistas de expediente (ADR-0005) |

**Fase 3 → Fase 4:** el handoff formal es el **congelamiento v1** (ADR-0006), no solo «acuerdo verbal».

---

## 6. Test gate obligatorio antes de SQL real contra MySQL legacy

**Regla de equipo (*decisión nueva de arquitectura*):** no está permitido ejecutar **SQL real** del adapter contra **MySQL legacy** (ni en rama compartida sin fixture aislada, ni en entornos que escriban datos reales) mientras **no estén en verde** (CI o comando de verificación acordado):

1. Toda la suite **UT-CMD-*** ([posting_tests.md](posting_tests.md) §2).
2. Toda la suite **UT-ADP-*** ([posting_tests.md](posting_tests.md) §4).
3. Los tests **preflight** **UT-PRE-*** ([posting_tests.md](posting_tests.md) §5).

Detalle y orden TDD: [posting_tests.md](posting_tests.md). Esta regla **refuerza** el DoD Fase 4 en [definition_of_done_by_phase.md](definition_of_done_by_phase.md).

**Además** bloquean merge/commit real: fixture mínima ([posting_tests.md](posting_tests.md) §8), feature flag, decisiones B2 del [open_decisions_checklist.md](open_decisions_checklist.md) cuando aplique.

---

## 7. Primer deploy seguro (rollout)

**Objetivo:** bajar el riesgo en el primer despliegue a un entorno usado por usuarios reales (p. ej. producción o pre-prod con operación real).

**Definición mínima:**

1. **Feature flag de posting legacy desactivado** (o `POSTING_BACKEND=noop|fake` equivalente): **ninguna** escritura en tablas AdministraNET desde este módulo.
2. **Flujo habilitado hasta la aprobación lógica** (captura, OCR, revisión, aprobar/rechazar **sin** commit legacy; respuesta acordada tipo stub o mensaje claro).
3. **Validación con usuarios reales** (analistas / operación) sobre ese alcance, con registro de incidencias y criterio de «listo para encender posting» firmado por producto + tech lead.

Posteriormente, en un despliegue separado, se activa el flag de posting real cumpliendo DoD Fase 4–5.

---

## 8. Trazabilidad documental

| Tema | Documento compras |
|------|---------------------|
| Comportamiento legacy | `auditoria_facturas_compras_*`, `posting_sql_spec.md` |
| Contrato posting | `posting_contract.md` |
| Tests | `posting_tests.md`, `test_cases.md`, `test_strategy.md` |
| Cuándo legacy | ADR-0001 |
| Transacción | ADR-0002 |
| UI vs posting | ADR-0005 |
| Congelamiento comando v1 | ADR-0006 |

---

## 9. Próximo paso inmediato para el equipo

Ejecutar [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md) en el siguiente sprint, con DoD tomado de [definition_of_done_by_phase.md](definition_of_done_by_phase.md) §Fase 1.
