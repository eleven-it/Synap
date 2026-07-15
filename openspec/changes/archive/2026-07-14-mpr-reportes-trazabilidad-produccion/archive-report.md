# Informe de archivo — mpr-reportes-trazabilidad-produccion

**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (Engram + openspec)  
**Verificación autorizada:** PASS WITH WARNINGS (#1698)  
**Ciclo SDD:** completo (explore → propose → spec → design → tasks → apply → verify → archive)

---

## Resumen ejecutivo

El cambio **mpr-reportes-trazabilidad-produccion** queda archivado. Se promovieron **7 specs nuevas** a `openspec/specs/` (ningún dominio existía previamente en main specs). La carpeta activa se movió a `openspec/changes/archive/2026-07-14-mpr-reportes-trazabilidad-produccion/`.

MVP técnico verificado (56/56 tests, 35/36 tareas MVP). Pendiente post-archive: QA manual 5.6 (administranet96) y fase P1 opcional 6.1–6.4.

---

## Trazabilidad Engram (observation IDs)

| Artefacto | topic_key | Observation ID | Notas |
|-----------|-----------|----------------|-------|
| proposal | `sdd/mpr-reportes-trazabilidad-produccion/proposal` | — | Solo filesystem (`proposal.md`) |
| spec | `sdd/mpr-reportes-trazabilidad-produccion/spec` | — | Solo filesystem (`specs/`) |
| design | `sdd/mpr-reportes-trazabilidad-produccion/design` | — | Solo filesystem (`design.md`) |
| tasks | `sdd/mpr-reportes-trazabilidad-produccion/tasks` | **#1110** | 35/40 completas; 5.6 manual abierta |
| verify-report | `sdd/mpr-reportes-trazabilidad-produccion/verify-report` | **#1698** | PASS WITH WARNINGS autorizado |
| archive-report | `sdd/mpr-reportes-trazabilidad-produccion/archive-report` | *(este guardado)* | Cierre del ciclo |

---

## Specs sincronizadas

| Dominio | Acción | Requisitos | Escenarios |
|---------|--------|------------|------------|
| `mpr-reportes-shell` | **Creada** | 9 (REQ-SHELL-01…09) | 3 |
| `mpr-reporte-resumen-diario` | **Creada** | 5 (REQ-RESUMEN-01…05) | 2 |
| `mpr-reporte-operario` | **Creada** | 6 (REQ-OPER-01…06) | 2 |
| `mpr-reporte-cadena-pipeline` | **Creada** | 6 (REQ-CADENA-01…06) | 2 |
| `mpr-reporte-pendiente-componentes` | **Creada** | 6 (REQ-PEND-01…06) | 2 |
| `mpr-reporte-brecha-pack` | **Creada** | 5 (REQ-BRECHA-01…05) | 2 |
| `mpr-reporte-trazabilidad` | **Creada** | 5 (REQ-TRAZ-01…05) | 2 |

**Estrategia de merge:** No existían specs main previas para estos dominios. Se copió el contenido íntegro de cada delta spec sin pérdida ni fusión destructiva.

**Rutas main actualizadas:**

- `openspec/specs/mpr-reportes-shell/spec.md`
- `openspec/specs/mpr-reporte-resumen-diario/spec.md`
- `openspec/specs/mpr-reporte-operario/spec.md`
- `openspec/specs/mpr-reporte-cadena-pipeline/spec.md`
- `openspec/specs/mpr-reporte-pendiente-componentes/spec.md`
- `openspec/specs/mpr-reporte-brecha-pack/spec.md`
- `openspec/specs/mpr-reporte-trazabilidad/spec.md`

---

## Contenido del archivo

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (35/40 completas) |
| `verify-report.md` | ✅ (PASS WITH WARNINGS) |
| `state.yaml` | ✅ |
| `specs/` (7 dominios) | ✅ |
| `archive-report.md` | ✅ (este archivo) |

**Ubicación:** `openspec/changes/archive/2026-07-14-mpr-reportes-trazabilidad-produccion/`

**Verificación post-movimiento:**

- [x] Main specs actualizadas (7 dominios)
- [x] Carpeta movida a archive con prefijo ISO
- [x] Archive contiene todos los artefactos
- [x] `openspec/changes/mpr-reportes-trazabilidad-produccion/` ya no existe

---

## Verificación al archivar

**Veredicto heredado:** PASS WITH WARNINGS (#1698)

| Métrica | Valor |
|---------|-------|
| Tests solicitados | 56 passed / 0 failed |
| Tests complementarios P0 | 14 passed |
| Escenarios specs | 7 COMPLIANT, 6 UNTESTED, 2 PARTIAL, 0 FAILING |
| Tareas MVP (fases 1–5) | 35/36 |

### Warnings residuales (no bloquean archive)

1. **5.6** — Verificación manual en administranet96 (timeline artículo 1275, presets Alpine, export CSV).
2. **URL legacy `tipo=pendiente`** — No redirige a `grupo=legacy&reporte=pendiente_opt` (desviación opcional vs REQ-SHELL-09).
3. **6 escenarios UI** sin test automatizado (shell presets, histórico OPT, empty states vista, brecha highlight, timeline completo, pipeline completo).
4. **Alpine inline** en `reportes.html` vs `static/mpr/js/reportes_hub.js` del design original.

### Tareas abiertas post-archive

| Tarea | Severidad | Acción recomendada |
|-------|-----------|-------------------|
| 5.6 QA manual administranet96 | WARNING | Ejecutar antes de release producción |
| 6.1–6.4 Reportes P1 | SUGGESTION | Nuevo change SDD si producto prioriza |

---

## Ciclo SDD

El cambio fue planificado, implementado, verificado y archivado. La fuente de verdad de comportamiento queda en `openspec/specs/` para los 7 dominios listados.

**Próximo paso recomendado:** `none` — ciclo cerrado. Para P1 o QA residual, abrir `/sdd-new` con alcance acotado.
