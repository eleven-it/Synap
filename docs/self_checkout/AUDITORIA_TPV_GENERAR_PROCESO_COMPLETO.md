# Auditoría: proceso "Generar" TPV administraNET vs Synap Self-Checkout

Objetivo: que el flujo de confirmación en Synap respete **en forma literal** las operaciones INSERT/UPDATE del TPV VB6 al generar una factura (Guardar_Factura), para paridad funcional y de datos.

---

## 1. Orden literal de operaciones en VB6 (Guardar_Factura — Factura)

Referencia: `administranet_vb6/Formularios/TPV.frm`, sub `Guardar_Factura` (aprox. líneas 8371–10320).

| # | Operación | Tabla | Sentencia / Acción | Líneas ref. |
|---|-----------|--------|--------------------|-------------|
| 1 | **UPDATE** | `codmov` | `CodigoMovimiento = contador` (contador = CodigoMovimiento + 1, o +2 si activ_contabilidad) WHERE codigo = 1. En un bloque transaccional previo. | ~8371, codmov |
| 2 | **UPDATE** | `talonarios` | `Nro = ContadorComp` (ContadorComp = Nro + 1) WHERE id_punto_venta = ? AND TipoComprobante = ? (FA/FB/FC/FM). Tras abrir rs_nro_fact por PV y tipo. | 8604–8642, 8785, 8825, 8891, 8980 |
| 3 | **INSERT** | `cuentacliente` | AddNew + asignación de todos los campos (Fecha, TipoComprobante, NroComprobante, NroCompBusq, id_pv, Codigo, Saldo, ImporteVenta, ImporteVentaL, ImporteCobro, Iva1, Iva2, Subtotal*, PorDesc*, ImpDesc*, CondVenta, id_condventa, tpv_importe_efectivo, tpv_pago_efectivo, tpv_cambio_efectivo, tpv_importe_tarjeta, tpv_importe_cheque, tpv_importe_ctacte, Estado, Vencimiento, Vencido, tpv_comp, etc.) + Update. | 8992–9454 |
| 4 | **UPDATE** | `cliente` | Solo si `Codigo_Cliente <> 1` y `Total_CtaCte <> 0`: Saldo = rs_cuentacliente.Saldo, fecha_ultima_compra = Fecha WHERE codigo = Codigo_Cliente. | 9044–9050 |
| 5 | **UPDATE** + **INSERT** | `caja_saldo`, `caja` | Si Total_Efectivo <> 0: UPDATE caja_saldo SET Saldo = Saldo + Total_Efectivo (± redondeo) WHERE id_caja = Principal.id_caja; INSERT caja (Tipo = 'Factura Contado TPV', nro_comprobante, ingreso, Fecha, id_usuario, cod_sucursal, Moneda, etc.). | 9207–9242, 9246–9305 |
| 6 | **UPDATE** + **INSERT** (por ítem) | `stock_deposito`, `stock` | Por cada renglón: UPDATE stock_deposito SET Saldo = Saldo - (Cantidad × cantidad_multiplicar); INSERT stock (Fecha, CodigoArticulo, Descripcion, TipoComp = 'Venta TPV', Comprobante, NroComprobante, precios, alícuotas, CodigoMovimiento, etc.). Si lote: UPDATE Lote. Si pedido: UPDATE stockp (saldo_pedido_cliente, remitido_facturado, etc.). | 9494–9905 |
| 7 | **UPDATE** | `cuerpostock` | `codigomovimiento = contador` WHERE Codusuario = Principal.idUsuario AND visualiza = 'No'. | 10241 |
| 8 | **INSERT** + **UPDATE** | `serie_salida`, `serie_entrada` | GuardarSerie: INSERT serie_salida; UPDATE serie_entrada SET disponible = 'No' para series usadas. | GuardarSerie |
| 9 | **INSERT** (si cheque) | `chequetercero`, `caja_saldo`, `caja` | Por cada cheque: INSERT chequetercero; UPDATE caja_saldo (caja cheque); INSERT caja (tipo cheque). | 9967–10012 |
| 10 | **INSERT** (si Cta Cte) | `recibo_factura` | Si (Condición <> Contado/Cheque/Tarjeta) y Total_CtaCte <> 0: INSERT recibo_factura (Fecha, TipoComprobante, Importe, cancelado, Saldo, NroComprobante, CodigoMovimiento, Codigo, Vencimiento, etc.). | 10016–10048 |
| 11 | **INSERT** (si tarjeta) | `tc_comprobante`, `caja_saldo`, `caja` | Por cada cupón en data_tarjeta_temp: INSERT tc_comprobante; UPDATE caja_saldo (id_caja_tarjeta); INSERT caja (tipo Tarjeta). | 10054–10100+ |
| 12 | **UPDATE** + **INSERT** (si pedido) | `comp_ped`, `ped_fact` | Si Comprobante_Pedido: UPDATE comp_ped Estado; INSERT ped_fact. | (en bloque pedido) |
| 13 | **—** | (asiento) | Si activ_contabilidad y conta_pv: generar_asiento_cont. | 10254–10264 |
| 14 | **—** | (puntos) | Actualiza_Puntos_SP, Actualiza_Puntos_PD (y canje/voucher). | 10269–10305 |
| 15 | **INSERT** | `resumen_venta_cv` | Guardar_resumen_venta_cv: INSERT resumen_venta_cv (Fecha, id_cliente, codigo_movimiento, tipo_comp, Comprobante = 'Factura TPV', importe_neto, nro_comprobante, importe_iva_1/2, importe_percep, importe_impuesto_interno, Importe_Interes, importe_exento, importe_total, Total_Efectivo, Total_CtaCte, Total_Tarjeta, Total_Cheque, id_cv). | 10311–10314, 39042–39108 |

