# Tabla `stockp` en AdministraNET (VB6): procedimientos y lógica de guardado

Documento que lista **todos los formularios/procedimientos que escriben en la tabla `stockp`** y cómo lo hacen, en la misma línea que `STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md`. Sirve para entender saldos de pedidos (cliente y proveedor), `cantidad_pendiente`, `remitido_facturado` y condiciones en las que un registro no actualiza algún campo.

---

## 1. Resumen: quién escribe en `stockp`

| Formulario | Acción | Comprobante | CodigoMovimiento | Operación | Campos clave |
|------------|--------|-------------|------------------|-----------|--------------|
| **Pedido.frm** | Alta pedido cliente | PED | contador PED | **AddNew** | Cantidad, cantidad_entregada, cantidad_pendiente, Salida, Saldo (si CodDeposito<>0), Tipo='Cliente', TipoComp='Pedido' |
| **Pedido_Interno.frm** | Alta pedido interno | PEDI | contador PEDI | **AddNew** | Cantidad, Salida=0, Entrada=0; **no** setea cantidad_pendiente/cantidad_entregada |
| **POrden_Compra.frm** | Alta orden de compra | OC | contador OC | **AddNew** | Cantidad, cantidad_entregada, cantidad_pendiente, Entrada, Saldo=0, Tipo='Proveedor', Comprobante='OC' |
| **Remito.frm** | Emitir remito desde pedido | — | — | **Update** | cantidad_pendiente -= Salida REM; remitido_facturado = "Si" si totalRemitido ≤ 0 |
| **PFactura.frm** | Factura de compra (desde OC) | — | — | **Update** | cantidad_pendiente -= Cantidad facturada; remitido_facturado = "Si" si queda 0 |
| **Presupuesto.frm** / **Visualiza_Presupuesto.frm** | Alta presupuesto (cliente) | PRE | contador | **AddNew** | Similar a PED (detalle en stockp); también Update Fecha/NroComprobante al modificar |
| **PPresupuesto.frm** | Alta presupuesto proveedor | PRE | contador | **AddNew** | Renglones en stockp desde cuerpostockp |
| **ConsultaComprobante.frm** | Anular PED/REM/OC/PRE/PEDI | — | — | **Update** | anulado='Si'; o (anular REM venta) remitido_facturado='No', cantidad_pendiente += Cantidad |
| **Pedido.frm** (modificar comprobante) | Cambiar fecha/número factura | — | — | **Update** | Fecha, NroComprobante |

---

## 2. Comportamiento detallado por formulario

### 2.1 Pedido.frm — Alta de pedido cliente (PED)

- **Qué hace:** Por cada renglón de `CuerpoStock` (cuerpostockpe) hace `rs_stock.AddNew` sobre **stockp** con:
  - `rs_stock.Open "SELECT * FROM stockp where CodigoMovimiento = 1"` (template), luego `AddNew`.
  - **Campos:** Fecha, CodigoArticulo, Descripcion, precios (PrecioVentaxU, PrecioCostoxU, …), Cantidad, cantidad_entregada, cantidad_pendiente, **Salida** = Cantidad (con multiplicadores bulto/display si aplica).
  - **Saldo:** Solo se asigna `rs_stock.Fields!Saldo` dentro del bloque `If CuerpoStock.Recordset.Fields!CodDeposito <> 0`: ahí abre `stock_deposito` por IDArt + CodDeposito; si `RecordCount > 0` hace `Update` de `saldo_pedido_cliente += Cantidad * cantidad_multiplicar` y luego `rs_stock.Fields!Saldo = rs_saldo_stock.Fields!saldo_pedido_cliente`. Si **CodDeposito = 0** (servicio) no entra a ese bloque y **no se setea Saldo** en el nuevo registro stockp. Si CodDeposito <> 0 pero **no existe fila en stock_deposito** (RecordCount = 0), en Pedido no se hace AddNew en stock_deposito para ese ítem y tampoco se asigna `rs_stock.Fields!Saldo` (porque solo se asigna cuando RecordCount > 0).
  - CodigoMovimiento = contador del PED, Tipo = "Cliente", TipoComp = "Pedido", Comprobante = "PED", anulado = "No", CodigoCP = cliente, etc.
