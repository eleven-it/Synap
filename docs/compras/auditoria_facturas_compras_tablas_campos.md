# Auditoría: Facturas de compras — Tablas y campos

**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

**Nota metodológica:** Los tipos SQL exactos deben contrastarse con el DDL MySQL del cliente (`docs/general/tablas` o dump). Aquí se documenta **uso en VB6** (lectura / cálculo / escritura) con referencia a procedimiento y asignación.

---

## Resumen de tablas por rol

| Tabla | Rol funcional | Momento | Operaciones |
|-------|---------------|---------|-------------|
| **codmov** | Numerador global de movimientos | Inicio transacción 1 | SELECT pessimistic, UPDATE `CodigoMovimiento` |
| **cuentaproveedor** | Cabecera comprobante proveedor (FA/FB/FC/FM, totales, CAI, estado) | Tras obtener `contador` | INSERT vía AddNew |
| **proveedor** | Maestro proveedor; saldo CC | Junto a cabecera | SELECT saldo; UPDATE `saldo` |
| **cond_venta** | Condición compra (días, texto) | Antes/asignación cabecera | SELECT por código (DataCV); en `Guardar` refresh explícito |
| **en_vale_factura** | Relación vale–factura | Tras preparar cabecera | INSERT…SELECT desde temp |
| **en_vale_factura_temp** | Buffer vales por usuario | Validación Factura Vale; origen datos | SELECT; *no borrado explícito en fragmento Guardar analizado* |
| **en_vale_viaje** | Estado del vale | Tras insert relación | UPDATE `estado='En Factura'` |
| **percep_prov_temp** | Percepciones IB en edición | Si `PercepIB <> 0` | SELECT loop |
| **percep_prov** | Percepciones IB persistidas | Mismo bloque | AddNew/Update |
| **percepcion_prov_convenio** | Percepciones por convenio | Mismo bloque | AddNew/Update |
| **caja_saldo** | Saldo por caja/moneda | Contado (`Dias = "0"`) | SELECT, UPDATE `Saldo`, `id_usuario` |
| **caja** | Movimiento de caja | Contado | AddNew (plantilla `codigo_movimiento = 1`) |
| **stock** | Renglones de compra | Loop ítems | AddNew/Update |
| **stock_deposito** | Saldo por artículo/depósito | Por ítem según reglas | SELECT, UPDATE (o no, si no entrega stock) |
| **stockp** | Líneas de OC pendientes | Si hay OC y no es solo remito-factura | SELECT, UPDATE `cantidad_pendiente`, `remitido_facturado` |
| **otro_egreso** | Imputación de gasto en renglón | Si `Codgasto <> 0` | AddNew/Update |
| **lote** / **lote_stock** | Trazabilidad por lote | Si aplica por artículo | SELECT/AddNew/Update + `last_insert_id()` |
| **articulo** | Maestro artículo | Lista compra / proveedor por artículo | UPDATE costos, listas, `codigoProveedor` |
| **iva** | Alícuota | Cálculo actualización precios | SELECT |
| **precios_historial** | Historial de precios | Si `actualiza_lista_compra` | AddNew/Update |
| **op_factura** | Documento a pagar (crédito) | Post ítems | AddNew si `Dias <> "0"` |
| **op_factura_par** | *Solo en modificación* | `modificacion_comp` | UPDATE fechas/número |
| **cuerpostockp** | Buffer grilla usuario | Validaciones; limpieza | SELECT; DELETE en `Elimina_Temporal` / borrado renglón |
| **oc_factp** | Vínculo factura–OC | Tras ítems | AddNew |
| **remp_factp** | Vínculo factura–remito | Factura Remito | AddNew |
| **cuentaproveedor** (OC/REM) | Estado OC o remito | UPDATE `Estado` / `estado_remito` | UPDATE |
| **serie_entrada_temp** | Series en edición | Validación / GuardarSerie | DELETE en `Elimina_Temporal` |
| **serie_entrada** | Series definitivas | Post stock | INSERT…SELECT |
| **serie_movimiento** | Movimiento serie–compra | Post serie_entrada | INSERT…SELECT JOIN stock |
| **periodos** / **years** | Período fiscal abierto | Antes de grabar / modificar | SELECT |
| **configuracion** | Flag contabilidad | `generar_asiento_cont` | SELECT `activ_contabilidad` |
| **cont_paramatriz** | Plan de cuentas parametrizado | Armado matriz asiento | SELECT por `id_paramatriz` |
| **cont_pc** | Plan de cuentas | Saldos y naturaleza | SELECT |
| **gastos** | Centro costo gasto | Si ítem es gasto | SELECT `id_pc` |
| **cont_ejercicio** | Ejercicio + nro asiento | Asiento | SELECT/UPDATE `Nro_asiento_ejercicio` |
| **cont_periodo** | Período activo | Asiento | SELECT |
| **cont_asiento** | Líneas de asiento | Asiento | AddNew/Update |
| **cont_ejercicio_saldo_cta** | Saldo por cuenta/ejercicio | Por línea asiento | SELECT/UPDATE |
| **cont_periodo_saldo_cta** | Saldo por cuenta/período | Por línea asiento | SELECT/UPDATE |
| **caja_abm** | Maestro caja (para asiento contado) | `generar_asiento_cont` | SELECT |
| **imputacion_p** | *Solo modificación* | `modificacion_comp` | UPDATE fechas ref. NC/OP |

