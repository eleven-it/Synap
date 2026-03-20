# OPP por componente y en unidades

La parte de producción (OPP) se muestra y registra por **artículo componente** y en **unidades**, no por pack. Esto permite distribuir de forma granular: por ejemplo, si una unidad de un componente salió mal, se puede enviar solo esa unidad a Scrap y el resto a Semi Elaborado, sin verse obligado a mandar un pack entero.

## Pantalla OPP

- **Matriz:** filas = componentes (artículos que forman parte de la BOM de los packs de la OPT), columnas = depósitos destino (Semi Elaborado, Scrap, 2ª Selección).
- **Disponible (unid.):** por cada componente, la suma de unidades que resultan de explotar los packs de la OPT × su `cantidad_pendiente_prod` vía BOM. Se obtiene con `get_opp_componentes_disponibles(base_empresa, id_lista_produccion)`.
- El usuario ingresa cantidades en **unidades** por celda (componente × depósito) y asigna **operario por componente**. Por componente, la suma por depósitos no puede superar el disponible.

## Registro (backend)

- **Entrada:** `distribucion_por_deposito = { cod_deposito_destino: [ (id_componente, qty_unidades), ... ] }` + `id_operario_por_componente = { id_componente: id_operario }`.
- Se valida que en el depósito de producción haya saldo suficiente de cada componente y que cada componente con cantidad > 0 tenga operario asignado.
- Por cada depósito destino con cantidades se genera un movimiento (Salida desde Producción, Entrada al destino) por cada componente.
- Tras todos los movimientos, se calcula el **equivalente pack** a decrementar en `lista_produccion_agrupada.cantidad_pendiente_prod`.

## Cálculo del equivalente pack

Para no “consumir” más componentes de los realmente distribuidos, el decremento de `cantidad_pendiente_prod` se hace en **equivalentes pack** a partir de las unidades enviadas:

1. **Total distribuido por componente:** `total_dispatch[comp]` = suma sobre todos los depósitos de las unidades del componente en esta OPP.
2. **Por cada pack (línea de la OPT):** con su BOM se calcula  
   `d_p_raw = min_comp(total_dispatch[comp] / cantidad_articulo en BOM)`  
   y `d_p = min(cantidad_pendiente_prod, d_p_raw)`.  
   Si el pack no tiene BOM, se trata como componente único (cantidad 1).
3. **Escalado cuando un componente es compartido:** si varios packs usan el mismo componente, la suma  
   `usage(comp) = sum_p (d_p * bom_p(comp))`  
   podría superar `total_dispatch[comp]`. Se aplica un factor de escala  
   `scale = min(1, min_comp(total_dispatch[comp] / usage(comp)))`  
   y se hace `d_p_final = d_p * scale` (truncado a entero).
4. Se actualiza `lista_produccion_agrupada` restando `d_p_final` a `cantidad_pendiente_prod` en cada fila (por `id_lista_produccion` e `id_articulo` del pack).
5. Se actualiza **lista_produccion_detalle**: para cada (id_lista_produccion, id_articulo pack, d_p) se reduce `cantidad_pendiente_prod` de forma proporcional al total de detalle para esa línea (factor = (total − d_p) / total).
6. Se inserta en **lista_produccion_historico** una fila por (componente, cantidad) con `tipo_evento = 'OPP'`, `id_articulo` = pack, `id_articulo_formula` = componente, `codigo_movimiento_opt` = comprobante de la OPT y `id_operario` = operario del componente (trazabilidad).

Funciones en `mpr/services.py`: `_calcular_decrementos_pack_desde_componentes`, `ejecutar_opp_por_componentes`.
