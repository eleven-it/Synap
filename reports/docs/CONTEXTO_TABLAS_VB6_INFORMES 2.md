# Contexto de tablas DB para informes (desde formularios VB6)

Contexto extraído de los formularios VB6: **Pedido_Avanzado**, **Pedido**, **Pedido_prep**, **Pedido_Interno**, **Stock**, **Pedido_prep_consulta**, **Pedido_Mod_Cant_Entregada**.

---

## 1. Cuerpo de comprobantes: `cuerpostockp` vs `cuerpostockpe` vs `cuerpostock`

### `cuerpostockpe` (Pedidos / Pedido Interno)

- **Uso**: Buffer temporal de **renglones de pedidos de venta (PED)** y **pedidos internos (PEDI)**.
- **Formularios**: Pedido, Pedido_Interno, Lista_Comp_Fact (remito desde pedidos), Pedido_prep (asignación preparación), ConsultaComprobante (visualiza).
- **Flujo**:
  - **Pedido.frm**: `CuerpoStock` = `cuerpostockpe` (visualiza = 'No', CodUsuario = usuario). Al guardar, se inserta en **stockp** y se actualiza **stock_deposito** (saldo_pedido_cliente). No se persisten filas en `cuerpostockpe` como definitivas.
  - **Pedido_Interno.frm**: `CuerpoStock` = `cuerpostockpe`. Al guardar PEDI, se escribe en **stockp** y **movimiento_stock**; `cuerpostockpe` es solo buffer de edición.
- **Campos relevantes** (desde VB6): `CodigoMovimiento`, `CodUsuario`, `visualiza`, `IDArt`, `id_manual`, `Descripcion`, `Cantidad`, `cantidad_entregada`, `cantidad_pendiente`, `PrecioVentaxU`, `PrecioVentaxR`, `Pordesc`, `CodDeposito`, `orden`, `Alicuota`, `imp_alicuota_iva`, `Lista_Precio`, etc.
- **Relación**: `CodigoMovimiento` → `comp_ped.CodigoMovimiento`.

### `cuerpostockp` (Compras / Factura–Remito desde compras)

- **Uso**: Buffer temporal de **renglones de comprobantes de compras**: OC, remito compra, factura compra. También usado en flujos de factura/remito desde compras (PFactura, Lista_Comp_Gral).
- **Formularios**: PFactura (remito, OC, factura desde compras), Lista_Comp_Gral (Orden de compra, Remito, Factura, Presupuesto compras), ConsultaComprobante (reporte distinto al de pedidos).
- **Flujo**: Temporal `visualiza = 'No'` por usuario; al confirmar se persiste en otras tablas (p. ej. `stock` para movimientos). Se limpia con `DELETE FROM cuerpostockp WHERE CodUsuario = ... AND visualiza = 'No'`.
- **Campos relevantes**: `PrecioNetoxR`, `Orden`, `CodigoMovimiento`, `CodUsuario`, `visualiza`, `id_stock`, etc. En PFactura también `codmov_remito`, `codmov_oc`.

### `cuerpostock` (sin sufijo; selección para facturar desde Pedido Avanzado)

- **Uso**: Buffer temporal de **renglones seleccionados para facturar** en Pedido Avanzado (FacturaA / FacturaB).
- **Formularios**: Pedido_Avanzado (Factura M, Factura B, TPV).
- **Flujo**: Los renglones mostrados en Pedido Avanzado vienen de **stockp** (renglones definitivos de PED). El usuario marca ítems (`Seleccionado`); los elegidos se cargan en `cuerpostock` y de ahí se abre FacturaA/FacturaB. `cuerpostock` se enlaza a `stockp` por `CodigoMovimiento` + `id_stock`.
- **Limpieza**: `delete from cuerpostock` y `delete from cuerpostockpe` al cargar Pedido_Avanzado.

### Resumen rápido

| Tabla           | Uso principal                          | Comprobantes / flujo                         |
|-----------------|----------------------------------------|----------------------------------------------|
| **cuerpostockpe** | Buffer edición pedidos venta/interno   | PED, PEDI → al guardar se persiste en stockp |
| **cuerpostockp**  | Buffer compras (OC, remito, factura)   | Compras                                      |
| **cuerpostock**   | Buffer selección para factura (Pedido Avanzado) | Factura desde PED vía stockp          |

---

## 2. Renglones definitivos de pedidos: `stockp`

