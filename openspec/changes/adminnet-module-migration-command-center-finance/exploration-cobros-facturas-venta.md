# Exploración: cobros de facturas de venta en AdministraNET

**Cambio:** `adminnet-module-migration-command-center-finance`  
**Fecha:** 19/05/2026  
**Objetivo:** Entender el proceso legacy **minucioso** antes de definir endpoints del Command Center (`ventas_cobros`, `tesoreria`).

---

## 1. Conceptos clave (no confundir)

| Concepto | Qué es | Dónde vive |
|----------|--------|------------|
| **Venta facturada** | Emisión FA/FB/FC/FE/FM/NC — importe neto `SubtotalDesc` | `cuentacliente` |
| **Condición de venta** | Contado vs plazo / cuenta corriente al facturar | `cond_venta.tipo_cv`, `cuentacliente.CondVenta`, `id_condventa` |
| **Medios al facturar (TPV/contado)** | Cuánto se cobró en el acto de la venta | `cuentacliente.tpv_importe_*`, `TotalEfectivoP`, `Total_Tarjeta`, `resumen_venta_cv` |
| **Cobranza posterior** | Recibo (REC) que cancela facturas pendientes | `cuentacliente` REC + `recibo_factura` + `medio_cobpag` + `caja` |
| **Ingreso en caja** | Movimiento físico de tesorería | `caja` + `caja_saldo` |

**Regla de oro:** una factura **a cuenta corriente** genera venta en `cuentacliente` pero el **efectivo/tarjeta** entra en `caja` recién al **Recibo de cobro**, no (en general) al emitir la factura.

---

## 2. Flujo A — Venta al contado (TPV / Factura contado)

### 2.1 Formularios VB6

- `TPV.frm`, `FacturaA.frm`, `FacturaB.frm`
- Documentación Synap: `docs/self_checkout/CAJA_ADMINISTRANET_PROCESOS.md` §4.2

### 2.2 Pasos (mismo `CodigoMovimiento` en todo)

1. **Cabecera** `INSERT cuentacliente`:
   - `TipoComprobante` = FA/FB/…
   - `SubtotalDesc` = total venta
   - `CondVenta` / `id_condventa` — típicamente contado (`Estado` = `Canc` si cancelada al momento)
   - Campos TPV: `tpv_importe_efectivo`, `tpv_importe_tarjeta`, `tpv_importe_cheque`, `tpv_importe_ctacte`
   - Paridad Synap: `self_checkout/services/confirmation_service.py` (~L387–425)

2. **Resumen medios** `INSERT resumen_venta_cv` (TPV y facturas que lo usan):
   - `total_efectivo`, `total_ctacte`, `total_tarjeta`, `total_cheque`, `total_transferencia`, `total_otro_medio`
   - `codigo_movimiento` = mismo que factura
   - Referencia VB6: `TPV.frm` `Guardar_resumen_venta_cv` (~10311)
   - Schema: `docs/general/tablas/resumen_venta_cv.md`

3. **Tarjeta detalle** (si aplica): `INSERT tc_comprobante` ligado a `codigo_movimiento`

4. **Caja** — uno o más `INSERT caja` con **el mismo** `codigo_movimiento`:
   - Efectivo: `id_caja_abm_origen` = caja usuario, `Tipo` = `Factura Contado TPV` / equivalente, `ingreso`
   - Tarjeta: caja tarjeta (`Principal.id_caja_tarjeta`), `Tipo` = `Tarjeta`
   - Cheque: caja cheque
   - Actualiza `caja_saldo`
   - Synap: `mercadopago.services.payment_service.write_caja_ingreso_with_cursor` desde TPV (~L806–831)

5. **Imputación cuenta corriente del comprobante** (si mezcla contado + cta cte en TPV):
   - `recibo_factura` / `recibo_factura_par` para trackear saldo del comprobante
   - TPV.frm múltiples referencias a `recibo_factura` al armar/imputar

### 2.3 Implicancia para Command Center

- **Medios al facturar (contado):** agregar desde `resumen_venta_cv` (preferido si existe fila) **o** columnas `cuentacliente.tpv_importe_*` / `TotalEfectivoP` / `Total_Tarjeta` para FA/FB del período con `Estado` cancelado.
- **Caja:** los ingresos FA aparecen en `caja` con `tipo_comprobante` de factura y `Tipo` descriptivo; Synap ya clasifica como `ingresos_ventas` en `query_runner._classify_movement`.

