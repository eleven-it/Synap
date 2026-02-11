# Info_Compra.frm — Estructura de tablas y campos (Compras y Proveedores)

Documento extraído del formulario **Info_Compra.frm** (informes de compras en administraNET VB6). Sirve como base para rastrear procesos que impactan stock en otros formularios.

---

## 1. Tablas principales

### 1.1 `cuentaproveedor` — Cabecera de comprobantes de compras

Tabla central para informes de compras. Contiene la cabecera de facturas, órdenes de compra, notas de crédito/débito, presupuestos, etc.

| Campo | Uso en Info_Compra | Descripción inferida |
|-------|-------------------|----------------------|
| **CodigoMovimiento** | Filtro `<> 0` (excluir movimientos vacíos) | PK o ID del movimiento |
| **CodSucursal** | Filtro sucursal | Sucursal del comprobante |
| **TipoComprobante** | FA, FB, FC, FE, FM (facturas), NC (nota crédito), ND (nota débito), OC (orden compra), PRE (presupuesto), EB | Tipo de comprobante |
| **Fecha** | Rango fecha | Fecha del comprobante |
| **FechaRegistro** | (comentado) Alternativa a Fecha | Fecha de registro |
| **Estado** | Pendiente, En preparación, etc. | Estado del comprobante |
| **Anulado** | 'No' (excluir anulados) | Si está anulado |
| **idUsuario** | Filtro por usuario responsable | Usuario que cargó |
| **TipoNC** | 'Importe' (para NC) | Tipo de nota de crédito |
| **Codigo** | (en comentario) id_proveedor | FK a proveedor |

**Relaciones inferidas:**
- `cuentaproveedor.Codigo` → `proveedor.Codigo`
- `cuentaproveedor.CodigoMovimiento` → enlace a renglones (stock, stockp, cuerpostockp, etc.)

---

### 1.2 `proveedor` — Maestro de proveedores

| Campo | Uso en Info_Compra |
|-------|-------------------|
| **Codigo** | PK, filtro por proveedor |
| **tipo** | Filtro por tipo de proveedor |
| **CodProvincia** | (implícito vía provincia) |
| **idDepartamento** | (implícito vía departamento) |
| **idDistrito** | (implícito vía distrito) |

**Relaciones:**
- `proveedor.CodProvincia` → `provincia.CodProvincia`
- `proveedor` → `provincia`, `departamento`, `distrito` (para reportes por ubicación geográfica)

---

### 1.3 `stock` — Movimientos de stock (compras)

Usado en reportes de **compras por rubro/subrubro**, **diferencia de cambio** y **gastos totalizados**. Representa movimientos de entrada/salida ligados a comprobantes de compra.

| Campo | Uso en Info_Compra |
|-------|-------------------|
| **idart** | Filtro por artículo |
| **TipoComp** | 'Compra', 'Devol - Proveedor', 'ND Anul NC', 'Anul NC Devol', 'Anul Compra' |
| **Comprobante** | FA, FB, FC, FE, FM (facturas de compra) |
| **CodigoGasto** | Filtro `<> 0` o `ISNULL/0` para excluir gastos en reportes de artículos |
| **Fecha** | (comentado en gastos) |

**Relación con cuentaproveedor:**
- `stock` se relaciona con `cuentaproveedor` por `CodigoMovimiento` (en los reportes .rpt).

---

### 1.4 `articulo` — Maestro de artículos

| Campo | Uso en Info_Compra |
|-------|-------------------|
| **IDArt** | PK |
| **id_manual** | Código manual |
| **NombreArticulo** | Descripción |
| **CodigoRubro** | FK a rubro |
| **IDSubRubro** | FK a subrubro |
| **Moneda** | 'Dolar' (reporte diferencia de cambio) |

---

### 1.5 `art_comp` — Vista o tabla de artículos comprados

Usada en reportes **Ranking artículo** y **Resumen condición de venta**. Parece ser una vista agregada por artículo y compra.

| Campo | Uso en Info_Compra |
|-------|-------------------|
| **CodSucursal** | Filtro sucursal |
| **Fecha** | Rango de fechas |

**Comentario en código:** "Tabla: art_comp (Vista), Registro Nro 54, campo calculado de suma de entrada"

---

### 1.6 `gastos` — Maestro de gastos

