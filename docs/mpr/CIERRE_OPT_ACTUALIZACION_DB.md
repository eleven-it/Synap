# Actualización en base de datos al cerrar una OPT

## Tabla donde se guardan las OPT (y las OPT a liberar)

Las **OPTs** (Órdenes de Producción de Trabajo), tanto las ya liberadas como las pendientes de liberar, se guardan en la tabla **`lista_produccion_agrupada`** (MySQL). Cada fila representa una OPT (o una línea de OPT agrupada); las que están "a liberar" son las que aún no tienen `codigo_movimiento_opt` asignado o que se listan desde demanda/pedidos antes de ejecutar la liberación.

**Tablero MPR – OPTs en proceso:** El panel «OPTs en proceso de producción» del tablero muestra **solo** OPTs con `en_proceso_produccion = 'Si'` (ya liberadas). Se usa el servicio `listar_opt_en_proceso(base_empresa, limit)` y, por cada OPT, `estado_acciones_opt(base_empresa, id_lista_produccion)` para determinar la acción principal: **Crear OPP** (si hay pendiente de OPP), **Crear OPA** (si hay armado pendiente con stock), o **Cerrar** (si pendiente OPP = 0 y no hay armado pendiente). Las funciones de detalle y armado existentes (`get_opt_detalle`, `get_lineas_armado_opt`, `get_cantidades_armadas_por_opt`) se usan dentro de `estado_acciones_opt`.

---

Al ejecutar **Cerrar OPT** (desde el wizard paso 5 o desde el detalle de la OPT), se llama a `cerrar_opt(base_empresa, id_lista_produccion)` en `mpr/services.py`. Este es el detalle de **todo lo que se actualiza en la DB**.

---

## 1. Condiciones previas

- La OPT debe existir y tener líneas (`get_opt_detalle` devuelve datos).
- **Pendiente total = 0**: `SUM(cantidad_pendiente_prod)` de las líneas de esa OPT debe ser 0 (toda la producción registrada vía OPP). Si no, la función devuelve error y no se modifica nada.

---

## 2. Tablas y columnas actualizadas

### 2.1 `comp_ped` (pedidos de venta)

- **Qué se hace:** Se actualiza `estado_pedido_opt` según si queda demanda pendiente para ese pedido: **`'Parcial'`** si en `lista_produccion_detalle` ese pedido tiene alguna línea con `cantidad_pendiente_prod > 0`; **`'Terminado'`** si no queda pendiente.
- **Criterio:** Por cada `codigo_movimiento_pedido` de la OPT se suma `cantidad_pendiente_prod` en detalle; si suma > 0 → `'Parcial'`, si no → `'Terminado'`.
- **Función auxiliar:** `_actualizar_comp_ped_estado_produccion(cursor, tbl_cp, codigos, estado)`.

### 2.2 `lista_produccion_agrupada`

- **Qué se hace:** Se cierra la OPT. Si hubo cantidad pedida no armada (cantidad_restante > 0), se **restaura el restante** como demanda de forma que al usar «Generar OPT» desde la pantalla de demanda se cree una **OPT con número nuevo** (no se reutilice la OPT cerrada), y **ambas OPTs (la cerrada y la nueva) quedan referenciadas al mismo pedido** (visible en «Ver OPTs» por pedido):
  - Se **INSERT** una nueva fila en `lista_produccion_agrupada` con `id_articulo`, `cantidad_pedida` = `cantidad_pendiente_prod` = cantidad_restante, `en_proceso_produccion` = `'No'`.
  - Tras restar en detalle lo ya armado (cantidad_ya_armada), se **INSERT** nuevas filas en `lista_produccion_detalle` con el mismo `codigo_movimiento_pedido` e `id_articulo`, apuntando a la nueva `id_lista_produccion` y con `cantidad_pendiente_prod` = cantidad_restante (en la primera fila).
  - Las filas de detalle de la OPT cerrada se dejan con `id_lista_produccion` = la OPT cerrada y se actualizan a `cantidad_pendiente_prod` = 0. Así la OPT cerrada sigue vinculada al pedido (con 0 pendiente) y la nueva OPT también (con el restante).
  - La fila **original** en agrupada de la OPT cerrada se actualiza con `cantidad_pendiente_prod` = 0, `en_proceso_produccion` = `'No'`, `id_opt` = NULL, `id_operario_opt` = NULL.
