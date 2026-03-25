# Análisis de Formularios VB6: Stock e Inventario

Documento para migración a Synap. Formularios analizados: `stock_consulta_avanzada`, `Stock_Control_Entrada`, `Stock`, `Inventario`, `InicSaldos`, `Info_Stock`, `CargaMovStock`.

---

## Resumen ejecutivo

| Formulario | Rol | Escribe `stock_deposito` | Escribe `saldo_pedido_proveedor` | ¿Afecta BO? |
|------------|-----|--------------------------|----------------------------------|-------------|
| **CargaMovStock** | Movimientos de stock | Sí (solo `Saldo`) | No | No |
| **Stock** | Ficha de stock (consulta) | No | No | No |
| **Inventario** | Inventario físico | No | No | No |
| **Info_Stock** | Informes de stock | No | No | No |
| **stock_consulta_avanzada** | Consulta artículos/stock | No | No | No |
| **Stock_Control_Entrada** | Control ingreso por código de barra | No | No | No |
| **InicSaldos** | Ajuste cuenta corriente | No | No | No |

**Conclusión:** Ninguno de estos formularios modifica `saldo_pedido_proveedor`. La diferencia en el análisis BO (saldo_pedido_proveedor vs stockp+cuentaproveedor) **no se explica** por movimientos generados en estos formularios.

---

## 1. CargaMovStock.frm — Movimiento de Stock

### Descripción
Formulario para cargar movimientos manuales de stock (entradas, salidas, transferencias, ensamble, desarme).

### Tablas que escribe
- **stock**: `AddNew` por cada renglón (entrada/salida).
- **stock_deposito**: `Update` del campo **Saldo** únicamente.
- **movimiento_stock**: cabecera del movimiento.
- **lote** / **lote_stock**: si aplica lotes.
- **cuerpostock**: buffer temporal (borrado al abrir).

### Campos que actualiza en stock_deposito
```vb
rs_saldo_stock.Fields!Saldo = rs_stock.Fields!Saldo
rs_saldo_stock.Update
```

**Importante:** Solo actualiza `Saldo`. No toca `saldo_pedido_proveedor` ni `saldo_pedido_cliente`.

### Motivos de movimiento
- Entrada, Salida, Transferencia, Ensamble, Desarme, etc.
- Comprobante: `MSTOCK`
- TipoComp: según motivo (ej. "Transferencia").

### Migración Synap
- Crear modelo `StockMovement` con motivo, depósito origen/destino, renglones.
- Al guardar, actualizar `stock_deposito.Saldo` y registrar en `stock` (o equivalente).
- No requiere lógica de `saldo_pedido_proveedor`.

---

## 2. Stock.frm — Ficha de Stock

### Descripción
Consulta de ficha de stock por artículo y depósito. Muestra historial de movimientos y saldo.

### Tablas que lee
- **stock**: movimientos con filtros (IDArt, CodDeposito, Fecha, no_entregado_fact).
- **stock_deposito**: saldo actual (Saldo).
- **articulo**, **lote**, **articulo_prov**, **deposito**.

### Comportamiento
- Solo lectura. No escribe en base de datos.
- Grid muestra: Fecha, TipoComp, Comprobante, NroComp, PrecioCosto, Entrada, Salida, Saldo, Lote, Detalle.
- Calcula saldo según stock_deposito.Saldo y presenta historial desde stock.

### Migración Synap
- Vista/pantalla de detalle de stock por artículo y depósito.
- Consulta a movimientos y saldo; sin lógica de escritura.

---

## 3. Inventario.frm — Inventario físico

### Descripción
Registro de inventario físico: comparación saldo sistema vs saldo manual (conteo).

### Tablas que escribe
- **inventario** / **inventario_id**: registros de inventario (saldo_sistema, saldo_manual, diferencia, Tipo: Sobrante/Faltante/Sin diferencia).
- **inventario_temp**: buffer temporal.
- **cont_asiento**, **cont_ejercicio_saldo_cta**: asientos contables por diferencias (si contabilidad activa).

