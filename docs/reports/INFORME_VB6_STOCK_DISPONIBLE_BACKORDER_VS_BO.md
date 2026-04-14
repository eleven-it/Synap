# Informe: VB6 «Stock físico, cantidades disponibles y backorder» vs reporte BO Synap

**Fecha:** 2026-02-15  
**Última actualización:** 2026-04-13 (sincronizado con la implementación en `reports/services/query_runner.py`, método `_run_backorder_vs_stock_vs_facturacion`, slug `bo-stock-facturacion`).

**Objetivo:** Comparar la lógica de **disponible** y **backorder** entre el reporte de AdministraNET VB6 «Stock físico, cantidades disponibles y backorder» y el reporte BO (Backorder vs Stock vs Facturación) de Synap. Referencia para alineación, documentación del comportamiento real del código y plan de migración del listado mayorista PHP «stock y existencias».

---

## 1. Ubicación del reporte VB6

| Elemento | Ubicación |
|----------|-----------|
| Formulario | `administranet_vb6/Formularios/Info_Stock.frm` |
| Sub que dispara el reporte | `Lista_Disponibles_Backorder()` (línea ~15840) |
| Lógica de datos | `administranet_vb6/Modulos/Informes.bas` → `View_Lista_Disponibles_Backorder` |
| Vista MySQL creada en tiempo de ejecución | `calculo_saldos_disponibles` |
| Reporte Crystal | `stock_vista_disponible_backorder.rpt` |

El reporte VB6 recibe: intervalo de fechas (desde/hasta), depósito (o «Todos» si `id_deposito = 0`) y usa la entidad fija `"Backorder"` para armar la vista.

---

## 2. Lógica VB6 (disponible y backorder)

En `View_Lista_Disponibles_Backorder`, cuando `entidad = "Backorder"` se ejecuta:

```sql
CREATE VIEW calculo_saldos_disponibles AS
  SELECT comp_ped.id_comp_ped, comp_ped.Codigo,
         articulo.IDArt, articulo.NroCodBarra, articulo.NroCodBarraF, articulo.NombreArticulo, articulo.id_manual AS id_manual,
         stock_deposito.saldo AS saldo_actual,
         SUM(IF((comp_ped.Estado = 'En preparación' OR comp_ped.Estado = 'Preparado'), stockp.cantidad, 0)) AS cantidad_reservada,
         SUM(IF((comp_ped.Estado = 'Pendiente'), stockp.cantidad, 0)) AS cantidad_pendiente,
         SUM(IF((comp_ped.Estado = 'En remito' OR comp_ped.Estado = 'Facturado'), stockp.cantidad, 0)) AS cantidad_facturada,
         SUM(IF((comp_ped.Estado = 'En preparación' OR comp_ped.Estado = 'Preparado'), stockp.PrecioNetoxR, 0)) AS total_reservado,
         SUM(IF((comp_ped.Estado = 'Pendiente'), stockp.PrecioNetoxR, 0)) AS total_pendiente
  FROM comp_ped
  LEFT JOIN stockp ON (stockp.CodigoMovimiento = comp_ped.CodigoMovimiento)
  LEFT JOIN articulo ON (articulo.IDArt = stockp.IDArt)
  LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = articulo.IDArt)
  LEFT JOIN deposito ON (deposito.coddeposito = stock_deposito.id_deposito)
  LEFT JOIN deposito_reposicion ON (...)
  WHERE [opcional: deposito.coddeposito = id_deposito]
    AND comp_ped.Anulado = 'No'
    AND comp_ped.TipoComprobante = 'PED'
    AND stockp.Fecha BETWEEN fecha_desde AND fecha_hasta
  GROUP BY stockp.IDArt
  ORDER BY articulo.NombreArticulo
```

- **Backorder (cantidad pendiente):** `cantidad_pendiente` = suma de `stockp.cantidad` cuando `comp_ped.Estado = 'Pendiente'`.
- **Reservado:** solo estados `'En preparación'` y `'Preparado'` (no incluye `'Parcial'` en la expresión de cantidad reservada de la vista).
- **Disponible:** no se calcula en la vista; el .rpt suele usar **saldo_actual − cantidad_reservada** (mismo concepto que Synap BO).
- **Stock (saldo_actual):** `stock_deposito.saldo`; el JOIN con `stock_deposito` no agrega por depósito: si hay varios depósitos por artículo, hay varias filas antes del `GROUP BY stockp.IDArt`, por lo que `saldo_actual` en «Todos» los depósitos es **no determinístico** (MySQL puede devolver el saldo de cualquiera de ellos).
- **Filtro temporal:** solo entran renglones con **`stockp.Fecha`** en el intervalo desde/hasta.
- **Precio para pendiente/reservado:** VB6 usa **PrecioNetoxR**. El reporte BO de Synap usa **PrecioNetoxR** para importes de backorder y prorrateos.

