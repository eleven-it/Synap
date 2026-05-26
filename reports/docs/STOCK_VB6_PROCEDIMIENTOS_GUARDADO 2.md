# Tabla `stock` en AdministraNET (VB6): procedimientos y lógica de guardado

Documento que lista **todos los formularios/procedimientos que escriben en la tabla `stock`** y cómo lo hacen, para entender la lógica de movimientos y por qué **SUM(Entrada) − SUM(Salida)** sobre toda la tabla (con anulado='No') **no** coincide con el saldo real: hay pares de registros que representan la **misma** operación física.

---

## 1. Resumen: quién escribe en `stock`

| Formulario | Acción | Comprobante | TipoComp | Entrada/Salida | Efecto en stock_deposito |
|------------|--------|-------------|----------|----------------|---------------------------|
| **Remito.frm** | Emitir remito (venta) | REM | Remito Salida | **Salida** | Saldo −, saldo_pedido_cliente − |
| **FacturaA.frm** / **FacturaB.frm** | Emitir factura (venta) | FA/FB | Venta | **Salida** | Saldo − (si no viene de remito ya descontado) |
| **TPV.frm** | Facturar desde TPV | FA/FB | Venta TPV | **Salida** | Saldo − |
| **NotaCred.frm** (y variantes NC) | Emitir nota de crédito (devolución) | NCB/NCA/… | Devol - Cliente | **Entrada** | Saldo + |
| **CargaMovStock.frm** | Movimiento manual / transferencia | MSTOCK | Transferencia, etc. | Entrada **o** Salida (o par origen/destino) | Saldo ± |
| **Lista_Comp_Fact.frm** | Remito desde pedidos (delega a Remito) | REM | Remito Salida | Salida | Idem Remito |
| **PRemito.frm** / **Visualiza_PRemito** | Remito de **compra** | REM | Remito Entrada | **Entrada** | Saldo + |
| **PFactura.frm** / **Visualiza_PFactura** | Factura de **compra** | FA/FB/… | Factura OC / … | **Entrada** (si factura OC) | Saldo +, saldo_pedido_proveedor + |
| **ConsultaComprobante.frm** | **Anular** remito/factura/NC/… | — | — | Marca `anulado='Si'` y/o **contramovimiento** (AddNew) | Saldo ± según contramovimiento |

---

## 2. Comportamiento detallado por formulario

### 2.1 Remito.frm — Remito de venta (salida)

- **Qué hace:** Por cada renglón del remito hace `rs_stock.AddNew` y asigna:
  - `Comprobante = "REM"`, `TipoComp = "Remito Salida"`
  - **Salida** = cantidad (Entrada = 0)
  - `Saldo` = saldo de stock_deposito **después** del descuento
  - `CodigoMovimiento` = contador del comprobante
  - Resto: artículo, depósito, precios, etc.
- **stock_deposito:** `Update` restando la cantidad del `Saldo` y ajustando `saldo_pedido_cliente` si viene de pedido.
- **Origen de datos:** `cuerpostock` / renglones del remito (desde pedido o carga directa).

### 2.2 FacturaA.frm / FacturaB.frm — Factura de venta (salida)

- **Qué hace:** Por cada renglón de la factura hace `rs_stock.AddNew` con:
  - `Comprobante = TipoFactura` (FA/FB), `TipoComp = "Venta"`
  - **Salida** = cantidad (Entrada = 0)
  - `Saldo` = saldo después del descuento
  - `CodigoMovimiento` = contador de la factura
- **stock_deposito:** Se descuenta `Saldo` (y si aplica, `saldo_pedido_cliente`).
- **Origen:** Puede ser desde **Pedido Avanzado** (facturar pedido/remito) o factura directa. Cuando la venta es **remito + factura**, el flujo típico es:
  1. Se emite el **REM** → se escribe **una** fila en `stock` (Salida) y se descuenta stock.
  2. Se emite la **FA** por ese mismo remito → se escribe **otra** fila en `stock` (Salida, misma cantidad).

**Consecuencia:** La misma salida física queda registrada **dos veces** en `stock` (REM + FA). Por eso **SUM(Salida)** con `anulado='No'` **sobrestima** las salidas si se toman todas las filas.

### 2.3 TPV.frm — Venta desde caja (TPV / Self Checkout)

- **Qué hace:** Al confirmar factura hace `rs_stock.AddNew` con:
  - `Comprobante = TipoFactura` (FA/FB), `TipoComp = "Venta TPV"` (o "Venta Self Checkout" desde Synap).
  - **Salida** = cantidad.
- **No hay REM previo:** una sola fila por ítem = una salida. No hay doble cuenta en TPV/SC.

### 2.4 NotaCred.frm (y variantes) — Devolución (entrada)

