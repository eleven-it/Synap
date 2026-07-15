# Tasks: Inventario tabla MPR en Stock

## Phase 1: Infraestructura y limpieza legacy

- [x] 1.1 Crear `stock/services/inventario_tabla.py` (filtros, SQL pivote, catálogo marcas)
- [x] 1.2 Eliminar ruta/vista/plantilla `consulta-ficha`; actualizar menú en `core/utils/utils.py`
- [x] 1.3 Registrar `inventario` y API en `stock/urls.py`

## Phase 2: Vista y API

- [x] 2.1 `inventario_view` en `stock/views.py` (GET, paginación 150, contexto)
- [x] 2.2 `api_inventario_articulos` en `stock/api_views.py`
- [x] 2.3 Plantillas `inventario.html` + partials (filtros tags, tabla, buscador)

## Phase 3: Presentación y JS

- [x] 3.1 Toggle unidades/docenas vía `mpr/reportes_presentacion`
- [x] 3.2 `stock/static/stock/js/inventario.js` (tags_filter + predictivo)
- [x] 3.3 Botón «Ver todos» (`incluir_ceros`)

## Phase 4: Tests y documentación

- [x] 4.1 Tests unitarios servicio y URLs
- [x] 4.2 `docs/stock/INVENTARIO_TABLA_MPR.md`
