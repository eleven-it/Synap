# Informe: VB6 «Stock físico, cantidades disponibles y backorder» vs reporte BO Synap

**Fecha:** 2026-02-15 (actualizado 2026-02-19)  
**Objetivo:** Comparar la lógica de **disponible** y **backorder** entre el reporte de AdministraNET VB6 «Stock físico, cantidades disponibles y backorder» y el reporte BO (Backorder vs Stock vs Facturación) de Synap. Referencia para alineación y opciones de “modo VB6”.

---

## 1. Ubicación del reporte VB6

| Elemento | Ubicación |
|----------|-----------|
| Formulario | `administranet_vb6/Formularios/Info_Stock.frm` |
| Sub que dispara el reporte | `Lista_Disponibles_Backorder()` (línea ~15840) |
| Lógica de datos | `administranet_vb6/Modulos/Informes.bas` → `View_Lista_Disponibles_Backorder` |
| Vista MySQL creada en tiempo de ejecución | `calculo_saldos_disponibles` |
| Reporte Crystal | `stock_vista_disponible_backorder.rpt` |

El reporte VB6 recibe: intervalo de fechas (desde/hasta), depósito (o “Todos” si `id_deposito = 0`) y usa la entidad fija `"Backorder"` para armar la vista.

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
- **Reservado:** solo estados `'En preparación'` y `'Preparado'` (no incluye `'Parcial'`).
- **Disponible:** no se calcula en la vista; el .rpt seguramente usa **saldo_actual − cantidad_reservada** (mismo concepto que Synap).
- **Stock (saldo_actual):** `stock_deposito.saldo`; el JOIN con `stock_deposito` no agrega por depósito: si hay varios depósitos por artículo, hay varias filas antes del `GROUP BY stockp.IDArt`, por lo que `saldo_actual` en “Todos” los depósitos es **no determinístico** (MySQL puede devolver el saldo de cualquiera de ellos).
- **Filtro temporal:** solo entran renglones con **`stockp.Fecha`** en el intervalo desde/hasta. Es un reporte “en el período” (movimientos PED con fecha en ese rango).
- **Precio para pendiente/reservado:** VB6 usa **PrecioNetoxR**. El reporte BO de Synap también usa **PrecioNetoxR** para importes de backorder (alineado desde 2026-02-15).

---

## 3. Lógica Synap BO (disponible y backorder)

En `reports/services/query_runner.py`, método `_run_backorder_vs_stock_vs_facturacion` (reporte slug `bo-stock-facturacion`):

- **Backorder:** renglones de **stockp** con **comp_ped** `TipoComprobante = 'PED'`, `Estado IN ('Pendiente')`, `Anulado = 'No'`. **Filtro por fecha:** solo renglones con **`sp.Fecha >= fecha_inicio AND sp.Fecha <= fecha_fin`** (alineado con VB6: backorder “en el período”). Opcional: **clientes excluidos** (`cp.Codigo NOT IN (...)`).
- **Cantidad e importe BO:** `bo_qty = SUM(sp.Cantidad)`, **`bo_importe = SUM(sp.PrecioNetoxR)`** (alineado con VB6).
- **Alcance:** solo artículos con **`HAVING bo_qty > 0`** (artículos con backorder en el período).
- **Stock (stock_actual):** `SUM(stock_deposito.saldo)` por `id_articulo` (subconsulta). Opcional: **depósitos excluidos** (`id_deposito NOT IN (...)`). Comportamiento determinístico.
- **Reservado (stock_reservado):** **stockp** + **comp_ped** con `TipoComprobante = 'PED'`, `Estado IN ('En preparación', 'Preparado', 'Parcial')` (incluye **Parcial**), `Anulado = 'No'`. Cantidad: `COALESCE(cantidad_pendiente, Cantidad - cantidad_entregada)`. **Sin filtro por fecha** en la subconsulta (reserva actual). Opcional: mismos clientes excluidos que en BO.
- **Disponible:** `GREATEST(0, stock_total - reservado)`.
- **OC pendiente:** calculado desde **stockp** + **cuentaproveedor** (`TipoComprobante = 'OC'`, `Estado = 'Pendiente'`). No se usa `stock_deposito.saldo_pedido_proveedor`. Sin filtro por fecha. Se usa para la cobertura “CON INGRESO” (primero cubre faltante de reservado, el resto cubre BO).
- **Cobertura:** CON STOCK (parte del BO cubierta por disponible), CON INGRESO (parte cubierta por OC pendiente restante), SIN STOCK (resto no cubierto). Los importes se prorratean desde `bo_importe` (PrecioNetoxR).
- **Precio:** **PrecioNetoxR** para `bo_importe` y todos los importes derivados (con_stock_importe, con_ingreso_importe, sin_stock_importe).