---

## 2. Orden literal de operaciones en Synap (ConfirmationService.confirmar)

Referencia: `self_checkout/services/confirmation_service.py`.

| # | Operación | Tabla | Sentencia / Acción |
|---|-----------|--------|--------------------|
| 0 | Idempotencia | `self_checkout_cart`, `cuentacliente` | SELECT estado, codigo_movimiento, id_cuentacliente; si confirmado, devolver sin duplicar. |
| 1 | Revalidar stock | `stock_deposito` | Por ítem: UPDATE stock_deposito SET saldo = saldo - cantidad WHERE ... AND disponible >= cantidad. |
| 2 | **UPDATE** | `codmov` | UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1 (contador = CodigoMovimiento + 1). |
| 3 | **UPDATE** | `talonarios` | UPDATE talonarios SET Nro = Nro + 1 WHERE id_punto_venta = ? AND TipoComprobante = ?. |
| 4 | **INSERT** | `cuentacliente` | INSERT con todos los campos alineados a TPV (CodigoMovimiento, NroComprobante, NroCompBusq, TipoComprobante, Fecha, Codigo, id_pv, ReciboMov, ImporteVenta, Saldo, Iva1, Iva2, Subtotal*, PorDesc*, tpv_*, etc.). |
| 5 | **INSERT** (por ítem) | `stock` | Por ítem: INSERT stock (TipoComp = 'Venta Self Checkout', Comprobante, NroComprobante, CodigoMovimiento, precios, alícuotas, etc.). Opcional: serie_movimiento INSERT + serie_entrada UPDATE. |
| 6 | **INSERT** | `resumen_venta_cv` | INSERT resumen_venta_cv (Factura TPV: Fecha, id_cliente, codigo_movimiento, tipo_comp, Comprobante = 'Factura TPV', importe_neto, nro_comprobante, importe_iva_1/2, importe_total, Total_Efectivo, Total_Tarjeta, etc.). |
| 7 | **UPDATE** | `self_checkout_cart` | estado = 'confirmado', codigo_movimiento, id_cuentacliente, tipo_comprobante, id_cliente, email, confirmed_at. |
| 8 | **INSERT** | `self_checkout_audit_log` | Trazabilidad (cart_id, accion 'confirmado', detalle JSON). |
| 9 | **UPDATE** (post-commit FE) | `cuentacliente` | Si FE: UPDATE fe_cae, fe_vto_cae, fe_comp, fe_transmitido, fe_regimen_tipo WHERE id_cuentacliente = ?. |
| — | **UPDATE** + **INSERT** | `caja_saldo`, `caja` | Dentro de confirmar (transacción atómica): write_caja_ingreso_with_cursor para efectivo ('Factura Contado TPV') y/o tarjeta ('Tarjeta'). |

