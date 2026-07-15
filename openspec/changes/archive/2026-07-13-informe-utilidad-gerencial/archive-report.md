# Informe de archivo — informe-utilidad-gerencial

**Fecha de archivo:** 13/07/2026  
**Modo artefactos:** híbrido (Engram + OpenSpec en repo).

## Engram — observaciones recuperadas

No existen en el store entradas con tópicos exactos `sdd/informe-utilidad-gerencial/{proposal|spec|design|tasks|verify-report}` (búsquedas en proyectos `sebastian`, `administranet 2` y query libre `informe-utilidad-gerencial` sin resultados).

Artefactos formales (proposal, spec delta, design, tasks, verify-report) permanecen en esta carpeta archivada bajo `openspec/changes/archive/2026-07-13-informe-utilidad-gerencial/`.

| Rol | ID Engram | Notas |
|-----|-----------|--------|
| proposal | — | Solo filesystem: `proposal.md` |
| spec (delta) | — | Solo filesystem: `specs/reports-utilidad-gerencial/spec.md` |
| design | — | Solo filesystem: `design.md` |
| tasks | — | Solo filesystem: `tasks.md` (7/7 fases completadas) |
| verify-report | — | Solo filesystem: `verify-report.md` (✅ implementado y verificado) |
| archive-report | *(este documento)* | Persistido también en Engram como `sdd/informe-utilidad-gerencial/archive-report` |

## Verificación previa al archivo

- `verify-report.md`: **Implementado y verificado** — 17/17 tests OK (`reports.tests.test_utilidad_gerencial_relay`); migración `0035_add_utilidad_gerencial_report` aplicada; sin incidencias críticas.
- Todas las tareas en `tasks.md` marcadas `[x]`.

## Especificación principal sincronizada

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `reports-utilidad-gerencial` | **Creada** | 8 requisitos añadidos (REQ-UT-001 … REQ-UT-008); spec nueva en `openspec/specs/reports-utilidad-gerencial/spec.md` |

No existía spec principal previa; el delta se copió y normalizó como fuente de verdad (sección `## Requisitos`, metadata archivado, tabla de implementación).

## Contenido del archivo

- `proposal.md` ✅
- `specs/reports-utilidad-gerencial/spec.md` ✅ (delta)
- `design.md` ✅
- `tasks.md` ✅ (7/7 fases completadas)
- `verify-report.md` ✅
- `archive-report.md` ✅

## Fuente de verdad actualizada

- `openspec/specs/reports-utilidad-gerencial/spec.md`

## Estado

Cambio archivado; ciclo SDD cerrado para `informe-utilidad-gerencial`.
