# Verification Report — ventas-precios-terminados-tabla

**Fecha:** 14/07/2026  
**Change:** ventas-precios-terminados-tabla  
**Modo:** Standard (hybrid — OpenSpec + Engram)  
**Veredicto:** **PASS WITH WARNINGS (READY MVP P0)**

---

## Completitud

| Métrica | Valor |
|---------|-------|
| Tasks total | 25 |
| Tasks completadas | 25 |
| Tasks incompletas | 0 |

Todas las fases (0–5) marcadas `[x]` en `tasks.md`.

---

## Build & Tests (ejecución real)

**Build / system check:** ✅ Passed

```
docker exec Synap_app python manage.py check
→ System check identified no issues (0 silenced).
```

**Tests:** ✅ 10 passed / ❌ 0 failed / ⚠️ 0 skipped

```
docker exec Synap_app python manage.py test ventas.tests.test_precios_terminados --keepdb
→ Found 10 test(s). Ran 10 tests in 0.020s — OK
```

**Coverage:** ➖ No disponible (sin umbral configurado en `openspec/config.yaml`)

---

## Matriz de cumplimiento de escenarios

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| R1 | S1 — Cambio de tipo (reset filtros secundarios) | `test_precios_terminados.py > test_build_qs_reset_secundarios`, `test_tipo_art_fab` | ⚠️ PARTIAL |
| R3 | S2 — Recálculo neto → final (IVA 21%, neto 100 → final 121) | `test_precios_terminados.py > test_neto_final_ida_vuelta_iva_21` | ⚠️ PARTIAL |
| R4 | S3 — Guardado con historial (lista 4, util, precios_historial) | (ninguno automatizado) | ❌ UNTESTED |

**Resumen de cumplimiento:** 0/3 escenarios plenamente COMPLIANT · 2/3 PARTIAL · 1/3 UNTESTED

Notas:
- **S1 PARTIAL:** los tests cubren mapeo `tipo_producto` y construcción de query con `reset_secundarios=True`; no hay test E2E de recarga de tabla ni filtro `Discontinuo = 'No'`.
- **S2 PARTIAL:** fórmula neto↔final verificada en servicio; estado dirty de celdas solo en template/JS (sin test automatizado).
- **S3 UNTESTED:** `guardar_lote` e `insertar_precios_historial` implementados en código; sin test de integración MySQL (documentado como validación manual en tasks 3.2).

---

## Correctitud (estática — evidencia estructural)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| R1 — Universo y filtro primario | ✅ Implementado | `tipo_art_fab_desde_param`, parse filtros, catálogos en `precios_terminados.py` |
| R2 — Filtros secundarios multi-tag | ✅ Implementado | Tags, listas 1–5, API buscar código en views/template |
| R3 — Tabla editable neto/final + dirty | ✅ Implementado | Template + JS; fórmulas en `precios_articulo_legacy.py` |
| R4 — Guardado articulo + util + historial | ✅ Implementado | `guardar_lote`, `aplicar_cambios_articulo`, `insertar_precios_historial` |
| R5 — Cambio masivo server-side | ✅ Implementado | `preview_cambio_masivo`, operaciones unitarias testeadas |

---

## Coherencia (diseño)

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Arquitectura views → services → MySQL legacy | ✅ Sí | `views_precios_terminados.py`, `precios_terminados.py`, `precios_articulo_legacy.py` |
| Reset filtros secundarios al cambiar tipo | ✅ Sí | `build_filtros_query_string(..., reset_secundarios=True)` |
| Shell MPR + tags + tabla sticky | ✅ Sí | `precios_terminados_tabla.html`, `mpr/base_mpr.html` |
| Persistencia por artículo modificado | ✅ Sí | UPDATE articulo + INSERT precios_historial |

---

## Issues encontrados

**CRITICAL** (bloquean archive estricto):
- Ninguno para alcance MVP P0 acordado.

**WARNING** (deberían corregirse antes de producción plena):
- Escenario S3 sin test automatizado de guardado e historial en MySQL legacy.
- S1/S2 sin cobertura E2E de UI (dirty, recarga tabla al cambiar tipo).
- Validación manual pendiente: permiso `ventas.precios_terminados.editar` en puesto real y fila en `precios_historial` en BD legacy.

**SUGGESTION**:
- Añadir test de integración mock/fixture para `guardar_lote` + `insertar_precios_historial`.
- Relay Tiendanube: fuera de alcance MVP (sin acción).

---

## Veredicto

**PASS WITH WARNINGS (READY MVP P0)**

Implementación completa según tasks; 10/10 tests verdes en contenedor; diseño coherente. Los warnings son gaps de prueba comportamental (S3) y validación manual en BD legacy, acordes con el alcance MVP documentado.

**Próximo paso recomendado:** `sdd-archive` (MVP) tras validación manual opcional en empresa real.
