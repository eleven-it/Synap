# Auditoría Técnica TPV VB6 - Tanda 1

**Fecha:** 23-01-2025  
**Formularios analizados:** TPV.frm, TPV_Seleccion_Articulo_Simple.frm, TPV_Modifica_Renglon.frm, TPV_Cliente_Ocasional.frm, TPV_Cliente_Comun.frm, TPV_2.frm  
**Formularios auxiliares:** TPV_DescMasivo_Renglon.frm

---

## 1. Resumen ejecutivo

- **cuerpostock** es el buffer temporal de renglones del TPV; se filtra por `CodUsuario` y `visualiza = 'No'`; `CodigoMovimiento = 1` indica no confirmado.
- Los renglones se insertan vía `data_renglon_tpv.Recordset.AddNew` (TPV_Modifica_Renglon) y se actualizan con `.Update`; la persistencia es inmediata (sin transacción explícita en agregar renglón).
- Al confirmar venta/NC: `codmov` se incrementa primero en transacción aparte; luego se graba `cuentacliente`, `stock`, `stock_deposito`; `cuerpostock.CodigoMovimiento` se actualiza al nuevo contador.
- Cliente ocasional: solo variables en memoria (TPV.Cliente, TPV.CUIT, etc.); no se crea fila en `cliente` ni en DB; "Modifica datos CF" actualiza `cuentacliente.tpv_*` por `codigomovimiento`.
- Cliente común: INSERT/UPDATE en `cliente` (TipoCliente, nombre_cliente, CUIT, domicilio, IVA); transacción con `conn.BeginTrans`/`CommitTrans`.
- TPV_Seleccion_Articulo_Simple: solo lectura (articulo, iva, activ_iibb, lote); no escribe en DB para el flujo TPV.
- TPV_DescMasivo_Renglon: actualiza `cuerpostock` (PorDesc, precios derivados) renglón por renglón; usa `rs_cuerpostock.Update` sin transacción global.

---

## 2. Flujo DB-first por proceso

### 2.1 Agregar renglón al TPV (TPV_Seleccion_Articulo → TPV_Modifica_Renglon)

| Paso | Tabla | Operación | Condición |
|------|-------|-----------|-----------|
| 1 | cuerpostock | INSERT (AddNew) | Tipo_Actualizacion = "Agrega" |
| 2 | cuerpostock | UPDATE | Tipo_Actualizacion = "Modifica" (cantidad, precio, descuento, etc.) |

**Claves:** `CodUsuario` = Principal.idUsuario, `visualiza` = 'No', `CodigoMovimiento` = 1 (mientras no confirmado).

**Orden:**  
1. RecordSource: `SELECT * FROM cuerpostock WHERE CodUsuario = X AND CodigoMovimiento = 1`  
2. AddNew con: CodigoArticulo, IDArt, Codusuario, id_manual, tipo_art, Alicuota, imp_alicuota_iva, AlicuotaIB, imp_alicuota_iibb, etc.  
3. Más adelante: PrecioVentaxU, Cantidad, Pordesc, PrecioIVAxU, PrecioBrutoxU, PrecioNetoxU, PrecioVentaxRD, Impdesc, PrecioIVAxR, PrecioNetoxR, PrecioBrutoxR, CodDeposito, orden, id_stock (si aplica), etc.  
4. Update

**Fuente:** TPV_Modifica_Renglon.frm → Grabar (líneas 1319-1322, 1367-1380, 2122, 4002-4315).

---

### 2.2 Eliminar renglón (TPV.frm)

| Paso | Tabla | Operación | Condición |
|------|-------|-----------|-----------|
| 1 | serie_salida_temp | DELETE | Por id_articulo, visualiza, id_usuario, tipo_comprobante='TPV', orden |
| 2 | cuerpostock | DELETE | Por Orden = id_cuerpostock **o** por IdArt si promoción "Cantidad - Unidad" |
| 3 | cuerpostock | DELETE | Por CodUsuario y visualiza='No' (Eliminar todos) |

**Fuente:** TPV.frm → Eliminar_Renglon (12218-12226), Eliminar_Todos (12313).

---