- **Qué hace:** Por cada renglón de la NC hace `rs_stock.AddNew` con:
  - `Comprobante = TipoCompNC` (NCB, NCA, etc.), `TipoComp = "Devol - Cliente"`
  - **Entrada** = cantidad (Salida = 0)
  - `Saldo` = saldo después de sumar
- **stock_deposito:** `Update` sumando la cantidad al `Saldo`.
- En flujos con **remito de devolución**, puede existir además un movimiento de tipo **REM** con descripción "Anul Remito" (reingreso) vinculado a la misma devolución → **dos filas** para la misma entrada física (NCB + REM Anul).

### 2.5 CargaMovStock.frm — Movimientos manuales y transferencias

- **Qué hace:**
  - **Entrada / Salida / Ensamble / Desarme:** una o más filas por renglón con `rs_stock.AddNew`:
    - `Comprobante = "MSTOCK"`, `TipoComp = Motivo.Text` (ej. "Transferencia").
    - **Entrada** o **Salida** según el motivo; en **transferencia** hay **dos** filas (origen: Salida, destino: Entrada) con el **mismo** `CodigoMovimiento`.
  - **stock_deposito:** solo actualiza `Saldo` (±). No toca `saldo_pedido_cliente` ni `saldo_pedido_proveedor`.
- **Consecuencia:** Para transferencias, SUM(Entrada)−SUM(Salida) a nivel **artículo** sigue siendo correcto (se compensan las dos filas). No introduce doble cuenta a nivel global.

### 2.6 PRemito.frm / Visualiza_PRemito — Remito de compra (entrada)

- **Qué hace:** Por cada renglón del remito de compra hace `AddNew` en `stock` con:
  - `Comprobante = "REM"`, `TipoComp` tipo "Remito Entrada" (recepción).
  - **Entrada** = cantidad recibida.
- **stock_deposito:** `Update` sumando a `Saldo` y, si viene de OC, a `saldo_pedido_proveedor`.
- **Contexto:** Compras (proveedor). No se mezcla con REM/FA de ventas en la doble cuenta venta.

### 2.7 PFactura.frm / Visualiza_PFactura — Factura de compra (entrada)

- **Qué hace:** Si el renglón es “Factura OC”, escribe en `stock` con **Entrada** y actualiza `stock_deposito.Saldo` y `saldo_pedido_proveedor`.
- **Contexto:** Compras. No genera doble cuenta con ventas.

### 2.8 ConsultaComprobante.frm — Anulaciones

- **Qué hace** con la tabla `stock`:
  1. **Marcar anulados:** para los movimientos del comprobante anulado hace `rs_stock.Fields!anulado = "Si"` (UPDATE sobre filas existentes).
  2. **Contramovimiento:** en anulaciones de **remito de venta** (y otros según flujo) abre `rs_stock_anul` y hace `AddNew` con:
     - Mismo artículo, depósito, cantidad.
     - **Signo invertido:** si el original tenía Salida, el contramovimiento tiene **Entrada** (y viceversa).
     - `TipoComp` / descripción de anulación (ej. "Anul Remito"); puede usarse `codigo_movimiento_anul` para vincular al movimiento original.
- **Efecto:** El movimiento original deja de contarse si se filtra `anulado='No'`. El contramovimiento (nuevo registro con anulado='No') devuelve el stock. Así, a nivel teórico, **solo con anulado='No'** ya se “corrige” la anulación. La doble cuenta **REM + FA** no se corrige con anulaciones: son dos filas distintas (REM y FA) para la misma operación.

---

## 3. Patrones que explican la doble cuenta en ventas

| Operación comercial | Registros en `stock` (anulado='No') | Conteo físico |
|--------------------|-------------------------------------|----------------|
| Venta con remito + factura | 1 REM (Salida) + 1 FA (Salida) | **1** salida |
| Venta solo factura (TPV / Self Checkout) | 1 FA/FB (Salida) | 1 salida |
| Transferencia entre depósitos | 1 Salida (origen) + 1 Entrada (destino) | 0 (global) |
| Devolución (NC + remito anulación) | 1 NCB (Entrada) + 1 REM "Anul Remito" (Entrada) | **1** entrada |
| Anulación de remito | Original: anulado='Si'; contramov: 1 Entrada | 0 neto |

Por tanto:

- **Salida:** REM y FA de la **misma** venta generan **dos** filas con Salida. Un saldo teórico con `SUM(Entrada)−SUM(Salida)` sobre **todas** las filas no anuladas **resta de más** (doble resta por cada venta remitada y facturada).
- **Entrada (devolución):** NCB y REM "Anul Remito" pueden ser **dos** filas para la **misma** devolución → **doble** suma de entrada si se cuentan ambas.

