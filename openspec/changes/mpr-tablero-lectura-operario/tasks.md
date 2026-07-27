# Tasks: Tablero de producción — lectura para operarios

**Change:** `mpr-tablero-lectura-operario` · **Decisions:** sin «Mi parte» en menú MPR (landing `/mpr/mi-parte/`); solo `tablero_ver` oculta E5, Enviar y chrome CC/Parte/KPI.

## Phase 1: Tests (RED)

- [x] 1.1 Crear `mpr/tests/test_tablero_lectura_operario.py` con factory/usuario mock (`parte_operario` + `tablero_ver`, sin `mpr.ver`).
- [x] 1.2 Test helpers: `_usuario_puede_ver_tablero_produccion` OR; `_usuario_puede_enviar_desde_tablero` solo con `mpr.ver`.
- [x] 1.3 Test GET `/mpr/tablero-produccion/` → 200 (tablero_ver); sin permiso → 403; POST `/mpr/tablero-produccion/actualizar/` → 200.
- [x] 1.4 Test POST `/mpr/tablero-produccion/enviar/` → 403; GET CC/clasificación y reportes MPR → 403 con solo `tablero_ver`.
- [x] 1.5 Test `landing_url_para_usuario` → `/mpr/mi-parte/` para operario+tablero (sin cambio en `mpr/landing.py`).
- [x] 1.6 Test menú: `apps_visibles_sin_filtro_pwa` muestra MPR con solo «Tablero de producción»; NO «Mi parte» ni CC/reportes.
- [x] 1.7 Regresión: usuario con `mpr.ver` — tablero GET/POST enviar 200, menú MPR completo.

## Phase 2: Foundation (permiso y mixins)

- [x] 2.1 Añadir `mpr.tablero_ver` («Ver tablero de producción (solo lectura)») en `core/constantes_permisos.py` → siembra vía sync catálogo.
- [x] 2.2 En `mpr/views.py`: `PERMISO_TABLERO_VER`, `_usuario_puede_ver_tablero_produccion`, `_usuario_puede_enviar_desde_tablero`, `_context_flags_tablero`.
- [x] 2.3 En `mpr/views.py`: `MprTableroVerMixin` (GET tablero) y `MprEscritorioVerMixin(MprPermisoMixin)` con `permiso_requerido = "mpr.ver"`.

## Phase 3: Backend guards

- [x] 3.1 `TableroProduccionView`, `TableroProduccionActualizarView`, `ManualUsuarioMprView`: `MprTableroVerMixin`; inyectar `**_context_flags_tablero(user)` en contexto.
- [x] 3.2 Mutaciones tablero: `EnviarProduccionLoteView`, `EnviosProduccionListView`, `AnularEnviosProduccionView`, `TransicionLoteView`, `ClasificacionProduccionView`, `RegistrarClasificacionProduccionView` → `MprEscritorioVerMixin`.
- [x] 3.3 Auditar `mpr/views.py`: `MprEscritorioVerMixin` en todas las vistas solo-`MprLoginRequiredMixin` del design (excl. `ParteMovilOperarioView` y lectura tablero).
- [x] 3.4 `mpr/best_migration/views.py`: `MprEscritorioVerMixin` en todas las clases con solo `MprLoginRequiredMixin`.

## Phase 4: Menú MPR parcial

- [x] 4.1 `core/utils/utils.py`: helper `_permiso_menu_ok(perm, permisos_usuario)` acepta `str | list[str]` (OR).
- [x] 4.2 Nodo `mpr` y ítem «Tablero de producción»: `permiso`/`permission` = `["mpr.ver", "mpr.tablero_ver"]`; REGLA 4 `apps_visibles_sin_filtro_pwa` usa OR.
- [x] 4.3 `_resolver_url_item` y `obtener_submenus_por_app` usan `_permiso_menu_ok`; resto ítems MPR sin cambio (requieren `mpr.ver` u otros).

## Phase 5: UI tablero solo lectura

- [x] 5.1 `mpr/templates/mpr/tablero_produccion.html`: `{% if puede_enviar %}` — columna Enviar, `#form-enviar-lote`, botón/modal Enviar, menú Armado/Anular.
- [x] 5.2 Mismo template: ocultar columna E5/transiciones por fila y enlace `maquinas_carga_articulos` cuando `solo_lectura_tablero`. **Nota:** la columna E5 / botones de transición por fila ya no existen en el template (flujo legacy retirado); solo aplicó `maquinas_carga_articulos` (indicador ámbar queda como `span` no navegable).
- [x] 5.3 Modal Fabricando: ocultar footer «Ir a CC» / «Ir al parte» si `solo_lectura_tablero`.
- [x] 5.4 `mpr/templates/mpr/includes/chrome_nav_flujo.html`: flag `solo_lectura_tablero` oculta enlaces Parte/CC/KPI; pasar desde `tablero_produccion.html`.

## Phase 6: Verificación y documentación

- [x] 6.1 Ejecutar `docker exec Synap_app python manage.py test mpr.tests.test_tablero_lectura_operario` (GREEN).
- [x] 6.2 Actualizar `docs/mpr/CARGA_MOVIL_OPERARIO.md` y `docs/mpr/ENVIO_PRODUCCION_TABLERO.md`: perfil operario+tablero, matriz permisos, UI solo lectura.
