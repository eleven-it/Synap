# Inventario por etapa MPR (Stock)

**Ruta:** `/stock/inventario/`  
**Permiso:** `stock.consultas`  
**Change SDD:** `stock-inventario-tabla-mpr`

## Descripción

Consulta operativa de inventario: una fila por artículo con columnas por etapa MPR (`deposito.tipo_mpr`) y columna **Consolidado**.

| Columna | Origen |
|---------|--------|
| Artículo | Código compuesto + nombre |
| Talle | Campo especial CE `TALLES` (`articulo_valor_ce.valor1`) |
| Color | Campo especial CE `COLOR` (`articulo_valor_ce.valor2`) |
| Producción | `tipo_mpr = Produccion` |
| Semi elaborado | `tipo_mpr = SemiElaborado` |
| 2da Selección | `tipo_mpr = 2daSeleccion` |
| Terminado | `tipo_mpr = Terminado` |
| Consolidado | Suma de las cuatro etapas |

Solo se suman depósitos con `suma_stock = 'Si'`.

## Filtros

| Parámetro | Descripción |
|-----------|-------------|
| `marcas_incluidos` | Multi-select tags (vacío = todas) |
| `q` | Búsqueda texto (≥ 2 caracteres), universo completo |
| `id_articulo` | Una fila concreta |
| `incluir_ceros=1` | Incluye artículos con consolidado ≤ 0 |
| `presentacion` | `unidades` (pares, default) o `docenas` (docenas de pares) |

Componentes UI compartidos con MPR operativo: `templates/includes/filtro_marcas_tags.html` (variant `light`), `templates/includes/toggle_docenas_pares.html` (toggle **Docenas | Pares**), JS `stock/static/stock/js/filtro_marcas_tags.mjs`.
| `page` | Paginación (150 filas) |

## API

`GET /stock/api/inventario/articulos/?q=` — búsqueda predictiva (mismos criterios, sin paginación de tabla).

## Código

- Servicio: `stock/services/inventario_tabla.py`
- Vista: `stock/views.inventario_view`
- Plantillas: `stock/templates/stock/inventario/`

## Legacy eliminado

`/stock/consulta-ficha/` y `consulta_ficha_stock` fueron eliminados; el menú **Inventario** apunta a `stock:inventario`.