- **Uso**: Renglones **definitivos** de pedidos de venta (PED) y pedidos internos (PEDI). Aquí se persisten las líneas al guardar desde Pedido o Pedido_Interno.
- **Formularios**: Pedido (destino al guardar), Pedido_Avanzado (grid de renglones), Pedido_prep, Pedido_prep_consulta.
- **Relación**: `stockp.CodigoMovimiento` = `comp_ped.CodigoMovimiento`.
- **Campos relevantes**: `id_stock`, `CodigoMovimiento`, `IDArt`, `Cantidad`, `cantidad_entregada`, `cantidad_pendiente`, `cantidad_dividir`, `PrecioVentaxU`, `PrecioVentaxR`, `PrecioCostoxR`, `CodDeposito`, `CodigoCP`, etc. En Pedido_Avanzado se usan también `cantidad_div`, `cantidad_entregada_div`, `cantidad_pendiente_div` (calculados desde `cantidad_dividir`).
- **Pedido_Mod_Cant_Entregada**: Modifica “cantidad entregada” en el grid de Pedido_Avanzado, que está ligado a **stockp** (vía `Data_Renglon`).

---

## 3. Cabecera de pedidos: `comp_ped`

- **Uso**: Cabecera de pedidos de venta (PED), pedidos internos (PEDI), presupuestos (PRE).
- **Formularios**: Todos los de pedidos, preparación y listados.
- **Campos relevantes**: `CodigoMovimiento`, `TipoComprobante` (PED, PEDI, PRE), `Fecha`, `NroComprobante`, `NroCompBusq`, `Codigo` (cliente), `CodViajante`, `Estado` (Pendiente, En preparación, En Remito, Parcial, Cerrado, Facturado, etc.), `Anulado`, `id_condventa`, `ImporteVenta`, `id_pv`, `codSucursal`, `Detalle`, `Vencimiento`, `FechaEntrega`, `FormaEntrega`, `id_deposito_despacho`, `id_transporte`, `id_repartidor`, `fecha_control`, `Tipopedido`, `autorizacion_sistema`, etc.
- **FK**: `Codigo` → cliente, `CodViajante` → viajantes, `id_condventa` → cond_venta.

---

## 4. Stock e inventario

### `stock`

- **Uso**: Movimientos de stock (entrada/salida) por depósito, tipo de comprobante, etc.
- **Formularios**: Stock.frm (consulta por artículo, depósito, lote).
- **Relación**: `idart` → articulo, lotes vía `lote` / `lote_stock`. Se usa con `articulo`, `articulo_prov`, `unidmed`, `lote`.

### `stock_deposito`

- **Uso**: Saldo por artículo y depósito; reserva para pedidos (`saldo_pedido_cliente`) y pendiente por OC (`saldo_pedido_proveedor`).
- **Formularios**: Pedido, Visualiza_Pedido, Remito, FacturaA/B, TPV, PFactura, CargaMovStock, CargaArticulo, ConsultaComprobante (anulaciones), etc.
- **Informes**: BO vs Stock vs Facturación usa `stock_deposito` para disponible (`saldo`) y reservado (`saldo_pedido_cliente`).

#### Qué se guarda en cada campo (VB6)

| Campo | Operación | Dónde / cuándo | Valor |
|-------|-----------|----------------|-------|
| **id_stock_deposito** | — | — | PK; no se asigna en VB6 (auto). |
| **id_articulo** | AddNew | Alta artículo (CargaArticulo), anulaciones/mov. stock (nueva fila), Factura/TPV ensamble | `articulo.IDArt` o `stock.IDArt`. |
| **id_deposito** | AddNew | Mismos casos | `deposito.CodDeposito` o `stock.CodDeposito`. |
| **saldo** | AddNew / Update | **AddNew**: 0 al dar de alta artículo por depósito (CargaArticulo); ± cantidad al crear fila en anulaciones o mov. stock. **Update**: ± según entradas/salidas (CargaMovStock, Remito, Factura, anulaciones, recepción OC, etc.). | Stock físico por artículo-depósito. |
| **saldo_pedido_cliente** | Update | **+** al guardar PED (Pedido.frm, Visualiza_Pedido.frm): `saldo_pedido_cliente + Cantidad * cantidad_multiplicar`. **−** al emitir Remito/Factura “sobre pedido” (Remito, FacturaA, FacturaB, TPV) o al anular remito (ConsultaComprobante). No se asigna en AddNew (default 0). | Reserva por pedidos de venta; “dato estadístico”. |
| **saldo_pedido_proveedor** | AddNew / Update | **AddNew**: solo al anular OC si se crea fila nueva → `-Cantidad`. **Update**: **−** al anular OC/recepción; **+** al facturar OC (PFactura). | Pendiente por órdenes de compra; “dato estadístico”. |