- Si no hay cantidad restante (todo armado), solo se actualiza la fila existente: `en_proceso_produccion` = `'No'`, `id_opt` = NULL, etc.

### 2.3 `lista_produccion_detalle`

- **Qué se hace:** Se reduce `cantidad_pendiente_prod` en las filas de la OPT restando la cantidad ya producida (armada), para coherencia con agrupada y con el estado del pedido.

### 2.4 `movimiento_stock` (comprobante de liberación OPT)

- **Qué se hace:** Se registra la **hora de cierre** en el movimiento de liberación de la OPT.
- **Columnas (según esquema):**
  - Si existe: `hora_salida_opt` = fecha/hora actual.
  - Si no existe `hora_salida_opt`: se intenta `hora_salida` (fallback).
- **Criterio:** La fila donde `codigo_movimiento` = `codigo_movimiento_opt` de la OPT (leído desde `lista_produccion_agrupada`).
- **Valor:** `datetime.now().strftime("%Y-%m-%d %H:%M:%S")`.

---

## 3. Orden de ejecución en código

1. **Validar** OPT existe y pendiente total = 0.
2. Obtener cantidades ya armadas por artículo (`get_cantidades_armadas_por_opt`).
3. Por cada línea: actualizar **lista_produccion_agrupada** (restante, en_proceso, id_opt NULL) y **lista_produccion_detalle** (reducir pendiente por lo producido).
4. Por cada pedido asociado: si suma `cantidad_pendiente_prod` en detalle > 0 → **comp_ped** `estado_pedido_opt = 'Parcial'`, si no → `'Terminado'`.
5. Actualizar **movimiento_stock**: `hora_salida_opt` (o `hora_salida`) = ahora.
6. **Commit** de la transacción.

---

## 4. Tablas que NO se modifican al cerrar

- **lista_produccion_detalle**: no se actualiza en el cierre.
- **lista_produccion_historico**: no se escribe ningún evento “Cierre”.
- **stock**, **stock_deposito**: no se modifican.

---

## 6. Restante por armar y unidades a desperdicio/otros depósitos

Solo la cantidad de OPP que fue a **Semi elaborado** es armable. La que fue a **Desperdicio** (tipo_mpr=Scrap), **2.ª selección** u otro depósito distinto de Semi elaborado **no se considera** pendiente de armar.

- **Cálculo:** El servicio `get_cantidad_opp_por_destino_opt(base_empresa, id_lista_produccion)` devuelve por **componente** (id_articulo = componente, ej. medias) la cantidad que entró a Semi elaborado, a otros depósitos y solo a **Desperdicio** (Scrap). El OPP registra movimientos en **unidades de componente**; para mostrar en pantalla en **packs** se usa `componentes_a_equivalentes_pack(base_empresa, id_pack, dict_componente_qty)` según el BOM (1 pack = N medias).
- **Restante por armar:** `max(0, equivalente_pack_semi - cantidad_ya_armada)`. Si 1 media fue a Desperdicio (1/3 pack), no queda "1 restante por armar" y la OPT puede cerrarse cuando el pendiente OPP es 0.
- **UI:** Todas las cantidades OPP (Semi, desperdicio, otros) se muestran en **packs** para no confundir con medias. No se muestra ninguna recomendación de reponer; el usuario gestiona la demanda manualmente desde la pantalla de demanda si lo desea.

---

## 7. Efecto en la pantalla

- Tras el cierre, las vistas que lean `lista_produccion_agrupada` (p. ej. wizard paso 5, detalle OPT) verán `en_proceso_produccion = 'No'`.
- El botón **Cerrar OPT** debe mostrarse solo cuando `en_proceso_produccion = 'Si'` y pendiente = 0; si la OPT ya está cerrada, se muestra el estado “OPT cerrada” y no el botón.
