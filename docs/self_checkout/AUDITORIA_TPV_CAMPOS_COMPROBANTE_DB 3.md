# Auditoría: Campos de comprobante TPV/Factura y persistencia en DB

## Objetivo

Verificar que **todos** los campos mostrados en la grilla "Comprobantes" (y usados en formularios TPV / FacturaA / FacturaB) se persisten correctamente en la base de datos al grabar una factura.

---

## 1. Mapeo grilla "Comprobantes" → tabla `cuentacliente`

La grilla de la lista de comprobantes (Lista_Comp_Fact, ConsultaComprobante) muestra facturas que provienen de la tabla **cuentacliente** (y JOIN con **cliente** para el nombre). Correspondencia:

| Columna en grilla | Campo en DB / origen | Tabla | ¿Se graba al emitir factura? |
|-------------------|----------------------|--------|-------------------------------|
| **Fecha** | `Fecha` | cuentacliente | ✅ TPV, FA, FB |
| **Comp** (Tipo comp) | `TipoComprobante` | cuentacliente | ✅ TPV, FA, FB |
| **Nro Comp** | `NroComprobante` | cuentacliente | ✅ TPV, FA, FB |
| **Cliente** | `cliente.nombre_cliente` (JOIN por `Codigo`) | cliente | ✅ Indirecto: `Codigo` se graba en cuentacliente |
| **Vencimiento** | `Vencimiento` | cuentacliente | ✅ TPV (por Cond. Venta), FA, FB |
| **Importe** | `ImporteVenta` | cuentacliente | ✅ TPV, FA, FB |
| **Cond Venta** | `CondVenta` (texto) + `id_condventa` | cuentacliente | ✅ TPV, FA, FB |
| **Estado** | `Estado` ("N/Canc" o "Canc") | cuentacliente | ✅ TPV, FA, FB |
| **Anul** | `anulado` ("Si" / "No") | cuentacliente | ✅ TPV, FA, FB (siempre "No" al grabar) |
| **Detalle** | `Detalle` | cuentacliente | ✅ TPV (si Detalle <> ""), FA, FB |
| **Observación interna** | `observacion_interna` | cuentacliente | ✅ FA, FB — ❌ **TPV no lo graba** |

---

## 2. Dónde se graba la factura (INSERT en cuentacliente)

- **TPV.frm**: al confirmar venta (factura FA/FB), bloque ~8987–9456: `rs_cuentacliente.AddNew` y asignación de campos.
- **FacturaA.frm**: al grabar factura desde pedido/remito/factura común, bloque ~4879–5229: `rs_cuentacliente.AddNew`.
- **FacturaB.frm**: idem, bloques ~5159–5516 y ~7992–8347: `rs_cuentacliente.AddNew`.

Todos escriben en **cuentacliente**; no se usa `comp_ped` para facturas ya emitidas (solo para PED/REM antes de facturar).

---

## 3. Campos que sí se guardan al grabar factura (resumen)

### 3.1 TPV.frm (factura FA/FB)

Se asignan, entre otros:

- **Cabecera**: `Fecha`, `TipoComprobante`, `NroComprobante`, `NroCompBusq`, `id_pv`, `Codigo` (cliente), `CodigoMovimiento`, `Detalle` (si `Detalle <> ""`).
- **Totales**: `ImporteVenta`, `ImporteVentaL`, `ImporteCobro`, `Saldo`, `Iva1`, `Iva2`, `Alicuota1`, `alicuota2`, `Exento`, `Subtotal1`, `Subtotal2`, `SubtotalGral`, `PorDesc1`, `ImpDesc1`, `ImpDesc2`, `SubTotalDesc1`, `SubTotalDesc2`, `SubtotalDesc`.
- **Condición de venta**: `CondVenta`, `id_condventa`.
- **Estado y vencimiento**: `anulado` = "No", `Estado` ("N/Canc" o "Canc"), `Vencimiento`, `Vencido`.
- **Usuario y sucursal**: `idUsuario`, `codSucursal`.
- **TPV**: `tpv_comp` = "Si", `tpv_importe_efectivo`, `tpv_importe_cheque`, `tpv_importe_tarjeta`, `tpv_importe_ctacte`, `tpv_nombre_ocasional`, `tpv_domicilio_ocasional`, `tpv_nro_identif_ocasional`, `tpv_cel_wp_ocasional`, `tpv_mail_ocasional`, `tpv_doc_cliente_ocasional`, etc.
- **Otros**: `ReciboMov`, `TipoFactura`, `codViajante`, `id_vendedor_asistente`, `comprobante_fiscal`, `impuesto_interno_total`, `total_percep`, `id_deposito_despacho`, `CotiDolar`, `total_costo`, `Monto_Devol`, `comp_supervisor`, `redondeo`, `tipo_redondeo`.

