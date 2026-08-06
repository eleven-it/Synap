# Inventario por etapa MPR (Stock)

**Ruta:** `/stock/inventario/`  
**Permiso:** `stock.consultas`  

**Consulta equivalente en MPR:** `/mpr/inventario/` con permiso `mpr.ver` (misma fuente `inventario_tabla`, templates PWA + escritorio bajo módulo MPR). Ver [../mpr/PWA_TABLERO_INVENTARIO.md](../mpr/PWA_TABLERO_INVENTARIO.md).

**Change SDD:** `stock-inventario-tabla-mpr`  
**Manual de usuario:** [MANUAL_USUARIO_STOCK.md](MANUAL_USUARIO_STOCK.md)

## Descripción

Consulta operativa de inventario: una fila por artículo con columnas por etapa MPR (`deposito.tipo_mpr`), **Talle**, **Color** y columna **Consolidado**.

El toggle **Tipo de artículo** separa dos universos según `articulo.tipo_art_fab` (no confundir con la etapa depósito «Terminado»):

| Ámbito (`ambito`) | Artículos (`tipo_art_fab`) | Columnas de stock | Consolidado |
|-------------------|----------------------------|-------------------|-------------|
| **Terminados** (default) | `Terminado`, `Tercero` | Terminado | *(sin columna Consolidado; sería idéntica a Terminado)* |
| **Fabricados** | `Fabricado`, `Fabricado 2da` | Producción, Semi elaborado, 2da Selección | Suma de esas tres |

| Columna | Origen |
|---------|--------|
| EAN | `NroCodBarraF` (preferido) o `NroCodBarra` en `articulo` |
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
| `ambito` | `terminados` (default) o `fabricados` |
| `marcas_incluidos` | Multi-select tags (vacío = todas) |
| `q` | Prefill del filtro cliente «Buscar en tabla» (no filtra SQL de la grilla) |
| `id_articulo` | Una fila concreta (también filtrada por ámbito) |
| `filtro_stock` | `todos` (default) · `con_stock` · `sin_stock` |
| `presentacion` | `unidades` (pares, default) o `docenas` (docenas de pares) |

La grilla carga **todo el ámbito** (tope 5000). El campo **Buscar en tabla** filtra en vivo en el cliente. Si la carga tarda más de 2 s se muestra el modal Synap de espera.

| `filtro_stock` | Criterio (etapas del ámbito activo) |
|----------------|--------------------------------------|
| **todos** (default) | Todos los artículos del ámbito; **muestra saldos negativos** (sin clamp a 0) |
| **con_stock** | Al menos una etapa con saldo **> 0** |
| **sin_stock** | Ninguna etapa con saldo > 0 (ceros y **negativos**, para ajustes) |

Compat URL legacy: `incluir_ceros=1` → `todos`; `incluir_ceros=0` → `con_stock`. El filtro de stock se aplica en `WHERE` (no `HAVING`) para evitar vaciar el resultado con joins a CE. El consolidado es la suma de las etapas del ámbito.

Componentes UI compartidos con MPR operativo: `templates/includes/filtro_marcas_tags.html` (variant `light`), JS `stock/static/stock/js/filtro_marcas_tags.mjs`. Los toggles **Fabricados | Terminados**, **Docenas | Pares** y **Todos | Con stock | Sin stock** se renderizan en `_filtros.html` (bindings Alpine).

## UI

Interfaz alineada al patrón visual de **Ingreso de movimiento de stock** (`/stock/ingreso-movimiento/`): hero oscuro slate (gradient) con breadcrumb/eyebrow, título, subtítulo y acciones (Ayuda + contador de artículos); tarjeta de filtros canónica. El botón primario **Actualizar** y los toggles activos usan acento purple. Las columnas de etapa llevan un borde superior de color sutil solo como diferenciación visual.

## API

`GET /stock/api/inventario/articulos/?q=&ambito=` — búsqueda predictiva (mismos criterios de ámbito/marcas/stock, sin paginación de tabla).

## Código

- Servicio: `stock/services/inventario_tabla.py` (`ce_texto`, JOIN `articulo_valor_ce`, `etapas_para_ambito`)
- Vista Stock: `stock/views.inventario_view`
- Vista MPR: `mpr/views.InventarioMprView` (`/mpr/inventario/`)
- Plantillas: `stock/templates/stock/inventario/` (`_tabla.html` incluye Talle/Color); PWA MPR en `mpr/templates/mpr/mobile/inventario.html`
- Tests: `stock/tests/test_inventario_tabla.py`, `mpr/tests/test_pwa_tablero_inventario.py`

## Legacy eliminado

`/stock/consulta-ficha/` y `consulta_ficha_stock` fueron eliminados; el menú **Inventario** apunta a `stock:inventario`.