---

## 4. Regla sugerida para “saldo teórico” desde movimientos

Para que el saldo teórico coincida con la lógica de negocio (y con `stock_deposito.saldo`), no debe sumarse/restarse dos veces la misma operación:

1. **Ventas (salidas):**
   - **Opción A:** Contar **solo** movimientos con `Comprobante = 'REM'` y `TipoComp = 'Remito Salida'` (y excluir FA/FB cuando exista REM con el mismo CodigoMovimiento o codmov_remito).
   - **Opción B:** Contar **solo** movimientos con `Comprobante IN ('FA','FB','FC')` y `TipoComp IN ('Venta','Venta TPV','Venta Self Checkout')`, y excluir REM cuando haya factura asociada al mismo CodigoMovimiento.
   - En ambos casos, ventas **sin** remito (TPV, Self Checkout) deben seguir contándose (una fila = una salida).

2. **Devoluciones (entradas por NC):**
   - Contar **solo** un tipo: por ejemplo **solo** `Comprobante` NCB/NCA y `TipoComp = 'Devol - Cliente'`, **o** solo los REM "Anul Remito" / contramovimientos de anulación, pero no ambos para la misma devolución.

3. **Movimientos manuales y compras:**
   - **CargaMovStock (MSTOCK):** contar todas las filas (Entrada/Salida); en transferencias las dos filas se compensan.
   - **PRemito / PFactura (compras):** contar normalmente (Entrada).

4. **Anulaciones:**
   - Solo incluir filas con `anulado = 'No'`. Los contramovimientos ya son nuevas filas con anulado='No' que revierten el efecto del movimiento anulado.

---

## 5. Referencias en el código VB6

| Formulario | Ubicación | Líneas relevantes (aprox.) |
|------------|-----------|----------------------------|
| CargaMovStock.frm | Formularios/CargaMovStock.frm | rs_stock.Open, AddNew, Update ~3544–4162; Comprobante=MSTOCK ~3960, 4130 |
| Remito.frm | Formularios/Remito.frm | rs_stock.Open ~4436, 12052, 12363; AddNew ~4466, 12075, 12386; TipoComp="Remito Salida", Comprobante=REM ~4857–4859, 12279–12280, 12588–12589 |
| FacturaA.frm | Formularios/FacturaA.frm | rs_stock.Open ~5235, 20599, 20909; TipoComp="Venta", Comprobante=FA ~5726–5729, 20825–20826, 21151–21152 |
| FacturaB.frm | Formularios/FacturaB.frm | Misma lógica que FacturaA (FA/FB) |
| TPV.frm | Formularios/TPV.frm | rs_stock.Open ~6508, 9462, 35119, 35431; AddNew ~6528, 9494, 35142, 35454; TipoComp="Venta TPV", "Devol - Cliente" ~6682, 9806, 35688 |
| NotaCred.frm | Formularios/NotaCred.frm | rs_stock.Open ~3993; AddNew ~3998; TipoComp="Devol - Cliente", Entrada ~4209–4227 |
| ConsultaComprobante.frm | Formularios/ConsultaComprobante.frm | rs_stock.Fields!anulado="Si" (múltiples bloques); rs_stock_anul.AddNew ~5222–5228 y siguientes (contramovimiento) |
| Lista_Comp_Fact.frm | Formularios/Lista_Comp_Fact.frm | Delega emisión a Remito.frm |
| PRemito.frm / PFactura.frm | Formularios/ | Escriben stock en compras (Entrada); ver INFO_COMPRA_TABLAS_CAMPOS.md |

---

## 6. Documentación relacionada

- **reports/docs/ANALISIS_FORMULARIOS_STOCK_VB6.md** — Formularios de stock/inventario (CargaMovStock, Stock, Inventario, etc.) y relación con stock_deposito.
- **reports/docs/INFO_COMPRA_TABLAS_CAMPOS.md** — Flujo compras (OC → REM → Factura) y escritura en stock/stock_deposito.
- **reports/docs/CONTEXTO_TABLAS_VB6_INFORMES.md** — Contexto de tablas para informes (stock, stock_deposito, stockp).
- **docs/AUDITORIA_TPV_CAMPOS_COMPROBANTE_DB.md** — Qué guarda TPV y Self-Checkout en stock; alineación de campos.
- **reports/services/reconciliation_saldo_stock.py** — Reconciliación actual (SUM(Entrada)−SUM(Salida)); requiere ajuste según §4 para no duplicar REM+FA ni NCB+REM Anul.

---

*Elaborado a partir de la búsqueda en administranet_vb6/Formularios (rs_stock, AddNew, Comprobante, TipoComp, Entrada, Salida, anulado) y de la documentación existente en reports/docs y docs.*
