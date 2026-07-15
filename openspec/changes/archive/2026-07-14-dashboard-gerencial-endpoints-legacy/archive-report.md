# Informe de archivo SDD

**Change:** `dashboard-gerencial-endpoints-legacy`  
**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS

---

## Resumen ejecutivo

Capa API de lectura legacy para Dashboard gerencial (`/api/reports/executive-dashboard/`), orquestador P0, endpoints P1 paginados, UI Command Center (`command-center-gerencial`) y delegación T13 `query_runner` → `ventas_metrics`. Tras sincronizar la spec al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

**Nota post-verify:** El verify inicial (#1690) reportó migración catálogo `0032_add_command_center_gerencial_report` ausente; el gap se cerró el **14/07/2026** (T-UI3, apply-progress #1691) antes de este archive.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Explore | #195 | `sdd/dashboard-gerencial-endpoints-legacy/explore` | Discovery inicial |
| Proposal | #196 | `sdd/dashboard-gerencial-endpoints-legacy/proposal` | También `proposal.md` |
| Spec + design | #197 | `sdd/dashboard-gerencial-endpoints-legacy/spec` | Resumen compacto; delta completo en filesystem |
| Design | — | `sdd/dashboard-gerencial-endpoints-legacy/design` | Solo filesystem (`design.md`) |
| Tasks | — | `sdd/dashboard-gerencial-endpoints-legacy/tasks` | Solo filesystem (`tasks.md`) |
| Verify report | #1690 | `sdd/dashboard-gerencial-endpoints-legacy/verify-report` | PASS WITH WARNINGS |
| Apply (migración 0032) | #1691 | `sdd/dashboard-gerencial-endpoints-legacy/apply-progress` | Cierre gap T-UI3 |
| Archive report | (este documento) | `sdd/dashboard-gerencial-endpoints-legacy/archive-report` | Persistido en Engram |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `reports-executive-dashboard` | **Actualizada** (merge selectivo) | Main spec ya contenía evoluciones posteriores (filtros fecha, inventario PrecioCosto, compras validadas, MPR módulo activo, búsqueda existencias). Del delta del change se aplicaron: CRM deprecado (REQ-ED-ORCH-02), sección CRM, escenario 1 sin stub, alcance con UI Command Center, fuera de alcance y nota evolución post-spec (tesorería, ventas_cobros, T13). **Preservados** requisitos main no regresados. |

**Totales delta del change:** spec completa (REQ-ED-* P0/P1) · merge no destructivo · 0 REMOVED de main

---

## Notas de merge

- La main spec en `openspec/specs/reports-executive-dashboard/spec.md` **ya era más completa** que el delta congelado en la carpeta del change (evolución paralela Command Center).
- **No se sobrescribió** la main con el delta íntegro para evitar regresión (p. ej. REQ-ED-FILT-01, REQ-ED-INV-02 PrecioCosto, REQ-ED-COMP-03 validado, REQ-ED-MFG-02 `ModuleConfig`).
- **Sí se sincronizó** el comportamiento implementado: CRM eliminado del orquestador (T-UI4), UI entregada, áreas tesorería/ventas_cobros documentadas como evolución post-spec.

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-14-dashboard-gerencial-endpoints-legacy/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (16/16 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/reports-executive-dashboard/spec.md` | ✅ (delta congelado) |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/dashboard-gerencial-endpoints-legacy/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/reports-executive-dashboard/spec.md` — merge selectivo post-archive

---

## Verificación al archivar

- [x] Main spec actualizada antes del movimiento (merge selectivo)
- [x] Requisitos main posteriores preservados
- [x] Carpeta movida a `archive/2026-07-14-dashboard-gerencial-endpoints-legacy/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 16/16 completadas
- [x] Tests: 33/33 OK (verify)
- [x] Migración 0032: gap cerrado post-verify (14/07/2026)

---

## Advertencias heredadas (no bloqueantes)

1. **Escenario 5 sin test:** `MprSchemaError` → `disponible=false` no cubierto en runtime.
2. **Escenarios 3–4 parciales:** 403 y 503 sin tests HTTP con `APIClient`.
3. **Desviación diseño:** fallo transitorio ventas no eleva 503 al orquestador (solo degradación por área).
4. **`test_executive_dashboard_api.py`:** opcional en design; no creado.

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado (PASS WITH WARNINGS), gap migración 0032 cerrado y archivado. Listo para el siguiente `/sdd-new` si aplica.
