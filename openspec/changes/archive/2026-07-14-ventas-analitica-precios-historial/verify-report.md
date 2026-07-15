# Informe de verificación — ventas-analitica-precios-historial

**Change**: ventas-analitica-precios-historial  
**Versión spec**: N/A  
**Modo**: Standard (sin Strict TDD)  
**Fecha verificación**: 14/07/2026 (re-verify post-migración 0033)  
**Verificador**: sdd-verify

---

## Veredicto

**PASS WITH WARNINGS**

Implementación estructural completa (servicio, API, modal, ranking SSR, runner Reports, migración `ReportDefinition`). Tests unitarios 5/5 OK. Cobertura comportamental limitada: sin tests de integración HTTP/MySQL ni de runner Reports. Checklist manual pendiente (WARNING, no bloqueante).

---

## Completitud de tareas

| Métrica | Valor |
|---------|-------|
| Tareas totales | 12 |
| Tareas completas | 12 |
| Tareas incompletas | 0 |

Todas las fases (0–5) marcadas `[x]` en `tasks.md`.

---

## Ejecución build y tests

**Build / system check**: ✅ Pasó

```bash
docker exec Synap_app python manage.py check
# System check identified no issues (0 silenced).
```

**Tests principales**: ✅ 5 passed / 0 failed / 0 skipped

```bash
docker exec Synap_app python manage.py test ventas.tests.test_precios_historial --keepdb -v 2
# Ran 5 tests in 0.057s — OK
```

| Test | Resultado |
|------|-----------|
| `PreciosHistorialCalculoTests.test_delta_pct` | ✅ ok |
| `PreciosHistorialCalculoTests.test_enriquecer_deltas` | ✅ ok |
| `PreciosHistorialCalculoTests.test_parse_filtros` | ✅ ok |
| `PreciosHistorialCalculoTests.test_resumen_evolucion` | ✅ ok |
| `PreciosHistorialUrlTests.test_urls` | ✅ ok |

**Cobertura**: ➖ No disponible (no configurada en este verify).

---

## Migración ReportDefinition (REQ-4)

**Estado**: ✅ Cerrado — `reports/migrations/0033_add_evolucion_precios_report.py`

La migración crea conceptualmente el `ReportDefinition` con:

| Campo | Valor |
|-------|-------|
| slug | `evolucion-precios` |
| name | Evolución de precios |
| category | operational |
| empresa | `None` (global) |
| is_active | `true` |
| runner | `reports/services/evolucion_precios_runner.py` (dispatch en `query_runner.py`) |
| widget | Tabla «Ranking variación de precios» con columnas alineadas al ranking SSR |

El slug también figura en `reports/services/catalog_service.py` (catálogo operativo).

> **Nota**: La ejecución de la migración en BD depende del entorno (`migrate reports 0033`). Este verify confirma existencia del artefacto y coherencia estática; no se ejecutó `migrate` en este ciclo.

---

## Matriz de cumplimiento spec (validación comportamental)

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| REQ-1 Historial por artículo | GET API con `lista`, fechas → JSON con deltas | `test_precios_historial.py` > `test_enriquecer_deltas`, `test_parse_filtros`, `test_urls` | ⚠️ PARTIAL — lógica de deltas y rutas OK; sin test HTTP/JSON ni consulta MySQL |
| REQ-2 Modal en precios terminados | Botón Historial abre modal con serie temporal | (ninguno) | ❌ UNTESTED — evidencia estática en template + `precios_terminados_historial.mjs` |
| REQ-3 Ranking agregado | GET `/ventas/evolucion-precios/` con filtros → tabla ranking | `test_precios_historial.py` > `test_urls`, `test_resumen_evolucion` | ⚠️ PARTIAL — URL y resumen unitario; sin test de vista ni `ranking_variaciones_precios` |
| REQ-4 Reports | Slug `evolucion-precios` devuelve mismos datos que SSR | (ninguno) | ❌ UNTESTED — migración + runner cableados; sin test de paridad runtime |

**Resumen cumplimiento**: 0/4 escenarios plenamente compliant · 2 partial · 2 untested

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| REQ-1 API historial | ✅ Implementado | `views_precios_historial.api_precios_historial_articulo`, `listar_historial_articulo`, permisos `ver`/`editar` |
| REQ-2 Modal drill-down | ✅ Implementado | Botón en `precios_terminados_tabla.html`, mixin `precios_terminados_historial.mjs`, `puedeVerHistorial` |
| REQ-3 Ranking SSR | ✅ Implementado | `evolucion_precios_view`, `evolucion_precios.html`, `ranking_variaciones_precios`, menú y permiso |
| REQ-4 Reports | ✅ Implementado | `evolucion_precios_runner.py`, dispatch en `query_runner.py`, migración `0033_add_evolucion_precios_report.py` |
| Cálculo deltas Python | ✅ Implementado | `_enriquecer_filas_con_deltas`, sin `LAG` SQL (coherente con design) |
| Permisos | ✅ Implementado | `ventas.precios_historial.ver` en `constantes_permisos.py`, menú y decoradores |
| Docs | ✅ Presente | `docs/ventas/ANALITICA_PRECIOS_HISTORIAL.md` |

---

## Coherencia (design)

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Arquitectura servicio → API / SSR / runner | ✅ Sí | Flujo según diagrama en `design.md` |
| Deltas en Python (sin LAG) | ✅ Sí | Confirmado en servicio y tests |
| Permisos `ver` + `editar` para historial | ✅ Sí | `_puede_ver_historial` en vistas |
| Ranking primer vs último snapshot | ✅ Sí | `ranking_variaciones_precios` |
| Migración ReportDefinition | ✅ Sí | `0033_add_evolucion_precios_report.py` — **bloqueador anterior cerrado** |

---

## Checklist manual

| Ítem | Automatizable | Estado | Clasificación |
|------|---------------|--------|---------------|
| Asignar `ventas.precios_historial.ver` a un puesto de consulta | No | Pendiente | ⚠️ WARNING |
| `/ventas/evolucion-precios/` — ranking con filtros fecha/lista/marca/rubro | No | Pendiente | ⚠️ WARNING |
| `/ventas/precios-terminados/` — botón historial abre modal con serie | No | Pendiente | ⚠️ WARNING |
| Reports slug `evolucion-precios` — mismas columnas que ranking SSR | No | Pendiente | ⚠️ WARNING |
| Guardar precio en terminados genera fila en `precios_historial` visible en modal | No | Pendiente | ⚠️ WARNING |

---

## Issues encontrados

### CRITICAL (corregir antes de archive)

Ninguno. *(Migración ReportDefinition ausente — **CERRADO** en re-verify 14/07/2026.)*

### WARNING (recomendado)

1. Sin tests de integración para API `api_precios_historial_articulo` (permisos, JSON, fechas).
2. Sin tests para `ranking_variaciones_precios` ni vista `evolucion_precios_view`.
3. Sin tests para `run_evolucion_precios` (paridad columnas SSR vs Reports).
4. REQ-2 (modal UI) y flujo end-to-end solo verificables manualmente.
5. Checklist manual completo sin ejecutar en este verify.

### SUGGESTION

1. Añadir tests con mock de `mysql_cursor` para historial y ranking sin depender de BD legacy.
2. Test de paridad de columnas entre `evolucion_precios.html` y payload del runner.

---

## Próximo paso recomendado

**sdd-archive** — sin bloqueadores CRITICAL; warnings de cobertura y checklist manual no impiden archivo.