---

## 4. Hallazgos: diferencias que pueden cambiar resultados

| # | Aspecto | VB6 | Synap BO | ¿Mismo resultado? |
|---|---------|-----|----------|--------------------|
| 1 | **Filtro por fecha** | Solo renglones con **stockp.Fecha** en el intervalo desde/hasta. | **Sí:** solo renglones con **sp.Fecha** en el intervalo del reporte (fecha_inicio, fecha_fin). | **Sí.** Ambos: backorder “en el período”. |
| 2 | **Reservado** | Solo `'En preparación'` y `'Preparado'`. | `'En preparación'`, `'Preparado'` y **`'Parcial'`**. | **No.** Synap incluye Parcial; VB6 no. Afecta reservado y por tanto **disponible**. |
| 3 | **Stock / disponible por depósito** | Con “Todos” los depósitos, `saldo_actual` viene de un JOIN que puede dar varias filas por artículo; `GROUP BY stockp.IDArt` deja un solo valor por artículo pero **no definido** (cualquier depósito). | Stock = `SUM(saldo)` de todos los depósitos (o menos los excluidos). Determinístico. | **No.** VB6 con “Todos” es ambiguo; Synap suma todos los depósitos. |
| 4 | **Precio para importes** | **PrecioNetoxR** (total_reservado, total_pendiente). | **PrecioNetoxR** (bo_importe y prorrateos: con_stock_importe, con_ingreso_importe, sin_stock_importe). | **Sí.** Alineado desde 2026-02-15. |
| 5 | **Alcance de artículos listados** | Incluye **todos** los artículos con al menos un renglón en stockp (PED) cuya **fecha** está en el rango (cualquier estado). Incluye artículos con cantidad_pendiente = 0. | Solo artículos con **backorder > 0** (estado Pendiente) en el período (`HAVING bo_qty > 0`). | **No.** VB6 puede listar más filas (por período, cualquier estado); Synap solo artículos con pendiente en el período. |

---

## 5. Hallazgos: coincidencias

- **Origen de renglones:** Ambos usan **stockp** + **comp_ped** para pedidos cliente (PED).
- **Backorder (concepto):** En ambos, el “backorder” es la cantidad asociada a pedidos en estado **Pendiente**.
- **Filtro por fecha:** Ambos restringen el backorder por **stockp.Fecha** en el intervalo del reporte (“en el período”).
- **Precio:** Ambos usan **PrecioNetoxR** para importes de backorder (y reservado en VB6).
- **Disponible (concepto):** En ambos, disponible = stock (saldo) menos reservado; la fórmula Synap `GREATEST(0, stock - reservado)` es coherente con lo que el .rpt VB6 puede calcular.
- **Depósito único en VB6:** Si en VB6 se elige **un** depósito, `saldo_actual` es el de ese depósito; el concepto es comparable a “stock de ese depósito”. Synap no filtra por depósito en el BO pero permite **depósitos excluidos** (no suman al stock).

---

## 6. Conclusión

- **Alineado con VB6 (desde 2026-02-15):** (1) **Filtro por fecha:** el backorder en Synap se filtra por `stockp.Fecha` en el intervalo del reporte (como VB6). (2) **Precio:** `bo_importe` y todos los importes derivados usan **PrecioNetoxR** (como VB6).

- **Diferencias que pueden cambiar resultados:**
  1. **Reservado:** Synap incluye estado `Parcial`; VB6 solo “En preparación” y “Preparado”. Afecta reservado y disponible.
  2. **Stock con “Todos” los depósitos:** VB6 no determina un único saldo por artículo (valor no definido); Synap suma todos los depósitos (determinístico). Opcional en Synap: excluir depósitos.
  3. **Alcance de filas:** VB6 lista todos los artículos con movimiento PED en el período (cualquier estado); Synap lista solo artículos con backorder > 0 en el período (`HAVING bo_qty > 0`).

- **Extras en Synap:** filtros opcionales **clientes excluidos** (BO y reservado) y **depósitos excluidos** (stock); **OC pendiente** calculado desde stockp + cuentaproveedor (no `stock_deposito.saldo_pedido_proveedor`); cobertura **CON STOCK / CON INGRESO / SIN STOCK** (OC cubre primero faltante de reservado, luego BO).

Este documento queda en **docs/reports/** como referencia para futuras alineaciones o opciones de “modo VB6” en el reporte BO.