**Sin nombre explícito «libro_iva» en PFactura:** totales e alícuotas viven en `cuentaproveedor`/`stock`; exportaciones AFIP en otros formularios. *Inferencia fuerte.*

---

## 1. cuentaproveedor (cabecera factura compra)

**Clave lógica:** `CodigoMovimiento` = `contador` (desde `codmov`). *Confirmado por asignación `Fields!CodigoMovimiento = contador`.*

### Campos asignados en `Guardar` (evidencia `PFactura.frm` ~3792–4183)

| Campo | Uso | Origen |
|-------|-----|--------|
| Fecha, FechaRegistro | Escritura | Controles `Fecha`, `FechaRegistro` |
| TipoComprobante | Escritura | FA / FB / FC / FM según `Tipo_Factura` |
| NroComprobante, NroCompBusq | Escritura | `num` formateado, `Nro.Text` |
| Detalle | Escritura | `Detalle.Text` |
| Saldo | Escritura / cálculo | Proveedor actual + `ImporteTotal` si crédito; si contado, igual a saldo proveedor sin sumar |
| OPMov | Escritura | `0` |
| ImporteCompra | Escritura | `ImporteTotal` |
| ImportePago | Escritura | `Null` |
| Iva1–3, Alicuota1, alicuota2, Alicuota3 | Escritura | Labels/cálculos UI |
| PercepIB, PercepGan, PercepIVA, OtrosImp | Escritura | Variables UI |
| NroCAI, FechaCAI | Escritura | Variables cargadas desde proveedor en `CargaComprobantesP` |
| idUsuario | Escritura | `Principal.idUsuario` |
| codSucursal | Escritura | `id_sucursal` o `Principal.codSucursal` |
| TipoFactura | Escritura | Texto según `TipoComprobante` (Factura / Factura Remito / Factura OC) |
| Exento | Escritura | `Exento` |
| anulado | Escritura | `"No"` |
| Codigo | Escritura | `CodigoProv` |
| CodBanco | Escritura | `2` (comentario: campo en blanco) |
| Subtotal1–3, SubtotalGral, impuestos desc., SubTotalDesc*, SubtotalDesc | Escritura | UI |
| CondCompra, id_condcompra | Escritura | `CV.Text`, `DataCV.Recordset.Fields!Codigo` |
| impuesto_interno, sobretasa_iva | Escritura | Variables |
| Estado | Escritura | `Canc` contado / `N/Canc` crédito |
| Vencimiento, Vencido | Escritura | `VencFact` vs `FechaActual` |
| ID_Proyecto | Escritura | Si `activ_proyecto` |
| remite_factura_art, estado_fact_remito | Escritura | Combinación `Principal.remite_factura_art`, `TipoComprobante`, combo usuario |
| CotiDolar | Escritura | `Cotizacion_Dolar` |