---

## 3. Lógica Synap BO (implementación actual)

**Código fuente:** `reports/services/query_runner.py` → `_run_backorder_vs_stock_vs_facturacion` (reporte slug **`bo-stock-facturacion`**).

El docstring del método indica explícitamente: *Reservado: stockp+comp_ped (Estado En preparación/Preparado; NO Pendiente ni Parcial)*. La subconsulta `reservado_sub` coincide: **`cp_res.Estado IN ('En preparación', 'Preparado')`** (no se incluye `'Parcial'`).

### 3.1 Reglas de negocio (detalle producto en SQL principal)

- **Backorder:** `stockp` + `comp_ped` con `TipoComprobante = 'PED'`, `Estado IN ('Pendiente')` (variable `bo_estados`), `Anulado = 'No'`, renglones no anulados. **Filtro por fecha:** `sp.Fecha` entre **fecha_inicio_bo** y **fecha_fin_bo** (alineado con criterio «en el período»; ver manejo de fechas INT YYYYMMDD en el mismo método).
- **Cantidad e importe BO:** `bo_qty = SUM(sp.Cantidad)`, **`bo_importe = SUM(sp.PrecioNetoxR)`**.
- **Alcance del listado de detalle BO:** `HAVING bo_qty > 0` (solo artículos con backorder positivo en el período).
- **Stock (`stock_actual` / `stock_total` en la vista SQL):** `SUM(stock_deposito.saldo)` por `id_articulo` en subconsulta `sd`. Si el payload trae **`depositos_incluidos`**, solo esos depósitos suman al stock (`WHERE id_deposito IN (...)`). Si la lista está vacía, entran **todos** los depósitos.
- **Reservado (`stock_reservado`):** subconsulta sobre **`stockp` + `comp_ped`**, PED, estados **`En preparación`** y **`Preparado`** únicamente, cantidad  
  `COALESCE(cantidad_pendiente, Cantidad - COALESCE(cantidad_entregada, 0))` con cantidad resultante &gt; 0. **No** usa `stock_deposito.saldo_pedido_cliente`. **Sin filtro por fecha** en la subconsulta (reserva «actual»). Opcional: **clientes excluidos** en reservado (`reservado_excl_clause`), **sucursal** (`suc_res_inner`) alineados al payload.
- **Disponible (columna del detalle):**  
  **`GREATEST(0, COALESCE(sd.stock_total, 0) - COALESCE(reservado_sub.reservado, 0))`**.
- **OC pendiente:** subconsulta `stockp` + **`cuentaproveedor`** (`TipoComprobante = 'OC'`, `Estado = 'Pendiente'`). No usa `stock_deposito.saldo_pedido_proveedor`. Sirve para cobertura **CON INGRESO**.
- **Cobertura (Python sobre cada fila):** CON STOCK / CON INGRESO / SIN STOCK con prorrateo de importes desde `bo_importe`.
- **Valorización:** lista de precio 0–6 vía `lista_precio` en payload → expresión `precio_segun_lista_sql` sobre `articulo` (costo, PNOficial, Precio1V…Precio5V).
- **Exclusión de artículos tipo gasto:** `(a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')` en el WHERE del detalle BO.

### 3.2 Filtros del payload (`filters`) soportados por el BO (referencia)

Resumen de lo que lee el método (además de `base_empresa`):

| Filtro | Uso |
|--------|-----|
| Período / fechas | `_resolve_period_dates` → `fecha_inicio`, `fecha_fin` para BO; facturación/remitos pueden usar `fecha_inicio_facturacion` / `fecha_fin_facturacion` si vienen informados. |
| `sucursales` | Lista de IDs; filtra cabecera BO (`cp.CodSucursal`) y la subconsulta de reservado. |
| `punto_venta` | Puntos de venta (según lógica del bloque de facturación/remitos en el mismo método). |
| `depositos_incluidos` | Lista de IDs de depósito: limita la suma de `stock_deposito.saldo` en `sd` (si vacío, todos los depósitos). |
| `clientes_excluidos` | Parseados vía `_parse_clientes_excluidos`; excluyen clientes del BO y del reservado. |
| `lista_precio` | Entero 0–6 para columnas de precio/valorización. |

(El detalle exacto de fechas duplicadas BO vs facturación está resuelto en el método para evitar inconsistencias entre consultas; ver comentarios «CORRECCIÓN INCONSISTENCIA» en el archivo.)

---

## 4. Hallazgos: diferencias que pueden cambiar resultados (VB6 vs Synap BO)

