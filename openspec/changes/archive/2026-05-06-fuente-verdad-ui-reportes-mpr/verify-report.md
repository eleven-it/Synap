# Verify report: fuente-verdad-ui-reportes-mpr

**Fecha:** 06/05/2026  
**Modo de verificación:** estándar (sin Strict TDD activo en `openspec/config.yaml`).  
**Alcance del cambio:** documentación y normativa OpenSpec únicamente; **sin** modificaciones a código ejecutable de aplicación.

## Resumen ejecutivo

| Resultado | Detalle |
|-----------|---------|
| **Estado global** | **COMPLIANT** para el entregable documental del cambio |
| **Riesgos** | Ninguno introducido por este cambio en runtime |
| **Tests automatizados** | **WARNING**: `reports.tests` reporta 2 fallos en entorno actual; **no atribuibles** a archivos añadidos en este cambio (solo `docs/`, `openspec/`). |

## Completitud de tareas (`tasks.md`)

| Fase | Total | Hechas | Pendientes |
|------|-------|--------|------------|
| Fase 1 | 5 | 5 | 0 |
| Fase 2 | 2 | 2 (cerradas en esta verificación) | 0 |
| Fase 3 | 2 | 0 | 2 (archivo SDD manual) |

**Nota:** 3.1–3.2 dependen de decisión de equipo (`sdd-archive`).

## Matriz de cumplimiento — requisitos del spec

### Requirement: Superficies UI consideradas fuente de verdad

| Criterio | Evidencia | Veredicto |
|-----------|-----------|-----------|
| Reportes `/reports/dashboard/<slug>/` y `DashboardDetailView` documentados | `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` §2.1; `reports/views.py` contiene `DashboardDetailView` (verificación previa en diseño) | **COMPLIANT** |
| Plantillas `dashboard_detail.html` / `executive_summary.html` citadas | Doc §2.1; archivos presentes en repo | **COMPLIANT** |
| MPR wizard y OPT citados | Doc §2.2; `mpr/urls.py` con rutas `wizard`, `opt_*` | **COMPLIANT** |
| `base_mpr.html` como layout | Doc §2.2; archivo `mpr/templates/mpr/base_mpr.html` existe | **COMPLIANT** |

**Escenarios**

| Escenario | Veredicto | Notas |
|-----------|-----------|--------|
| Identificación de canon para informe nuevo | **COMPLIANT** | Norma y rutas en doc + spec; cumplimiento operativo es proceso humano/agente. |
| Identificación de canon para flujo OPT | **COMPLIANT** | Plantillas `wizard.html`, `opt_list.html`, `opt_detail.html` listadas y existentes en repo. |

### Requirement: Exclusión explícita de Ventas (objetivos y presupuestos)

| Criterio | Evidencia | Veredicto |
|-----------|-----------|-----------|
| Rutas y plantillas `ventas/` excluidas como referencia | Doc §3; spec §ADDED segundo requisito | **COMPLIANT** |

**Escenarios**

| Escenario | Veredicto | Notas |
|-----------|-----------|--------|
| Code review | **UNTESTED** (proceso humano) | Norma documentada; no automatizable. |
| Asistente automatizado | **UNTESTED** (proceso de revisión) | Idem. |

### Requirement: Documento general de referencia

| Criterio | Evidencia | Veredicto |
|-----------|-----------|-----------|
| Documento en español en `docs/general/` | `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` | **COMPLIANT** |
| Lista rutas, plantillas, estáticos, exclusiones, notas paleta | Secciones §2–§4 del doc | **COMPLIANT** |

**Escenario: Cambio mayor en dashboard**

| Veredicto | Notas |
|-----------|--------|
| **UNTESTED** | Condicional futuro; el requisito queda como obligación en el spec al fusionar cambios. |

### Requirement: Coherencia con OpenSpec

| Criterio | Evidencia | Veredicto |
|-----------|-----------|-----------|
| Delta spec bajo el cambio | `openspec/changes/.../specs/ui-fuente-verdad-reportes-mpr/spec.md` | **COMPLIANT** |
| Spec fusionado en `openspec/specs/` | No aún (pendiente archivo) | **WARNING** — esperado hasta `sdd-archive` |

**Escenario: Producto rehabilita Ventas**

| Veredicto | Notas |
|-----------|--------|
| **UNTESTED** | Evento futuro. |

## Coherencia con `design.md`

| Decisión | Implementación observada | Veredicto |
|----------|--------------------------|-----------|
| Canon por rutas/plantillas concretas | Doc y tablas en `design.md` alineados | **COMPLIANT** |
| Scripts slug objetivos: shell canónico, no patrón ventas | Reflejado en `design.md` y doc §2.1 nota | **COMPLIANT** |
| Un único doc en `docs/general/` | `FUENTE_VERDAD_UI_REPORTES_MPR.md` | **COMPLIANT** |
| Sin edición de `reports/` / `mpr/` en esta entrega | Diff conceptual: solo docs/openspec | **COMPLIANT** |

## Coherencia `proposal.md` ↔ `spec.md`

| Ítem de alcance (proposal) | Cobertura en spec/doc | Veredicto |
|----------------------------|------------------------|-----------|
| Documentar fuente de verdad en `docs/general/` | Requisito “Documento general” + archivo | **COMPLIANT** |
| Capability `ui-fuente-verdad-reportes-mpr` | Delta spec completo | **COMPLIANT** |
| Enlazar desde política (opcional) | `POLITICA_DOCUMENTACION.md` actualizado | **COMPLIANT** |
| Fuera de alcance: no rediseñar ventas | No hay cambios en `ventas/` | **COMPLIANT** |

## Verificación estática — `FUENTE_VERDAD_UI_REPORTES_MPR.md` y exclusión ventas

- Las únicas menciones a `ventas/templates` están en **§3 Exclusiones** (“No usar como referencia visual”), no como patrón a imitar.  
- **Cumple** el criterio de la tarea 2.2.

## Ejecución de tests (`manage.py test`)

**Comando:** `docker exec Synap_app python manage.py test reports.tests --verbosity=0 --noinput`

**Resultado:** `FAILED (failures=2, skipped=2)` — ejemplos: `test_bo_agregado_vs_renglones_consistencia_con_fechas_yyyymmdd` en `test_bo_report_real_db.py` (aserción de consistencia BO vs datos reales).

**Interpretación:** este cambio **no** modifica `reports/services`, consultas BO ni plantillas de informes. Los fallos se clasifican como **preexistentes o dependientes de datos/entorno**, no como regresión del cambio `fuente-verdad-ui-reportes-mpr`.

**Recomendación:** ejecutar de nuevo en CI o con dataset conocido; **no bloquea** el cierre documental de este cambio.

## Conclusión

- **COMPLIANT** para entrega de gobernanza UI documentada.  
- **WARNING**: spec principal en `openspec/specs/` pendiente de archivo; tests `reports.tests` en rojo en el entorno local verificado.  
- **Siguiente paso recomendado:** Fase 3 en `tasks.md` (`sdd-archive`) cuando el equipo apruebe.