---

## 2. stock (detalle)

**Patrón:** `rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = 1"` → `AddNew` por cada fila de `CuerpoStock.Recordset` (~4193–4643).

**Inventario exhaustivo de asignaciones a `rs_stock.Fields!…`:** ver **Anexo A** (extraído línea a línea de `Private Sub Guardar`, `PFactura.frm` ~4207–4643).

**Regla condicional (entrada física):** si existe fila en `stock_deposito` y se cumplen permisos `remite_factura_art` / `TipoComprobante <> "Factura Remito"`, se actualiza depósito y se copia **`Saldo`** al renglón; si no entra mercadería, **`no_entregado_fact = "Si"`** (~4235–4264). Si **no** hay fila en `stock_deposito` (`RecordCount = 0`), ese bloque no ejecuta y **`Saldo` / `no_entregado_fact` pueden no tocarse** en el loop (quedan valores del `AddNew` plantilla o nulos según motor). *Confirmado por estructura If anidados.*

---

## 3. stock_deposito

**Evidencia:** `SELECT * FROM stock_deposito WHERE id_articulo = … And id_deposito = …` (~4210).  
**Uso:** actualizar `Saldo` cuando corresponde entrada física. *Confirmado por código.*

---

## 4. codmov

**Evidencia:** `SELECT * FROM codmov where codigo = 1` pessimistic lock; incremento y `Update` (~3756–3761).  
**Campo crítico:** contador devuelto como `CodMov` / `contador` para todas las tablas hijas.

---

## 5. proveedor

**Campos:** `codigo`, `saldo` — lectura inicial; **UPDATE** `saldo` = saldo calculado en cabecera (~3867–3870).

---

## 6. caja / caja_saldo

**Contado:** `Dias = "0"` en `cond_venta` asociada a `CV.BoundText`.  
**caja_saldo:** resta `ImporteTotal` del saldo en moneda `Pesos`.  
**caja:** `Tipo = "Factura Compra Contado"`, `egreso = ImporteTotal`, `codigo_movimiento = contador`, `codigo_prov`, `id_caja_abm_origen`, etc. (~4034–4101).

---

## 7. op_factura

**Condición:** `DataCV.Recordset.Fields!Dias <> "0"` (~3834 vs ~5085–5129).  
**Plantilla:** `SELECT * FROM op_factura WHERE CodigoMovimiento = 1` → AddNew.

---

## 8. Tablas de modificación (`modificacion_comp`)

**Evidencia `PFactura.frm` ~8022–8133:** actualización de campos en `cuentaproveedor`, `stock`, `op_factura`, `op_factura_par`, `imputacion_p`, `caja` filtrados por `CodigoMovimiento` del comprobante abierto.

---

## 9. Contabilidad (resumen de campos en líneas)

**cont_asiento:** `codigo_movimiento`, `nro_asiento`, `id_periodo`, `id_ejercicio`, `debe_asiento`, `haber_asiento`, `id_pc`, `saldo_asiento`, etc. (~9268–9518).  
**cont_ejercicio:** `Nro_asiento_ejercicio` incrementado (~9249–9257).  
**Saldos:** `cont_ejercicio_saldo_cta`, `cont_periodo_saldo_cta` según naturaleza `cont_pc.saldo_pc` (Deudor/Acreedor).

---

## 10. Dependencias de orden de inserción (obligatorias)

1. **codmov** (obtener `contador`).  
2. **cuentaproveedor** (cabecera; antes o junto con vales/percepciones que referencian `contador`).  
3. **proveedor.saldo** coherente con cabecera.  
4. **stock** (y **stock_deposito**, **stockp**, **lote**, **otro_egreso** por ítem).  
5. **op_factura** si crédito.  
6. **oc_factp** / actualización OC; **remp_factp** / remito.  
7. **GuardarSerie** (depende de **stock** y `serie_entrada` generados).  
8. **generar_asiento_cont** (lee `CuerpoStock` / totales cabecera; requiere tablas ya consistentes en la misma transacción).

