# Informe de verificación

**Change:** stock-inventario-tabla-mpr  
**Versión spec:** delta en `openspec/changes/stock-inventario-tabla-mpr/specs/`  
**Modo:** Standard (strict_tdd no activo)  
**Fecha:** 14/07/2026

---

## Completitud de tareas

| Métrica | Valor |
|---------|-------|
| Tareas totales | 14 |
| Tareas completadas | 14 |
| Tareas incompletas | 0 |

Todas las fases (1–4) están marcadas como completadas en `tasks.md`.

---

## Ejecución de build y tests

**Build / system check:** ✅ Pasó

```
docker exec Synap_app python manage.py check
→ System check identified no issues (0 silenced).
```

**Tests:** ✅ 23 pasaron / ❌ 0 fallaron / ⚠️ 0 omitidos

```
docker exec Synap_app python manage.py test stock.tests.test_inventario_tabla stock.tests.test_urls stock.tests --keepdb -v 2
→ Ran 23 tests in 0.061s — OK
```

Cobertura de tests del change:

| Archivo | Tests |
|---------|-------|
| `stock/tests/test_inventario_tabla.py` | 8 (código compuesto, filtros, query string, presentación) |
| `stock/tests/test_urls.py` | 5 (incl. `stock:inventario` → `/stock/inventario/`) |
| `stock/tests.py` | 1 duplicado URL inventario + otros stock |

**Cobertura:** ➖ No disponible (sin umbral configurado en `openspec/config.yaml`)

---

## Matriz de cumplimiento de escenarios

Criterio: escenario **COMPLIANT** solo si un test que lo cubre **pasó** en la ejecución anterior.

### stock-inventario-tabla

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| REQ-INV-01 | ESC-INV-01 Acceso autorizado | (ninguno integración) | ❌ UNTESTED |
| REQ-INV-07/08 | ESC-INV-02 Ver todos los artículos | `test_inventario_tabla.ParseFiltrosTest.test_incluir_ceros` | ⚠️ PARTIAL |
| REQ-INV-09 | ESC-INV-03 Toggle docenas | `test_inventario_tabla.ParsePresentacionTest.test_docenas` | ⚠️ PARTIAL |
| REQ-INV-04 | ESC-INV-04 Código compuesto | `test_inventario_tabla.CodigoCompuestoTest.test_manual_y_prov` | ✅ COMPLIANT |
| REQ-INV-04 | ESC-INV-05 CodArtProv vacío | `test_inventario_tabla.CodigoCompuestoTest.test_solo_manual` | ✅ COMPLIANT |
| REQ-INV-05/06 | ESC-INV-06 Suma por tipo_mpr | (ninguno) | ❌ UNTESTED |
| REQ-INV-06 | ESC-INV-07 Consolidado | (ninguno) | ❌ UNTESTED |
| REQ-INV-10 | ESC-INV-08 Paginación 150 | `test_inventario_tabla.QueryStringTest.test_paginacion_y_marcas` | ⚠️ PARTIAL |
| REMOVED | ESC-INV-09 Ruta legacy 404 | (ninguno) | ❌ UNTESTED |
| REQ-INV-06 | ESC-INV-10 Scrap excluido | (ninguno) | ❌ UNTESTED |

### stock-inventario-filtros

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| REQ-FIL-02 | ESC-FIL-01 Multi-marca | (ninguno) | ❌ UNTESTED |
| REQ-FIL-02 | ESC-FIL-02 Sin marcas | (ninguno) | ❌ UNTESTED |
| REQ-FIL-03/04 | ESC-FIL-03 Búsqueda fuera de página | (ninguno) | ❌ UNTESTED |
| REQ-FIL-06 | ESC-FIL-04 q en tabla | (ninguno) | ❌ UNTESTED |
| REQ-FIL-03 | ESC-FIL-05 API marcas e incluir_ceros | (ninguno) | ❌ UNTESTED |
| REQ-FIL-01 | ESC-FIL-06 Limpiar filtros | (ninguno) | ❌ UNTESTED |
| REQ-FIL-02 | ESC-FIL-07 Componente tags | (ninguno) | ❌ UNTESTED |
| REQ-FIL-08 | ESC-FIL-08 Paginación preserva marcas | `test_inventario_tabla.QueryStringTest.test_paginacion_y_marcas` | ⚠️ PARTIAL |
| REQ-FIL-05 | ESC-FIL-09 id_articulo inexistente | (ninguno) | ❌ UNTESTED |
| REQ-FIL-03 | ESC-FIL-10 Búsqueda CodArtProv | (ninguno) | ❌ UNTESTED |

