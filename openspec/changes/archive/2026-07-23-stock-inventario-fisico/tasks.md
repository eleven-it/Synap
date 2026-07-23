# Tasks: Inventario físico / Conteo (Stock)

> Orden: fundación → campaña → APIs/sync → offline móvil → Nivel A → ajuste MSTOCK (solo tras sync completo) → docs.
> TDD: cada RED antes del GREEN correspondiente. Runner: `docker exec Synap_app python manage.py test`.

## Fase 1: Fundación (DDL, permisos, rutas)

- [x] 1.1 RED: `stock/tests/test_inv_fisico_catalog.py` — DDL idempotente vía catalog
- [x] 1.2 GREEN: crear `stock/sql/001_inv_fisico_tables.sql` (`inv_fisico_campana`, `_linea`, `_evento`)
- [x] 1.3 GREEN: `run_stock_inv_fisico_tables_mysql` + registro en `core/services/legacy_mysql_schema/catalog.py`
- [x] 1.4 Registrar permisos `stock.inventario_fisico.{contar,gestionar,autorizar}` y decorador `@tiene_permiso`
- [x] 1.5 Esqueleto rutas en `stock/urls.py`: `/inventario-fisico/`, `/conteo/`, `api/conteo/`

## Fase 2: Campaña (`stock-inventario-fisico-campana`)

- [x] 2.1 RED: `stock/tests/test_inv_fisico_campana.py` — MPR elegibles, snapshot sin freeze, estados, asignación
- [x] 2.2 GREEN: `stock/services/inventario_fisico.py` — campañas, snapshot `stock_deposito.saldo`, líneas, transiciones
- [x] 2.3 GREEN: vistas escritorio en `stock/views.py` + `stock/templates/stock/inventario_fisico/` (listado, crear, monitor; canon reports/MPR)
- [x] 2.4 Test integración: `/stock/inventario/` pivote intacto; menú distingue consulta vs inventario físico

## Fase 3: APIs ciegas y sync (`sync-offline` + contrato contador)

- [x] 3.1 RED: `stock/tests/test_inv_fisico_no_filtracion.py` — prefetch/sync sin `saldo_snapshot`/`diferencia`
- [x] 3.2 RED: `stock/tests/test_inv_fisico_sync.py` — `client_event_id` idempotente, batch `{aceptados,conflictos,rechazados}`, LWW mismo operario, conflicto entre operarios
- [x] 3.3 GREEN: `api_conteo_prefetch` y `api_conteo_sync` en `stock/api_views.py` + serializadores rol contar
- [x] 3.4 GREEN: sync en `inventario_fisico.py` — ledger `inv_fisico_evento`, proyección `inv_fisico_linea`, tipos `administranet_types`

## Fase 4: PWA offline e IndexedDB (`conteo-movil` + `sync-offline`)

- [x] 4.1 GREEN: `theme/static/js/inv_fisico_offline.js` — store `synap_inv_fisico` (catalogo/cola/meta), prefetch, cola offline, sync batch, banner pendientes
- [x] 4.2 GREEN: `stock/mobile_views.py` + `stock/templates/stock/conteo/` (patrón `mpr/mobile/parte_operario.html`; escáner html5-qrcode de `alta_movimiento`)
- [x] 4.3 UI: progreso operario, estados sync/conflicto, modales Synap (sin alert/confirm); fechas dd/MM/yyyy

## Fase 5: Nivel A (whitelist PWA)

- [x] 5.1 RED: `stock/tests/test_inv_fisico_middleware.py` — permite `/stock/conteo/` y `/stock/api/conteo/`; bloquea fuera de whitelist
- [x] 5.2 GREEN: patrones en `core/middleware/mobile_level_a_middleware.py` (`^/stock/conteo/`, `^/stock/api/conteo/`)
- [x] 5.3 GREEN: alta app conteo en `core/pwa_nivel_a.py`; precache shell en `theme/static/sw.js` (mantener `/api/` fuera de cache)

## Fase 6: Analizador y ajuste MSTOCK (`stock-inventario-fisico-ajuste`)

> Depende de Fase 3 sync completo. MUST NOT autorizar con eventos pendientes.

- [x] 6.1 RED: `stock/tests/test_inv_fisico_ajuste.py` — diferencia contado−snapshot, bloqueo sync pendiente, cero MSTOCK sin autorizar
- [x] 6.2 GREEN: analizador + monitor conflictos en `stock/views.py` y templates `inventario_fisico/` (< 2 clics a detalle)
- [x] 6.3 GREEN: `api_campana_autorizar` en `stock/api_views.py` — modal bloqueante si pendientes; transición Autorizado→Aplicado
- [x] 6.4 GREEN: posteo masivo vía `core/services/administranet_stock.py` (`alta_movimiento` Faltante=3/Sobrante=4); anulación Borrador/EnConteo sin MSTOCK

## Fase 7: Documentación y cierre

- [x] 7.1 Documentar módulo en `docs/stock/` — arquitectura, permisos, offline, rollback (POLITICA_DOCUMENTACION)
- [x] 7.2 Verificación manual MVP: scan→qty < 8 s prefetched; 30+ min offline 100% sync o conflictos explícitos