- **Alta de filas**: CargaArticulo crea una fila por cada depósito al dar de alta un artículo (`Saldo = 0`, `id_articulo`, `id_deposito`). Si no existe fila, varios flujos (anulaciones, mov. stock, Factura/TPV ensamble) hacen AddNew con `id_articulo`, `id_deposito` y `saldo` según el movimiento.
- **Pedido**: Solo actualiza `saldo_pedido_cliente` cuando ya existe fila (`RecordCount > 0`); no crea filas. La fila suele existir por CargaArticulo o por un movimiento previo.

---

## 5. Artículos y categorías

### `articulo`

- **Uso**: Maestro de artículos.
- **Campos relevantes**: `IDArt`, `id_manual`, `NombreArticulo`, `CodigoRubro`, `IDSubRubro`, `codigoProveedor`, `Alicuota`, `moneda`, `cantidad_promedio_bulto`, `id_unimed`, `serie`, etc.
- **Relaciones**: `CodigoRubro` → rubro, `IDSubRubro` → subrubro.

### `rubro` / `subrubro`

- **Uso**: Categorías y subcategorías para informes y filtros.
- **Informes**: BO usa `rubro.NombreRubro` como categoría.

---

## 6. Clientes, vendedores, zonas

### `cliente`

- **Uso**: Maestro de clientes.
- **Campos**: `Codigo`, `nombre_cliente`, `id_manual_cli`, `id_zona`, `CodProvincia`, `IDDepartamento`, `IDDistrito`, `CodViajante`, etc.

### `viajantes`

- **Uso**: Vendedores.
- **Relación**: `comp_ped.CodViajante` → `viajantes.CodViajante`.

### `erp_zona`

- **Uso**: Zonas de venta.
- **Formularios**: Pedido_Avanzado, Pedido_prep (filtros por zona).

---

## 7. Otros

### `deposito` / `deposito_usr`

- Depósitos; restricción por usuario cuando aplica.

### `cond_venta`

- Condiciones de venta; usadas en pedido y factura.

### `talonarios`

- Puntos de venta y numeración (PED, PEDI, PREP, etc.).

### `codmov`

- Contador de `CodigoMovimiento` para comprobantes.

### `movimiento_stock`

- Cabecera de movimientos de stock (Pedido_Interno guarda ahí).

### `lote` / `lote_stock`

- Lotes y vencimientos; Stock.frm y facturación con lote.

### `ped_prep` / `prepp_datos` / `ped_prep_temp`

- Preparación de pedidos (Pedido_prep); relación con `comp_ped` vía `ped_numeracion` = `CodigoMovimiento`.

---

## 8. Validaciones para informes

### 8.1 BO vs Stock vs Facturación – renglones de backorder

- **Estado actual**: El informe usa **stockp** + **comp_ped** para renglones de backorder (detalle agregado y row-level). `cant_pend` = `stockp.cantidad_pendiente`.
- **En VB6**: Los renglones **definitivos** de PED se guardan en **stockp**; **cuerpostockpe** es solo buffer de edición. Pedido_Avanzado muestra renglones desde **stockp**.

### 8.2 Precio e importes en renglones

- **stockp** incluye `PrecioVentaxR`, `PrecioVentaxU`, `cantidad_entregada`, `cantidad_pendiente`. El informe BO usa **stockp**; importes solo desde `PrecioVentaxR` (sin fallback; si es 0 es correcto).

### 8.3 CON INGRESO (Backorder con ingreso)

- **Definición:** Cantidades en **órdenes de compra aprobadas y pendientes de entrega**.
- **Origen:** `stock_deposito.saldo_pedido_proveedor` agregado por `id_articulo` (`oc_pendiente`). **Prioridad:** (1) Stock cubre primero reservado; disponible = max(0, stock − reservado). (2) OC pend. cubre primero el faltante de reservado (max(0, reservado − stock)); solo el resto se usa para BO. (3) Clasificación BO: **con stock** = min(BO, disponible); **con ingreso** = min(resto BO, OC restante para BO); **sin stock** = resto.
- **Tooltip OC pend. qty:** Por artículo, se consulta detalle de OC pendientes (`stockp` + `cuentaproveedor` + `proveedor`, `TipoComprobante = 'OC'`, `Estado = 'Pendiente'`). El tooltip muestra por cada OC: fecha creación/aprobación, número, vencimiento (fecha entrega), proveedor y cantidad pendiente. Mismo estilo visual que los tooltips de los gráficos de ventas-netas (fondo oscuro, bordes, separadores, label/valor).

