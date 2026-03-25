# Optimización del endpoint `GET /api/self-checkout/articulos/`

**Contexto:** listado de artículos para la grilla TPV del kiosco (`articulos_list` en `self_checkout/api_views.py`).

## Cambios de backend

1. **Precio:** `LEFT JOIN articulo_precio` sobre `id_lista` y `CASE` que replica la lógica previa (precio de lista si es positivo; si no, `Precio1V` / `Precio1VI` del artículo). Se evita un `SELECT` por fila.
2. **Promoción:** columnas de promoción se leen en el mismo `SELECT` cuando existen en el esquema; la evaluación de vigencia y lista usa `promocion_desde_fila_articulo` en `self_checkout/services/promotion_service.py` (misma regla que `obtener_promocion_articulo`, que ahora delega en esa función tras un único `SELECT` por artículo cuando se usa en otros flujos).
3. **Compatibilidad:** si faltan columnas (`NroCodBarra`, campos de promoción, etc.), se reintenta con variantes de la consulta; si falla el `JOIN` a `articulo_precio` (tabla inexistente, columnas distintas, errores 1054/1146 u operacionales recuperables), se usa el mismo listado que antes el refactor (**solo `articulo` + `iva`**) y los precios de lista se cargan con **un** `SELECT … IN (...)` a `articulo_precio` cuando esa tabla responde. En el peor caso la promoción vuelve a resolverse con `obtener_promocion_articulo` por fila (bases muy antiguas).
4. **Stock por depósito:** `StockService.get_disponible_map` hace un único `SELECT … WHERE id_articulo IN (...)`; si falla, se hace fallback fila a fila con `get_disponible`.

## Cambios de frontend (kiosco)

- **AbortController** en `cargarArticulos`: al cambiar el texto se aborta la petición anterior; `fetch` del kiosco trata `AbortError` sin abrir el modal de error de conexión.
- Al vaciar la búsqueda se aborta la petición en curso y se apaga el indicador de carga.

## Archivos tocados

- `self_checkout/api_views.py` — `_fetch_articulos_list_rows`, `articulos_list`
- `self_checkout/services/promotion_service.py` — `promocion_desde_fila_articulo`, refactor de `obtener_promocion_articulo`
- `self_checkout/services/stock_service.py` — `get_disponible_map`
- `self_checkout/templates/self_checkout/kiosco.html` — búsqueda TPV + `fetch` con `signal`