| Campo | Uso en Info_Compra |
|-------|-------------------|
| **codigo** | Filtro por gasto (compras_gasto_totalizado.rpt) |

**Relación:** `stock.CodigoGasto` → `gastos.codigo`

---

### 1.7 `caja_abm` — Cajas de cobro/pago

| Campo | Uso en Info_Compra |
|-------|-------------------|
| **id_caja** | Filtro por caja (compras_periodo_caja.rpt) |

**Relación:** usado junto a `cuentaproveedor` para filtrar compras por caja de pago.

---

### 1.8 Tablas auxiliares (maestros)

| Tabla | Campos usados |
|-------|----------------|
| **sucursales** | id_sucursal, nombre_sucursal |
| **rubro** | CodigoRubro, NombreRubro |
| **subrubro** | IDSubRubro |
| **provincia** | CodProvincia |
| **departamento** | IDDepartamento, NombreDepartamento |
| **distrito** | IDDistrito |
| **usuarios** | id_usuario, nombre_usuario |
| **reporte_usuario** | id_reporte, nombre_reporte, perfil_reporte = 'Compras' |
| **cotizacion** | ValorPesos (para reportes en dólares) |

---

## 2. Tipos de comprobante (TipoComprobante)

| Código | Descripción | Reportes |
|--------|-------------|----------|
| FA, FB, FC, FE, FM | Facturas de compra | Compras periodo, proveedor, usuario, rubro, gastos, etc. |
| NC | Nota de crédito | ND proveedor, NC periodo |
| ND | Nota de débito | ND proveedor |
| EB | (incluido en filtros) | Compras periodo |
| OC | Orden de compra | OC proveedor, OC detalle |
| PRE | Presupuesto compras | Presup proveedor, detalle |

---

## 3. Reportes Crystal y tablas que usan

| Reporte .rpt | Tablas principales |
|--------------|--------------------|
| compras_periodo.rpt | cuentaproveedor, proveedor |
| compras_periodo_detalle.rpt | cuentaproveedor, proveedor |
| compras_proveedor.rpt | cuentaproveedor, proveedor |
| compras_nd_proveedor.rpt | cuentaproveedor, proveedor |
| compras_usuario.rpt | cuentaproveedor |
| compras_tipoproveedor.rpt | cuentaproveedor, proveedor |
| compras_provincia*.rpt | cuentaproveedor, proveedor, provincia, departamento, distrito |
| compras_rubro*.rpt | cuentaproveedor, stock, articulo, rubro, subrubro |
| compras_facturas_detalle_proveedor.rpt | cuentaproveedor, proveedor |
| compras_nc_periodo.rpt | cuentaproveedor |
| compras_ranking_articulo_vista.rpt | art_comp |
| compras_resumen_cond_venta.rpt | art_comp |
| compras_oc_*.rpt, compras_presup_*.rpt | cuentaproveedor, proveedor |
| compras_gasto_totalizado.rpt | cuentaproveedor, stock, gastos |
| compras_periodo_caja.rpt | cuentaproveedor, caja_abm |
| compras_diferencia_cambio.rpt | cuentaproveedor, stock, articulo, proveedor |
| compras_articulo*.rpt | cuentaproveedor, stock, articulo |
| compras_lista_factura_remito_compra.rpt | cuentaproveedor |

---

## 4. Conexión con stock e impacto en inventario

### 4.1 Flujo compras → stock

Según **CONTEXTO_TABLAS_VB6_INFORMES.md** y **Info_Compra**:

1. **cuentaproveedor** = cabecera de comprobantes de compras (OC, remito, factura compra).
2. **stock** = movimientos de stock; `stock.TipoComp` indica tipo de movimiento:
   - 'Compra' — entrada por factura compra
   - 'Devol - Proveedor' — devolución a proveedor
   - 'ND Anul NC', 'Anul NC Devol', 'Anul Compra' — anulaciones
3. **stock_deposito** = saldos por artículo-depósito; `saldo_pedido_proveedor` se actualiza con OC (según CONTEXTO).
4. **cuerpostockp** = buffer temporal de renglones de compras (OC, remito, factura) hasta persistir en `stock` y otros.

### 4.2 Tablas a revisar en formularios de proceso

Para rastrear cómo las compras afectan stock, revisar formularios que:

- Inserten/actualicen **cuentaproveedor**
- Inserten/actualicen **stock** con `TipoComp` de compras
- Actualicen **stock_deposito.saldo_pedido_proveedor**
- Usen **cuerpostockp** (buffer de renglones)
- Usen **stockp** cuando comp_ped/cuentaproveedor vinculen pedidos con OC

**Formularios sugeridos (según CONTEXTO):**
- **PFactura** — remito, OC, factura desde compras (cuerpostockp)
- **Lista_Comp_Gral** — OC, remito, factura, presupuesto compras
- **ConsultaComprobante** — anulaciones
- **CargaMovStock** — movimientos manuales de stock
- **Stock_Control_Entrada** — control de entradas

---

## 5. Campos de fecha

Info_Compra usa la variable `tipoFecha`, que puede ser:
- `Fecha`
- `FechaRegistro`

Según el reporte, se filtra por rango de fechas en `cuentaproveedor`.

---

## 6. Resumen para trazabilidad stock

| Tabla | Rol en compras | Impacto en stock |
|-------|----------------|------------------|
| **cuentaproveedor** | Cabecera OC, factura, NC, ND, presupuesto | Origen de CodigoMovimiento que dispara movimientos |
| **stock** | Movimientos de compra (TipoComp, Comprobante) | Entrada/salida de inventario |
| **stock_deposito** | Saldos por artículo-depósito | saldo, saldo_pedido_proveedor |
| **cuerpostockp** | Buffer renglones compras | Persistencia en stock |
| **stockp** | Renglones definitivos PED/PEDI | También usado en OC (cuentaproveedor.TipoComprobante='OC') |
| **proveedor** | Maestro | Solo datos de proveedor |
| **articulo, rubro, subrubro** | Maestros | Clasificación de artículos |

---

## 7. Análisis de formularios que impactan stock (descubrimiento)

### 7.1 PFactura.frm — Factura de compras

**Rol:** Emite facturas de compra (desde OC, remito o directo). Es el punto donde la compra ingresa formalmente a stock.

**Tablas que escribe:**
- **cuentaproveedor** — AddNew con cabecera FA/FB/FC/FE/FM (Factura, Factura OC, Factura Remito)
- **stock** — AddNew por cada renglón (movimiento de entrada)
- **stock_deposito** — Update de `Saldo` y `saldo_pedido_proveedor`

**Lógica de stock_deposito:**
1. **Saldo:** Aumenta (`+`) la cantidad recibida según multiplicadores (bulto/display).
2. **saldo_pedido_proveedor:** Si es "Factura OC" y el renglón tiene `codmov_oc`:
   - Busca en `stockp` la cantidad por `IDArt` + `CodigoMovimiento` (OC)
   - `saldo_pedido_proveedor = saldo_pedido_proveedor + Cantidad` de stockp

**Fuente de renglones:** `cuerpostockp` (buffer) con `CodigoMovimiento` del comprobante origen (OC o remito).

---

### 7.2 Lista_Comp_Gral.frm — Listado de comprobantes de compras

**Rol:** Lista OC, remitos, facturas, presupuestos. Abre PFactura, PRemito, POrden_Compra, etc.

**Tablas que lee (no escribe directamente):**
- **cuentaproveedor** — Cabecera (TrasDetalle "cuentaproveedor")
- **stockp** — Renglones de OC (para cargar en cuerpostockp de PFactura/PRemito)
- **stock** — Renglones de remito ya facturado (para cargar en cuerpostockp de PFactura)
- **cuerpostockp** — Buffer temporal; valida `visualiza='No' AND CodigoMovimiento = X`
- **stock_deposito** — Consulta saldo por artículo (solo lectura para grilla)

**Flujo típico:**
- OC → stockp; Remito → stock (cuentaproveedor REM); Factura → stock + stock_deposito.
- Al abrir "Facturar" desde remito: lee `stock` del remito y copia a `cuerpostockp` de PFactura.
- Al abrir "Facturar" desde OC: lee `stockp` de la OC y copia a `cuerpostockp` de PFactura.

---

### 7.3 CargaMovStock.frm — Movimientos de stock manuales

**Rol:** Ajustes, transferencias, stock inicial. No pasa por cuentaproveedor.

