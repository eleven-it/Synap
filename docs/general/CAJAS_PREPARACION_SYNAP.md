# Cajas de preparación antes del control de salida

## Circuito

`Pedido_prep.frm` agrupa pedidos en `ped_prep.CodigoMovimiento_prep`. En
`Stock_Control_Cajas_Deposito_Prep.frm`, administraNET lee los artículos de
`stockp` por pedido, arma cajas y después genera remitos. El nuevo paso de
Synap ocurre **antes** de ese control y no afecta existencias, pedidos ni
remitos.

1. El operario selecciona una preparación existente de administraNET.
2. Ve los artículos pendientes de cada pedido y sucursal.
3. Abre una caja; el número comienza en 1 y nunca se reutiliza dentro de la
   misma preparación. La caja toma el cliente y domicilio del pedido origen.
4. Cada lectura de código asigna el artículo al primer pedido compatible del
   mismo destino que tenga cantidad pendiente suficiente. Se muestran los
   faltantes en tiempo real. Una caja puede contener varios pedidos solo si
   son del mismo cliente y sucursal/domicilio.
5. Puede deshacer lecturas, cerrar y reabrir cajas mientras no hayan sido
   importadas en el control de salida.
6. El operario escribe el número grande `1`, `2`, etc. en cada caja física.

La pantalla está en **Stock → Cajas de preparación**. Requiere el permiso
`stock.preparacion_cajas`. La base de datos de cada empresa debe recibir el
proveedor `stock_prep_cajas_synap` de la herramienta global de migración MySQL.

## Fuente VB6 y reglas de paridad

- `Pedido_prep.frm`: `CodigoMovimiento_prep` agrupa `ped_numeracion`.
- `Stock_Control_Cajas_Deposito_Prep.frm`: `Carga_Datos_List_Pedido_Prep`
  obtiene el pendiente efectivo; `ResolverDestinoAutomaticoPrep` elige por
  orden de grilla el primer pedido y caja compatibles.
- `ControlSalidaPrepCajas.bas`: caja abierta/cerrada, serialización del número
  y validación del pendiente antes de cada lectura.
- El domicilio se compara primero por `id_cliente_domicilio`; cuando falta
  en alguno de los pedidos, se compara el texto normalizado. Clientes o
  sucursales distintos nunca comparten caja.
- El código `333` contiene ID de artículo y cantidad; display y bulto se
  convierten con `articulo_prov`. Los artículos con lote o serie solo se leen
  por unidad. Los códigos `334` de caja de stock no forman parte de este paso.

## Tablas y puente futuro con VB6

Las tres tablas nuevas de `stock/sql/003_prep_cajas_synap.sql` conservan
secuencia, cabecera de caja y lecturas, incluido el código leído, unidades,
pedido, línea `stockp`, usuario y fecha. `idempotency_key` impide duplicar un
escaneo reenviado por la red. Deshacer marca la lectura anulada: no la borra.

La futura opción **Control en el lugar** de VB6 recibirá
`CodigoMovimiento_prep` y `numero_caja`, leerá solamente cajas `Cerrada` y
lecturas no anuladas, y revalidará pedido, destino y pendiente antes de
registrarlas en `stock_control_caja` y `stock_control_caja_detalle`. En la
misma transacción vinculará `id_stock_control` y `fecha_importacion` y pasará
la caja a `Importada`; un segundo intento no volverá a registrar lecturas.
La generación de remitos, etiquetas finales y trazabilidad posterior seguirá
en el circuito VB6 existente.

Hasta implementar ese puente, estas cajas son una **preparación física
registrada en Synap** y no equivalen a cajas cerradas del control de salida.