### Tablas que lee
- **stock_deposito**: para obtener saldo_sistema (Saldo).
- **articulo**, **deposito**.

### Comportamiento
- No escribe en `stock` ni en `stock_deposito`.
- Registra diferencias y genera asientos contables.
- El ajuste físico de stock se realiza típicamente mediante **CargaMovStock** (movimiento manual) u otro proceso externo.

### Migración Synap
- Modelo `InventoryCount` con renglones (articulo, deposito, saldo_sistema, saldo_manual, diferencia).
- Integración con contabilidad si aplica.
- Proceso separado para aplicar diferencias a stock (equivalente a CargaMovStock).

---

## 4. Info_Stock.frm — Informes de stock

### Descripción
Selector de informes de stock para impresión (Crystal Reports u otro motor).

### Comportamiento
- Solo configuración y disparo de reportes.
- No escribe en base de datos.
- Lee reportes definidos en `reporte_usuario` / `reporte`.

### Migración Synap
- Sustituir por reportes en Synap (PDF, Excel, dashboards).
- Sin cambios en modelo de datos.

---

## 5. stock_consulta_avanzada.frm — Consulta avanzada

### Descripción
Consulta avanzada de artículos y stock con filtros (depósito, fechas, presentación).

### Tablas que lee
- **stock_deposito**: saldo, saldo_pedido_cliente.
- **articulo**, **deposito**, **articulo_prov**.
- **stockp**, **comp_ped**, **cuentaproveedor**: para calcular saldo_pedido_cliente y saldo_pedido_proveedor por artículo (consulta OC).

### Consultas relevantes para BO
```vb
' Saldo pedido proveedor desde stockp + cuentaproveedor
" SUM(stockp.entrada) " & calculo_pedido_proveedor & " AS saldo_pedido_proveedor "
" LEFT JOIN stockp ON (stockp.CodigoMovimiento = cuentaproveedor.CodigoMovimiento) "
```

- Usa `stockp` + `cuentaproveedor` para OC (como nuestro cálculo B).
- También lee `stock_deposito.saldo` y `stock_deposito.saldo_pedido_cliente`.

### Comportamiento
- Solo lectura.
- No escribe en base de datos.

### Migración Synap
- Vista de consulta con filtros y agregaciones.
- Reutilizar lógica de saldos (stock_deposito, stockp+cuentaproveedor) para reportes.

---

## 6. Stock_Control_Entrada.frm — Control de ingreso

### Descripción
Control de mercadería en entrada por código de barra (UPC). Usado en logística para marcar productos leídos en una ruta/preparación.

### Tablas que escribe
- **cliente_datos_adicionales**: `UPDATE orden_ruta` para cada pedido en la ruta.

### Tablas que lee
- **cuentacliente**, **stock**, **articulo**, **cliente**, **cliente_datos_adicionales**, **logi_hoja_ruta**.

### Comportamiento
- No escribe en `stock`, `stock_deposito` ni `stockp`.
- Actualiza orden de ruta en pedidos de venta para logística.
- Usa `stock` solo para mostrar cantidades de artículos en la ruta.

### Migración Synap
- Módulo de logística/rutas; no incide en stock físico ni en saldo_pedido_proveedor.

---

## 7. InicSaldos.frm — Ajuste cuenta corriente

### Descripción
Ajuste de saldo inicial de cuenta corriente (clientes o proveedores).

### Tablas que escribe
- **cuentacliente** o **cuentaproveedor**: `AddNew` de comprobantes de ajuste.
- **recibo_factura**, **recibo_factura_par**, **op_factura**, **op_factura_par**: según tipo.
- **cont_asiento** (si contabilidad activa).

### Comportamiento
- No toca `stock`, `stock_deposito`, `stockp`.
- Solo ajustes de cuenta corriente (saldo inicial).
- No afecta saldo_pedido_proveedor.

### Migración Synap
- Modelo de ajustes de cuenta corriente.
- Sin impacto en inventario ni BO.

---

## 8. Relación con el análisis BO (saldo_pedido_proveedor vs stockp+cuentaproveedor)