**Tablas que escribe:**
- **stock** — AddNew por cada renglón (Entrada/Salida)
- **stock_deposito** — Update de `Saldo` (entrada: `+`, salida: `-`)
- **movimiento_stock** — Cabecera del movimiento (MSTOCK)
- **talonarios** — Numeración MSTOCK

**Lógica:**
- Lee `cuerpostock` (o similar) como buffer.
- Por cada línea: actualiza `stock_deposito` (entrada/salida según `ES`), inserta en `stock`.
- Usa `ref_movstock` para tipo de referencia.

---

### 7.4 ConsultaComprobante.frm — Anulaciones

**Rol:** Consulta y anulación de comprobantes (ventas, compras, stock).

**Para compras (cuentaproveedor):** Llama a `Anular_Compras` (no mostrado en grep; existe por Case "keyAnular").

**Para stock (MSTOCK, remito compra, etc.):** `Anular_Stock`:
- **stock** — `anulado = 'Si'` en los renglones del movimiento
- **stock** — AddNew registro de anulación (contramovimiento) con `anulado = 'No'`
- **stock_deposito** — Resta la cantidad (`Saldo = Saldo - Cantidad`)
- **saldo_pedido_proveedor** — Resta: `saldo_pedido_proveedor - Cantidad` (o asigna `-Cantidad` si no había fila)

**Tablas adicionales según tipo:**
- Remito compra: `cuentaproveedor` (comp_ped), `stock`
- MSTOCK: `movimiento_stock`, `stock`

---

### 7.5 Stock_Control_Entrada.frm — Control de entrada

**Rol:** Consulta/control de entregas (hoja de ruta, cliente). No parece modificar stock de compras; usa `cuentacliente` y `stock` de ventas.

**Tablas que lee:**
- `cliente_datos_adicionales`, `cuentacliente`, `stock`, `articulo`

---

### 7.6 Formularios que actualizan saldo_pedido_proveedor

| Formulario | Acción | Efecto en saldo_pedido_proveedor |
|------------|--------|----------------------------------|
| **POrden_Compra** / Visualiza_POrden_Compra | Crear/aprobar OC | **+** Cantidad |
| **PFactura** / Visualiza_PFactura | Facturar OC | **+** Cantidad (stockp) |
| **PRemito** / Visualiza_PRemito | Emitir remito desde OC | **+** Cantidad (stockp) |
| **ConsultaComprobante** | Anular remito/OC | **−** Cantidad |

---

### 7.7 Flujo resumido: Compras → Stock

```
OC (POrden_Compra)     → cuentaproveedor + stockp + stock_deposito.saldo_pedido_proveedor (+)
Remito (PRemito)       → cuentaproveedor + stock + stock_deposito.Saldo (+) + saldo_pedido_proveedor (+)
Factura (PFactura)     → cuentaproveedor + stock + stock_deposito.Saldo (+) + saldo_pedido_proveedor (+) si Factura OC
CargaMovStock          → stock + stock_deposito.Saldo (±) [sin cuentaproveedor]
Anulación (ConsultaC.) → stock.anulado, stock_deposito.Saldo (−), saldo_pedido_proveedor (−)
```

---

## 8. Formularios adicionales (descubrimiento ampliado)

### 8.1 POrden_Compra.frm — Orden de compra

**Rol:** Alta y edición de órdenes de compra. Es el origen del flujo OC → Remito → Factura.

**Tablas que escribe:**
- **cuentaproveedor** — AddNew, TipoComprobante = 'OC', Estado = 'Pendiente'
- **stockp** — AddNew por cada renglón (renglones definitivos de la OC)
- **stock_deposito** — Update de `saldo_pedido_proveedor` (+)

**Lógica:**
- Lee renglones desde `cuerpostockp` (buffer).
- Inserta cabecera en cuentaproveedor.
- Por cada renglón: inserta en **stockp** (no en stock) y actualiza `stock_deposito.saldo_pedido_proveedor += Cantidad`.
- stockp almacena: Cantidad, cantidad_entregada, cantidad_pendiente, CodigoMovimiento (OC), Comprobante='OC', TipoComp='Compra'.

---

### 8.2 PRemito.frm — Remito de compra

**Rol:** Emite remitos de compra (desde OC o directo). Primera recepción física de mercadería.