*Confirmado por orden secuencial en `Guardar`;* *inferencia fuerte* en puntos finos si ADO hace flush implícito antes del asiento.

---

## 11. Claves foráneas

*Hipótesis / pendiente:* el VB6 no muestra DDL; se infieren por nombres (`CodigoMovimiento`, `id_articulo`, `id_deposito`, `codigo_prov`, `id_caja`). Validar en MySQL con `INFORMATION_SCHEMA`.

---

## Anexo A — Campos de la tabla `stock` escritos en `Guardar` (`PFactura.frm`)

**Alcance:** *Confirmado por código.* Bucle `Do While Not CuerpoStock.Recordset.EOF` tras `rs_stock.AddNew`, hasta `rs_stock.Update` (~4207–4643). Los nombres de campo siguen la notación **VB6** (`rs_stock.Fields!…`); contrastar mayúsculas/minúsculas con el DDL MySQL real.

**Referencias genéricas:** `CS` = `CuerpoStock.Recordset`, `P` = `Principal`, `contador` = `CodigoMovimiento` del comprobante, `num` = número de comprobante formateado, `cantidad_multiplicar` = variable calculada antes del bloque de lote (embalaje/bulto/display).

### A.1 Tabla de trazabilidad campo → origen / condición

| Campo (VB6) | Origen o expresión | Condición / notas |
|-------------|-------------------|-------------------|
| `Saldo` | `rs_saldo_stock.Fields!Saldo` (tras `stock_deposito.Update`) | Solo si hay fila `stock_deposito`, entrada física y no rama `Factura Remito` / no `no_entregado_fact` (~4257–4258) |
| `no_entregado_fact` | `"Si"` | Si no corresponde sumar depósito: `Factura Remito` o combo `remite_factura_art` en índice «no entrega» (~4259–4263) |
| `Fecha` | `Format(Fecha, "short date")` | Siempre (~4274) |
| `CodigoArticulo` | `CS.Fields!CodigoArticulo` | Siempre (~4275) |
| `Descripcion` | `CS.Fields!Descripcion` | Siempre (~4276) |
| `PrecioVentaxU` | `CS.Fields!PrecioVentaxU` | Siempre (~4277) |
| `PrecioCostoxU` | `CS.Fields!PrecioCostoxU` | Siempre (~4278) |
| `PrecioIVAxU` | `CS.Fields!PrecioIVAxU` | Siempre (~4279) |
| `PrecioBrutoxU` | `CS.Fields!PrecioBrutoxU` | Siempre (~4280) |
| `Impdesc` | `CS.Fields!Impdesc` | Siempre (~4281) |
| `Pordesc` | `CS.Fields!Pordesc` | Siempre (~4282) |
| `PrecioVentaxR` | `CS.Fields!PrecioVentaxR` | Siempre (~4283) |
| `PrecioCostoxR` | `CDbl(Format(CS.Fields!PrecioCostoxR, "##,###.00"))` | Siempre (~4284) |
| `PrecioIVAxR` | `CS.Fields!PrecioIVAxR` | Siempre (~4285) |
| `PrecioBrutoxR` | `CS.Fields!PrecioBrutoxR` | Siempre (~4286) |
| `PrecioNetoxR` | `CS.Fields!PrecioNetoxR` | Siempre (~4287) |
| `Alicuota` | `CS.Fields!Alicuota` | Siempre (~4288) |
| `imp_alicuota_iva` | `CS.Fields!imp_alicuota_iva` | Siempre (~4289) |
| `orden` | `CS.Fields!orden` | Siempre (~4290) |
| `Entrada` | `CS.Cantidad * CS.multiplicador_comp` o `CS.Cantidad * cant_por_bulto * cant_unidad_display` o `CS.Cantidad` | Ramas `P.utiliza_embalaje` y bulto/display (~4300–4330) |
| `Cantidad` | Igual lógica que `Entrada` en rama embalaje; o `CS.Cantidad` sin embalaje | (~4301–4330) |
| `cantidad_dividir` | `cantidad_multiplicar` | Solo si bulto cerrado o display activo (~4316) |
| `cantidad_unidad_display` | `cantidad_unidad_display` (local) | Solo misma rama (~4317) |
| `tipo_unidad` | `"Bulto"` / `"Unidad"` | Según `cantidad_por_bulto` y `cantidad_unidad_display` (~4320–4325) |
| `multiplicador_comp` | `CS.Fields!multiplicador_comp` | Siempre (~4334) |
| `multiplicador_vta` | `CS.Fields!multiplicador_vta` | Siempre (~4335) |
| `cantidad_uni` | `CS.Fields!cantidad_uni` | Siempre (~4336) |
| `id_unimed_comp` | `CS.Fields!id_UniMed` | Siempre (~4340) |
| `id_presentacion_comp` | `CS.Fields!id_presentacion` | Siempre (~4341) |
| `nombre_unimed_comp` | `CS.Fields!nombre_unimed` | Siempre (~4342) |
| `nombre_presentacion_comp` | `CS.Fields!nombre_presentacion` | Siempre (~4343) |
| `TipoComp` | `"Compra"` | Siempre (~4352) |
| `CodigoMovimiento` | `contador` | Siempre (~4354) |
| `CodigoCP` | `CodigoProv` | Siempre (~4355) |
| `Tipo` | `"Proveedor"` | Siempre (~4356) |
| `anulado` | `"No"` | Siempre (~4357) |
| `impdesc_bonif` | `CS.Fields!impdesc_bonif` | Siempre (~4358) |
| `pordesc_bonif` | `CS.Fields!pordesc_bonif` | Siempre (~4359) |
| `Comprobante` | `Tipo_Factura` luego forzado `"FC"` / `"FA"` / `"FM"` si aplica | (~4361, ~4395–4404) |
| `Detalle` | `CS.Fields!Detalle` | Siempre (~4364) |
| `CodigoGasto` | `0` si `Codgasto` nulo; si no `CS.Fields!Codgasto` | (~4368–4371) |
| `NroComprobante` | `num` | Siempre (~4407) |
| `TipoIVA` | `CS.Fields!TipoIVA` | Siempre (~4408) |
| `idUsuario` | `P.idUsuario` | Siempre (~4409) |
| `codSucursal` | `id_sucursal` o `P.codSucursal` | Según `P.modifica_sucursal_comp` (~4412–4415) |
| `IDArt` | `CS.Fields!IDArt` | Siempre (~4418) |
| `CodLaboratorio` | `CS.Fields!CodLaboratorio` | Siempre (~4419) |
| `CodDeposito` | `CS.Fields!CodDeposito` | Siempre (~4423) |
| `id_manual` | `CS.Fields!id_manual` | Si no es Null (~4428–4429) |
| `NroPresupuesto` | `CS.Fields!nro_presupuesto` | Si `nro_presupuesto` no Null (~4432–4434) |
| `codmov_presupuesto` | `CS.Fields!codmov_presupuesto` | Misma condición (~4434) |
| `NroPedido` | `CS.Fields!nro_oc` | Si `nro_oc` no Null (~4437–4439) |
| `codmov_pedido` | `CS.Fields!codmov_oc` | Misma condición (~4439) |
| `NroRemito` | `CS.Fields!nro_remito` | Si `nro_remito` no Null (~4442–4444) |
| `codmov_remito` | `CS.Fields!codmov_remito` | Misma condición (~4444) |
| `id_lote` | `rs_lote.Fields!id_lote` o `idlote` desde `last_insert_id()` | Si `CS.Lote = "Si"` y `TipoComprobante <> "Factura Remito"` y permisos entrega (~4516, ~4549) |
| `stock_lote_deposito` | `CS.Cantidad * cantidad_multiplicar` | Misma rama lote (~4517, ~4550) |
| `id_stockp` | `CS.Fields!id_stock` | Si `nro_oc` no Null y `TipoComprobante <> "Factura Remito"` (~4597) |
| `cantidad_entregada_pend` | `CS.Cantidad * cantidad_multiplicar` | Si `P.remite_factura_art = "Si"`, no remito-factura, `remite_factura_art.ListIndex = 1` (~4603–4607) |
| `desc_serie` | `CS.Fields!desc_serie` | Si `CS.Fields!serie = "Si"` (~4615) |
| `serie` | `"Si"` | Misma condición (~4616) |
| `unidad_art_peso` | `CDbl(Format(CS.Fields!unidad_art_peso, P.Decimales))` | Si `P.usa_multiplica_bulto_promedio = "Si"` y no Null (~4620–4623) |
| `coti_dolar` | `Actualiza_Cotizacion_Dolar_Articulo(CS.IDArt, "coti_dolar")` | Siempre en el flujo (~4627) |
| `id_cotizacion` | `Actualiza_Cotizacion_Dolar_Articulo(CS.IDArt, "id_cotizacion")` | Siempre (~4628) |
| `impuesto_interno_subtotal` | `CS.Fields!impuesto_interno_subtotal` | Siempre (~4641) |

