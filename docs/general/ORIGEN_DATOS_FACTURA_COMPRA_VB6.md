# Origen de datos para Factura de Compra (VB6) — Mapa completo

En VB6 **no son “tipos de factura”** sino **orígenes desde donde se toman los datos** para armar la factura. El mismo formulario PFactura.frm se abre con una variable `TipoComprobante` que indica el **origen** y cambia la UI y la lógica de guardado.

---

## 1. Los cuatro orígenes en CargaComprobantesP y PFactura

| Origen (menú CargaComprobantesP) | key | PFactura.TipoComprobante | Qué datos se usan para armar la factura |
|----------------------------------|-----|---------------------------|----------------------------------------|
| Factura de Compra (manual)       | keyFact | `"Factura"`           | Sin origen: el usuario carga renglones a mano en cuerpostockp. |
| Factura de Compra / Remito       | keyFactRem | `"Factura Remito"` | Renglones desde **remitos de compra** pendientes (cuentaproveedor TipoComprobante='REM', estado_remito='Pendiente'). Se copian a cuerpostockp con `codmov_remito`. |
| Factura de Compra / Orden de Compra | keyFactOC | `"Factura OC"`    | Renglones desde **órdenes de compra** pendientes (cuentaproveedor TipoComprobante='OC', Estado='Pendiente' o 'Parcial'). Se copian a cuerpostockp con `codmov_oc`. |
| Factura de Compra / Vale          | keyFactVALE | `"Factura Vale"`   | Importes/renglones desde **vales** (liquidación): en_vale_viaje, en_vale_factura_temp → al confirmar en_vale_factura y estado vales 'En Factura'. |

---

## 2. Flujo por origen (VB6)

### 2.1 Origen: ninguno (`TipoComprobante = "Factura"`)

- CargaComprobantesP asigna `PFactura.TipoComprobante = "Factura"` y no muestra ListaRem ni ListaVales.
- Usuario en PFactura: encabezado (proveedor, fechas, nro, etc.) + agrega ítems manualmente (artículo, cantidad, precio) al buffer **cuerpostockp** (CodigoMovimiento=0 hasta guardar).
- Al generar: cuentaproveedor (cabecera FA/FB/FC), stock (renglones), stock_deposito.Saldo (+), op_factura. No hay vínculo con remito ni OC.

### 2.2 Origen: Remito (`TipoComprobante = "Factura Remito"`)

- CargaComprobantesP asigna `PFactura.TipoComprobante = "Factura Remito"` y hace `PFactura.ListaRem.Visible = True`.
- Usuario en PFactura: hace clic en **ListaRem** (“Listado de Remitos”) → se abre **Lista_Comp_Gral** con:
  - `TipoComprobante = "Remito de Compra"`
  - Filtro: cuentaproveedor Anulado='No', TipoComprobante='REM', Codigo=proveedor, estado_remito='Pendiente'
  - Grilla de comprobantes (remitos) y grilla de renglones; F11 = agrega ítem del renglón, F12 = agrega comprobante completo.
- Al elegir remito(s), los renglones se copian a **cuerpostockp** del usuario con `codmov_remito` = CodigoMovimiento del remito (y nro_remito).
- Al **Generar** en PFactura:
  - Se valida que exista al menos un renglón con `codmov_remito` (rs_hayremito).
  - cuentaproveedor: TipoFactura = `"Factura Remito"`.
  - **No** se vuelve a dar de alta stock por ítem (el stock ya se dio de alta en el Remito de compra); en cambio se actualiza la relación remito–factura y el estado del remito:
    - `remp_factp`: relación codigo_movimientof (factura) ↔ codigo_movimientor (remito).
    - cuentaproveedor del remito: estado_remito pasa a “Facturado” (o similar).
  - stock: sí se insertan registros (según código PFactura) pero con lógica que evita duplicar movimiento de stock; remp_factp vincula factura con remito.

### 2.3 Origen: Orden de Compra (`TipoComprobante = "Factura OC"`)

- CargaComprobantesP asigna `PFactura.TipoComprobante = "Factura OC"` y hace `PFactura.ListaRem.Visible = True`, `ListaRem.ToolTipText = "Lista de Ordenes de compra"`.
- Usuario hace clic en **ListaRem** → se abre **Lista_Comp_Gral** con:
  - `TipoComprobante = "Orden de Compra"`
  - Filtro: cuentaproveedor Anulado='No', TipoComprobante='OC', Codigo=proveedor, Estado='Pendiente' OR 'Parcial'
  - Comprobantes = OC; renglones = **stockp** (renglones de la OC).
