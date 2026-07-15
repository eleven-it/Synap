# Informe de archivo SDD

**Change:** `stock-inventario-tabla-mpr`  
**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS (autorizado)

---

## Resumen ejecutivo

Consulta operativa de inventario MPR en Stock (`/stock/inventario/`): tabla pivote por etapa física (`tipo_mpr`), columna Consolidado, filtros multi-marca con tags, buscador predictivo, toggle Unidades/Docenas y eliminación del stub legacy `/stock/consulta-ficha/`. Tras sincronizar dos specs nuevas al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Proposal | — | `sdd/stock-inventario-tabla-mpr/proposal` | Solo filesystem (`proposal.md`) |
| Spec | — | `sdd/stock-inventario-tabla-mpr/spec` | Solo filesystem (deltas en `specs/`) |
| Design | — | `sdd/stock-inventario-tabla-mpr/design` | Solo filesystem (`design.md`) |
| Tasks | — | `sdd/stock-inventario-tabla-mpr/tasks` | Solo filesystem (`tasks.md`) |
| Verify report | #1695 | `sdd/stock-inventario-tabla-mpr/verify-report` | PASS WITH WARNINGS |
| Archive report | (este documento) | `sdd/stock-inventario-tabla-mpr/archive-report` | Persistido en Engram |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `stock-inventario-tabla` | **Creada** | 12 requisitos (REQ-INV-01–12), 1 REMOVED (consulta-ficha), 10 escenarios |
| `stock-inventario-filtros` | **Creada** | 10 requisitos (REQ-FIL-01–10), 10 escenarios |

**Totales:** 2 capabilities nuevas · 0 MODIFIED · 0 merge destructivo · main specs no existían previamente

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-14-stock-inventario-tabla-mpr/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (14/14 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/stock-inventario-tabla/spec.md` | ✅ (delta congelado) |
| `specs/stock-inventario-filtros/spec.md` | ✅ (delta congelado) |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/stock-inventario-tabla-mpr/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/stock-inventario-tabla/spec.md` — spec principal (nueva)
- `openspec/specs/stock-inventario-filtros/spec.md` — spec principal (nueva)

---

## Verificación al archivar

- [x] Main specs creadas desde deltas antes del movimiento
- [x] Carpeta movida a `archive/2026-07-14-stock-inventario-tabla-mpr/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 14/14 completadas
- [x] Tests: 23/23 OK (`manage.py check` sin issues)
- [x] PASS WITH WARNINGS autorizado por producto/orquestador

---

## Advertencias heredadas (no bloqueantes)

1. **Cobertura de tests insuficiente:** 14/20 escenarios UNTESTED; solo 2 COMPLIANT con evidencia runtime.
2. **Sin test de 404 legacy:** `ESC-INV-09` (`/stock/consulta-ficha/`) no verificado automáticamente.
3. **Sin tests de SQL pivote:** consolidado, suma `tipo_mpr`, exclusión Scrap e `incluir_ceros` en consulta real.
4. **Sin tests de API** `GET /stock/api/inventario/articulos/`.
5. **Archivo huérfano** `stock/views 2.py` conserva `consulta_ficha_stock_view` (no enlazado).
6. **Desviación de tarea 3.2:** JS inline en plantilla en lugar de `stock/static/stock/js/inventario.js`.
7. **Desviación menor tags:** componente `filtro_marcas_tags` vs `reports/.../tags_filter.mjs` (misma UX).

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado (PASS WITH WARNINGS), specs sincronizadas y archivado. Listo para el siguiente `/sdd-new` si aplica.