### 2.3 Descuento masivo (TPV_DescMasivo_Renglon)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | cuerpostock | SELECT por Orden, CodUsuario, visualiza |
| 2 | cuerpostock | UPDATE Pordesc, PrecioIVAxU, PrecioBrutoxU, PrecioNetoxU, PrecioVentaxRD, Impdesc, PrecioIVAxR, PrecioNetoxR, PrecioBrutoxR |

**Fuente:** TPV_DescMasivo_Renglon.frm → Aceptar_Click (304-350).

---

### 2.4 Confirmación venta (Factura / ticket) (TPV.frm)

| Paso | Tabla | Operación | Notas |
|------|-------|-----------|-------|
| 1 | codmov | UPDATE CodigoMovimiento = contador + 1 | Transacción aparte; si contabilidad activa, +2 |
| 2 | talonarios | UPDATE NroActual (u equivalente) | Por id_punto_venta, TipoComprobante |
| 3 | cuentacliente | INSERT (AddNew) | Cabecera comprobante |
| 4 | percep_cli | INSERT | Si hay percepciones |
| 5 | stock_deposito | UPDATE saldo (y saldo_pedido_cliente si es factura desde pedido) | Por id_articulo, id_deposito |
| 6 | stock | INSERT | Movimiento salida |
| 7 | lote / lote_stock | UPDATE | Si articulo con lote |
| 8 | stockp | UPDATE cantnc | Si proviene de pedido |
| 9 | cuerpostock | UPDATE CodigoMovimiento = contador | Relaciona renglones con comprobante |
| 10 | caja, saldo_caja, tc_comprobante, chequetercero, etc. | INSERT/UPDATE | Medios de pago |
| 11 | imputacion, asig_cobranza, recibo_factura | INSERT/UPDATE | Si hay cta. cte. |
| 12 | cuentacliente_fe, fe_codbarra | UPDATE | Si FE electrónica (CAE) |

**Orden de persistencia:** codmov → talonarios → cuentacliente → stock_deposito → stock → lote → cuerpostock (CodigoMovimiento) → medios de pago → imputación.

**Fuente:** TPV.frm → Grabar (aprox. 5753-10900), Confirmar_Cobro (aprox. 8457-10860).

---

### 2.5 Confirmación NC por devolución (TPV.frm)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | codmov | UPDATE |
| 2 | cuentacliente | INSERT (NC) |
| 3 | stock_deposito | UPDATE saldo += cantidad (reingreso) |
| 4 | stock | INSERT (entrada por devolución) |
| 5 | stock (nc) | UPDATE cantnc |
| 6 | lote | UPDATE stock_total_lote, stock_lote |
| 7 | cuerpostock | UPDATE CodigoMovimiento |
| 8 | imputacion, recibo_factura_nc, cliente.Saldo | Según cta. cte. |

**Fuente:** TPV.frm → Grabar (NC, ~6220-7600).

---

### 2.6 Cliente ocasional (TPV_Cliente_Ocasional)

| Paso | Tabla | Operación | Condición |
|------|-------|-----------|-----------|
| - | (ninguna) | - | Formulario_Seleccion = "TPV": solo asigna TPV.Cliente, TPV.CUIT, TPV.datos_ocasional, etc. |
| 1 | cuentacliente | UPDATE tpv_nombre_ocasional, tpv_domicilio_ocasional, tpv_nro_identif_ocasional, tpv_mail_ocasional, tpv_cel_wp_ocasional, tpv_doc_cliente_ocasional | Formulario_Seleccion = "Modifica datos CF", por codigo_movimiento_comp |

**Fuente:** TPV_Cliente_Ocasional.frm → Aceptar_Click (322-359, 334-358).

---

### 2.7 Cliente común – Alta (TPV_Cliente_Comun)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | cliente | INSERT (AddNew) con TipoCliente, nombre_cliente, Descuento, Credito, codViajante, CUIT/tipo_doc, IDIVA, Estado, ListaPrecio, FechaAlta, id_cv, id_sucursal, domicilio, id_pc (de cont_paramatriz) |
| 2 | LAST_INSERT_ID | Para obtener Codigo del nuevo cliente |