Nota: En Synap el **stock_deposito** se actualiza una sola vez por ítem en el paso 1 (revalidar); no se vuelve a tocar en el paso 5 (solo INSERT stock). Esto es equivalente al TPV (una vez descontado por ítem).

---

## 3. Correspondencia tabla por tabla (INSERT/UPDATE)

| Tabla | VB6 (Generar Factura) | Synap (confirmar) | Coincide / Observación |
|-------|------------------------|-------------------|-------------------------|
| **codmov** | UPDATE CodigoMovimiento WHERE codigo = 1 (+2 si activ_contabilidad) | UPDATE idem; lee activ_contabilidad de configuracion, usa +2 si 'Si' | Sí. |
| **talonarios** | UPDATE Nro = Nro+1 por id_pv y TipoComprobante | UPDATE Nro = Nro + 1 id_punto_venta, TipoComprobante | Sí. |
| **cuentacliente** | INSERT (AddNew + Update) con todos los campos TPV | INSERT con campos alineados (ver AUDITORIA_TPV_CAMPOS_COMPROBANTE_DB.md) | Sí. ImporteVentaL = NULL en Synap (TPV usa ESCRITO). |
| **cliente** | UPDATE Saldo, fecha_ultima_compra si CtaCte | No | Solo TPV cuando Total_CtaCte <> 0. Self-Checkout no usa CtaCte; no aplica. |
| **caja_saldo** | UPDATE Saldo += efectivo (y por cheque/tarjeta) | write_caja_ingreso_with_cursor dentro de confirmar | Sí (dentro de la misma transacción). |
| **caja** | INSERT (efectivo, cheque, tarjeta según medios) | write_caja_ingreso_with_cursor (efectivo 'Factura Contado TPV' y/o tarjeta) | Sí (dentro de la misma transacción). |
| **stock_deposito** | UPDATE Saldo -= cantidad por ítem | UPDATE saldo -= cantidad en revalidación (por ítem) | Sí. |
| **stock** | INSERT por ítem (TipoComp 'Venta TPV') | INSERT por ítem (TipoComp 'Venta Self Checkout') | Sí (origen diferenciado por tipo). |
| **Lote** | UPDATE si artículo con lote | No (opcional si se implementa series/lotes en kiosk) | Solo si TPV usa lote; kiosk puede no tener lotes. |
| **stockp** | UPDATE si ítem viene de pedido | No | Solo cuando hay pedido; kiosk sin pedidos. |
| **cuerpostock** | UPDATE codigomovimiento = contador | No | TPV usa cuerpostock como renglones temporales de la venta; Synap usa self_checkout_cart_item. No aplica. |
| **serie_salida** / **serie_entrada** | GuardarSerie: INSERT serie_salida, UPDATE serie_entrada | INSERT serie_movimiento; UPDATE serie_entrada (si hay serie en ítem) | Sí cuando el ítem tiene serie. |
| **chequetercero** | INSERT si Total_Cheque <> 0 | No | Kiosk no cobra con cheque. |
| **recibo_factura** | INSERT si Total_CtaCte <> 0 | No | Kiosk no vende en CtaCte. |
| **tc_comprobante** | INSERT por cupón tarjeta | No | TPV guarda cada cupón; Synap solo total en cuentacliente (tpv_importe_tarjeta). Opcional añadir 1 fila “Mercado Pago” si se requiere paridad de reportes. |
| **comp_ped** / **ped_fact** | UPDATE/INSERT si Comprobante_Pedido | No | Kiosk sin pedidos. |
| **resumen_venta_cv** | INSERT (Guardar_resumen_venta_cv) | INSERT (Factura TPV) | Sí; implementado para paridad literal. |
| **asiento contable** | generar_asiento_cont | No | Contabilidad no integrada en Synap. |
| **puntos / voucher** | Actualiza_Puntos_SP, Actualiza_Puntos_PD | marcar_voucher_usado (post-commit) | Parcial; voucher PD cubierto; SP no. |