- **stock_deposito:** Update (o AddNew si no existe) de `saldo_pedido_cliente` solo cuando CodDeposito <> 0.

**Condiciones en que un registro en stockp no actualiza algún campo:**
- **Saldo:** No se actualiza (queda default/null) cuando: (1) **CodDeposito = 0** (artículo servicio), o (2) **CodDeposito <> 0** pero no existe fila en `stock_deposito` para ese artículo+depósito (no se asigna `rs_stock.Fields!Saldo`).

---

### 2.2 Pedido_Interno.frm — Alta de pedido interno (PEDI)

- **Qué hace:** Por cada renglón hace `rs_stock.AddNew` sobre stockp con:
  - `rs_stock.Open "SELECT * FROM stockp where CodigoMovimiento = 1"`.
  - Fecha, CodigoArticulo, Descripcion, precios, **Cantidad** (con multiplicador bulto/display), **Salida = 0**, **Entrada = 0**, orden, CodigoMovimiento, CodDeposito, IDArt, Tipo = "Pedido Interno", TipoComp = tipo_pedido, Comprobante = "PEDI", anulado = "No", NroComprobante = Nro.
  - **No se asignan** `cantidad_entregada` ni `cantidad_pendiente` en el código revisado; quedarían en valor por defecto (0 o null) en la tabla.

**Condiciones:** PEDI no actualiza cantidad_pendiente/cantidad_entregada en el alta (no se usan en el flujo de PEDI como en PED/OC).

---

### 2.3 POrden_Compra.frm — Alta de orden de compra (OC)

- **Qué hace:** Por cada renglón de `CuerpoStock` (cuerpostockp) hace `rs_stock.AddNew` sobre **stockp** con:
  - `rs_stock.Open "SELECT * FROM stockp where CodigoMovimiento = 1"`.
  - Fecha, CodigoArticulo, Descripcion, precios, **Saldo = 0**, TipoComp = "Compra", **Entrada** = Cantidad (con multiplicadores), **Cantidad**, **cantidad_entregada**, **cantidad_pendiente**, CodigoMovimiento = contador OC, CodigoCP = proveedor, Tipo = "Proveedor", Comprobante = "OC", anulado = "No", NroComprobante, etc.
  - **stock_deposito:** Update (o AddNew si no existe) de `saldo_pedido_proveedor` por artículo+depósito.

No se identifican condiciones donde se omita la escritura de campos del nuevo registro stockp en el flujo normal de guardado.

---

### 2.4 Remito.frm — Remito de venta (desde pedido): actualización de stockp

- **Qué hace:** Cuando el remito se arma **desde pedido** (`Not IsNull(CuerpoStock.Recordset.Fields!NroPedido)`):
  - Abre stockp por `id_stock` y `codmov_pedido`:  
    `rs_stockp.Open "SELECT * FROM stockp WHERE stockp.id_stock = " & ... & " AND stockp.CodigoMovimiento = " & CuerpoStock.Recordset.Fields!codmov_pedido`.
  - Si `rs_stockp.RecordCount > 0`:
    - `totalRemitido = rs_stockp.Fields!cantidad_pendiente - rs_stock.Fields!Cantidad` (cantidad pendiente menos lo que sale en este remito).
    - Si totalRemitido ≤ 0: `rs_stockp.Fields!remitido_facturado = "Si"`, totalRemitido = 0.
    - `rs_stockp.Fields!cantidad_pendiente = totalRemitido`
    - `rs_stockp.Update`
  - Además asigna `rs_stock.Fields!id_stockp = CuerpoStock.Recordset.Fields!id_stock` en la tabla **stock** para vincular remito con pedido.

**Condiciones en que stockp no se actualiza:**
- Remito **no** originado en pedido (NroPedido es null): no se toca stockp.
- Remito desde pedido pero **no se encuentra** la fila en stockp (`rs_stockp.RecordCount = 0`): por ejemplo si `id_stock` o `codmov_pedido` no coinciden, no se ejecuta el Update; `cantidad_pendiente` y `remitido_facturado` quedarían desactualizados para ese pedido.