**Fuente:** TPV_Cliente_Comun.frm → Guardar (1107-1151).

---

### 2.8 Cliente común – Modificación (TPV_Cliente_Comun)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | cliente | UPDATE por Codigo = id_cliente_actual |

**Fuente:** TPV_Cliente_Comun.frm → Guardar (1239-1300).

---

## 3. Mapa de commit points

| Momento | Estado | Tablas |
|---------|--------|--------|
| Antes de confirmar | Borrador/buffer | cuerpostock (CodigoMovimiento=1 o NULL), serie_salida_temp, chequetercero_temp, tc_temp, percep_cli_temp |
| Confirmación iniciada | Transacción codmov | codmov |
| Confirmación en curso | Transacción principal | cuentacliente, stock, stock_deposito, lote, talonarios, cuerpostock (CodigoMovimiento asignado), caja, imputacion, etc. |
| Commit final | Persistencia irreversible | Todo lo anterior + asiento contable (si activo) |

**Punto de no retorno:** Tras `conn.CommitTrans` de la transacción principal. Antes: rollback posible.

---

## 4. Efectos colaterales

### 4.1 stock_deposito

- **saldo:** − en venta (stock.AddNew con Entrada negativo o Salida); + en NC devolución.
- **saldo_pedido_cliente:** − cuando se factura “desde pedido” (Comprobante_Pedido = "Si") por cada renglón con codmov_pedido.

### 4.2 stock

- INSERT por cada renglón de cuerpostock al confirmar; `CodigoMovimiento` = contador; `Entrada` o `Salida` según tipo.

### 4.3 codmov

- `CodigoMovimiento` se incrementa en 1 (o +2 si contabilidad activa) al iniciar confirmación; usa `adLockPessimistic`.

### 4.4 talonarios

- `NroActual` (o campo equivalente) se actualiza al asignar número de comprobante (FA/FB/NCA/NCB/NCC/NCM).

### 4.5 cuerpostock

- `CodigoMovimiento`: 1 o NULL = borrador; al confirmar se actualiza al contador definitivo.
- Limpieza: `DELETE FROM cuerpostock WHERE CodUsuario = X AND visualiza = 'No'` al cerrar/vaciar TPV.

### 4.6 cuentacliente

- Fuente de verdad del comprobante (Factura, NC, Recibo).
- Campos tpv: tpv_nombre_ocasional, tpv_domicilio_ocasional, tpv_nro_identif_ocasional, tpv_mail_ocasional, tpv_cel_wp_ocasional, tpv_doc_cliente_ocasional.

---

## 5. Reglas de negocio detectadas

| Regla | Ubicación | Condición |
|-------|-----------|-----------|
| Filtro cuerpostock TPV | TPV.frm 12814 | `CodUsuario = Principal.idUsuario AND visualiza = 'No'` |
| CodigoMovimiento borrador | TPV_Modifica_Renglon, TPV | `CodigoMovimiento = 1` en RecordSource al agregar |
| Tipo Factura A/B según IVA | TPV.frm 5788-5817 | Principal.IDIVA, ID_Cat_Contribuyente, resol_afip_5003 |
| Cliente ocasional = CF | TPV_Cliente_Ocasional | TPV.Codigo_Cliente = 1, ID_Cat_Contribuyente = 4 |
| Validación stock | TPV.frm 9497+ | stock_deposito por id_articulo, id_deposito; permite salida sin stock según configuración |
| Descuento masivo límite | TPV_DescMasivo_Renglon | Principal.lim_desc_renglon; comp_supervisor = "No" |
| Promoción anula descuento masivo | TPV_DescMasivo_Renglon | Si Obtener_Promo_Articulo = True y cambio_lista_conserva_promo = "Si" → CancelUpdate |
| Modifica datos CF | TPV_Cliente_Ocasional | Solo UPDATE cuentacliente por codigo_movimiento_comp |

---

## 6. SQL equivalente (pseudo-SQL)

### Agregar renglón

