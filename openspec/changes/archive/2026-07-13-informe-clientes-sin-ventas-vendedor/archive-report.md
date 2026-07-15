# Informe de archivo SDD

**Change:** `informe-clientes-sin-ventas-vendedor`  
**Fecha de archivo:** 13/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** ✅ APROBADO

---

## Resumen ejecutivo

Migración del informe PHP «Clientes sin ventas por vendedor» a Synap `reports/`: servicio parametrizado, relay operativo/gerencial, ReportDefinition `clientes-sin-ventas-vendedor`, UI canónica y 18 tests OK. Tras sincronizar la spec al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Proposal | — | `sdd/informe-clientes-sin-ventas-vendedor/proposal` | Solo filesystem (OpenSpec) |
| Spec | — | `sdd/informe-clientes-sin-ventas-vendedor/spec` | Solo filesystem (OpenSpec) |
| Design | — | `sdd/informe-clientes-sin-ventas-vendedor/design` | Solo filesystem (OpenSpec) |
| Tasks | — | `sdd/informe-clientes-sin-ventas-vendedor/tasks` | Solo filesystem (OpenSpec) |
| Verify report | — | `sdd/informe-clientes-sin-ventas-vendedor/verify-report` | Solo filesystem (OpenSpec) |
| Contexto migración | #958 | — | Memoria de patrón relay legacy |
| Archive report | (este documento) | `sdd/informe-clientes-sin-ventas-vendedor/archive-report` | Persistido en Engram |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `reports-clientes-sin-ventas` | **Creada** | 7 REQ (CSV-001..007) · 17 escenarios · 0 MODIFIED · 0 REMOVED |

**Totales delta:** 7 requisitos · 17 escenarios · 0 REMOVED

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-13-informe-clientes-sin-ventas-vendedor/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (25/25 completadas) |
| `verify-report.md` | ✅ APROBADO |
| `specs/reports-clientes-sin-ventas/spec.md` | ✅ |
| `archive-report.md` | ✅ |

La carpeta activa `openspec/changes/informe-clientes-sin-ventas-vendedor/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/reports-clientes-sin-ventas/spec.md`

---

## Verificación al archivar

- [x] Main spec creada antes del movimiento
- [x] Carpeta movida a `archive/2026-07-13-informe-clientes-sin-ventas-vendedor/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 25/25 completadas
- [x] Tests: 18/18 OK (`reports.tests.test_clientes_sin_ventas_relay`)

---

## Advertencias heredadas (no bloqueantes)

1. **Paridad numérica fina** contra BD real — validación operativa Fase D pendiente.
2. **Verificación visual E2E** con sesión real (login + permisos) — recomendada antes de release.

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado y archivado. Listo para el siguiente `/sdd-new` si aplica.