**No se asigna en TPV**: `observacion_interna`. TPV no tiene control de texto para "Observación interna" y no escribe ese campo en `cuentacliente`.

### 3.2 FacturaA.frm y FacturaB.frm

Incluyen todo lo anterior (según corresponda) y además:

- **Observación interna**: `observacion_interna` = valor del control `observacion_interna` (FacturaA línea ~5225, FacturaB ~5516 y ~8347).

En FA/FB sí existe el control y se persiste el campo.

---

## 4. Hallazgo: campo no persistido desde TPV

| Campo | Grilla Comprobantes | TPV al grabar factura | FacturaA / FacturaB |
|-------|---------------------|------------------------|----------------------|
| **observacion_interna** | Sí (columna "Observación interna") | ❌ No se guarda | ✅ Se guarda |

- En **TPV.frm** no existe referencia a `observacion_interna` (búsqueda en el .frm: 0 resultados).
- TPV solo dispone de **Detalle** (texto que se guarda en `Detalle`); no hay caja de texto para observación interna.
- Por tanto, las facturas emitidas desde **TPV** quedan con `observacion_interna` en NULL o valor por defecto en DB, aunque la grilla de comprobantes muestre esa columna.

---

## 5. Recomendaciones

1. **Unificar criterio con FA/FB**  
   Si el negocio requiere que las facturas del TPV también tengan observación interna:
   - Añadir en **TPV.frm** un control (por ejemplo `observacion_interna`) equivalente al de FacturaA/FacturaB.
   - Antes de `rs_cuentacliente.Update`, asignar:
     - `rs_cuentacliente.Fields!observacion_interna = observacion_interna.Text`  
     (o el nombre del control que se use), y manejar cadena vacía como `""` o `Null` según estándar del resto del módulo.

2. **Revisar en base de datos**  
   - Consultar `cuentacliente` para comprobantes con `tpv_comp = 'Si'` y verificar:
     - Que `Fecha`, `TipoComprobante`, `NroComprobante`, `Codigo`, `ImporteVenta`, `CondVenta`, `id_condventa`, `Estado`, `anulado`, `Vencimiento`, `Detalle` tengan los valores esperados.
     - Que `observacion_interna` sea NULL o vacío en facturas emitidas desde TPV y, si se implementa el punto 1, que se persista correctamente después del cambio.

3. **Documentar en CONTEXTO_TABLAS_VB6_INFORMES**  
   - En la sección de `cuentacliente`, dejar explícito que:
     - TPV hoy no graba `observacion_interna`.
     - FacturaA y FacturaB sí lo graban desde el control homónimo.

---

## 6. Condiciones de Vencimiento y Estado (TPV VB6)

En **TPV.frm** (líneas ~9371-9389) la lógica es:

### Estado

- **"Canc"** (cancelado = cobrado): cuando **no** hay cuenta corriente y **sí** hay efectivo y/o tarjeta y/o cheque.  
  `If (Total_Efectivo <> 0 Or Total_Tarjeta <> 0 Or Total_Cheque <> 0) And Total_CtaCte = 0 Then Estado = "Canc"`.
- **"N/Canc"** (no cancelado = pendiente de cobro): cuando hay monto en cuenta corriente.  
  `Else Estado = "N/Canc"`.

### Vencimiento

- Si **Estado = "Canc"** (todo contado): `Vencimiento = Fecha` (misma fecha de la factura).
- Si **Estado = "N/Canc"** (hay Cta Cte): se consulta `cond_venta.Dias` y `Vencimiento = Fecha + Dias`.

### Vencido

- Si `Vencimiento <= Principal.Fecha` → `Vencido = "Si"`.
- Si no → `Vencido = "No"`.

### Condición de venta (CondVenta / id_condventa)

- Solo efectivo → "Contado", id = 1  
- Solo tarjeta → "Tarjeta", id = 2  
- Solo cheque → "Cheque", id = 3  
- Solo Cta Cte → texto de la combo CV, id = CV.BoundText  
- Varios medios → "Multiple", id = 12  