**Campos comentados (no escritos en runtime):** `id_UniMed`, `id_presentacion` directos (~4337–4338 comentados); `id_serie_entrada` (~4614 comentado).

### A.2 Otras tablas tocadas dentro del mismo íter (mismo renglón)

| Tabla | Operación | Condición | Líneas aprox. |
|-------|-----------|-----------|---------------|
| `stock_deposito` | UPDATE `Saldo`, opcional `saldo_pedido_proveedor` | Ver §2 y rama OC | ~4210–4257 |
| `otro_egreso` | INSERT | `CS.Codgasto <> 0` | ~4376–4391 |
| `lote` / `lote_stock` | UPDATE o INSERT | `Lote = "Si"` y no Factura Remito y entrega | ~4463–4563 |
| `stockp` | UPDATE `cantidad_pendiente`, `remitido_facturado` | `nro_oc` no Null y no Factura Remito | ~4581–4596 |

### A.3 Efectos sobre `CuerpoStock.Recordset` (no son columnas `stock`)

Tras asignar `stock`, si `P.usa_multiplica_bulto_promedio = "Si"`, se **reescribe** `CS.Fields!unidad_art_peso` (~4631–4637). Synap debe decidir si replica ese efecto colateral en el buffer o solo persiste el valor ya calculado en `stock`.

