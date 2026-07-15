# Informe de archivo SDD

**Change:** `adminnet-module-migration-command-center-finance`  
**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS

---

## Resumen ejecutivo

Extensión financiera del Command Center gerencial: tesorería en caja (P0), ventas por medio de cobro (P0), banco `librobanco` (P1), detalle cobros paginado (P1) y movimientos caja paginado (P1). Clasificación compartida `caja_classification.py`. Orquestador con 7 áreas operativas; `areas.tesoreria.banco` anidado sin sumar con caja.

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `reports-executive-dashboard` | **Actualizada** (merge no destructivo) | REQ-ED-ORCH-02/03/04 ampliados: `areas.tesoreria`, `areas.ventas_cobros`, `areas.tesoreria.banco`, endpoints P1, sin `impuestos`. Secciones tesorería/ventas-cobros con referencia a specs hijas. Escenario 1: 7 áreas. Evolución post-spec actualizada. |
| `reports-executive-dashboard-tesoreria` | **Creada** | Spec completa REQ-ED-TES P0/P1 (caja, banco, movimientos). |
| `reports-executive-dashboard-ventas-cobros` | **Creada** | Spec completa REQ-ED-COB P0/P1 (resumen + detalle). |

**Totales delta:** 4 ADDED + 1 MODIFIED en orquestador · 2 specs dominio nuevas · 0 REMOVED de main

---

## Notas de merge

- Main `reports-executive-dashboard` **preservó** requisitos previos del archive `dashboard-gerencial-endpoints-legacy` (filtros, inventario PrecioCosto, compras validadas, MPR `ModuleConfig`, búsqueda existencias).
- **No se sobrescribió** la main con el delta íntegro del change.
- Specs tesorería y ventas-cobros son **copia directa** del delta (spec completa, no delta parcial).

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-14-adminnet-module-migration-command-center-finance/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `exploration-tesoreria-administranet.md` | ✅ |
| `exploration-cobros-facturas-venta.md` | ✅ |
| `tasks.md` | ✅ (24/24 completadas, incl. P1.1–P1.3) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ archived |
| `specs/reports-executive-dashboard/spec.md` | ✅ (delta congelado) |
| `specs/reports-executive-dashboard-tesoreria/spec.md` | ✅ |
| `specs/reports-executive-dashboard-ventas-cobros/spec.md` | ✅ |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/adminnet-module-migration-command-center-finance/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/reports-executive-dashboard/spec.md`
- `openspec/specs/reports-executive-dashboard-tesoreria/spec.md`
- `openspec/specs/reports-executive-dashboard-ventas-cobros/spec.md`

---

## Verificación al archivar

- [x] Main specs actualizadas antes del movimiento
- [x] Requisitos main previos preservados
- [x] Carpeta movida a archive
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 24/24 completadas (P1.1–P1.3 incluidas)
- [x] Tests P1: 35/35 OK (14/07/2026)
- [x] UAT P0 waterfall documentado (19/05/2026)

---

## Advertencias heredadas (no bloqueantes)

1. **P1 sin UAT manual** contra informes legacy (banco, detalle cobros, movimientos).
2. **403/503 HTTP** en endpoints aislados: cobertura parcial.
3. **Timeout tesorería** en tests de degradación: simulado, esperado.

---

## Ciclo SDD

**Completo.** Planificado, implementado (P0+P1), verificado y archivado. Listo para siguiente change.
