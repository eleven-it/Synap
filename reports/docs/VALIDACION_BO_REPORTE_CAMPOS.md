# Validación BO vs Stock vs Facturación – Campos y tablas

Revisión del reporte frente a `CONTEXTO_TABLAS_VB6_INFORMES.md` y formularios VB6. **No se aplicaron cambios**; solo se listan discrepancias y validaciones sugeridas.

---

## 1. Tabla de renglones de backorder (CRÍTICO)

| Aspecto | Reporte actual | Contexto VB6 | Observación |
|--------|-----------------|--------------|-------------|
| **Tabla renglones BO** | `cuerpostockpe` | **`stockp`** (renglones definitivos de PED) | **Discrepancia.** En VB6, Pedido y Pedido_Interno guardan en **stockp**; **cuerpostockpe** es buffer de edición. Pedido_Avanzado y Pedido_prep muestran renglones desde **stockp**, no desde cuerpostockpe. |
| **Uso de cuerpostockpe** | Se usa para detalle BO agregado (por producto) y para detalle row-level (Backorder detalle). | Solo temporal al cargar/editar pedido; al guardar → stockp. | Si al guardar se limpia o no se persiste en cuerpostockpe, el reporte podría estar leyendo datos vacíos o solo ítems en edición, y omitiendo pedidos ya guardados. |

**Recomendación:** Validar en la base si los PED guardados tienen renglones **solo en stockp** o también en cuerpostockpe. Si solo en **stockp**, conviene cambiar el reporte para usar **stockp** en lugar de **cuerpostockpe** para renglones de backorder (manteniendo `comp_ped` para cabecera y estados).

---

## 2. Campos de renglones BO

### 2.1 Detalle agregado (por producto) y row-level

| Campo reporte | Origen actual | En VB6 / stockp | Observación |
|---------------|---------------|------------------|-------------|
| **Cantidad (bo_qty)** | `SUM(cpe.Cantidad)` (cuerpostockpe) | `stockp.Cantidad` | Mismo concepto. Si se pasa a stockp, usar `SUM(stockp.Cantidad)`. |
| **PrecioVentaxR / bo_importe** | `SUM(cpe.PrecioVentaxR)` (cuerpostockpe) | `stockp.PrecioVentaxR` | Mismo nombre. stockp lo usa en Pedido_Avanzado. |
| **IDArt, id_manual, Descripcion** | `cpe` + `articulo` | `stockp.IDArt`, `id_manual`, `Descripcion`; articulo.NombreArticulo | stockp tiene `Descripcion`; se usa `COALESCE(csp.Descripcion, a.NombreArticulo)`. Con stockp sería análogo. |
| **cant_pend** | `0` (hardcodeado) | **`stockp.cantidad_pendiente`** | **Discrepancia.** Hoy no hay cant pendiente real. **stockp** tiene `cantidad_pendiente`. Si se usa stockp, se podría tomar este campo (p. ej. por renglón o agregado según vista). |
| **precio_x_renglon** | `csp.PrecioVentaxR` (cuerpostockpe) | `stockp.PrecioVentaxR` | Mismo concepto. |

### 2.2 Stock y cobertura

| Campo reporte | Origen actual | Contexto | Observación |
|---------------|---------------|----------|-------------|
| **stock_actual** | `SUM(stock_deposito.saldo)` por `id_articulo` | stock_deposito.saldo, id_articulo | Correcto. Join `sd.id_articulo = sp.IDArt`. |
| **stock_reservado** | `SUM(stock_deposito.saldo_pedido_cliente)` por `id_articulo` | stock_deposito.saldo_pedido_cliente | Correcto. |
| **disponible** | `GREATEST(0, stock_actual - stock_reservado)` | Coincide con “disponible” en contexto | Correcto. |
| **oc_pendiente / CON INGRESO** | `SUM(stock_deposito.saldo_pedido_proveedor)` por `id_articulo` | OC aprobadas pend. entrega; VB6 actualiza saldo_pedido_proveedor en OC/recepción | Correcto. OC pend. cubre primero faltante reservado; el resto cubre BO. CON INGRESO = parte del BO cubierta por ese OC restante (tras disponible). |
| **Agregación por depósito** | Se agrupa solo por `id_articulo` (todos los depósitos) | stock_deposito tiene `id_deposito` | El reporte no filtra por depósito. Si en el futuro se exige “stock por depósito” para BO, habría que agregar filtro por depósito. |

---

## 3. Cabecera y remitos