### A.4 Validación previa que aborta el `Update` del renglón

Si `Lote = "Si"` y faltan `cod_lote` / `vto_lote`: `MsgBox`, `RollbackTrans`, `Exit Sub` (~4447–4456). No se llega a `rs_stock.Update` para ese intento.

### A.5 Cierre de `rs_saldo_stock`

Tras `rs_stock.Update`: si `TipoComprobante = "Factura OC"` y `remite_factura_art.ListIndex = 1`, se llama `rs_saldo_stock.CancelUpdate` antes de `Close`; si no, solo `Close` (~4647–4651). *Confirmado por código:* en ese caso se deshace la actualización pendiente del recordset de depósito en memoria (coherente con «no entregar» vía OC).

### A.6 Trazabilidad hallazgo → evidencia → conclusión

| Hallazgo | Evidencia | Conclusión |
|----------|-----------|------------|
| Lista cerrada de columnas `stock` en alta | Asignaciones `rs_stock.Fields!` únicas en ~4274–4641 | *Confirmado por código* |
| `Comprobante` puede quedar FA/FB según `Tipo_Factura` sin re-asignación explícita posterior a FM | Solo bloques `If Tipo_Factura = "FC"`, `"FA"`, `"FM"` (~4395–4404); no hay `Else` para FB | *Inferencia fuerte:* FB queda el valor inicial `Tipo_Factura` (~4361) |
| `Saldo` en renglón opcional | Depende de existencia de fila `stock_deposito` y ramas | *Confirmado por código* |
