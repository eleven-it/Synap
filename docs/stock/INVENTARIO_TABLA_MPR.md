# Inventario por etapa MPR (Stock)

**Ruta:** `/stock/inventario/`  
**Permiso:** `stock.consultas`  
**Change SDD:** `stock-inventario-tabla-mpr`

## Descripción

Consulta operativa de inventario: una fila por artículo con columnas por etapa MPR (`deposito.tipo_mpr`) y columna **Consolidado**.

| Columna | `tipo_mpr` |
|---------|-------------|
| Producción | `Produccion` |
| Semi elaborado | `SemiElaborado` |
| 2da Selección | `2daSeleccion` |
| Terminado | `Terminado` |
| Consolidado | Suma de las cuatro anteriores |

Solo se suman depósitos con `suma_stock = 'Si'`.

## Filtros

| Parámetro | Descripción |
|-----------|-------------|
| `marcas_incluidos` | Multi-select tags (vacío = todas) |
| `q` | Búsqueda texto (≥ 2 caracteres), universo completo |
| `id_articulo` | Una fila concreta |
| `incluir_ceros=1` | Incluye artículos con consolidado ≤ 0 |
| `presentacion` | `unidades` (default) o `docenas` |
| `page` | Paginación (150 filas) |

## API

`GET /stock/api/inventario/articulos/?q=` — búsqueda predictiva (mismos criterios, sin paginación de tabla).

## Código

- Servicio: `stock/services/inventario_tabla.py`
- Vista: `stock/views.inventario_view`
- Plantillas: `stock/templates/stock/inventario/`

## Legacy eliminado

`/stock/consulta-ficha/` y `consulta_ficha_stock` fueron eliminados; el menú **Inventario** apunta a `stock:inventario`.