---

## 3. Flujo B — Venta a cuenta corriente (sin cobro inmediato)

### 3.1 Al facturar

- `cuentacliente`: `SubtotalDesc` = venta; `Estado` = `N/Canc` (o similar); `Saldo` > 0
- `CondVenta` / `cond_venta.tipo_cv` = plazo / cuenta corriente
- **No** hay filas de ingreso en `caja` por el importe total de la factura (salvo anticipos parciales vía TPV con `tpv_importe_ctacte` parcial)

### 3.2 Seguimiento de deuda

- `recibo_factura`: una fila por comprobante cliente con `Saldo`, `Cancelado`, `Estado`, `CodigoMovimiento` de la **factura**
- `CuentaCliente.frm`, consultas de comprobantes no cancelados

### 3.3 Implicancia

- **Ventas netas del período** (KPI actual Command Center) **incluyen** estas facturas aunque **no** estén cobradas.
- **Medios de cobro** de esas ventas **no** deben leerse de `cuentacliente` al facturar; hay que esperar el **Recibo**.

---

## 4. Flujo C — Recibo de cobro (`ReciboCobro.frm`)

### 4.1 Propósito

Cobrar facturas pendientes (y otros conceptos): genera comprobante **REC** y registra **cómo** pagó el cliente.

### 4.2 Tablas y orden lógico (inferido VB6 + Synap parcial)

| Paso | Tabla | Rol |
|------|-------|-----|
| 1 | `cuentacliente` | Cabecera REC: `TipoComprobante='REC'`, `ImporteCobro`, `TotalRecibo`, `CodigoMovimiento` nuevo |
| 2 | `medio_cobpag_temp` → `medio_cobpag` | Cada medio: `tipo_mcp_tipo`, `nombre_mcp`, `importe_mcp`, `codigo_movimiento_rec` |
| 3 | `recibo_factura` / `recibo_factura_par` | Imputación a facturas: `Cancelado`, `Saldo`, `ReciboMov`, `Recibo` |
| 4 | `imputacion` | Trazabilidad REC ↔ factura (Synap: `fe_afip/services/recibo_guardado_legacy_service.py`) |
| 5 | `cuentacliente` (facturas) | `UPDATE` facturas: `Estado='Canc'`, `ReciboMov`, `Recibo` si saldo 0 |
| 6 | `caja` | Por cada medio: ej. `Cobranza Efectivo`, tarjeta, cheque; `ingreso`; mismo `codigo_movimiento` REC |
| 7 | Satélites | `tc_comprobante`, `transferencia` / `transferencia_temp`, retenciones, cheques terceros |

Referencias:

- `docs/self_checkout/CAJA_ADMINISTRANET_PROCESOS.md` §4.3
- `docs/general/tablas/medio_cobpag.md` — `codigo_movimiento_rec` liga al REC
- `docs/general/tablas/recibo_factura.md`, `recibo_factura_par.md`
- `fe_afip/services/recibo_guardado_legacy_service.py` — imputación web (sin `medio_cobpag` ni `caja` aún en ese servicio)

### 4.3 Medios en ReciboCobro

Durante la carga, VB6 usa `medio_cobpag_temp` (por usuario). Al guardar, pasa a `medio_cobpag` con tipos desde catálogo `medio_cobpag_abm` / `medio_cobpag_tipo`.

Cada medio dispara movimiento en **caja** con caja destino según tipo:

- Efectivo → caja operativa (`Caja.BoundText`)
- Tarjeta → `Principal.id_caja_tarjeta`
- Cheque → caja cheques
- Transferencia → `transferencia_temp` / `transferencia`

### 4.4 Clasificación en informes Synap (`query_runner`)

- Movimientos `caja` con `tipo_comprobante='REC'` → `ingresos_cobranzas` (`_classify_movement`)
- `_get_payment_method('REC', caja.tipo)` → Efectivo / Cheque / Recibo según texto de `caja.Tipo`

**No** usa `medio_cobpag` hoy en reports.

---