```sql
-- Implícito vía ADO Recordset AddNew/Update sobre:
INSERT INTO cuerpostock (
  CodigoArticulo, IDArt, Codusuario, id_manual, tipo_art, Alicuota, imp_alicuota_iva,
  AlicuotaIB, imp_alicuota_iibb, PrecioVentaxU, Cantidad, Pordesc, PrecioIVAxU,
  PrecioBrutoxU, PrecioNetoxU, PrecioVentaxRD, Impdesc, PrecioIVAxR, PrecioNetoxR,
  PrecioBrutoxR, CodDeposito, orden, CodigoMovimiento, visualiza, ...
) VALUES (...);
-- CodigoMovimiento = 1
```

### Confirmar venta (resumen)

```sql
BEGIN;
  UPDATE codmov SET CodigoMovimiento = CodigoMovimiento + 1 WHERE codigo = 1;
COMMIT;  -- Transacción aparte

BEGIN;
  SELECT @contador := CodigoMovimiento FROM codmov WHERE codigo = 1;
  UPDATE talonarios SET NroActual = NroActual + 1 WHERE id_punto_venta = ? AND TipoComprobante = ?;
  INSERT INTO cuentacliente (..., CodigoMovimiento, NroComprobante, ...) VALUES (..., @contador, ?, ...);
  -- Por cada renglón en cuerpostock:
  UPDATE stock_deposito SET saldo = saldo - cantidad WHERE id_articulo = ? AND id_deposito = ?;
  INSERT INTO stock (CodigoMovimiento, IDArt, Cantidad, Entrada, Salida, ...) VALUES (@contador, ?, ?, 0, ?, ...);
  UPDATE cuerpostock SET CodigoMovimiento = @contador WHERE CodUsuario = ? AND visualiza = 'No';
  -- Medios de pago, imputación, etc.
COMMIT;
```

### Eliminar renglón

```sql
DELETE FROM serie_salida_temp WHERE id_articulo = ? AND visualiza = 'No' AND id_usuario = ? AND tipo_comprobante = 'TPV' AND orden = ?;
DELETE FROM cuerpostock WHERE Orden = ?;  -- o WHERE IdArt = ? AND CodUsuario = ? AND visualiza = 'No' (promo 2x1)
```

---

## 7. Riesgos y sugerencias

| Riesgo | Nivel | Sugerencia |
|--------|-------|------------|
| AddNew/Update en cuerpostock sin transacción | Media | Envolver agregar/modificar renglón en transacción |
| Commits parciales en confirmación | Alta | Revisar que toda la confirmación esté en una única transacción con rollback en error |
| CodigoMovimiento = 1 compartido entre usuarios | Baja | Confirmar que filtro CodUsuario evita cruces |
| Descuento masivo sin transacción | Media | Usar transacción para el loop de UPDATE en cuerpostock |
| Cliente ocasional sin INSERT en cliente | Baja | Documentar que es por diseño (CF sin alta) |

---

## 8. Checklist de pruebas

- [ ] Agregar renglón: se inserta en cuerpostock con CodigoMovimiento = 1.
- [ ] Modificar renglón: se actualiza el mismo Orden en cuerpostock.
- [ ] Eliminar renglón: desaparece de cuerpostock; serie_salida_temp se limpia si aplica.
- [ ] Eliminar todos: cuerpostock vacío para CodUsuario y visualiza = 'No'.
- [ ] Descuento masivo: Pordesc y precios derivados actualizados en todos los renglones.
- [ ] Confirmar venta: codmov +1, cuentacliente INSERT, stock INSERT, stock_deposito saldo −, cuerpostock.CodigoMovimiento asignado.
- [ ] Confirmar NC: stock_deposito saldo +, stock con entrada, imputación si cta. cte.
- [ ] Cliente ocasional TPV: sin INSERT en cliente; variables en memoria.
- [ ] Modifica datos CF: UPDATE cuentacliente.tpv_* por codigo_movimiento.
- [ ] Cliente común alta: INSERT en cliente, LAST_INSERT_ID para pasar al TPV.
- [ ] Cliente común modificación: UPDATE cliente por Codigo.

---

## 9. Formularios auxiliares referenciados