---

### 2.5 PFactura.frm — Factura de compra (desde OC): actualización de stockp

- **Qué hace:** Al facturar renglones que vienen de OC (tienen id_stock y codmov_oc):
  - Abre stockp por `id_stock` y `CodigoMovimiento` del movimiento de OC:  
    `rs_stockp.Open "SELECT * FROM stockp WHERE stockp.id_stock = " & CuerpoStock.Recordset.Fields!id_stock & " AND stockp.CodigoMovimiento = " & CuerpoStock.Recordset.Fields!codmov_oc`
  - Si `rs_stockp.RecordCount > 0`:
    - `totalRemitido = rs_stockp.Fields!cantidad_pendiente - (Cantidad * cantidad_multiplicar)`
    - Si totalRemitido = 0: `rs_stockp.Fields!remitido_facturado = "Si"`
    - `rs_stockp.Fields!cantidad_pendiente = totalRemitido`
    - `rs_stockp.Update`

**Condiciones en que stockp no se actualiza:** Si no existe fila en stockp para ese id_stock + CodigoMovimiento (OC), no se hace Update (RecordCount = 0).

---

### 2.6 Presupuesto.frm / Visualiza_Presupuesto.frm — Presupuesto cliente (PRE)

- **Qué hace:** Al guardar el presupuesto hacen `rs_stock.AddNew` sobre **stockp** con `rs_stock.Open "SELECT * FROM stockp where CodigoMovimiento = 1"`. Los campos son análogos a los del Pedido (Fecha, artículo, Cantidad, precios, Tipo, TipoComp, Comprobante tipo presupuesto, etc.). Al modificar comprobante, actualizan en stockp **Fecha** y **NroComprobante** por CodigoMovimiento. Visualiza_Presupuesto además puede **DELETE** de stockp y **INSERT** en stockp al editar renglones (sincronizar cuerpostockpe con stockp).

### 2.7 PPresupuesto.frm — Presupuesto proveedor

- **Qué hace:** Al guardar el presupuesto proveedor hace `rs_stock.AddNew` sobre **stockp** desde `cuerpostockp`, con `rs_stock.Open "SELECT * FROM stockp where CodigoMovimiento = 1"`. Comportamiento análogo a OC para renglones del presupuesto.

### 2.8 ConsultaComprobante.frm — Anulaciones y contramovimientos

**Anulación de comprobantes que tienen filas en stockp (Presupuesto, OC, PED, PEDI):**
- Abre `rs_stock` sobre **stockp** por CodigoMovimiento del comprobante anulado:
  - Ej.: `rs_stock.Open "SELECT * FROM stockp WHERE stockp.CodigoMovimiento = " & DataConsulta.Recordset.Fields!CodigoMovimiento`
- Recorre los registros y hace `rs_stock.Fields!anulado = "Si"` y `rs_stock.Update`.
- Además se revierte `stock_deposito.saldo_pedido_cliente` o `saldo_pedido_proveedor` según tipo de comprobante (no se modifica otro campo de stockp en este camino).

**Anulación de REM de venta (remito que sale de pedido):**
- Abre **stock** por CodigoMovimiento del remito; por cada fila de stock con `id_stockp` no null:
  - Abre **stockp** por `id_stock = rs_stock_id.Fields!id_stockp`.
  - Si `rs_mod_stockp.RecordCount > 0`:  
    `remitido_facturado = "No"`,  
    `cantidad_pendiente = cantidad_pendiente + rs_stock.Fields!Cantidad`,  
    `rs_mod_stockp.Update`.

**Condiciones:** Si al anular REM no existe registro en stockp con ese `id_stock` (p. ej. id_stockp en stock erróneo o borrado), no se actualiza stockp (RecordCount = 0).

---

### 2.9 Pedido.frm — Modificación de comprobante (cambiar fecha / número de factura)

