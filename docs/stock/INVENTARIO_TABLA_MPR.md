# Inventario por etapa MPR (Stock)

**Ruta:** `/stock/inventario/`  
**Permiso:** `stock.consultas`  
**Change SDD:** `stock-inventario-tabla-mpr`  
**Manual de usuario:** [MANUAL_USUARIO_STOCK.md](MANUAL_USUARIO_STOCK.md)

## Descripción

Consulta operativa de inventario: una fila por artículo con columnas por etapa MPR (`deposito.tipo_mpr`), **Talle**, **Color** y columna **Consolidado**.

El toggle **Tipo de artículo** separa dos universos según `articulo.tipo_art_fab` (no confundir con la etapa depósito «Terminado»):

| Ámbito (`ambito`) | Artículos (`tipo_art_fab`) | Columnas de stock | Consolidado |
|-------------------|----------------------------|-------------------|-------------|
| **Fabricados** (default) | `Fabricado`, `Fabricado 2da` | Producción, Semi elaborado, 2da Selección | Suma de esas tres |
| **Terminados** | `Terminado` | Terminado | *(sin columna Consolidado; sería idéntica a Terminado)* |

| Columna | Origen |
|---------|--------|
| Artículo | Nombre del artículo |
| Talle | Campo especial CE `TALLES` (`articulo_valor_ce.valor1`) |
| Color | Campo especial CE `COLOR` (`articulo_valor_ce.valor2`); puede ser sólido o combo `A/B` |
| Producción | `tipo_mpr = Produccion` (solo ámbito Fabricados) |
| Semi elaborado | `tipo_mpr = SemiElaborado` (solo Fabricados) |
| 2da Selección | `tipo_mpr = 2daSeleccion` (solo Fabricados) |
| Terminado | `tipo_mpr = Terminado` (solo ámbito Terminados) |
| Consolidado | Suma de etapas Fabricados (oculto en Terminados) |

Solo se suman depósitos con `suma_stock = 'Si'` y no anulados.

Detalle de modelo CE: [../mpr/ARTICULO_CE_TALLES_COLOR.md](../mpr/ARTICULO_CE_TALLES_COLOR.md).

## Filtros

| Parámetro | Descripción |
|-----------|-------------|
| `ambito` | `fabricados` (default) o `terminados` |
| `marcas_incluidos` | Multi-select tags (vacío = todas) |
| `q` | Filtro de texto (también se filtra en vivo en la página cargada: nombre, talle, color, códigos) |
| `id_articulo` | Una fila concreta (también filtrada por ámbito) |
| `incluir_ceros=1` | Incluye artículos sin saldo positivo en ninguna etapa del ámbito |
| `presentacion` | `unidades` (pares, default) o `docenas` (docenas de pares) |
| `page` | Paginación (150 filas) |

Con el filtro predeterminado **Solo con stock**, un artículo se muestra si tiene saldo **> 0** en al menos una etapa **del ámbito activo**. Saldos en cero o negativos no entran. El consolidado es la suma de esas mismas etapas. El filtro de stock se aplica en `WHERE` (no `HAVING`) para evitar vaciar el resultado con joins a CE.

Componentes UI compartidos con MPR operativo: `templates/includes/filtro_marcas_tags.html` (variant `light`), JS `stock/static/stock/js/filtro_marcas_tags.mjs`. Los toggles **Fabricados | Terminados** y **Docenas | Pares** se renderizan en `_filtros.html` (bindings Alpine `cambiarAmbito` / `cambiarPresentacion`).

## UI

Interfaz alineada al patrón visual de **Ingreso de movimiento de stock** (`/stock/ingreso-movimiento/`): hero oscuro slate (gradient) con breadcrumb/eyebrow, título, subtítulo y acciones (Ayuda + contador de artículos); tarjeta de filtros canónica. El botón primario **Actualizar** y los toggles activos usan acento purple. Las columnas de etapa llevan un borde superior de color sutil solo como diferenciación visual.

## API

`GET /stock/api/inventario/articulos/?q=&ambito=` — búsqueda predictiva (mismos criterios de ámbito/marcas/stock, sin paginación de tabla).

## Código

- Servicio: `stock/services/inventario_tabla.py` (`ce_texto`, JOIN `articulo_valor_ce`, `etapas_para_ambito`)
- Vista: `stock/views.inventario_view`
- Plantillas: `stock/templates/stock/inventario/` (`_tabla.html` incluye Talle/Color)
- Tests: `stock/tests/test_inventario_tabla.py`

## Legacy eliminado

`/stock/consulta-ficha/` y `consulta_ficha_stock` fueron eliminados; el menú **Inventario** apunta a `stock:inventario`.
