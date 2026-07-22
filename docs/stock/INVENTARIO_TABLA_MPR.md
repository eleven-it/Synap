# Inventario por etapa MPR (Stock)

**Ruta:** `/stock/inventario/`  
**Permiso:** `stock.consultas`  
**Change SDD:** `stock-inventario-tabla-mpr`  
**Manual de usuario:** [MANUAL_USUARIO_STOCK.md](MANUAL_USUARIO_STOCK.md)

## Descripción

Consulta operativa de inventario: una fila por artículo con columnas por etapa MPR (`deposito.tipo_mpr`), **Talle**, **Color** y columna **Consolidado**.

| Columna | Origen |
|---------|--------|
| Artículo | Código compuesto + nombre |
| Talle | Campo especial CE `TALLES` (`articulo_valor_ce.valor1`) |
| Color | Campo especial CE `COLOR` (`articulo_valor_ce.valor2`); puede ser sólido o combo `A/B` |
| Producción | `tipo_mpr = Produccion` |
| Semi elaborado | `tipo_mpr = SemiElaborado` |
| 2da Selección | `tipo_mpr = 2daSeleccion` |
| Terminado | `tipo_mpr = Terminado` |
| Consolidado | Suma de las cuatro etapas |

Solo se suman depósitos con `suma_stock = 'Si'` y no anulados.

Detalle de modelo CE: [../mpr/ARTICULO_CE_TALLES_COLOR.md](../mpr/ARTICULO_CE_TALLES_COLOR.md).

## Filtros

| Parámetro | Descripción |
|-----------|-------------|
| `marcas_incluidos` | Multi-select tags (vacío = todas) |
| `q` | Búsqueda texto (≥ 2 caracteres), universo completo |
| `id_articulo` | Una fila concreta |
| `incluir_ceros=1` | Incluye artículos con consolidado ≤ 0 |
| `presentacion` | `unidades` (pares, default) o `docenas` (docenas de pares) |
| `page` | Paginación (150 filas) |

Componentes UI compartidos con MPR operativo: `templates/includes/filtro_marcas_tags.html` (variant `light`), JS `stock/static/stock/js/filtro_marcas_tags.mjs`. El toggle **Docenas | Pares** se renderiza local en `_filtros.html` con paleta slate/sky (mismos bindings Alpine `cambiarPresentacion`).

## UI

Interfaz alineada al patrón visual de **Ingreso de movimiento de stock** (`/stock/ingreso-movimiento/`): hero oscuro slate (gradient) con breadcrumb/eyebrow, título, subtítulo y acciones (Ayuda + contador de artículos); tarjeta de filtros canónica y paleta **slate/sky** (sin acento purple). El botón primario **Actualizar** usa slate; el toggle Presentación y el estado «incluir ceros» usan acento sky. Las columnas de etapa (Producción / Semi elaborado / 2da Selección / Terminado) llevan un borde superior de color sutil solo como diferenciación visual.

## API

`GET /stock/api/inventario/articulos/?q=` — búsqueda predictiva (mismos criterios, sin paginación de tabla).

## Código

- Servicio: `stock/services/inventario_tabla.py` (`ce_texto`, JOIN `articulo_valor_ce`)
- Vista: `stock/views.inventario_view`
- Plantillas: `stock/templates/stock/inventario/` (`_tabla.html` incluye Talle/Color)
- Tests: `stock/tests/test_inventario_tabla.py`

## Legacy eliminado

`/stock/consulta-ficha/` y `consulta_ficha_stock` fueron eliminados; el menú **Inventario** apunta a `stock:inventario`.
