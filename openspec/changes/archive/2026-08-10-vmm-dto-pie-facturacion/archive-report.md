# Informe de archivo — vmm-dto-pie-facturacion

**Fecha de archivo:** 10/08/2026  
**Modo artefactos:** híbrido (Engram + OpenSpec en repo).

## Engram — observaciones recuperadas

| Rol | ID | topic_key |
|-----|-----|-----------|
| Proposal | **#2785** | `sdd/vmm-dto-pie-facturacion/proposal` |
| Specs (delta) | **#2786** | `sdd/vmm-dto-pie-facturacion/specs` |
| Design | **#2788** | `sdd/vmm-dto-pie-facturacion/design` |
| Tasks | **#2790** | `sdd/vmm-dto-pie-facturacion/tasks` |
| Apply progress | **#2791** | `sdd/vmm-dto-pie-facturacion/apply-progress` |
| Verify | **#2792** | `sdd/vmm-dto-pie-facturacion/verify` |

## Verificación previa al archivo

- **Verdict:** PASS WITH WARNINGS
- **Tasks:** 20/20 completas
- **Tests:** 88/88 verdes (`test_comprobante_descuento_cabecera`, `test_ventas_marcas_mensual`, `test_dabra_consolidado_remitos`)
- **Compliance:** 10/13 escenarios COMPLIANT, 3/13 PARTIAL, 0 FAILING
- **CRITICAL:** ninguno (no bloquea archivo)

### Warnings residuales (no bloqueantes)

1. Test dedicado filtro marca parcial (ADR-4) ausente
2. Escenarios integrados regalías/TC y proyección post-pie parciales
3. Sin validación E2E MySQL real
4. Checkboxes Success Criteria en `proposal.md` sin marcar (inconsistencia documental menor)

## Especificación principal

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `reports-ventas-marcas-mensual` | **Creada** | 6 requisitos (REQ-VMM-PIE-01 … REQ-VMM-PIE-06), 13 escenarios |

**Ruta fuente de verdad:** `openspec/specs/reports-ventas-marcas-mensual/spec.md`

## Contenido archivado

- `proposal.md` ✅
- `specs/reports-ventas-marcas-mensual/spec.md` ✅ (delta)
- `design.md` ✅
- `tasks.md` ✅ (20/20 tareas completadas)
- `verify-report.md` ✅
- `archive-report.md` ✅
- `state.yaml` ✅ (status: archived, phase: archive)

## Estado

Cambio archivado; ciclo SDD cerrado para `vmm-dto-pie-facturacion`.
