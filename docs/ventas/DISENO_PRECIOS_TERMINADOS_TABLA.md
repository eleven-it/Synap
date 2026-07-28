# Diseño — Precios terminados en tabla

**Ruta:** `/ventas/precios-terminados/`  
**Permiso:** `ventas.precios_terminados.editar`  
**Change SDD:** `openspec/changes/ventas-precios-terminados-tabla/`

## Resumen

Pantalla operativa tipo tablero MPR para actualizar precios y reserva de productos con `tipo_art_fab` **Terminado** o **Fabricado 2da**.

## Filtros (dos niveles)

1. **Tipo producto** (píldoras): Terminado | 2da — al cambiar resetea filtros secundarios (marca, proveedor, etc.) pero **conserva** orden, dirección y filtro de reserva.
2. **Dependientes:** marca, código (tags multi + predictivo), proveedor, rubro, subrubro, listas visibles.
3. **Reserva** (píldoras): Todas | = 0 | > 0 — filtro server-side con `COALESCE(stock_reserva, 0)`. Query param `reserva=` vacío | `eq0` | `gt0`.

## Ordenación

Server-side sobre el universo filtrado (afecta paginación). Query params `orden` y `dir=asc|desc` (default `orden=codigo`, `dir=asc`).

Columnas: `id`, `codigo`, `nombre`, `reserva`, `neto_N` / `final_N` (N = listas 1–5 visibles). Click en header: misma columna alterna asc/desc; otra columna inicia en asc. Whitelist estricta en SQL.

## Tabla

Columnas fijas: IDArt, id_manual, nombre, reserva.  
Por cada lista visible: neto y final editables con recálculo cruzado y marcado dirty (ámbar).

## Cambio masivo

Modal con preview server-side; aplica **solo a los artículos visibles en la tabla** (página actual + búsqueda en página). Permite elegir una o más listas de precios cuando el ámbito es neto o final.

## Persistencia

`ventas/services/precios_articulo_legacy.py` — UPDATE `articulo` + INSERT `precios_historial`.

## Archivos

| Archivo | Rol |
|---------|-----|
| `ventas/services/precios_terminados.py` | Listado, catálogos, masivo |
| `ventas/views_precios_terminados.py` | Vistas y API |
| `ventas/templates/ventas/precios_terminados_tabla.html` | UI |
| `ventas/static/ventas/js/precios_terminados_*.mjs` | Filtros y tabla |

## Histórico de precios (analítica)

Desde cada fila, botón **Historial** abre modal con serie temporal (`precios_historial`). Ver `docs/ventas/ANALITICA_PRECIOS_HISTORIAL.md` y ranking en `/ventas/evolucion-precios/`.
