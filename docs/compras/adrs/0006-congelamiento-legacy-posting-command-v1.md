# ADR-0006 — Congelamiento de `LegacyPostingCommand` v1 al cierre de Fase 3

**Estado:** aceptado  
**Fecha:** 2026-03-24  
**Contexto:** [posting_contract.md](../posting_contract.md), [master_execution_plan.md](../master_execution_plan.md), Fase 3 workflow.

## Contexto

Antes de implementar SQL real contra MySQL AdministraNET (Fase 4), el equipo necesita un **contrato estable** entre dominio Synap, mapper y adapter. Si el shape del comando cambia durante Fase 4 sin gobierno, se multiplican regresiones y divergencias respecto a [posting_sql_spec.md](../posting_sql_spec.md) y a la auditoría VB6.

## Decisión

1. **`LegacyPostingCommand` v1 se considera congelado al cierre exitoso de la Fase 3** (DoD Fase 3 cumplido en [definition_of_done_by_phase.md](../definition_of_done_by_phase.md)), con firma y campos alineados a `posting_contract.md` v1 y reflejados en código (tipos, validaciones, tests golden).
2. **Cualquier cambio posterior al congelamiento** que altere el contrato (campos obligatorios, semántica, códigos de error expuestos al caller) debe tratarse como **v2**:
   - versionado explícito en código y documentación (`LegacyPostingCommandV2` o campo `schema_version` acordado);
   - **actualización obligatoria** de tests (UT-CMD-*, mappers, integración) y de referencias en `posting_contract.md` / apéndice;
   - **aprobación técnica** del tech lead (o comité arquitectura Synap) antes de merge a la rama de integración del módulo.

## Implementación congelada (Synap)

- Tipos y validación ejecutables: `factura_compra_posting/legacy_posting_command_v1.py`.
- Mapper desde expediente: `factura_compra_posting/mapper_v1.py`.
- Documentación de entrega Fase 3: [../desarrollo/fase_3_result.md](../desarrollo/fase_3_result.md).

## Consecuencias

- Fase 4 puede asumir v1 estable; el riesgo de «cambiar el blanco en movimiento» queda acotado.
- Excepciones urgentes (hotfix) siguen el mismo camino: v2 o parche documentado con aprobación técnica, no cambios silenciosos en v1.

## Relación con otros ADRs

- Complementa [0005-aislamiento-posting-workflow-ui.md](0005-aislamiento-posting-workflow-ui.md): el boundary posting no mezcla UI, y el **contrato** que cruza ese boundary queda versionado tras Fase 3.