---

## 4. Resumen de diferencias y literalidad

- **Respeto literal:** codmov, talonarios, cuentacliente (campos principales), stock_deposito, stock, resumen_venta_cv (desde esta auditoría), series (cuando aplica).
- **Caja dentro de transacción:** caja_saldo y caja se actualizan dentro de `confirmar` (write_caja_ingreso_with_cursor) antes del commit; si falla caja → rollback completo (paridad administraNET).
- **No aplican en Self-Checkout:** cliente (solo CtaCte), recibo_factura, chequetercero, comp_ped/ped_fact, cuerpostock, stockp/Lote (salvo que se implemente pedido/lotes en kiosk).
- **Opcional para paridad de reportes:** tc_comprobante (una fila por venta tarjeta “Mercado Pago” si se desea consistencia con reportes que lean esa tabla).
- **No implementado:** generar_asiento_cont, Actualiza_Puntos_SP (puntos de programa SP).

---

## 5. Consultas literales de referencia (VB6)

- **codmov:**  
  `UPDATE codmov SET CodigoMovimiento = <contador> WHERE codigo = 1`

- **talonarios:**  
  `UPDATE talonarios SET Nro = <ContadorComp> WHERE id_punto_venta = <id_pv> AND TipoComprobante = '<FA|FB|FC|FM>'`  
  (ContadorComp = valor actual de Nro + 1)

- **cuentacliente:**  
  INSERT con columnas según TPV.frm ~8992–9454 (ver AUDITORIA_TPV_CAMPOS_COMPROBANTE_DB.md).

- **resumen_venta_cv (Factura TPV):**  
  INSERT con: Fecha, id_cliente, codigo_movimiento, tipo_comp, Comprobante = 'Factura TPV', importe_neto, nro_comprobante, importe_iva_1, importe_iva_2, importe_percep, importe_impuesto_interno, Importe_Interes, importe_exento, importe_total, id_cv, Total_Efectivo, Total_CtaCte, Total_Tarjeta, Total_Cheque (y los que existan en la tabla).

---

## 6. Cambios realizados en Synap (mitigaciones auditoría)

- **INSERT `resumen_venta_cv`** en `ConfirmationService.confirmar` (Factura TPV).
- **codmov +2** cuando `configuracion.activ_contabilidad = 'Si'`.
- **Caja dentro de transacción:** `write_caja_ingreso_with_cursor` se ejecuta dentro de `confirmar` antes del commit; si falla caja → rollback completo.
- **INSERT `tc_comprobante`** cuando `tpv_imp_tarjeta > 0` (una fila 'Mercado Pago' por venta tarjeta).
- **resumen_venta_cv:** log WARNING en fallo (visibilidad en monitoreo).
- Eliminadas llamadas redundantes a `write_caja_ingreso` en `api_views` y `self_checkout_confirm_pending` (caja ya se registra en `confirmar`).

Documento generado para cumplir con el requisito de respetar en forma literal las consultas INSERT/UPDATE del proceso "Generar" del TPV en Synap.
