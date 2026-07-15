# Informe de archivo SDD

**Change:** `ventas-analitica-precios-historial`  
**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS (autorizado; migración 0033 cerrada)

---

## Resumen ejecutivo

Analítica de `precios_historial` en Synap: servicio de lectura legacy, API JSON drill-down, modal en precios terminados, ranking SSR `/ventas/evolucion-precios/` y runner Reports `evolucion-precios`. Tras copiar la spec al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

**Nota post-verify:** El verify reportó migración `0033_add_evolucion_precios_report.py` como bloqueador inicial; el gap se cerró el **14/07/2026** (re-verify) antes de este archive.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Proposal | — | `sdd/ventas-analitica-precios-historial/proposal` | Solo filesystem (`proposal.md`) |
| Spec | — | `sdd/ventas-analitica-precios-historial/spec` | Solo filesystem (delta en `specs/`) |
| Design | — | `sdd/ventas-analitica-precios-historial/design` | Solo filesystem (`design.md`) |
| Tasks | — | `sdd/ventas-analitica-precios-historial/tasks` | Solo filesystem (`tasks.md`) |
| Verify report | — | `sdd/ventas-analitica-precios-historial/verify-report` | Solo filesystem (`verify-report.md`) |
| Archive report | #1703 | `sdd/ventas-analitica-precios-historial/archive-report` | Persistido en Engram + filesystem |

> Búsqueda Engram (`project: Synap`) no devolvió observaciones previas para este change; trazabilidad primaria en OpenSpec archivado.

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `ventas-analitica-precios-historial` | **Creada** | Spec completa copiada desde delta del change (4 requisitos: REQ-1 API historial, REQ-2 modal, REQ-3 ranking SSR, REQ-4 Reports). No existía main spec previa. |

**Totales:** 4 requisitos añadidos · 0 modificados · 0 eliminados

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-14-ventas-analitica-precios-historial/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (12/12 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/ventas-analitica-precios-historial/spec.md` | ✅ (delta congelado) |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/ventas-analitica-precios-historial/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/ventas-analitica-precios-historial/spec.md` — spec nueva (copia íntegra del delta)

---

## Verificación al archivar

- [x] Main spec creada antes del movimiento
- [x] Carpeta movida a `archive/2026-07-14-ventas-analitica-precios-historial/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 12/12 completadas
- [x] Tests: 5/5 OK (`ventas.tests.test_precios_historial`)
- [x] Migración 0033: gap cerrado post-verify (14/07/2026)

---

## Advertencias heredadas (no bloqueantes)

1. **Sin tests de integración** para API `api_precios_historial_articulo` (permisos, JSON, fechas).
2. **Sin tests** para `ranking_variaciones_precios`, vista `evolucion_precios_view` ni `run_evolucion_precios`.
3. **REQ-2 (modal UI)** y flujo end-to-end solo verificables manualmente.
4. **Checklist manual** (5 ítems) pendiente de ejecución en entorno operativo.
5. **Cumplimiento comportamental:** 0/4 escenarios plenamente compliant · 2 partial · 2 untested.

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado (PASS WITH WARNINGS), gap migración 0033 cerrado y archivado. Listo para el siguiente `/sdd-new` si aplica.