**Resumen de cumplimiento:** 2/20 escenarios COMPLIANT · 4/20 PARTIAL · 14/20 UNTESTED

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| REQ-INV-01 Ruta y permiso | ✅ Implementado | `stock/urls.py`, `inventario_view` con `@tiene_permiso("stock.consultas")` |
| REQ-INV-02 Menú | ✅ Implementado | `core/utils/utils.py` → `stock:inventario` |
| REQ-INV-03 Columnas fijas | ✅ Implementado | `ETAPAS_INVENTARIO` + Consolidado en servicio y `_tabla.html` |
| REQ-INV-04 Columna Artículo | ✅ Implementado | `codigo_compuesto_articulo`, plantilla con líneas principal/secundaria |
| REQ-INV-05 Fuente saldos | ✅ Implementado | SQL pivote en `inventario_tabla.py`, filtros `anulado`/`suma_stock` |
| REQ-INV-06 Consolidado | ✅ Implementado | Suma aritmética 4 etapas; Scrap excluido del `IN` |
| REQ-INV-07/08 Universo e incluir ceros | ✅ Implementado | `HAVING consolidado > 0` + toggle en `_filtros.html` |
| REQ-INV-09 Unidades/Docenas | ✅ Implementado | `preparar_filas_inventario_presentacion` + subencabezados docenas |
| REQ-INV-10 Paginación 150 | ✅ Implementado | `PAGE_SIZE = 150`, enlaces en plantilla |
| REQ-INV-11 UI canónica | ✅ Implementado | `base_app.html`, sticky, dark mode, patrón MPR |
| REQ-INV-12 Estados vacíos | ✅ Implementado | Mensajes en `_tabla.html` y banner `sin_config_mpr` |
| REMOVED consulta-ficha | ✅ Implementado | Ruta eliminada de `urls.py`; plantilla no existe |
| REQ-FIL-01–10 Filtros | ✅ Implementado | API, tags, buscador Alpine, `build_inventario_query_string` |

---

## Coherencia con diseño

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Pipeline 4 etapas + Consolidado | ✅ Sí | Orden fijo en servicio y tabla |
| Filtros compactos patrón MPR | ✅ Sí | `_filtros.html` con altura `h-9`, purple accent |
| Tags multi-marca | ⚠️ Desviación menor | Usa `includes/filtro_marcas_tags.html` + `filtro_marcas_tags.mjs` en lugar de `reports/.../filters_stock_existencias.html` + `tags_filter.mjs` (misma UX, componente compartido distinto) |
| JS en `inventario.js` | ⚠️ Desviación | Lógica Alpine embebida en `inventario.html`; no existe `stock/static/stock/js/inventario.js` |
| Eliminar legacy consulta-ficha | ✅ Sí | Sin ruta ni plantilla |
| Paginación servidor 150 | ✅ Sí | `PAGE_SIZE = 150` |
| Presentación docenas MPR | ✅ Sí | Reutiliza `mpr.reportes_presentacion` |

---

## Issues encontrados

### CRITICAL (corregir antes de archivar)

Ninguno de implementación faltante. Los escenarios UNTESTED no tienen evidencia de regresión en runtime, pero representan deuda de calidad significativa.

### WARNING (recomendado corregir)

1. **Cobertura de tests insuficiente:** 14/20 escenarios sin test de integración/vista/API; solo 2 COMPLIANT con evidencia runtime.
2. **Sin test de 404 legacy:** `ESC-INV-09` no verificado automáticamente (`/stock/consulta-ficha/`).
3. **Sin tests de SQL pivote:** consolidado, suma `tipo_mpr`, exclusión Scrap e `incluir_ceros` en consulta real.
4. **Sin tests de API** `GET /stock/api/inventario/articulos/`.
5. **Archivo huérfano** `stock/views 2.py` conserva `consulta_ficha_stock_view` (no enlazado, pero confuso).
6. **Desviación de tarea 3.2:** no se creó `stock/static/stock/js/inventario.js` (JS inline en plantilla).

### SUGGESTION

1. Añadir tests de vista con cliente Django mock de sesión/permisos para ESC-INV-01 y ESC-INV-09.
2. Tests de servicio con cursor mock para ESC-INV-06/07/10 y ESC-FIL-04/05.
3. Eliminar o archivar `stock/views 2.py`.

---

## Veredicto

### PASS WITH WARNINGS

Implementación completa y coherente con spec y diseño; todas las tareas cerradas; 23 tests en verde y `manage.py check` sin issues. La brecha principal es **cobertura de escenarios** (2/20 COMPLIANT): faltan tests de integración para vista, API, paginación real, legacy 404 y lógica SQL pivote.

**Próximo paso recomendado:** ampliar tests (opcional) y luego `sdd-archive`; o archivar con deuda documentada si producto acepta validación manual.