### ¿Qué formularios actualizan saldo_pedido_proveedor?

Según la documentación existente (`INFO_COMPRA_TABLAS_CAMPOS.md`, `CONTEXTO_TABLAS_VB6_INFORMES.md`), `saldo_pedido_proveedor` se actualiza en:

1. **POrden_Compra** / **Visualiza_POrden_Compra**: al crear OC → `+`
2. **PRemito** / **Visualiza_PRemito**: al emitir remito desde OC → `+` (si nro_oc)
3. **PFactura** / **Visualiza_PFactura**: al facturar OC → `+` (si Factura OC)
4. **ConsultaComprobante**: al anular OC/PRE → `−`

### Formularios de stock/inventario analizados

Ninguno de los formularios analizados aquí (`CargaMovStock`, `Stock`, `Inventario`, `Info_Stock`, `stock_consulta_avanzada`, `Stock_Control_Entrada`, `InicSaldos`) escribe en `saldo_pedido_proveedor`.

### Implicancia para la diferencia BO

La diferencia entre:
- **A:** `stock_deposito.saldo_pedido_proveedor`
- **B:** `SUM(stockp.cantidad_pendiente)` con `cuentaproveedor.TipoComprobante='OC'` y `Estado='Pendiente'`

**no se explica** por movimientos generados en los formularios de stock/inventario analizados.

Las causas más probables (según documentación previa) son:

1. **Presupuesto (PRE)**: si impacta `saldo_pedido_proveedor` pero no persiste en `stockp` (solo `cuerpostockp`).
2. **Estados de OC distintos de "Pendiente"**: OCs con estado cambiado que mantienen saldo pero quedan fuera del filtro.
3. **Inconsistencias en VB6**: bugs o flujos que modifican saldo sin actualizar stockp/cuentaproveedor correctamente.
4. **Anulaciones parciales o mal aplicadas**: casos donde se resta saldo pero no se marcan bien los registros en stockp/cuentaproveedor.

---

## 9. Mapa de dependencias para migración

```
┌─────────────────────────────────────────────────────────────────────┐
│ Formularios que escriben stock_deposito                              │
├─────────────────────────────────────────────────────────────────────┤
│ • CargaMovStock → stock_deposito.Saldo (±)                           │
│ • POrden_Compra, PRemito, PFactura, ConsultaComprobante              │
│   → stock_deposito.saldo_pedido_proveedor (±)                        │
│ • Pedido, Remito, Factura, TPV, ConsultaComprobante                  │
│   → stock_deposito.saldo_pedido_cliente (±)                          │
│ • CargaArticulo → stock_deposito (AddNew Saldo=0)                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Formularios de stock analizados (solo lectura o Saldo)               │
├─────────────────────────────────────────────────────────────────────┤
│ • Stock, Info_Stock, stock_consulta_avanzada → Solo lectura          │
│ • CargaMovStock → Solo Saldo, NO saldo_pedido_proveedor              │
│ • Inventario → inventario/inventario_id, NO stock_deposito           │
│ • Stock_Control_Entrada → cliente_datos_adicionales.orden_ruta       │
│ • InicSaldos → cuentacliente/cuentaproveedor, NO stock               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Checklist de migración

| Componente | Prioridad | Notas |
|------------|-----------|-------|
| CargaMovStock | Alta | Único que escribe stock_deposito en este conjunto; migrar lógica de Saldo. |
| Stock | Media | Vista de ficha de stock; reutilizar consultas. |
| Inventario | Media | Registrar diferencias; definir proceso para aplicar ajustes. |
| stock_consulta_avanzada | Media | Consulta con filtros; reutilizar lógica de saldos. |
| Info_Stock | Baja | Reemplazar por reportes Synap. |
| Stock_Control_Entrada | Baja | Logística; módulo separado. |
| InicSaldos | Baja | Cuenta corriente; no afecta stock. |

---

*Documento generado a partir del análisis de los formularios VB6 en administranet_vb6/Formularios/.*
