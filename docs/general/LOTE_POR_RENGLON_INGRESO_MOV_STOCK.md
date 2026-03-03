# Lote por renglón en Ingreso Mov. Stock (Fase 1)

Implementación de **lote_articulo** y **stock_lote** en el formulario de ingreso de movimiento de stock: el usuario puede elegir por cada renglón un lote (cod_lote, vto_lote) y ver el stock de ese lote; al confirmar el movimiento se actualiza `lote` y `lote_stock` (Lote_ed).

## API

- **GET** `stock/api/ingreso/lotes-articulo/?id_articulo=&id_deposito=`  
  Lista de lotes del artículo en el depósito con stock > 0. Respuesta: `{ "lotes": [ { "id_lote", "cod_lote", "vto_lote", "fecha_vto_lote", "stock_lote" }, ... ] }`.  
  Usado por el modal "Elegir lote" para rellenar las opciones.

- **Servicio** `core/services/administranet_stock.py`  
  - `get_stock_por_lote(base_empresa, id_articulo, id_deposito=None)`: devuelve lista con **id_lote**, cod_lote, fecha_vto_lote, vto_lote (texto), stock_lote. Solo lotes no anulados y con stock_lote <> 0 en el depósito (o suma por lote si no se pasa id_deposito).
  - Add/update renglón temporal ya aceptan **id_lote**, **cod_lote**, **vto_lote** en `agregar_renglon_temporal` y `actualizar_renglon_temporal`.

## Flujo Lote_ed en confirmación (alta_movimiento)

Dentro de la transacción de `alta_movimiento`, por cada renglón con datos de lote:

- **Salida (ES = 'S'):**  
  Si el renglón tiene `id_lote`: se valida que exista `lote_stock` para (id_lote, id_deposito) y que `stock_lote >= Cantidad`. Si no cumple, se hace rollback y se devuelve error. Si cumple: `UPDATE lote_stock SET stock_lote = stock_lote - Cantidad` y `UPDATE lote SET stock_total_lote = stock_total_lote - Cantidad`.

- **Entrada (ES = 'E'):**  
  Si el renglón tiene `id_lote` o `cod_lote`:  
  - Si hay `id_lote`: se busca el lote por id_lote; si existe se actualiza `lote.stock_total_lote += entrada` y se actualiza o inserta `lote_stock` para (id_lote, id_deposito) sumando la entrada.  
  - Si no hay id_lote pero hay `cod_lote`: se busca lote por (cod_lote, id_articulo); si existe se hace lo mismo que arriba; si no existe se hace `INSERT` en `lote` (cod_lote, fecha_vto_lote, id_articulo, anulado='No', stock_total_lote=entrada) y `INSERT` en `lote_stock` (id_lote, id_deposito, stock_lote=entrada).

## UX/UI (alta_movimiento.html)

- **Columna Lote:** Por renglón: si no hay lote elegido, botón "Elegir lote" (deshabilitado si no hay depósito origen). Si hay lote: se muestra "cod_lote (vto_lote)", texto "Stock: &lt;stock_lote&gt;" (cuando está disponible) y botón "Cambiar".
- **Modal "Elegir lote":** Se abre al hacer clic en "Elegir lote" o "Cambiar". Carga vía API la lista de lotes del artículo en el depósito origen; cada ítem muestra cod_lote, vto_lote y stock_lote. Al elegir uno se asignan id_lote, cod_lote, vto_lote y stock_lote al renglón y se envía PUT al renglón para persistir; el modal se cierra.
- **Validación salida:** Antes de confirmar el movimiento, si un renglón es de salida y tiene id_lote y stock_lote (en front), se valida que Cantidad ≤ stock_lote; si no, se muestra error y no se confirma. El backend además valida contra `lote_stock` al confirmar.

## Referencias

- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md): lote_articulo / Lote_ed → Sí.
- [BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md](BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md): búsqueda con stock_lotes en sugerencias.
- Tablas: [lote.md](tablas/lote.md), [lote_stock.md](tablas/lote_stock.md).
