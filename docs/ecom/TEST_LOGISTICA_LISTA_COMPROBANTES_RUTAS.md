# Plan de pruebas — Lista de comprobantes en rutas (informe legacy Reports)

**Spec:** `docs/ecom/SPEC_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`  
**Fecha:** 2026-04-09.  
**Actualización:** 2026-04-09 — tests bajo módulo `reports`, API `query` y permisos operativos.  
**Criterio:** validar **resultados de negocio** y permisos, no paridad 1:1 de JSON o HTML con PHP.

---

## 1. Ubicación del código de tests (post-implementación)

Archivo propuesto: `reports/tests/test_logistica_lista_comprobantes_rutas.py`.

Ejecución (contenedor):

```bash
docker exec Synap_app python manage.py test reports.tests.test_logistica_lista_comprobantes_rutas
```

---

## 2. Pruebas sin base MySQL (rápidas)

| ID | Nombre | Qué valida |
|----|--------|------------|
| T01 | `test_query_sin_base_empresa_en_filtros` | `POST /api/reports/query/` sin `base_empresa` efectivo (sesión sin clave) → error controlado o vacío según política del runner (documentar igual que otros legacy). |
| T02 | `test_query_sin_permiso_operativo` | Usuario sin `reports.view_operational` → 403. |
| T03 | `test_query_anonimo` | Sin sesión / no autenticado → 403 o no permitido. |
| T04 | `test_autocomplete_clientes_q` | GET autocomplete con permisos y sesión mínima → 200 y `results` lista. |
| T05 | `test_post_entrega_validacion` | POST entrega sin campos requeridos → 400; `No` sin motivo → 400. |

**Implementación:** `APIClient` de DRF con sesión que incluya `session['user']` (`base_empresa`, y si aplica flags supervisor); usuario mockeado con `tiene_permiso` / `get_permisos_totales` que devuelvan `reports.view_operational` (mismo patrón que tests existentes de `reports`).

---

## 3. Pruebas con MySQL (integración, opcional)

Marcar con `@skipUnless` o variable de entorno si no hay BD administraNET en CI.

| ID | Nombre | Qué valida |
|----|--------|------------|
| I01 | `test_query_runner_smoke` | `QueryRunnerService(user).run(report, payload)` con slug `comprobantes-rutas` y filtros de fechas → `QueryResult.data` es lista. |
| I02 | `test_filtro_estado_sin_datos` | Misma idea que spec de paridad. |
| I03 | `test_detalle_remito` | GET detalle con `cod_mov` conocido. |
| I04 | `test_guardar_entrega` | Solo entorno desechable. |

---

## 4. Equivalencia de datos (no réplica byte a byte)

- Con mismos filtros y `base_empresa`, el conjunto de **hechos de negocio** relevantes (p. ej. mismos `CodigoMovimiento` de remito incluidos, mismos totales por línea) debe coincidir o documentarse la divergencia aceptada.
- No es obligatorio comparar nombres de columnas ni formato de strings entre PHP y Synap.

---

## 5. Pruebas manuales UI (checklist)

- [ ] Desde **catálogo de reportes**, abrir el ítem y cargar `/reports/dashboard/comprobantes-rutas/`.  
- [ ] Sesión Synap normal (no sesión mayoristapp ecom): el informe debe funcionar si el usuario tiene permiso operativo.  
- [ ] Autocomplete, filtros, tabla agrupada, modales, export Excel (si está habilitado en template).  
- [ ] Verificar que la conexión MySQL sea la misma empresa que el selector / `base_empresa` de sesión.

---

## 6. Criterio de aceptación Fase 1

- T01–T05 en verde en CI.  
- Al menos una prueba que importe `QueryRunnerService` y el slug nuevo (aunque sea con pool mockeado).  
- Checklist manual §5 ejecutado en entorno con datos reales.
