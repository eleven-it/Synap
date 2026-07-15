# Tasks: ventas-precios-terminados-tabla

## Phase 0 — Documentación

- [x] 0.1 `docs/ventas/INVENTARIO_FORMULARIO_VARIACION_PRECIO.md`
- [x] 0.2 `docs/ventas/DISENO_PRECIOS_TERMINADOS_TABLA.md`

## Phase 1 — Backend

- [x] 1.1 `ventas/services/precios_articulo_legacy.py` (neto/final, util, historial)
- [x] 1.2 `ventas/services/precios_terminados.py` (listado, catálogos, filtros)
- [x] 1.3 `ventas/views_precios_terminados.py` + URLs + API buscar
- [x] 1.4 Tests servicio listado y filtros

## Phase 2 — UI

- [x] 2.1 Template `precios_terminados_tabla.html` + includes filtros
- [x] 2.2 JS recálculo, dirty, autocomplete código multi
- [x] 2.3 Modal guardar y barra inferior sticky

## Phase 3 — Persistencia

- [x] 3.1 POST guardar lote
- [x] 3.2 Tests guardado e historial (fórmulas unitarias; integración MySQL manual)

## Phase 4 — Masivo

- [x] 4.1 Preview y aplicar masivo server-side
- [x] 4.2 Tests masivo (operaciones unitarias)

## Phase 5 — Integración

- [x] 5.1 Permiso `ventas.precios_terminados.editar` y menú
- [x] 5.2 Verify tests en contenedor (`ventas.tests.test_precios_terminados` — 8 OK)
