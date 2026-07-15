# Informe de archivo SDD

**Change:** `best-articulos-terminados-fabricados-olas`  
**Fecha de archivo:** 15/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS

---

## Resumen ejecutivo

Migración BEST→MPR: colas UI de stock inicial por olas anti-duplicado, rename «Artículos terminados» (gate PED sin cambio), dominio no bloqueante «Artículos fabricados» con matcher BOM inverso Admin→BEST y stock Semi-Embalado opcional post-cutover. 26/26 tareas completas; 11/11 tests del scope en verde.

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `best-migracion-stock-inicial-colas` | **Creada** | 4 requisitos ADDED, 6 escenarios (colas pendiente/listos/cargados, confirmación solo pendientes, copy Terminados, métricas ola) |
| `best-migracion-articulos-terminados` | **Creada** | 4 requisitos ADDED, 6 escenarios (rename display, matcher Terminado, gate PED sin fabricados, descripción dominio) |
| `best-migracion-articulos-fabricados` | **Creada** | 6 requisitos ADDED, 10 escenarios (dominio no bloqueante, pantalla espejo, BOM Admin, matcher inverso, stock Semi opcional, separación datos) |

**Totales delta:** 14 ADDED · 0 MODIFIED · 0 REMOVED (specs nuevas, sin main previa)

---

## Notas de merge

- No existían specs previas en `openspec/specs/` para las 3 capabilities BEST migración.
- **Copia directa** del delta con formato main spec (sección `Requirements`, nota de archivo en `Purpose`).
- Sin merge destructivo.

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-15-best-articulos-terminados-fabricados-olas/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (26/26 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ archived |
| `specs/best-migracion-stock-inicial-colas/spec.md` | ✅ (delta congelado) |
| `specs/best-migracion-articulos-terminados/spec.md` | ✅ |
| `specs/best-migracion-articulos-fabricados/spec.md` | ✅ |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/best-articulos-terminados-fabricados-olas/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/best-migracion-stock-inicial-colas/spec.md`
- `openspec/specs/best-migracion-articulos-terminados/spec.md`
- `openspec/specs/best-migracion-articulos-fabricados/spec.md`

---

## Trazabilidad Engram

| Artefacto | topic_key | Observation ID |
|-----------|-----------|----------------|
| proposal | `sdd/best-articulos-terminados-fabricados-olas/proposal` | — (no persistido en Engram; fuente: filesystem) |
| spec | `sdd/best-articulos-terminados-fabricados-olas/spec` | — |
| design | `sdd/best-articulos-terminados-fabricados-olas/design` | — |
| tasks | `sdd/best-articulos-terminados-fabricados-olas/tasks` | — |
| verify-report | `sdd/best-articulos-terminados-fabricados-olas/verify-report` | — |
| archive-report | `sdd/best-articulos-terminados-fabricados-olas/archive-report` | **1808** |

> Artefactos de fases previas no encontrados en Engram (`mem_search` sin resultados). Trazabilidad completa vía filesystem archivado + este informe.

---

## Verificación al archivar

- [x] Main specs creadas antes del movimiento
- [x] Carpeta movida a archive con prefijo `2026-07-15`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 26/26 completadas
- [x] Tests scope change: 11/11 OK
- [x] Build check: passed (`manage.py check`)

---

## Advertencias heredadas (no bloqueantes)

1. **5 escenarios UI/copy** sin test de comportamiento (hub tarjeta fabricados, banner cutover, Asignar Terminado/Fabricado, texto ayuda).
2. **3 escenarios PARTIAL** (filtro cola vista, métricas post-confirm UI, REP_RECETAS sin test explícito).
3. **Suite completa `mpr.best_migration`:** 1 fallo preexistente en `test_reset_staging.ReiniciarStagingBestTests.test_reiniciar_borra_todas_las_tablas`.
4. Warning Django global: modelos con cambios sin migración reflejada (no específico del change).

---

## Ciclo SDD

**Completo.** Planificado, implementado, verificado (PASS WITH WARNINGS) y archivado. Listo para siguiente change.