| # | Aspecto | VB6 | Synap BO (código actual) | ¿Mismo resultado? |
|---|---------|-----|---------------------------|-------------------|
| 1 | **Filtro por fecha (backorder)** | `stockp.Fecha` en el intervalo. | `sp.Fecha` en el intervalo del reporte BO. | **Sí** en intención (período). |
| 2 | **Reservado** | Solo `'En preparación'` y `'Preparado'`. | Solo **`'En preparación'`** y **`'Preparado'`** (sin `'Parcial'`). | **Sí** frente a la vista VB6 citada arriba. |
| 3 | **Stock «Todos» depósitos** | `saldo_actual` ambiguo por JOIN sin agregación correcta por depósito. | `SUM(saldo)` por artículo (con filtro opcional `depositos_incluidos`). | **No** frente al VB6 con «Todos»; Synap es determinístico. |
| 4 | **Precio importes BO** | PrecioNetoxR. | PrecioNetoxR. | **Sí.** |
| 5 | **Alcance de filas del detalle BO** | VB6 puede listar más variedad según vista/.rpt. | Solo artículos con **`bo_qty > 0`** en el período. | **No** necesariamente (alcance distinto del listado VB6 completo). |

**Nota histórica:** versiones anteriores de este documento indicaban que Synap incluía el estado **`Parcial`** en el reservado. Eso **no coincide** con la implementación vigente en `query_runner.py` (subconsulta `reservado_sub`). Cualquier análisis antiguo que asumiera `Parcial` debe considerarse **obsoleto**.

---

## 5. Hallazgos: coincidencias

- **Origen de renglones BO:** `stockp` + `comp_ped` para PED.
- **Backorder:** cantidad asociada a pedidos en estado **Pendiente** en el período.
- **Reservado para disponible:** estados **En preparación** y **Preparado**, con cantidad pendiente explícita en renglón.
- **Disponible:** `GREATEST(0, stock − reservado)` con stock agregado desde `stock_deposito` y reservado desde `stockp`+`comp_ped`, **no** desde `saldo_pedido_cliente` del depósito.

---

## 6. Conclusión

- **Alineado:** filtro temporal del BO por `stockp.Fecha`; importes de backorder y prorrateos con **PrecioNetoxR**; reservado sin **Parcial** (igual que la parte de cantidad reservada de la vista VB6 mostrada arriba).

- **Diferencias relevantes:** agregación de stock por depósito (Synap suma de forma explícita); alcance del grid BO (`HAVING bo_qty > 0`); filtros adicionales en Synap (sucursales, depósitos incluidos, clientes excluidos, listas de precio, etc.).

- **No usar para el BO:** `stock_deposito.saldo_pedido_cliente` como sustituto del reservado calculado en la subconsulta (el informe BO fue diseñado con la lógica de renglones PED + estados).

Este documento permanece en **docs/reports/** como referencia del reporte BO y de la comparación con VB6.

---

## 7. Migración: listado «Stock y existencias» (mayorista PHP → Synap)

**Implementado** en Synap como informe operativo con slug **`stock-existencias`** (workspace de reportes, `QueryRunner` legacy). Especificación técnica: **`docs/reports/SPEC_STOCK_EXISTENCIAS.md`**.

### 7.1 Criterio de **disponible**

Mismo criterio que el informe BO: `GREATEST(0, saldo − reservado)` por artículo y depósito (`stock_deposito.saldo`), con reservado agregado por `(IDArt, CodDeposito)` desde `stockp` + `comp_ped` (PED *En preparación* / *Preparado*), sin usar `saldo_pedido_cliente`. Es un listado **instantáneo** (sin rango de fechas de backorder).

### 7.2 Cobertura de filtros respecto al PHP

| PHP (referencia) | Synap |
|------------------|--------|
| Depósito(s) | `depositos_incluidos` (tags; vacío = todos). |
| Orden | Por cabeceras de tabla en el cliente (nombre artículo, marca, rubro, subrubro). |
| Stock en cero | `incluir_stock_cero` si/no. |
| Búsqueda | Predictiva en la tabla (texto en columnas visibles; mín. 2 caracteres). |
| — | `marcas_incluidos`, `rubros_incluidos`, `subrubros_incluidos` (tags; vacío = todos). |
| — | Filtros en formulario en **dos columnas** (~50 % cada una desde `md`). |

Pendiente de producto si se restringe el listado por **permisos de depósito por usuario** como en el mayorista (`deposito_usr`).

### 7.3 Pendientes opcionales

- Integración PWA mayorista / permisos de depósito por rol.
- Tests de integración MySQL cuando haya dataset de CI.