| Aspecto | Reporte actual | Contexto | Observación |
|--------|----------------|----------|-------------|
| **comp_ped** | Cabecera PED (BO) y REM (remitos no facturados) | Mismo uso en VB6 | Correcto. |
| **Estados BO** | `Pendiente`, `En preparación`, `En Remito`, `Parcial` | Igual en formularios | Correcto. |
| **Remitos no facturados** | `comp_ped.TipoComprobante = 'REM'`, `Estado = 'Pendiente'`, `SubtotalDesc` | Remitos en comp_ped | Correcto. |
| **Sucursal / PV** | `cp.CodSucursal`, `cp.id_pv`; JOIN `sucursales.id_sucursal = cp.CodSucursal`, `punto_venta.id_punto_venta = cp.id_pv` | comp_ped usa codSucursal, id_pv; VB6 a veces `codSucursal` | En el proyecto se usa `CodSucursal` de forma coherente. Validar que en la base `comp_ped.CodSucursal` = `sucursales.id_sucursal` y `comp_ped.id_pv` = `punto_venta.id_punto_venta` según el esquema real. |

---

## 4. Facturación y facturación por cliente

| Aspecto | Reporte actual | Contexto | Observación |
|--------|----------------|----------|-------------|
| **Facturación** | `cuentacliente`: FA/FB/FC/FE/FM, NCA–NCM, `SubtotalDesc`, `Fecha`, `Anulado` | Facturación desde cuentacliente | Correcto. |
| **Facturación por cliente** | `cl.Codigo = cc.Codigo`, vendedor `cl.CodViajante` → viajantes, zona `cl.id_zona` → erp_zona | Vendedor y zona desde cliente, no desde movimiento | Correcto. |
| **Sucursal/PV** | `cc.CodSucursal`, `cc.id_pv` en filtros | cuentacliente | Correcto. |

---

## 5. Artículos, rubros, subrubros, cliente, vendedor

| Tabla / campo | Uso en reporte | Contexto | Observación |
|---------------|----------------|----------|-------------|
| **articulo** | `IDArt`, `id_manual`, `NombreArticulo`, `CodigoRubro` | Mismo en VB6 | Correcto. |
| **rubro** | `CodigoRubro`, `NombreRubro` (categoría) | Mismo | Correcto. |
| **subrubro** | `IDSubRubro`, `NombreSubRubro` (row-level) | Mismo | Correcto. |
| **cliente** | `Codigo`, `nombre_cliente`, `CodViajante`, `id_zona`, etc. | Mismo | Correcto. |
| **viajantes** | `CodViajante`, `Nombre` | Mismo | Correcto. |

---

## 6. Resumen de diferencias y acciones sugeridas

| # | Diferencia | Gravedad | Estado |
|---|------------|----------|--------|
| 1 | Renglones BO desde **cuerpostockpe** en lugar de **stockp** | **Alta** | **Resuelto.** El reporte ahora usa **stockp** + **comp_ped** para detalle agregado y row-level BO. |
| 2 | **cant_pend** siempre 0 | Media | **Resuelto.** Se usa `stockp.cantidad_pendiente` para cant_pend en el detalle row-level. |
| 3 | Fallback PrecioVentaxR → PrecioUnitario, etc. | — | **No se usa.** Solo `PrecioVentaxR`; si es 0 es correcto. |

---

## 7. Depósitos y stock_deposito

- **Detección:** El reporte cuenta depósitos con `SELECT COUNT(*) FROM deposito WHERE (anulado IS NULL OR anulado = 'No')`.
- **Si hay más de un depósito:** Se añade una nota al resultado: *"Hay N depósitos en la base. Stock y reservado se muestran agregados por artículo (todos los depósitos). Definir si se requiere filtro o desglose por depósito."* También se registra en log.
- **Definición final:** Según tu indicación, solo se detecta; la decisión de filtrar o desglosar por depósito se toma después en función de si hay más de uno.

---

## 8. Lo que está alineado (sin cambios sugeridos)

- **Backorder:** Renglones desde **stockp** + **comp_ped**; `cant_pend` = `stockp.cantidad_pendiente`; `bo_importe` = `SUM(PrecioVentaxR)` sin fallback (si es 0 es correcto).
- **CON INGRESO:** Cantidades en OC aprobadas y pendientes de entrega (`stock_deposito.saldo_pedido_proveedor`). OC pend. cubre primero faltante de reservado; el resto cubre BO. Clasificación BO: disponible → oc_restante_bo → sin stock.
- Facturación (cuentacliente, tipos de comprobante, SubtotalDesc, filtros por fecha).
- Facturación por cliente (cliente, vendedor desde cliente, zona desde cliente).
- Remitos no facturados (comp_ped REM, Estado Pendiente, SubtotalDesc, sucursal/PV).
- Stock y cobertura (stock_deposito por id_articulo, saldo, saldo_pedido_cliente, disponible).
- Cabecera BO (comp_ped, estados, TipoComprobante PED, Anulado).
- Maestros: articulo, rubro, subrubro, cliente, viajantes, erp_zona.
- Joins y filtros de sucursal/PV (CodSucursal, id_pv) en comp_ped y cuentacliente.

---

*Validación sin modificación de código. Antes de cambiar tablas o campos, confirmar esquema real de la base y reglas de negocio.*