## 5. Flujo D — Otros ingresos relacionados

| Origen | caja | Notas |
|--------|------|-------|
| Mercado Pago (Synap) | `ingreso`, `Tipo` Tarjeta | `write_caja_ingreso`, mismo `codigo_movimiento` factura |
| Cobro cheque en clearing | MCAJ / CHEQ | Clasificación cobranzas |
| Notas de crédito | Ajustan `cuentacliente`, pueden afectar `recibo_factura` | NC en ventas netas |

---

## 6. Qué NO sirve como fuente única para «ventas por medio de cobro»

| Fuente | Por qué no alcanza |
|--------|-------------------|
| Solo `ventas_metrics` / `SubtotalDesc` | Incluye cta cte no cobrada |
| Solo `resumen_venta_cv` | No todas las facturas lo llenan (legacy fuera TPV) |
| Solo `caja` + `_get_payment_method` | Mezcla cobranzas REC con ventas contado FA; no ve «venta tarjeta» si solo hubo REC después |
| Solo `cond_venta.tipo_cv` | Dice condición comercial, no medio efectivo/tarjeta |

---

## 7. Modelo recomendado para KPIs Command Center (área `ventas_cobros`)

### Serie 1 — Facturado por medio (al emitir)

**Fuentes (prioridad):**

1. `resumen_venta_cv` agregado por período (`fecha`, `id_sucursal`): SUM columnas `total_*`
2. Complemento: `cuentacliente` FA/FB con `anulado='No'`, sin fila en resumen: SUM `tpv_importe_efectivo`, `tpv_importe_tarjeta`, `tpv_importe_ctacte`, `TotalEfectivoP`, `Total_Tarjeta`, etc.

**Buckets:** efectivo, tarjeta, cuenta_corriente, cheque, transferencia, otro.

### Serie 2 — Cobrado en caja (tesorería real)

**Fuente:** `caja` período, `anulado='No'`, clasificar:

- Ingresos con `tipo_comprobante` IN (`FA`,`FB`,`FC`,`FE`,`FM`) → ventas contado (subclasificar con `_get_payment_method` o join futuro a `resumen_venta_cv` por `codigo_movimiento`)
- Ingresos `REC` → cobranzas; medio desde `caja.Tipo` + opcional `SUM(medio_cobpag.importe_mcp)` por `codigo_movimiento_rec`

**Nota:** esta serie alimenta coherencia con `tesoreria` y cash-flow.

### Serie 3 — Pendiente de cobro (opcional P0)

**Fuente:** `recibo_factura` WHERE `Estado='N/Canc'`, `Anulado='No'`, `Saldo>0` (patrón ecom `SPEC_MAYORISTAPP_COMPROBANTES.md`).

---

## 8. Impacto en otras áreas del cambio

### Tesorería (`tesoreria`)

- Reutilizar agregados `caja` de `query_runner._run_cash_flow_waterfall` / `by_account`
- Separar en meta: ingresos ventas vs ingresos cobranzas vs egresos

### Impuestos

- **Fuera de alcance** de esta spec (descartado por producto).

---

## 9. Validación pendiente con negocio / VB6

- [ ] Confirmar si facturas **FacturaB** fuera TPV siempre graban `resumen_venta_cv`
- [ ] Listar valores reales de `medio_cobpag.tipo_mcp_tipo` / `nombre_mcp` en empresa piloto
- [ ] Cruzar totales Serie 1 + Serie 2 vs informe legacy de cobranzas / Info_Estadistica
- [ ] Definir si NC deben restar en medios o solo en ventas netas

---

## 10. Referencias de código Synap

| Archivo | Uso |
|---------|-----|
| `reports/services/query_runner.py` | `_classify_movement`, `_get_payment_method`, `cash_flow_*` |
| `reports/services/executive_dashboard/ventas_metrics.py` | Ventas netas período (sin medios) |
| `self_checkout/services/confirmation_service.py` | Factura TPV + resumen_venta_cv + caja |
| `fe_afip/services/recibo_guardado_legacy_service.py` | REC imputación (parcial) |
| `docs/self_checkout/CAJA_ADMINISTRANET_PROCESOS.md` | Procesos caja |
| `docs/general/tablas/*.md` | Schemas |
