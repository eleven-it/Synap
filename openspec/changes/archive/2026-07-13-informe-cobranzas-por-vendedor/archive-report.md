# Informe de archivo — informe-cobranzas-por-vendedor

**Fecha de archivo:** 13/07/2026  
**Modo artefactos:** híbrido (Engram + OpenSpec en repo).

## Engram — observaciones recuperadas

No existen en el store entradas con tópicos exactos `sdd/informe-cobranzas-por-vendedor/{proposal|spec|design|tasks|verify-report}`. Trazabilidad relacionada:

| Rol | ID | Notas |
|-----|-----|--------|
| Progreso / cierre implementación | **962** | `mem_get_observation(962)` — migración PHP→Synap, servicio, relays, slug, migración 0034, tests 14/14 OK |

Artefactos formales (proposal, spec delta, design, tasks, verify-report) permanecen en esta carpeta archivada bajo `openspec/changes/archive/2026-07-13-informe-cobranzas-por-vendedor/`.

## Verificación previa al archivo

- `verify-report.md`: ✅ Implementado y verificado; 14/14 tests OK; sin incidencias críticas.
- REQ-COB-001 a REQ-COB-007 cubiertos según tabla de cobertura en verify-report.
- Pendiente operativo (no bloqueante): validación E2E con login real y paridad de sumas contra PHP legacy.

## Especificación principal

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `reports-cobranzas-vendedor` | **Creada** | 7 requisitos añadidos (REQ-COB-001 … REQ-COB-007), 11 escenarios Gherkin |

**Ruta fuente de verdad:** `openspec/specs/reports-cobranzas-vendedor/spec.md`

## Contenido archivado

- `proposal.md` ✅
- `specs/reports-cobranzas-vendedor/spec.md` ✅ (delta)
- `design.md` ✅
- `tasks.md` ✅ (7/7 fases completadas)
- `verify-report.md` ✅

## Estado

Cambio archivado; ciclo SDD cerrado para `informe-cobranzas-por-vendedor`.
