# Documentación — módulo Compras (factura de compra, captura PWA, posting legacy)

**Convención de equipo:** toda documentación nueva de la **app Compras** (facturas de compra, captura, OCR, workflow, posting AdministraNET) debe guardarse en **`docs/compras/`** (esta carpeta).

### Implementación (Fase 1–2)

- Código: apps Django `factura_compra_captura` (expediente, documentos, OCR, API `/api/compras/`, captura móvil `/compras/captura/movil/`) y `factura_compra_posting` (contrato + stub).
- **Fase 2 (captura + OCR):** resumen técnico, endpoints y decisiones en [desarrollo/fase_2_result.md](desarrollo/fase_2_result.md).
- Divergencias respecto al modelo de dominio documentadas en [DOMAIN_MODEL_FASE1_DIVERGENCIAS.md](DOMAIN_MODEL_FASE1_DIVERGENCIAS.md).
- Variable de entorno opcional: `FACTURA_COMPRA_POSTING_BACKEND` (`fake` por defecto, `noop` para desactivar simulación de posting).

### Plan de ejecución y gobernanza (tech lead)

Documentos que ordenan fases, UI/UX, DoD y el primer sprint ejecutable:

| Documento | Contenido |
|-----------|-----------|
| [master_execution_plan.md](master_execution_plan.md) | Fases, dependencias, paralelismos, respuestas a las 8 preguntas de gobierno |
| [uiux_plan.md](uiux_plan.md) | Cuándo entra UX, wireframes MVP, sincronización con dominio sin posting real |
| [open_decisions_checklist.md](open_decisions_checklist.md) | Decisiones abiertas, impacto, bloqueos B0–B3 |
| [definition_of_done_by_phase.md](definition_of_done_by_phase.md) | DoD Fase 0–6 |
| [phase_1_bootstrap_plan.md](phase_1_bootstrap_plan.md) | Primer sprint: apps Django, modelos, API, tests sin MySQL legacy |
| [desarrollo/fase_2_result.md](desarrollo/fase_2_result.md) | Entrega Fase 2: flujo captura, OCR, endpoints, runbook |
| [desarrollo/fase_3_result.md](desarrollo/fase_3_result.md) | Fase 3: revisión, aprobación stub, permisos, comando v1 congelado |
| [desarrollo/fase_4_result.md](desarrollo/fase_4_result.md) | Fase 4: test gate posting, adapter grabación, flag SQL |
| [desarrollo/fase_5_result.md](desarrollo/fase_5_result.md) | Fase 5: hardening, logs, rate limit, runbooks |
| [desarrollo/fase_6_result.md](desarrollo/fase_6_result.md) | Fase 6: rollout, flags, plantilla métricas |
| [desarrollo/fase_validacion_dup_fiscal_result.md](desarrollo/fase_validacion_dup_fiscal_result.md) | PASO 4: duplicados Synap + fiscal CAE antes de preflight |

**TDD validación duplicados / fiscal:** tests `tests/compras/test_validation_phase3_5.py`; diseño [change_design.md](change_design.md). Ejecutar `python manage.py test tests.compras.test_validation_phase3_5`.

---

## Índice

### Auditoría VB6 (fuente de verdad del guardado legacy)

| Documento | Contenido |
|-----------|-----------|
| [auditoria_facturas_compras_resumen.md](auditoria_facturas_compras_resumen.md) | Resumen ejecutivo |
| [auditoria_facturas_compras_flujo_completo.md](auditoria_facturas_compras_flujo_completo.md) | Flujo extremo a extremo |
| [auditoria_facturas_compras_objetos_vb6.md](auditoria_facturas_compras_objetos_vb6.md) | Objetos VB6 |
| [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md) | Tablas, campos, Anexo A `stock` |
| [auditoria_facturas_compras_sql.md](auditoria_facturas_compras_sql.md) | SQL detectado |
| [auditoria_facturas_compras_reglas_negocio.md](auditoria_facturas_compras_reglas_negocio.md) | Reglas y validaciones |
| [auditoria_facturas_compras_integracion_django.md](auditoria_facturas_compras_integracion_django.md) | Pautas replicación Django |
| [auditoria_facturas_compras_pendientes_dudas.md](auditoria_facturas_compras_pendientes_dudas.md) | Dudas y riesgos |
| [especificacion_tecnica_replicacion_factura_compra.json](especificacion_tecnica_replicacion_factura_compra.json) | Especificación máquina-legible |
| [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md) | Origen Manual / Remito / OC / Vale |

### Producto y arquitectura (captura + aprobación + posting)

| Documento | Contenido |
|-----------|-----------|
| [product_requirements.md](product_requirements.md) | PRD |
| [domain_model.md](domain_model.md) | Dominio Synap vs legacy |
| [architecture.md](architecture.md) | Arquitectura propuesta |
| [legacy_integration_spec.md](legacy_integration_spec.md) | Boundary MySQL |
| [implementation_plan.md](implementation_plan.md) | Plan por fases |
| [test_strategy.md](test_strategy.md) | Estrategia TDD |
| [test_cases.md](test_cases.md) | Casos de prueba |

### Contrato ejecutable de posting

| Documento | Contenido |
|-----------|-----------|
| [posting_contract.md](posting_contract.md) | `LegacyPostingCommand`, transacción, idempotencia, errores |
| [posting_sql_spec.md](posting_sql_spec.md) | SQL por módulo P0–P10 |
| [posting_tests.md](posting_tests.md) | Tests unitarios previos a la lógica real |

### ADRs (decisiones)

| ADR | Tema |
|-----|------|
| [adrs/0001-momento-escritura-mysql-legacy.md](adrs/0001-momento-escritura-mysql-legacy.md) | Cuándo escribir en legacy |
| [adrs/0002-transaccion-atomica-vs-dos-fases-vb6.md](adrs/0002-transaccion-atomica-vs-dos-fases-vb6.md) | Transacción única vs VB6 |
| [adrs/0003-modelado-buffers-temporales-legacy.md](adrs/0003-modelado-buffers-temporales-legacy.md) | Buffers temp legacy |
| [adrs/0004-validacion-duplicados-fm.md](adrs/0004-validacion-duplicados-fm.md) | Duplicados FM |
| [adrs/0005-aislamiento-posting-workflow-ui.md](adrs/0005-aislamiento-posting-workflow-ui.md) | Aislamiento posting / UI |
| [adrs/0006-congelamiento-legacy-posting-command-v1.md](adrs/0006-congelamiento-legacy-posting-command-v1.md) | Congelamiento `LegacyPostingCommand` v1 al cierre Fase 3 |

---

## Decisiones abiertas (recordatorio)

- Motor OCR, almacenamiento de archivos, política FM default, concurrencia `codmov`, post-commit contable / centros de costo. Detalle en el PRD y ADRs.

---

## Enlaces desde `docs/general/`

Los documentos de planificación en `docs/general/` que hablan de factura de compra enlazan aquí: [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md) y la auditoría vía este README o el resumen.