- Al elegir OC(s), los ítems se copian a **cuerpostockp** con `codmov_oc` (y nro_oc, id_stock de stockp).
- Al **Generar**:
  - Se valida que exista al menos un renglón con `codmov_oc` (rs_hayOC).
  - cuentaproveedor: TipoFactura = `"Factura OC"`.
  - stock: AddNew por renglón; stock_deposito.Saldo (+); stockp: remitido_facturado y saldo_pedido_proveedor según lógica (resta pendiente OC).
  - op_factura, pedido_factura (codigo_movimiento_oc) para trazabilidad OC → factura.

### 2.4 Origen: Vale (`TipoComprobante = "Factura Vale"`)

- CargaComprobantesP asigna `PFactura.TipoComprobante = "Factura Vale"` y hace `PFactura.ListaVales.Visible = True`, `LabelVales.Visible = True`.
- Usuario hace clic en **ListaVales** → se abre **En_Liquidacion_Vales** (liquidación de vales): filtros (transporte, temporada, productor, chofer, materia prima), listas “Vales a liquidar” / “Vales seleccionados”, total neto. Los vales seleccionados se cargan en **en_vale_factura_temp** (id_usuario, codmov_vale).
- Al **Generar** en PFactura:
  - Se valida que exista al menos un registro en en_vale_factura_temp (rs_hay_vale).
  - cuentaproveedor (cabecera factura); renglones/importes según liquidación de vales.
  - `en_vale_factura`: relación CodMovVale ↔ CodMovFactura desde en_vale_factura_temp.
  - `en_vale_viaje`: estado = 'En Factura' para los vales liquidados.

---

## 3. Tablas y buffers implicados por origen

| Origen   | Origen de datos (lectura) | Buffer / temporal | Al guardar (escritura además de cuentaproveedor) |
|----------|---------------------------|-------------------|--------------------------------------------------|
| Factura  | —                         | cuerpostockp (manual) | stock, stock_deposito, op_factura |
| Remito   | cuentaproveedor REM + stock (renglones remito) | cuerpostockp (codmov_remito, nro_remito) | remp_factp, estado remito Facturado; stock según PFactura (vinculado a remito) |
| OC       | cuentaproveedor OC + stockp (renglones OC)     | cuerpostockp (codmov_oc, nro_oc, id_stock) | stock, stock_deposito, stockp (remitido_facturado), saldo_pedido_proveedor, pedido_factura |
| Vale     | en_vale_viaje, en_vale_factura_temp            | en_vale_factura_temp (id_usuario, codmov_vale) | en_vale_factura, en_vale_viaje.estado |

---

## 4. UI en PFactura según origen

- **Factura (manual):** Solo encabezado + cuerpo + pie. No se muestra ListaRem ni ListaVales.
- **Factura Remito:** TabFactura con ListaRem visible; botón “Listado de Remitos” abre Lista_Comp_Gral (Remito de Compra).
- **Factura OC:** Mismo control ListaRem visible; texto “Lista de Ordenes de compra”; abre Lista_Comp_Gral (Orden de Compra).
- **Factura Vale:** ListaVales y LabelVales visibles; botón “Vales” abre En_Liquidacion_Vales.

En los cuatro casos el **resultado** es un comprobante de tipo factura (FA/FB/FC según IDIVA); lo que cambia es **de dónde se obtienen los renglones/importes** y qué tablas adicionales se actualizan al guardar.

---

## 5. Nomenclatura recomendada en Synap

- No usar “tipo de factura” para estos cuatro casos.
- Usar **“Origen de datos”** o **“Origen del comprobante”** con valores:
  - **Sin origen** (o “Manual”): factura cargada íntegramente a mano.
  - **Desde Remito**: datos desde remitos de compra pendientes.
  - **Desde Orden de compra**: datos desde OC pendientes.
  - **Desde Vale**: datos desde liquidación de vales.

En la pantalla única de Factura de Compra en Synap, el selector debe etiquetarse por ejemplo como **“Origen de los datos”** con las opciones: *Manual*, *Desde Remito*, *Desde Orden de compra*, *Desde Vale*, y según la opción mostrar el panel correspondiente (selector de remitos, de OC, o liquidación de vales) y reutilizar la misma lógica de guardado que VB6 vía legacy_db.

---

## 6. Referencias

- CargaComprobantesP.frm: Case "keyFact", "keyFactRem", "keyFactOC", "keyFactVALE" (asignación de TipoComprobante y visibilidad ListaRem/ListaVales).
- PFactura.frm: TipoComprobante, ListaRem_Click, ListaVales_Click, Generar (validaciones por TipoComprobante y escritura en remp_factp, stock, stockp, en_vale_factura, etc.).
- INFO_COMPRA_TABLAS_CAMPOS.md: tablas cuerpostockp, stockp, stock, cuentaproveedor, remp_factp, flujos Remito/OC/Factura.