| Formulario | Carpeta | Uso |
|------------|---------|-----|
| TPV_DescMasivo_Renglon | Formularios | Descuento % masivo sobre cuerpostock |
| CargaChequeTercero | Formularios | Carga cheques para pago |
| Clave_Supervisor | Formularios | Autorización para eliminar/anular |
| Carga_DatosAdicionales | Formularios | Datos adicionales del comprobante |
| ABMCliente | Formularios | Alta/modificación cliente (referido desde TPV_Cliente_Comun) |
| Serie_salida | Formularios | Series de salida para artículos |
| Articulo | Formularios | ABM artículo (consulta desde TPV) |
| VisualizarFichaArt | Formularios | Ficha de artículo |
| Lista_Comp_Gral | Formularios | Listado comprobantes |
| Programa_Descuentos_Canje | Formularios | Programa descuentos |
| CtaCteCliente | Formularios | Cuenta corriente cliente |

---

## 10. Archivos pendientes para cerrar proceso TPV

### 10.1 Analizados (Tanda 2)

#### CargaChequeTercero (form en ChequeCliente.frm, VB_Name = CargaChequeTercero)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | chequetercero_temp | INSERT (AddNew) o UPDATE según Modifica_Cheque |
| 2 | — | Al confirmar TPV: TPV graba en chequetercero definitivo |

**Flujo TPV:** Accion = "TPV". AddNew/Update en `chequetercero_temp` filtrado por `CodUsuario`. Al confirmar cobro, TPV inserta en `chequetercero` y hace DELETE de `chequetercero_temp` por usuario. Fuente: ChequeCliente.frm (CargaChequeTercero) 986-1007, 1110-1125, 1145-1165.

#### Serie_salida.frm

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | serie_salida_temp | INSERT (desde serie_entrada, ids seleccionados) |
| 2 | serie_salida_temp | DELETE (al quitar selección) |
| 3 | cuerpostock | UPDATE desc_serie = GROUP_CONCAT(nro_serie, vto_serie) por orden |

**Flujo TPV:** frmTipo = "TPV". serie_entrada → serie_salida_temp (visualiza='No', id_usuario, tipo_comprobante='TPV', orden). Luego UPDATE cuerpostock.desc_serie. Al confirmar venta, TPV persiste serie_movimiento desde serie_salida_temp. Fuente: Serie_salida.frm 600-650, 763-774, 938-942.

#### Carga_DatosAdicionales.frm

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | cuerpostock / cuerpostockpe | UPDATE CodDeposito, etc. si cambia depósito |
| 2 | — | Asigna variables a TPV: id_deposito_despacho, Fentrega, id_transporte, id_repartidor, id_cliente_domicilio, id_cliente_contacto, OrigenPedido, NomDomicilio, NomContacto, etc. |

**Flujo TPV:** FrmOrigen = "TPV". Solo UPDATE cuerpostock.CodDeposito si EstadoDepo ≠ DepositoOrigen; resto son variables en memoria. Fuente: Carga_DatosAdicionales.frm 2594-2675.

---

### 10.2 Analizados (Tanda 3)

#### FE/CAE (cuentacliente_fe, fe_codbarra)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | cuentacliente | UPDATE fe_cae, fe_vto_cae, fe_comp, fe_transmitido, fe_regimen_tipo (por id_cuentacliente) |
| 2 | fe_codbarra | AddNew/Update codigo_movimiento, texto_cod_qr, id_usuario, img_codbarra |

**Flujo:** Tras transmitir a AFIP, se actualiza cuentacliente con CAE/CAEA; fe_codbarra guarda el código de barras del comprobante. Emitir_FE_CAEA (CAEA): UPDATE cuentacliente + fe_codbarra. Fuente: TPV.frm 7834-7882, 10557-10589, 36388-36497, 39489-39553.

#### Asiento contable (generar_asiento_cont_dev, Conta_PV_Esp)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | newasiento / asiento | INSERT asiento contable |
| 2 | nroasiento | UPDATE contador |
| 3 | SaldoCtaCont | UPDATE débitos/créditos por cuenta |

