# Cajas de preparación antes del control de salida

## Circuito

`Pedido_prep.frm` agrupa pedidos en `ped_prep.CodigoMovimiento_prep`. En
`Stock_Control_Cajas_Deposito_Prep.frm`, administraNET lee los artículos de
`stockp` por pedido, arma cajas y después genera remitos. El nuevo paso de
Synap ocurre **antes** de ese control y no afecta existencias, pedidos ni
remitos.

1. El operario selecciona una preparación existente de administraNET.
   La lista y el encabezado muestran tanto el número de comprobante como
   `CodigoMovimiento_prep`; este último es el código que se ingresa en el
   control de salida de VB6 y también figura en el resumen final.
   Synap la reserva para esa sesión: otra sesión no puede abrir cajas ni
   registrar o corregir lecturas de la misma preparación. La pantalla renueva
   la reserva mientras permanece abierta. **Terminar y liberar** la entrega a
   otro operario; si la sesión desaparece, la reserva vence a los 5 minutos.
2. Ve los artículos pendientes de cada pedido y sucursal.
3. Abre una caja; el número comienza en 1. Mientras haya cajas vigentes, la
   numeración sigue creciendo. Si se eliminan todas, la próxima vuelve a ser
   la caja 1. La caja toma el cliente y domicilio del pedido origen.
4. Cada lectura de código asigna el artículo al primer pedido compatible del
   mismo destino que tenga cantidad pendiente suficiente. Se muestran los
   faltantes en tiempo real, junto al escáner y por artículo. Las lecturas
   activas de otras preparaciones del mismo pedido también descuentan el
   disponible, para no volver a preparar un parcial ya puesto en cajas.
   El campo del escáner se vacía al enviar cada código, incluso si la lectura
   es rechazada, y recupera el foco mientras la caja siga disponible para leer.
   Una caja puede contener varios pedidos solo si
   son del mismo cliente y sucursal/domicilio.
5. Puede deshacer lecturas, cerrar incluso una caja vacía abierta por error y
   reabrir cajas mientras no hayan sido importadas en el control de salida.
   En una caja abierta, **Eliminar artículo** anula todas sus lecturas activas
   en esa caja y devuelve las unidades al pendiente; las lecturas anuladas
   permanecen en el historial.
   La pantalla señala una caja vacía cerrada como vacía. También puede eliminar
   una caja abierta o cerrada sin lecturas activas. La caja queda anulada y
   desaparece de la vista, pero se conservan su número histórico, ID interno y
   lecturas anuladas para trazabilidad. Ese número puede volver a utilizarse
   cuando no queda ninguna caja vigente de la preparación.
6. El operario escribe el número grande `1`, `2`, etc. en cada caja física.

Si faltan artículos por falta de stock, el operario puede cerrar las cajas con
contenido igualmente. El resumen indica **armado parcial**, las unidades
guardadas y el saldo no preparado por artículo. Ese saldo se debe conservar
pendiente en el control de salida de administraNET. Si todas las unidades se
leyeron pero hay cajas abiertas, la pantalla pide cerrarlas; muestra un solo
aviso de estado arriba. El resumen queda listo para usar con el código de
movimiento y números de caja cuando todas las cajas con contenido están
cerradas. Synap no modifica `stockp` ni el pendiente del pedido en este paso.

La pantalla está en **Stock → Armado de cajas** y funciona tanto en escritorio
como en la PWA móvil, en `/stock/preparacion-cajas/`. Requiere el permiso
`stock.preparacion_cajas`, visible bajo **Stock** en la asignación de permisos
por puesto. Un puesto con solo este permiso puede entrar desde el menú Stock;
un puesto sin él no ve la entrada ni puede abrir la página o su API. En móvil,
el acceso principal de Stock abre una pantalla permitida por ese puesto, no
Ingreso Mov. Stock.

El permiso se guarda en el catálogo `synap_permiso` de **cada base de empresa**.
Con `SYNAP_PERMISOS_SOURCE=synap` (o `dual` durante la transición), activar
el permiso para un puesto controla el acceso efectivo de sus usuarios. Si
`SYNAP_AUTO_ENSURE_SCHEMA=True`, la apertura de la pantalla de permisos
siembra los permisos nuevos aunque siga viva la caché de una versión anterior.
Si está desactivado, un administrador de la base debe sembrar el catálogo
antes de asignar el permiso; `apply_synap_permisos_tables <base_empresa>`
incluye esa siembra y requiere permisos de DDL.

La base de datos de cada empresa debe recibir el
proveedor `stock_prep_cajas_synap` de la herramienta global de migración MySQL.
También se puede aplicar por empresa desde el contenedor de Synap:

```bash
docker exec Synap_app python manage.py apply_stock_prep_cajas administranet1
```

El comando usa el mismo proveedor que la pantalla y falla con código distinto
de cero si MySQL rechaza el cambio. Ejecutarlo primero sobre la base de prueba;
la empresa productiva se actualiza después de validar el circuito.
La cuenta MySQL usada por `Synap_app` necesita permisos `CREATE` y, si ya
existían cajas con el esquema anterior, `ALTER`. Si la cuenta de aplicación
solo tiene permisos de operación, un DBA debe ejecutar el proveedor con una
cuenta DDL o aplicar `stock/sql/003_prep_cajas_synap.sql` y comprobar la
columna generada `numero_caja_vigente` en `synap_prep_caja`. Para una tabla
preexistente sin esa columna también hace falta el `ALTER` que figura en
`run_stock_prep_cajas_mysql`.

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
- La pantalla inicia en modo **Display**; el operador puede cambiar a **Unidad**
  antes de escanear. En Unidad,
  el código unitario suma 1; en Display suma `cantidad_unidad_display` de
  `articulo_prov` (por ejemplo, 6 unidades en Best Sox). Los códigos propios
  de display/bulto conservan su factor y el `333` conserva su cantidad. Cada
  lectura se valida contra el faltante antes de guardarse.

## Tablas y puente futuro con VB6

Las cuatro tablas nuevas de `stock/sql/003_prep_cajas_synap.sql` conservan
secuencia, cabecera de caja y lecturas, incluido el código leído, unidades,
pedido, línea `stockp`, usuario y fecha. `idempotency_key` impide duplicar un
escaneo reenviado por la red. Deshacer marca la lectura anulada: no la borra.
La reserva del operador vive en `synap_prep_caja_reserva`; cada operación de
escritura valida la sesión bajo el mismo bloqueo transaccional de numeración.
`numero_caja_vigente` impone unicidad solo para cajas no anuladas. El ID interno
`id_caja` distingue una caja histórica anulada de una nueva que reutiliza su
número visible después de comenzar de cero.

La futura opción **Control en el lugar** de VB6 recibirá
`CodigoMovimiento_prep` y `numero_caja`, leerá solamente cajas `Cerrada` con
al menos una lectura no anulada, y revalidará pedido, destino y pendiente antes de
registrarlas en `stock_control_caja` y `stock_control_caja_detalle`. En la
misma transacción vinculará `id_stock_control` y `fecha_importacion` y pasará
la caja a `Importada`; un segundo intento no volverá a registrar lecturas.
La generación de remitos, etiquetas finales y trazabilidad posterior seguirá
en el circuito VB6 existente.

Hasta implementar ese puente, estas cajas son una **preparación física
registrada en Synap** y no equivalen a cajas cerradas del control de salida.
