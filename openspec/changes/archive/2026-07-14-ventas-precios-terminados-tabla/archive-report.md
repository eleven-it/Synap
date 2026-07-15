# Informe de archivo SDD

**Change:** `ventas-precios-terminados-tabla`  
**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS (READY MVP P0) — autorizado para archive

---

## Resumen ejecutivo

Migración a Synap de la tabla operativa de precios terminados (`/ventas/precios-terminados/`): filtros primario/secundario, edición inline neto/final por listas 1–5, guardado en lote, cambio masivo server-side y persistencia en `articulo` + `precios_historial`. Tras copiar la spec al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Proposal | — | `sdd/ventas-precios-terminados-tabla/proposal` | No persistido en Engram; fuente: `proposal.md` archivado |
| Spec | — | `sdd/ventas-precios-terminados-tabla/spec` | No persistido en Engram; delta en filesystem |
| Design | — | `sdd/ventas-precios-terminados-tabla/design` | No persistido en Engram; fuente: `design.md` archivado |
| Tasks | — | `sdd/ventas-precios-terminados-tabla/tasks` | No persistido en Engram; fuente: `tasks.md` archivado |
| Verify report | — | `sdd/ventas-precios-terminados-tabla/verify-report` | No persistido en Engram; fuente: `verify-report.md` archivado |
| Archive report | (este documento) | `sdd/ventas-precios-terminados-tabla/archive-report` | Persistido en Engram + filesystem |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `ventas-precios-terminados-tabla` | **Creada** | No existía main spec. Se copió la delta completa (5 requisitos R1–R5, 3 escenarios S1–S3) a `openspec/specs/ventas-precios-terminados-tabla/spec.md`. |

**Totales:** 5 requisitos añadidos · 0 modificados · 0 eliminados · merge no destructivo (spec nueva)

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-14-ventas-precios-terminados-tabla/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (25/25 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/ventas-precios-terminados-tabla/spec.md` | ✅ (delta congelado) |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/ventas-precios-terminados-tabla/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/ventas-precios-terminados-tabla/spec.md` — spec completa (nueva)

---

## Verificación al archivar

- [x] Main spec creada antes del movimiento
- [x] Carpeta movida a `archive/2026-07-14-ventas-precios-terminados-tabla/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 25/25 completadas
- [x] Tests: 10/10 OK en contenedor (`ventas.tests.test_precios_terminados`)
- [x] Veredicto PASS WITH WARNINGS autorizado para MVP P0

---

## Advertencias heredadas (no bloqueantes)

1. **S3 UNTESTED:** `guardar_lote` e `insertar_precios_historial` sin test de integración MySQL legacy.
2. **S1/S2 PARTIAL:** cobertura de servicio; sin E2E de UI (dirty, recarga al cambiar tipo).
3. **Validación manual pendiente:** permiso `ventas.precios_terminados.editar` en puesto real y fila en `precios_historial` en BD legacy.
4. **Relay Tiendanube:** fuera de alcance MVP (sin acción).

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado (PASS WITH WARNINGS), y archivado. Listo para el siguiente `/sdd-new` si aplica.
