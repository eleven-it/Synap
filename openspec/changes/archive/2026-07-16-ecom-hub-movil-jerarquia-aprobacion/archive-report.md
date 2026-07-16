# Informe de archivo SDD

**Change:** `ecom-hub-movil-jerarquia-aprobacion`  
**Fecha de archivo:** 16/07/2026  
**Modo:** engram (+ filesystem hybrid para visibilidad del equipo)  
**Veredicto de verificación:** PASS WITH WARNINGS

---

## Resumen ejecutivo

Change archivado y cerrado. Hub pedidos mobile-first, jerarquía comercial G→S→V (reemplazo JSON carteras), workflow de aprobación comercial opcional y alcance unificado en hub/objetivos/informe. 35/35 tareas completadas; 118 tests del change OK. Specs sincronizadas a `openspec/specs/` (5 nuevas, 3 actualizadas).

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key |
|-----------|-----------|-----------|
| Proposal | #1838 | `sdd/ecom-hub-movil-jerarquia-aprobacion/proposal` |
| Spec (delta) | #1840 | `sdd/ecom-hub-movil-jerarquia-aprobacion/spec` |
| Design | #1841 | `sdd/ecom-hub-movil-jerarquia-aprobacion/design` |
| Tasks | #1842 | `sdd/ecom-hub-movil-jerarquia-aprobacion/tasks` |
| Apply progress | #1848 | `sdd/ecom-hub-movil-jerarquia-aprobacion/apply-progress` |
| Verify report | #1858 | `sdd/ecom-hub-movil-jerarquia-aprobacion/verify-report` |
| Archive report | (este documento) | `sdd/ecom-hub-movil-jerarquia-aprobacion/archive-report` |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `ecom-jerarquia-comercial` | **Creada** | 4 REQ (JER-01..04) |
| `ecom-aprobacion-pedidos` | **Creada** | 4 REQ (APR-01..04) |
| `ecom-hub-pedidos-mobile` | **Creada** | 3 REQ (MOB-01..03) |
| `ecom-objetivos-alcance-jerarquia` | **Creada** | 2 REQ (OBJ-01..02) |
| `ecom-ajustes-workflow-comercial` | **Creada** | 2 REQ (GLOB-01, AJU-01) |
| `ecom-pedidos-hub-kanban` | **Actualizada** | 1 MODIFIED (HUB-05), 1 ADDED (HUB-06) |
| `ecom-vendedor-operativo` | **Actualizada** | 2 MODIFIED (VOP-02, VOP-03) |
| `ecom-gestion-pedidos-navegacion` | **Actualizada** | 1 MODIFIED (NAV-03), 1 ADDED (NAV-04) |

**Totales delta:** 21 requisitos · 21 escenarios GIVEN/WHEN/THEN · 0 REMOVED

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-16-ecom-hub-movil-jerarquia-aprobacion/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (35/35 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `archive-report.md` | ✅ |
| `state.yaml` | ✅ |
| `specs/` (8 dominios) | ✅ |

No existía carpeta activa `openspec/changes/ecom-hub-movil-jerarquia-aprobacion/` (change engram-only); archivo filesystem creado para visibilidad del equipo.

---

## Source of truth actualizado

- `openspec/specs/ecom-jerarquia-comercial/spec.md`
- `openspec/specs/ecom-aprobacion-pedidos/spec.md`
- `openspec/specs/ecom-hub-pedidos-mobile/spec.md`
- `openspec/specs/ecom-objetivos-alcance-jerarquia/spec.md`
- `openspec/specs/ecom-ajustes-workflow-comercial/spec.md`
- `openspec/specs/ecom-pedidos-hub-kanban/spec.md`
- `openspec/specs/ecom-vendedor-operativo/spec.md`
- `openspec/specs/ecom-gestion-pedidos-navegacion/spec.md`

---

## Verificación al archivar

- [x] Sin issues CRITICAL en verify-report (#1858)
- [x] Tareas 35/35 completadas (#1842)
- [x] Main specs actualizadas (8 dominios)
- [x] Carpeta archivada en `openspec/changes/archive/2026-07-16-ecom-hub-movil-jerarquia-aprobacion/`
- [x] IDs Engram registrados para trazabilidad
- [x] Tests change-specific: 118/118 OK

---

## Advertencias heredadas (no bloqueantes)

1. **REQ-JER-02:** sin test explícito 403 ABM jerarquía sin permiso.
2. **Escenarios mobile UX** (MOB-01, HUB-06, NAV-03): evidencia estática; sin tests browser/visual.
3. **REQ-VOP-03:** selector org sin test dedicado.
4. **Suite ecom completa:** 9 failures + 34 errors preexistentes ajenos al change.
5. **REQ-JER-01 DDL runtime:** PARTIAL — provider verificado estáticamente; sin test integración DDL MySQL.

---

## Ciclo SDD

**Completo.** El change fue planificado (Engram), implementado, verificado (PASS WITH WARNINGS) y archivado. Listo para el siguiente `/sdd-new` si aplica.