- **Qué hace:** Al actualizar el comprobante (ej. asignar número de factura), abre **stockp** por CodigoMovimiento del pedido:  
  `rs_item.Open "SELECT * FROM stockp WHERE CodigoMovimiento = " & CuerpoStock.Recordset.Fields!CodigoMovimiento`
- Si `rs_item.RecordCount > 0`, recorre y actualiza en cada registro: **Fecha**, **NroComprobante** y cierra.

No se identifican condiciones adicionales donde falte actualizar un campo (salvo no encontrar el CodigoMovimiento).

---

## 3. Formularios que solo leen stockp (sin escribir)

- **Lista_Comp_Gral.frm**, **Lista_Comp_Fact.frm**: leen `stockp.cantidad_pendiente` (y otros campos) para armar PRemito/PFactura desde OC o para mostrar pedidos/remitos.
- **Remito.frm**: además de actualizar stockp cuando remito es desde pedido, consulta stockp (ej. `rs_consulta_pedido_cliente`) para datos de pantalla.
- **Visualiza_Pedido.frm**: usa cantidad_pendiente / cantidad_pendiente_faltante para visualización; código comentado que actualizaba `rs_stock.Fields!cantidad_pendiente` no está activo.
- **Lista_Pedidos_OPT.frm**: lee stockp (cantidad_pendiente_opt, etc.) para desarme/opciones.

---

## 4. Reglas para uso en informes / reconciliación

1. **Saldos por pedido cliente (venta):**  
   Usar `stockp` con `Tipo = 'Cliente'`, `TipoComp = 'Pedido'`, `Comprobante = 'PED'`, `anulado = 'No'`. El campo **Saldo** en stockp puede ser null o incorrecto para servicios (CodDeposito = 0) o cuando no existía stock_deposito al guardar; para saldo “reservado” por pedidos es más fiable **stock_deposito.saldo_pedido_cliente** o el cálculo por comp_ped + stockp usado en el BO.

2. **Saldos por OC (compra):**  
   Usar `stockp` con `Comprobante = 'OC'`, `anulado = 'No'`. cantidad_pendiente y remitido_facturado se actualizan al emitir REM compra (PRemito) y FC (PFactura); si por error no se encuentra la fila en stockp al remitar/facturar, esos campos pueden quedar desactualizados.

3. **PEDI:**  
   Los registros PEDI en stockp no usan cantidad_pendiente/cantidad_entregada en el alta; no deben mezclarse con la lógica de “pendiente de remitir/facturar” de PED/OC.

4. **Anulaciones:**  
   Siempre filtrar `anulado = 'No'` en stockp. Al anular REM de venta, ConsultaComprobante restaura cantidad_pendiente y remitido_facturado en la fila de stockp correspondiente; si esa fila no se encuentra, el pedido queda con cantidad_pendiente desactualizada.

---

## 5. Condiciones resumidas: cuándo un registro en stockp no actualiza algún campo

| Contexto | Campo no actualizado | Condición |
|----------|----------------------|-----------|
| **Pedido.frm** (alta PED) | Saldo | CodDeposito = 0 (servicio) **o** no existe fila en stock_deposito para artículo+depósito |
| **Pedido_Interno.frm** (alta PEDI) | cantidad_pendiente, cantidad_entregada | No se setean en el código; quedan en default |
| **Remito.frm** (remito desde pedido) | cantidad_pendiente, remitido_facturado | Remito no desde pedido (NroPedido null) **o** no se encuentra fila en stockp (id_stock + codmov_pedido) |
| **PFactura.frm** (factura desde OC) | cantidad_pendiente, remitido_facturado | No se encuentra fila en stockp para id_stock + CodigoMovimiento OC |
| **ConsultaComprobante** (anular REM venta) | cantidad_pendiente, remitido_facturado | id_stockp null en stock **o** no existe fila en stockp con ese id_stock |

---

*Documento generado a partir del análisis del código VB6 en `administranet_vb6/Formularios/` (Pedido, Pedido_Interno, POrden_Compra, Remito, PFactura, Presupuesto, PPresupuesto, Visualiza_Presupuesto, ConsultaComprobante).*