**Flujo:** Si activ_contabilidad = "Si". generar_asiento_cont_dev: genera asiento por NC devolución desde data_renglon_tpv, articulo.id_pc_vta. Conta_PV_Esp (Principal): retorna id_pv electrónico. Fuente: TPV.frm 7546, 19619+, Principal.frm 8571.

#### Flujo tarjeta (tc_temp → tc_comprobante)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | tc_temp | AddNew/Update (buffer por id_usuario, visualiza='No') |
| 2 | tc_comprobante | INSERT desde data_tarjeta_temp (nombre_tc, plan, importe, cuotas, etc.) |
| 3 | caja, saldo_caja | INSERT/UPDATE (ingreso por tarjeta) |
| 4 | tc_temp | DELETE por id_tc_temp (al quitar cupón) |

**Flujo:** data_tarjeta_temp enlaza a tc_temp. Al confirmar: loop sobre data_tarjeta_temp → INSERT tc_comprobante (codigo_movimiento), caja, saldo_caja. Fuente: TPV.frm 10054-10137, 11649 (DELETE tc_temp).

#### Flujo percep_cli_temp → percep_cli

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | percep_cli_temp | INSERT desde percep_visualiza (id_percep_cli_tipo, alicuota, importe, cod_afip, id_usuario) |
| 2 | percep_cli | INSERT desde percep_cli_temp (id_percep_cli_tipo, alicuota_percep_cli, importe_percep_cli, codigo_movimiento, id_cliente, tipo_comp) |
| 3 | cuentacliente | UPDATE total_percep |
| 4 | percep_cli_temp | DELETE por id_usuario, visualiza='No' (al cerrar) |

**Flujo:** percep_visualiza INSERT percep_cli_temp. TPV al confirmar: loop percep_cli_temp → AddNew percep_cli. Fuente: TPV.frm 6447-6464, 9416-9434, 16810; percep_visualiza.frm 312.

#### Ensamblaje venta (Ensamblaje)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | articulo, en_abm, en_abm_formula | SELECT (ensamblado, descuenta_en, insumos) |
| 2 | stock | INSERT entrada (MstockE: artículo ensamblado) |
| 3 | stock | INSERT salida (MstockS: insumos por cantidad × fórmula) |
| 4 | stock_deposito | UPDATE saldo |
| 5 | lote, lote_stock | Si aplica |

**Flujo:** Si articulo.ensamblado='Si' y en_abm.descuenta_en='Venta'. MstockE: entrada producto armado. MstockS: salida insumos. Anular_Ensamblaje: revierte (stock_anul, saldo+). Fuente: TPV.frm 35730-35838, 35840-36070; MstockE/MstockS 35111-35391.

#### Logística (Guarda_Logistica)

| Paso | Tabla | Operación |
|------|-------|-----------|
| 1 | cliente_datos_adicionales | INSERT (AddNew) FechaEntrega, id_deposito_despacho, Fentrega, id_transporte, id_repartidor, id_cliente_domicilio, id_cliente_contacto, origen_pedido, operador_logistico, TipoComprobante, id_cliente, CodigoMovimiento, id_ruta |

**Flujo:** Si id_ruta <> 0. Fuente: TPV.frm 33968-34020.

#### Sistema de puntaje (Actualiza_Puntos_SP, Actualiza_Puntos_PD)

| SP | Tabla | Operación |
|----|-------|-----------|
| SP | sp_movimiento_premios | INSERT (Fecha, id_cliente, tipo_comp, nro_comp, monto_neto, monto_final, puntos_acumulados, codigo_movimiento) |
| SP | sp_saldo_cliente_premios | UPDATE saldo_premios ± o AddNew |
| PD | sp_desc_mov (sp_movimiento_premios PD) | INSERT |
| PD | sp_desc_saldo | UPDATE saldo_puntos ± o AddNew |

**Flujo:** Si mod_sp/mod_pd y activ_sp/activ_pd. Actualiza_Puntos_SP/PD en Funciones.bas. Fuente: TPV.frm 7558, 7570, 10272, 10285; Funciones.bas 7840-7935, 12022-12125.

---

### 10.3 Pendientes (cerrados)

Todos los flujos críticos del TPV han sido documentados.