**Self-Checkout (Synap)** paga con Mercado Pago = contado → debe grabar **Estado = "Canc"**, **Vencimiento = Fecha**, **Vencido = "No"**, **CondVenta = "Contado"**, **id_condventa = 1**.  

Los registros de `cuentacliente` con **Vencimiento**, **Estado** y **Cond Venta** vacíos en consulta suelen ser los creados por el **Self-Checkout** (Synap), porque el INSERT en `confirmation_service.py` no incluía esos campos. Se actualizó el INSERT para setearlos; a partir de esa corrección los nuevos comprobantes quedarán completos.

---

## 6.1 Viajante (vendedor) en TPV y Self-Checkout

### Cómo lo busca y guarda el TPV VB6

1. **Al abrir el TPV** (Form_Load, ~líneas 12800-12805): se asigna el vendedor del usuario logueado:
   - `Principal.id_vendedor_usr` = vendedor asociado al usuario en el sistema.
   - Se ejecuta: `SELECT * FROM viajantes WHERE anulado = 'No' AND CodViajante = Principal.id_vendedor_usr`.
   - Se setea `codViajante = rs_vendedor.Fields!codViajante` y se muestra el nombre en `Viajante.Caption`.

2. **Cambio manual**: el usuario puede elegir otro vendedor desde "Selección de vendedor" (ListaViajante); al elegir se setea `codViajante` y `cambio_vendedor = "Si"`.

3. **Al grabar la factura** (~líneas 9392, 6427): se persiste en `cuentacliente`:
   - `rs_cuentacliente.Fields!codViajante = codViajante`
   - Si hay asistente: `rs_cuentacliente.Fields!id_vendedor_asistente = CodViajante_Asistente`, si no `id_vendedor_asistente = 0`.

Resumen: el viajante en TPV viene del **usuario logueado** (`Principal.id_vendedor_usr`) o del que el usuario elige en pantalla, y ese valor se guarda en `cuentacliente.codViajante` (y opcionalmente `id_vendedor_asistente`).

### Self-Checkout (Synap)

- **Hoy no se guarda** `codViajante` ni `id_vendedor_asistente` en el INSERT de `confirmation_service.py`; esos campos quedan en NULL o valor por defecto en la base.
- La tabla `self_checkout_kiosk` **no tiene** campo de vendedor/viajante asignado al kiosco.

Opciones para paridad con TPV:

1. **Valor fijo para autoservicio**: usar un mismo `CodViajante` para todas las ventas del Self-Checkout (por ejemplo 0 o un viajante "Autoservicio" en `viajantes`) e incluirlo en el INSERT.
2. **Vendedor por kiosco**: agregar en `self_checkout_kiosk` una columna `id_viajante` (o `cod_viajante`) y, al confirmar, leerla y grabar ese valor en `cuentacliente.codViajante`.

---

## 7. Tabla `stock`: qué guarda TPV al facturar

Al confirmar una factura (FA/FB), el TPV VB6 y el Self-Checkout escriben movimientos en la tabla **stock** (un registro por ítem). Coinciden en lo mínimo necesario para salida de stock; el VB6 además guarda precios, descripción, vendedor, etc.

### 7.1 VB6 TPV (factura = salida)

En **TPV.frm** (flujo factura ~9494, 9652-9809) se hace `rs_stock.AddNew` y se asignan, entre otros:

| Campo | Valor |
|-------|--------|
| CodigoMovimiento | contador |
| IDArt | id artículo |
| Cantidad | cantidad × multiplicador (bulto/display) |
| **Entrada** | 0 (no se asigna; salida) |
| **Salida** | cantidad × multiplicador |
| CodDeposito | depósito del renglón |
| **TipoComp** | **"Venta TPV"** (tipo de movimiento) |
| **Comprobante** | TipoFactura (FA/FB) |
| NroComprobante | NroComp |
| Fecha, CodigoArticulo, Descripcion, PrecioVentaxU/R, PrecioCostoxU/R, … | del renglón |
| codViajante, codSucursal, idUsuario, Tipo, CodigoCP, anulado, … | cabecera/seguridad |
| visualiza_ensamble | 'No' en venta normal (ensamble en otro flujo) |

### 7.2 Self-Checkout (Django) — persistencia fiel al TPV VB6

En **confirmation_service.py** (paso 7) se hace un INSERT por ítem con **todos** los campos que el TPV VB6 asigna en el flujo de factura (venta), para que administraNET y procesos downstream no se rompan:

| Campo | Origen (TPV VB6: data_renglon_tpv / cabecera) |
|-------|--------|
| CodigoMovimiento, IDArt, Cantidad, Entrada (0), Salida, CodDeposito | contador, ítem, id_deposito |
| Fecha, CodigoArticulo, Descripcion | fecha, cart_item/articulo (id_manual, NombreArticulo) |
| **PrecioCostoxU** | articulo.PrecioCosto |
| **PrecioNetoxU** | (importe_total − importe_iva) / cant — neto unitario |
| **PrecioIVAxU** | importe_iva / cant |
| **PrecioBrutoxU** | PrecioNetoxU + PrecioIVAxU (bruto unitario) |
| **PrecioVentaxU** | precio_unitario (cart) o PrecioNetoxU |
| **PrecioCostoxR, PrecioNetoxR, PrecioIVAxR, PrecioBrutoxR, PrecioVentaxR** | costo×cant, neto renglón, importe_iva, bruto renglón, neto renglón |
| **Impdesc, Pordesc** | 0 (kiosk sin descuento; TPV: renglón.Impdesc, renglón.Pordesc) |
| **imp_alicuota_iva, imp_alicuota_iibb** | Porcentajes (21, 3.5), no importes. Origen: iva.Alicuota (o articulo.Alicuota si no hay iva), articulo.AlicuotaIB |
| Alicuota, AlicuotaIB | cart_item.alicuota_iva, articulo.AlicuotaIB |
| Saldo | stock_deposito.saldo tras el descuento |
| orden, CodViajante, CodLaboratorio, Detalle | cart_item.orden, kiosk.cod_viajante, articulo.CodLaboratorio, descripción |
| **TipoComp** | 'Venta Self Checkout' |
| **Comprobante** | tipo_comprobante (FA/FB — TPV: TipoFactura) |
| **NroComprobante** | PV-nro (0001-00000031) |
| **anulado** | 'No' (TPV: literal) |
| Tipo, CodigoCP, codSucursal | 'Cliente', id_cliente, id_sucursal |
| **idUsuario** | Usuario logueado: `session['user']['id_usuario']` (login); si no hay sesión, 0 (TPV: Principal.idUsuario) |
| TipoIVA | articulo.tipoIVA |
| Lista_Precio, promocion, promocion_por, promocion_tipo, promocion_cant | 1, 'No', 0, '', 0 |
| impuesto_interno, impuesto_interno_subtotal | 0, 0 |
| tipo_unidad, cantidad_unidad_display, cantidad_dividir | 'Unidad', 1, 1 |
| multiplicador_vta, multiplicador_comp, visualiza_ensamble, id_manual | 1, 1, 'No', articulo.id_manual |

**No se persisten desde kiosco** (por no existir en carrito/articulo o por ser flujos específicos VB6): NroPresupuesto, codmov_presupuesto, NroPedido, codmov_pedido, NroRemito, codmov_remito, id_stockp, serie, desc_serie, ensamblado, coti_dolar, id_cotizacion, id_lote, stock_lote_deposito. Esos campos quedan en NULL/0; el TPV los rellena cuando hay presupuesto/pedido/remito/lote/serie/ensamble.

### 7.3 Comparación real: registro Self-Checkout vs administraNET TPV

Comparando un registro de **stock** creado por Self-Checkout (CodigoMovimiento=62771) con uno del TPV administraNET (CodigoMovimiento=44631):

| Campo | Self-Checkout (62771) antes de alinear | TPV administraNET (44631) |
|-------|----------------------------------------|----------------------------|
| Fecha | vacío | 12/11/2025 |
| CodigoArticulo | vacío | 22.3.15 |
| Descripcion | vacío | Coony Collagen Eye Zone Mask |
| Tipo | vacío | Cliente |
| Comprobante | vacío | FB |
| TipoComp | vacío (registros antiguos) | Venta Self Checkout (nuevos) |
| NroComprobante | 1 (o vacío) | 0006-00000031 |
| CodSucursal / idUsuario / CodViajante | vacíos | 4, 34, 1 |
| Saldo | 0 | 1 (saldo en depósito tras salida) |
| Precios, Alicuota, TipoIVA, etc. | vacíos/0 | rellenados desde renglón |

Tras la alineación en código, los nuevos registros Self-Checkout rellenan todos esos campos: Fecha, CodigoArticulo, Descripcion, Tipo, Comprobante, TipoComp, NroComprobante, codSucursal, idUsuario (0), CodViajante, Saldo, precios (neto/bruto/IVA desde importe_total e importe_iva del ítem), Impdesc/Pordesc (0), imp_alicuota_iva/imp_alicuota_iibb, anulado ('No').

