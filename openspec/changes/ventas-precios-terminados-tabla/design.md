# Diseño — Precios terminados tabla

## Arquitectura

```
ventas/views_precios_terminados.py  → GET tabla, API buscar, POST guardar/masivo
ventas/services/precios_terminados.py → listado, catálogos, masivo, guardar_lote
ventas/services/precios_articulo_legacy.py → neto↔final, util, INSERT historial
MySQL articulo + precios_historial (legacy AdministraNET)
```

## Filtro primario

`tipo_producto=terminado|2da` → `tipo_art_fab` = `'Terminado'` | `'Fabricado 2da'`. Al cambiar tipo, reset filtros secundarios vía GET con query limpia.

## Persistencia

Por artículo modificado: UPDATE `Precio{i}V/VI`, recalc `Util{i}`, opcional `stock_reserva`, INSERT `precios_historial`.

## UI

Shell `mpr/base_mpr.html`, tabla sticky como `armado_tablero.html`, tags `tags_filter.mjs` + autocomplete inventario para código multi.
