# Analítica — histórico de precios (`precios_historial`)

**Change SDD:** `ventas-analitica-precios-historial`  
**Tabla origen:** MySQL `precios_historial` (legacy AdministraNET)  
**Escritura Synap:** `ventas/services/precios_articulo_legacy.py` → `insertar_precios_historial` con `tipo_modificacion = 'Synap precios terminados'`

## Alcance

| Entregable | Ruta / artefacto |
|------------|------------------|
| Servicio consulta + deltas | `ventas/services/precios_historial.py` |
| API drill-down | `GET /ventas/precios-terminados/api/historial/<id_articulo>/` |
| Modal en precios terminados | `precios_terminados_tabla.html` + `precios_terminados_historial.mjs` |
| Ranking SSR | `GET /ventas/evolucion-precios/` |
| Informe Reports | slug `evolucion-precios` → `reports/services/evolucion_precios_runner.py` |

## Permisos

- `ventas.precios_historial.ver` — consulta historial y página de evolución
- `ventas.precios_terminados.editar` — edición de precios; también permite ver historial (modal y ranking)

Menú Ventas → **Evolución de precios** requiere `ventas.precios_historial.ver`. Usuarios solo con edición acceden al historial desde la tabla de precios terminados.

## Cálculo de variaciones

Los snapshots se ordenan por `fecha_control`, `id_precios_historial`. Los deltas se calculan en Python (sin `LAG` SQL) para compatibilidad MariaDB/MySQL legacy:

- `delta_neto = neto_actual − neto_anterior`
- `delta_pct = delta / anterior × 100` si `anterior > 0`

**Ranking de período:** por `id_articulo`, variación entre el **primer** y **último** snapshot dentro del rango de fechas (lista configurable 1–5).

## Filtros ranking / informe

| Parámetro | Descripción |
|-----------|-------------|
| `fecha_desde`, `fecha_hasta` | Rango; por defecto últimos 90 días |
| `lista` | Lista de precios (1–5) |
| `marcas_incluidos`, `rubros_incluidos` | Filtros opcionales |
| `solo_synap` | Solo registros con `tipo_modificacion` que comienza con `Synap` |
| `limit` | Máximo de filas en ranking (default 50, máx. 200) |

## API historial artículo

```
GET /ventas/precios-terminados/api/historial/<id_articulo>/?lista=1&fecha_desde=2026-01-01&fecha_hasta=2026-03-31
```

Respuesta JSON: `filas[]` con `neto`, `final`, `delta_neto`, `delta_pct`, `tipo_modificacion`, `fecha`; `resumen` con variación acumulada.

## Tests

```bash
docker exec Synap_app python manage.py test ventas.tests.test_precios_historial
```

## Referencias

- Diseño precios terminados: `docs/ventas/DISENO_PRECIOS_TERMINADOS_TABLA.md`
- Tabla legacy: `reports/docs/tablas/precios_historial.md`
- Inventario VB6: `docs/ventas/INVENTARIO_FORMULARIO_VARIACION_PRECIO.md`