### 8.4 Detalle sin stock

- **Origen:** Filas de `backorder_detalle` con `sin_stock_qty > 0`, ordenadas por `sin_stock_importe` DESC.
- **Vista:** Detalle por artículo (codigo, articulo, categoria, bo_qty, bo_importe, stock, reservado, disponible, oc_pendiente, sin_stock_qty, sin_stock_importe). La vista por categoría se obtiene con **Agrupar por → Categoría**, misma lógica que Facturación, Remitos y Backorder detalle.

### 8.5 Diferencias `cuerpostockp` vs `cuerpostockpe`

- **cuerpostockpe:** pedidos de venta (PED) y pedidos internos (PEDI); buffer temporal → persistencia en **stockp**.
- **cuerpostockp:** compras (OC, remito, factura compra); buffer temporal en esos flujos.
- No usar **cuerpostockp** para informes de backorder de **ventas**; esos flujos son de compras.

---

## 9. Resumen por informe

| Informe | Tablas principales | Notas |
|--------|---------------------|-------|
| **BO vs Stock vs Facturación** | comp_ped, **stockp**, stock_deposito, articulo, rubro, cliente, viajantes | Renglones BO desde stockp; cant_pend = cantidad_pendiente. CON INGRESO = OC aprobadas pend. entrega (saldo_pedido_proveedor). Detalle sin stock por artículo; agrupar por categoría para vista por rubro. Si >1 depósito, nota. |
| **Ventas netas / Facturación** | cuentacliente, sucursales, punto_venta | FA–FM, NCA–NCM, SubtotalDesc; filtros período, sucursal, PV. Ver `VALIDACION_VENTAS_NETAS.md`. |
| **Remitos no facturados** | comp_ped (remitos), comprobantes vinculados | Según configuración de remitos en VB6. |
| **Pedidos pendientes** | comp_ped (PED) | Estado IN ('En preparación', 'Preparado'); SubtotalDesc. Ver `VALIDACION_PEDIDOS_PENDIENTES.md`. |

---

## 10. Formularios analizados

| Formulario | Ubicación | Tablas principales |
|------------|-----------|--------------------|
| Pedido_Avanzado | `administranet_vb6/Formularios/Pedido_Avanzado.frm` | comp_ped, stockp, cuerpostock, cuerpostockpe, cliente, viajantes, cond_venta, erp_zona, deposito |
| Pedido | `administranet_vb6/Formularios/Pedido.frm` | comp_ped, cuerpostockpe, stockp, stock_deposito, cliente, cond_venta, talonarios, codmov, cuentacliente |
| Pedido_prep | `administranet_vb6/Formularios/Pedido_prep.frm` | comp_ped, stockp, ped_prep, prepp_datos, cliente, erp_zona, viajantes, articulo, usuarios |
| Pedido_Interno | `administranet_vb6/Formularios/Pedido_Interno.frm` | comp_ped, cuerpostockpe, stockp, movimiento_stock, deposito, talonarios, codmov |
| Stock | `administranet_vb6/Formularios/Stock.frm` | stock, articulo, lote, lote_stock, stock_deposito, articulo_prov, unidmed, deposito |
| Pedido_prep_consulta | `administranet_vb6/Formularios/Pedido_prep_consulta.frm` | comp_ped, ped_prep, stockp, cliente |
| Pedido_Mod_Cant_Entregada | `administranet_vb6/Formularios/Pedido_Mod_Cant_Entregada.frm` | Modifica cantidad entregada en grid (stockp) desde Pedido_Avanzado, Logi_Gestion, etc. |

---

## 11. Referencias

- **Rendimiento y error 3024 (BO)**: `reports/BO_REPORT_PERFORMANCE.md`
- **BO IMPORTE / CON STOCK IMPORTE**: `BO_REPORT_PERFORMANCE.md` § "BO IMPORTE y CON STOCK IMPORTE" (solo PrecioVentaxR; si es 0 es correcto).
- **Pedidos pendientes**: `reports/docs/VALIDACION_PEDIDOS_PENDIENTES.md` (validación de consultas y datos frente a VB6).
- **Ventas netas**: `reports/docs/VALIDACION_VENTAS_NETAS.md` (validación de consultas y datos frente a VB6).

---

*Documento generado a partir del análisis de los formularios VB6 indicados. Revisar con esquema real de la base y reglas de negocio antes de aplicar cambios en informes.*