---

## 8. Alineación completa Self-Checkout: cuentacliente (confirmation_service.py)

El Self-Checkout graba en **cuentacliente** todos los campos que asigna el TPV VB6 al facturar (factura contado), con valores coherentes para pago con Mercado Pago (contado = tarjeta):

| Campo | Origen Self-Checkout |
|-------|----------------------|
| CodigoMovimiento, NroComprobante, NroCompBusq, TipoComprobante, Fecha | contador, talonarios, fecha |
| Codigo, CodSucursal, id_pv | id_cliente, id_sucursal, id_punto_venta |
| ReciboMov | 0 |
| ImporteVenta | total del carrito |
| ImporteVentaL | NULL (TPV usa “número a letras”) |
| ImporteCobro | NULL (contado) |
| Saldo | saldo actual del cliente (SELECT cliente.saldo) |
| Iva1, Iva2, Alicuota1, alicuota2, Exento | total−subtotal, 0, 21, 0, 0 |
| anulado | 'No' |
| Subtotal1, Subtotal2, SubtotalGral, PorDesc1, ImpDesc1, ImpDesc2 | subtotal, 0, total, 0, 0, 0 |
| SubTotalDesc1, SubTotalDesc2, SubtotalDesc | subtotal, 0, subtotal |
| idUsuario | 0 (kiosk) |
| TipoFactura | 'Sistema' |
| Detalle | '' |
| CondVenta, id_condventa | 'Contado', 1 |
| Vencimiento, Vencido, Estado | Fecha, 'No', 'Canc' |
| tpv_comp | 'Si' |
| tpv_importe_efectivo, tpv_importe_tarjeta, tpv_importe_cheque, tpv_importe_ctacte | 0, total, 0, 0 |
| tpv_mail_ocasional | email del carrito |
| codViajante | self_checkout_kiosk.cod_viajante |
| id_vendedor_asistente | 0 |
| impuesto_interno_total, total_percep | 0, 0 |
| id_deposito_despacho | id_deposito del carrito |
| CotiDolar, total_costo | 0, suma(costo×cant ítems) |

**No se graban desde Self-Checkout** (igual que TPV cuando no aplica): observacion_interna, comp_supervisor, comprobante_fiscal, tpv_nombre_ocasional, tpv_domicilio_ocasional, tpv_nro_identif_ocasional, tpv_cel_wp_ocasional, tpv_doc_cliente_ocasional, redondeo, tipo_redondeo (kiosk sin efectivo), tpv_cambio_efectivo, tpv_pago_efectivo, CotiDolar/TotalEfectivoD. **Monto_Devol** no se persiste (la columna no existe en la base actual). total_costo se calcula como suma de PrecioCosto×cantidad por ítem.

---

## 9. Resumen

- **cuentacliente**: el Self-Checkout persiste todos los campos que el TPV VB6 asigna al grabar una factura contado (ReciboMov, ImporteVenta, ImporteVentaL, ImporteCobro, Saldo, Iva1, Iva2, Alicuota1, alicuota2, Exento, Subtotal1/2/Gral, descuentos, idUsuario, TipoFactura, Detalle, CondVenta, id_condventa, Vencimiento, Vencido, Estado, tpv_*, codViajante, id_vendedor_asistente, impuesto_interno_total, total_percep, id_deposito_despacho, CotiDolar, total_costo), con valores coherentes para pago Mercado Pago (contado/tarjeta). Monto_Devol no se persiste (columna inexistente en la base).
- **stock**: al facturar, TPV VB6 graba TipoComp = "Venta TPV", Comprobante = FA/FB, etc. El Self-Checkout graba TipoComp = **"Venta Self Checkout"** para distinguir origen y está alineado en el resto de campos (Fecha, CodigoArticulo, Descripcion, Tipo, NroComprobante, precios, alícuotas, etc.) — véase §7.2.
- **Casi todos** los campos de la grilla "Comprobantes" se almacenan en `cuentacliente` y se rellenan al grabar la factura desde TPV, FacturaA, FacturaB o Self-Checkout.
- La única diferencia relevante es **observacion_interna**: se guarda desde FacturaA/FacturaB y **no** desde TPV ni Self-Checkout, por falta de control en TPV y de uso en kiosk.