**Tablas que escribe:**
- **cuentaproveedor** — AddNew, TipoComprobante = 'REM', estado_remito = 'Pendiente'
- **stock** — AddNew por cada renglón (TipoComp = 'Remito Entrada', Comprobante = 'REM')
- **stock_deposito** — Update de `Saldo` (+) y `saldo_pedido_proveedor` (+) si viene de OC

**Lógica saldo_pedido_proveedor:**
- Si el renglón tiene `nro_oc` / `codmov_oc`: busca en stockp la cantidad por IDArt + CodigoMovimiento (OC) y suma a `saldo_pedido_proveedor`.
- Actualiza `Saldo` con la cantidad recibida (con multiplicadores bulto/display).

**Origen:** cuerpostockp (desde Lista_Comp_Gral, cargado desde stockp de OC o desde stock de remito previo).

---

### 8.3 Visualiza_POrden_Compra.frm — OC desde módulo visualización

**Rol:** Crear/editar OC desde el módulo de carga de comprobantes de proveedor (CargaComprobantesP). Comportamiento equivalente a POrden_Compra.

**Tablas:** Idénticas a POrden_Compra (cuentaproveedor, stockp, stock_deposito.saldo_pedido_proveedor).

---

### 8.4 Visualiza_PRemito.frm — Remito desde módulo visualización

**Rol:** Emitir remito de compra desde CargaComprobantesP. Equivalente a PRemito.

**Tablas:** Idénticas a PRemito (cuentaproveedor, stock, stock_deposito).

---

### 8.5 ConsultaComprobante — Anulaciones de compras

**Anular_Compras** delega según TipoComprobante:

| TipoComprobante | Procedimiento           | Tablas afectadas |
|-----------------|-------------------------|------------------|
| FA, FB, FC, FM  | Anular_Compras_Factura  | cuentaproveedor, stock, stock_deposito.Saldo, caja, imputación |
| PRE             | Bloque específico       | cuentaproveedor, stockp, stock_deposito.saldo_pedido_proveedor |
| OC              | (bloque OC)             | cuentaproveedor, stockp, stock_deposito.saldo_pedido_proveedor |
| REM             | (bloque REM)            | cuentaproveedor, stock, stock_deposito |

**saldo_pedido_proveedor en anulaciones:**
- Anular **Presupuesto** o **OC** (stockp): `saldo_pedido_proveedor -= Cantidad`.
- Si no existe fila en stock_deposito: AddNew con `saldo_pedido_proveedor = -Cantidad`.

** stock / Saldo en anulaciones:**
- Factura compra: marca stock.anulado='Si', inserta contramovimiento, resta Saldo si remite_factura_art.
- Remito compra: similar, resta Saldo.

---

### 8.6 Diferencia OC vs Remito vs Factura

| Comprobante | Tabla renglones | stock_deposito.Saldo | stock_deposito.saldo_pedido_proveedor |
|-------------|-----------------|----------------------|--------------------------------------|
| **OC**      | stockp          | No modifica          | + al crear, − al anular              |
| **REM**     | stock           | + al emitir          | + si viene de OC                     |
| **FA/FB/FC/FM** | stock       | + al facturar (si no es "Factura Remito") | + si Factura OC |

---

### 8.7 Flujo completo compras → stock (actualizado)

```
Presupuesto (PRE)  → cuentaproveedor + cuerpostockp (solo buffer, no persistido como stockp)
        ↓
OC (POrden_Compra) → cuentaproveedor + stockp + stock_deposito.saldo_pedido_proveedor (+)
        ↓
Remito (PRemito)   → cuentaproveedor + stock + stock_deposito.Saldo (+) + saldo_pedido_proveedor (+) si nro_oc
        ↓
Factura (PFactura) → cuentaproveedor + stock + stock_deposito.Saldo (+) + saldo_pedido_proveedor (+) si Factura OC

CargaMovStock      → stock + stock_deposito.Saldo (±) [sin cuentaproveedor]
Anulación          → stock/stockp.anulado, stock_deposito.Saldo (±), saldo_pedido_proveedor (−) para OC/PRE
```

---

*Generado a partir de Info_Compra.frm, PFactura, Lista_Comp_Gral, CargaMovStock, ConsultaComprobante, Stock_Control_Entrada, POrden_Compra, PRemito, Visualiza_POrden_Compra, Visualiza_PRemito.*
